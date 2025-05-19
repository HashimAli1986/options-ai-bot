import requests
import pandas as pd
import time
from datetime import datetime
from flask import Flask
from threading import Thread

app = Flask('')

@app.route('/')
def home():
    return "المحلل الذكي للأسهم الأمريكية يعمل بنجاح"

def run():
    app.run(host='0.0.0.0', port=8080)

def keep_alive():
    t = Thread(target=run)
    t.start()

# التوكن والقناة الجديدة
BOT_TOKEN = "7560392852:AAGNoxFGThp04qMKTGEiIJN2eY_cahTv3E8"
CHANNEL_ID = "@hashimAlico"

def send_telegram_message(text):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    data = {"chat_id": CHANNEL_ID, "text": text}
    try:
        requests.post(url, data=data)
    except Exception as e:
        print(f"Telegram Error: {e}")

# الشركات المراد تحليلها
stocks = {
    "MSTR": {},
    "APP": {},
    "AVGO": {},
    "SMCI": {},
    "GS": {},
    "MU": {},
    "META": {},
    "APPL": {},
    "COIN": {},
    "TSLA": {},
    "LLY": {},
}

def fetch_daily_data(symbol):
    try:
        url = f"https://query1.finance.yahoo.com/v8/finance/chart/{symbol}?range=1y&interval=1d"
        headers = {"User-Agent": "Mozilla/5.0"}
        response = requests.get(url, headers=headers)
        data = response.json()["chart"]["result"][0]
        df = pd.DataFrame(data["indicators"]["quote"][0])
        df["Date"] = pd.to_datetime(data["timestamp"], unit="s")
        df.set_index("Date", inplace=True)
        return df.dropna().tail(1000)
    except Exception as e:
        print(f"Fetch error for {symbol}: {e}")
        return None

def calculate_indicators(df):
    df["EMA9"] = df["Close"].ewm(span=9).mean()
    df["EMA21"] = df["Close"].ewm(span=21).mean()
    df["RSI"] = 100 - (100 / (1 + (df["Close"].diff().where(lambda x: x > 0, 0).rolling(14).mean() / 
                                   df["Close"].diff().where(lambda x: x < 0, 0).abs().rolling(14).mean())))
    return df

def evaluate_stock(symbol, df):
    last = df.iloc[-1]
    prev = df.iloc[-2]
    signal_strength = 0
    if prev["EMA9"] < prev["EMA21"] and last["EMA9"] > last["EMA21"] and last["RSI"] < 40:
        signal_strength = 1
    if prev["EMA9"] > prev["EMA21"] and last["EMA9"] < last["EMA21"] and last["RSI"] > 60:
        signal_strength = 1
    return signal_strength

def pick_best_stock():
    best = None
    for symbol in stocks:
        df = fetch_daily_data(symbol)
        if df is None: continue
        df = calculate_indicators(df)
        strength = evaluate_stock(symbol, df)
        if strength:
            best = (symbol, df)
            break
    return best

def send_option_trade(symbol, df):
    last_price = df["Close"].iloc[-1]
    strike_price = round(last_price * 1.02, 2)
    option_price = 2.5
    target_price = option_price * 3  # ربح 200%

    msg = (
        f"توصية اليوم:\n"
        f"الرمز: {symbol}\n"
        f"نوع الصفقة: {'Call' if df['EMA9'].iloc[-1] > df['EMA21'].iloc[-1] else 'Put'}\n"
        f"Strike: {strike_price}\n"
        f"سعر العقد: ${option_price:.2f}\n"
        f"الهدف: ${target_price:.2f} (200%)\n"
        f"تاريخ: {datetime.now().strftime('%Y-%m-%d')}"
    )
    send_telegram_message(msg)

def main_loop():
    sent = False
    while True:
        now = datetime.utcnow()
        if now.hour == 13 and not sent:  # 16 بتوقيت السعودية (افتتاح السوق)
            result = pick_best_stock()
            if result:
                symbol, df = result
                send_option_trade(symbol, df)
                sent = True
        elif now.hour > 13:
            sent = False
        time.sleep(900)

if __name__ == "__main__":
    keep_alive()
    send_telegram_message("✅ تم تشغيل بوت توصيات الخيارات للأسهم الأمريكية.")
    main_loop()
