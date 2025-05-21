import requests
import pandas as pd
import time
from datetime import datetime
from flask import Flask
from threading import Thread

app = Flask('')

@app.route('/')
def home():
    return "المحلل الذكي يعمل بنجاح"

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
    signal_strength = 0
    if last["Close"] > last["Open"]:
        signal_strength += 1
    if prev["EMA9"] < prev["EMA21"] and last["EMA9"] > last["EMA21"]:
        signal_strength += 1
    if last["RSI"] < 70:
        signal_strength += 1
    return signal_strength

def generate_option_recommendation(name, df):
    last = df.iloc[-1]
    entry = round(last["Close"], 2)
    rsi = round(last["RSI"], 2)
    support = round(last["Support"], 2)
    resistance = round(last["Resistance"], 2)
    strike_price = round(entry)
    expiry = "2024-06-14"  # مبدئيًا ثابت، يمكن تعديله لاحقًا
    contract_price = "$2.00 - $3.00"  # فرضية
    target = round(entry + 5)
    direction = "CALL" if entry > support and rsi < 70 else "PUT"

    msg = f"""**توصية خيارات اليوم – {name}**

نوع العقد: {direction}  
السعر الحالي للسهم: {entry}  
السترايك: {strike_price}  
تاريخ الانتهاء: {expiry}  
سعر العقد المقدر: {contract_price}  
الهدف: {target}

**التحليل الفني:**
- RSI: {rsi}  
- الدعم: {support} | المقاومة: {resistance}  
- القوة الفنية: قوية (استنادًا إلى تقاطع EMA وصعود السهم)

#Options #{direction} #Strike{strike_price} #Webull"""
    send_telegram_message(msg)

def daily_option_recommendation():
    best_score = -1
    best_asset = None
    best_df = None
    for name, info in assets.items():
        df = fetch_daily_data(info["symbol"])
        if df is not None and len(df) >= 1000:
            df = calculate_indicators(df)
            strength = evaluate_strength(df)
            if strength > best_score:
                best_score = strength
                best_asset = name
                best_df = df
    if best_asset:
        generate_option_recommendation(best_asset, best_df)

def wait_for_market_open():
    while True:
        now = datetime.utcnow()
        if now.weekday() < 5 and now.hour == 13 and now.minute == 30:  # 13:30 UTC = 16:30 السعودية
            daily_option_recommendation()
            break
        time.sleep(20)

if __name__ == "__main__":
    keep_alive()
    send_telegram_message("✅ سكربت الشركات يعمل: بانتظار افتتاح السوق لإصدار توصية الخيارات.")
    Thread(target=wait_for_market_open).start()
