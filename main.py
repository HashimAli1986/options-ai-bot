import requests
import pandas as pd
import time
from datetime import datetime
from flask import Flask
from threading import Thread

app = Flask(__name__)

@app.route('/')
def home():
    return "سكربت توصيات أسبوعية يعمل بنجاح"

def run():
    app.run(host='0.0.0.0', port=8080)

def keep_alive():
    t = Thread(target=run)
    t.start()

BOT_TOKEN = "7560392852:AAGNoxFGThp04qMKTGEiIJN2eY_cahTv3E8"
CHANNEL_ID = "@hashimAlico"

def send_telegram_message(text):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    data = {"chat_id": CHANNEL_ID, "text": text}
    try:
        requests.post(url, data=data)
    except Exception as e:
        print(f"Telegram Error: {e}")

assets = {
    "MSTR": "MicroStrategy",
    "APP": "AppLovin",
    "AVGO": "Broadcom",
    "SMCI": "Super Micro Computer",
    "GS": "Goldman Sachs",
    "MU": "Micron Technology",
    "META": "Meta Platforms",
    "AAPL": "Apple",
    "COIN": "Coinbase",
    "TSLA": "Tesla",
    "LLY": "Eli Lilly"
}

def fetch_weekly_data(symbol):
    try:
        url = f"https://query1.finance.yahoo.com/v8/finance/chart/{symbol}?range=5y&interval=1wk"
        headers = {"User-Agent": "Mozilla/5.0"}
        response = requests.get(url, headers=headers)
        data = response.json()
        result = data["chart"]["result"][0]
        timestamps = result["timestamp"]
        prices = result["indicators"]["quote"][0]
        df = pd.DataFrame({
            "Open": prices["open"],
            "High": prices["high"],
            "Low": prices["low"],
            "Close": prices["close"]
        })
        df["Date"] = pd.to_datetime(timestamps, unit="s")
        df.set_index("Date", inplace=True)
        return df.dropna().iloc[-100:]
    except Exception as e:
        print(f"fetch_data error ({symbol}): {e}")
        return None

def calculate_indicators(df):
    df["EMA9"] = df["Close"].ewm(span=9).mean()
    df["EMA21"] = df["Close"].ewm(span=21).mean()
    delta = df["Close"].diff()
    gain = delta.clip(lower=0).rolling(14).mean()
    loss = -delta.clip(upper=0).rolling(14).mean()
    rs = gain / loss
    df["RSI"] = 100 - (100 / (1 + rs))
    df["MACD"] = df["Close"].ewm(span=12).mean() - df["Close"].ewm(span=26).mean()
    df["Signal"] = df["MACD"].ewm(span=9).mean()
    return df

def is_strong_breakout(df):
    last = df.iloc[-1]
    prev = df.iloc[-2]
    rsi = last["RSI"]
    macd_cross = last["MACD"] > last["Signal"] and prev["MACD"] < prev["Signal"]
    up_breakout = last["Close"] > prev["High"] and rsi < 70 and macd_cross
    down_breakout = last["Close"] < prev["Low"] and rsi > 30 and not macd_cross
    return up_breakout, down_breakout

def analyze_and_send():
    best_opportunity = None
    msg = f"تحديث الساعة {datetime.utcnow().strftime('%H:%M')} UTC – تحليل أسبوعي\n\n"

    for symbol, name in assets.items():
        df = fetch_weekly_data(symbol)
        if df is None or len(df) < 20:
            msg += f"{name} ({symbol}): البيانات غير متوفرة\n\n"
            continue

        df = calculate_indicators(df)
        last = df.iloc[-1]
        up, down = is_strong_breakout(df)
        price = last["Close"]
        target = price * 1.05 if up else price * 0.95
        stop = price * 0.97 if up else price * 1.03
        if up or down:
            best_opportunity = {
                "name": name,
                "symbol": symbol,
                "price": price,
                "type": "CALL" if up else "PUT",
                "strike": round(price),
                "target": round(target, 2),
                "stop": round(stop, 2),
                "rsi": round(last["RSI"], 2)
            }
        msg += f"{name} ({symbol}):\nالسعر: {price:.2f}\nRSI: {last['RSI']:.2f}\nMACD: {last['MACD']:.2f} / {last['Signal']:.2f}\n"
        msg += f"Breakout: {'صعود قوي' if up else 'هبوط قوي' if down else 'لا يوجد'}\n\n"

    if best_opportunity:
        o = best_opportunity
        msg += f"""🔥 **توصية خيارات – {o['name']} ({o['symbol']})**

نوع العقد: {o['type']}  
السعر الحالي: {o['price']:.2f}  
Strike: {o['strike']}  
الهدف: {o['target']}  
الوقف: {o['stop']}  
RSI: {o['rsi']}"""

    send_telegram_message(msg.strip())

def hourly_loop():
    last_sent_hour = -1
    while True:
        now = datetime.utcnow()
        if now.hour != last_sent_hour and now.minute >= 0:
            last_sent_hour = now.hour
            analyze_and_send()
        time.sleep(30)

if __name__ == "__main__":
    keep_alive()
    send_telegram_message("✅ تم تشغيل سكربت توصيات الخيارات الأسبوعية باحتراف.")
    Thread(target=hourly_loop).start()
