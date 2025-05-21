import requests
import pandas as pd
import time
from datetime import datetime
from flask import Flask
from threading import Thread

app = Flask('')

@app.route('/')
def home():
    return "سكربت الشركات يعمل بنجاح"

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
    "MicroStrategy (MSTR)": {"symbol": "MSTR"},
    "AppLovin (APP)": {"symbol": "APP"},
    "Broadcom (AVGO)": {"symbol": "AVGO"},
    "Super Micro Computer (SMCI)": {"symbol": "SMCI"},
    "Goldman Sachs (GS)": {"symbol": "GS"},
    "Micron Technology (MU)": {"symbol": "MU"},
    "Meta Platforms (META)": {"symbol": "META"},
    "Apple (AAPL)": {"symbol": "AAPL"},
    "Coinbase (COIN)": {"symbol": "COIN"},
    "Tesla (TSLA)": {"symbol": "TSLA"},
    "Eli Lilly (LLY)": {"symbol": "LLY"}
}

def fetch_daily_data(symbol):
    try:
        url = f"https://query1.finance.yahoo.com/v8/finance/chart/{symbol}?range=5y&interval=1d"
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
        return df.dropna().iloc[-1000:]
    except Exception as e:
        print(f"fetch_data error ({symbol}): {e}")
        return None

def calculate_indicators(df):
    df["EMA9"] = df["Close"].ewm(span=9).mean()
    df["EMA21"] = df["Close"].ewm(span=21).mean()
    delta = df["Close"].diff()
    gain = delta.where(delta > 0, 0).rolling(14).mean()
    loss = -delta.where(delta < 0, 0).rolling(14).mean()
    rs = gain / loss
    df["RSI"] = 100 - (100 / (1 + rs))
    df["Support"] = df["Low"].rolling(50).min()
    df["Resistance"] = df["High"].rolling(50).max()
    return df

def evaluate_strength(df):
    last = df.iloc[-1]
    prev = df.iloc[-2]
    score = 0
    if last["Close"] > last["Open"]:
        score += 1
    if prev["EMA9"] < prev["EMA21"] and last["EMA9"] > last["EMA21"]:
        score += 1
    if last["RSI"] < 70:
        score += 1
    return score

def analyze_asset(name, df):
    last = df.iloc[-1]
    price = last["Close"]
    direction = "صاعدة" if last["Close"] > last["Open"] else "هابطة"
    ema_cross = "صعود" if df["EMA9"].iloc[-2] < df["EMA21"].iloc[-2] and df["EMA9"].iloc[-1] > df["EMA21"].iloc[-1] else "هبوط" if df["EMA9"].iloc[-2] > df["EMA21"].iloc[-2] and df["EMA9"].iloc[-1] < df["EMA21"].iloc[-1] else "جانبي"
    rsi = last["RSI"]
    rsi_zone = "تشبع بيع" if rsi < 30 else "تشبع شراء" if rsi > 70 else "محايد"
    support = last["Support"]
    resistance = last["Resistance"]

    return (
        f"{name}:\n"
        f"السعر الحالي: {price:.2f}\n"
        f"الاتجاه المتوقع: {direction}\n"
        f"تقاطع EMA: {ema_cross}\n"
        f"RSI: {rsi:.2f} ({rsi_zone})\n"
        f"الدعم: {support:.2f} | المقاومة: {resistance:.2f}\n"
    )

def generate_option_recommendation(name, df):
    last = df.iloc[-1]
    price = round(last["Close"], 2)
    rsi = round(last["RSI"], 2)
    support = round(last["Support"], 2)
    resistance = round(last["Resistance"], 2)
    strike = round(price)
    expiry = "2024-06-14"
    contract_range = "$2.00 - $3.00"
    target = round(price + 5)
    option_type = "CALL" if price > support and rsi < 70 else "PUT"

    msg = f"""**توصية خيارات – {name}**

نوع العقد: {option_type}  
السعر الحالي للسهم: {price}  
السترايك: {strike}  
تاريخ الانتهاء: {expiry}  
سعر العقد المتوقع: {contract_range}  
الهدف: {target}

تحليل فني:
- RSI: {rsi}
- الدعم: {support} | المقاومة: {resistance}
- القوة: قوية (حسب الاتجاه والمؤشرات)

#Options #{option_type} #Strike{strike} #Webull
"""
    send_telegram_message(msg)

def analyze_and_send():
    best_score = -1
    best_asset = None
    best_df = None
    report = f"تحديث الساعة {datetime.utcnow().strftime('%H:%M')} UTC\n\n"
    for name, info in assets.items():
        df = fetch_daily_data(info["symbol"])
        if df is not None and len(df) >= 1000:
            df = calculate_indicators(df)
            strength = evaluate_strength(df)
            report += analyze_asset(name, df) + "\n"
            if strength > best_score:
                best_score = strength
                best_asset = name
                best_df = df
        else:
            report += f"{name}: البيانات غير متوفرة\n\n"
    send_telegram_message(report)
    if best_asset:
        generate_option_recommendation(best_asset, best_df)

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
    send_telegram_message("✅ تم تشغيل سكربت الشركات: توصية خيارات كل ساعة + أقوى شركة.")
    Thread(target=hourly_loop).start()
