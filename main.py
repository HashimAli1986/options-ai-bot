import requests
import pandas as pd
import time
from datetime import datetime
from flask import Flask
from threading import Thread

app = Flask('')

@app.route('/')
def home():
    return "📈 محلل الأسهم يعمل بنجاح!"

def run():
    app.run(host='0.0.0.0', port=8080)

def keep_alive():
    t = Thread(target=run)
    t.start()

# التوكن والقناة
BOT_TOKEN = "7560392852:AAGNoxFGThp04qMKTGEiIJN2eY_cahTv3E8"
CHANNEL_ID = "@hashimAlico"

def send_telegram_message(text):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    data = {"chat_id": CHANNEL_ID, "text": text}
    try:
        requests.post(url, data=data)
    except Exception as e:
        print("Telegram error:", e)

# الشركات المستهدفة
companies = {
    "MSTR": "MSTR",
    "APP": "APP",
    "AVGO": "AVGO",
    "SMCI": "SMCI",
    "GS": "GS",
    "MU": "MU",
    "META": "META",
    "APPL": "AAPL",
    "COIN": "COIN",
    "TSLA": "TSLA",
    "LLY": "LLY"
}

active_trade = None

def fetch_daily_data(symbol):
    try:
        url = f"https://query1.finance.yahoo.com/v8/finance/chart/{symbol}?range=2y&interval=1d"
        headers = {"User-Agent": "Mozilla/5.0"}
        response = requests.get(url, headers=headers)
        data = response.json()
        result = data["chart"]["result"][0]
        timestamps = result["timestamp"]
        prices = result["indicators"]["quote"][0]
        df = pd.DataFrame(prices)
        df["Date"] = pd.to_datetime(timestamps, unit="s")
        df.set_index("Date", inplace=True)
        return df.dropna().tail(1000)
    except Exception as e:
        print(f"Data fetch error for {symbol}:", e)
        return None

def calculate_indicators(df):
    df["EMA9"] = df["Close"].ewm(span=9).mean()
    df["EMA21"] = df["Close"].ewm(span=21).mean()
    delta = df["Close"].diff()
    gain = delta.where(delta > 0, 0).rolling(14).mean()
    loss = -delta.where(delta < 0, 0).rolling(14).mean()
    rs = gain / loss
    df["RSI"] = 100 - (100 / (1 + rs))
    return df

def generate_option_recommendation(symbol, df):
    last = df.iloc[-1]
    prev = df.iloc[-2]
    direction = None
    if prev["EMA9"] < prev["EMA21"] and last["EMA9"] > last["EMA21"] and last["RSI"] < 35:
        direction = "CALL"
    elif prev["EMA9"] > prev["EMA21"] and last["EMA9"] < last["EMA21"] and last["RSI"] > 65:
        direction = "PUT"

    if direction:
        price = round(last["Close"], 2)
        strike_price = round(price * 1.03 if direction == "CALL" else price * 0.97, 2)
        contract_price = 2.5
        target_price = contract_price * 3

        return {
            "symbol": symbol,
            "direction": direction,
            "strike": strike_price,
            "entry": contract_price,
            "target": target_price,
            "last_price": price,
            "RSI": round(last["RSI"], 2)
        }
    return None

def check_market_open():
    now = datetime.utcnow()
    return now.hour == 13 and now.minute < 5

def send_recommendation_once():
    global active_trade
    if active_trade:
        return  # لا ترسل توصية جديدة إذا لم تنتهِ السابقة

    for symbol in companies.values():
        df = fetch_daily_data(symbol)
        if df is not None:
            df = calculate_indicators(df)
            recommendation = generate_option_recommendation(symbol, df)
            if recommendation:
                active_trade = recommendation
                msg = (
                    f"توصية اليوم: {recommendation['symbol']}\n"
                    f"نوع العقد: {recommendation['direction']}\n"
                    f"Strike Price: {recommendation['strike']}\n"
                    f"سعر العقد: {recommendation['entry']}$ → الهدف: {recommendation['target']}$ (ربح 200%)\n"
                    f"سعر السهم الحالي: {recommendation['last_price']}$\n"
                    f"RSI: {recommendation['RSI']}\n"
                    f"تاريخ: {datetime.now().strftime('%Y-%m-%d %H:%M')}"
                )
                send_telegram_message(msg)
                break

def monitor_active_trade():
    global active_trade
    if active_trade:
        df = fetch_daily_data(active_trade["symbol"])
        if df is not None:
            last_price = df.iloc[-1]["Close"]
            send_telegram_message(
                f"متابعة {active_trade['symbol']}:\n"
                f"العقد: {active_trade['direction']} | Strike: {active_trade['strike']}\n"
                f"الهدف: {active_trade['target']}$ | لا يزال مفعلاً\n"
                f"سعر السهم الحالي: {round(last_price, 2)}$"
            )

def main_loop():
    sent_today = False
    while True:
        now = datetime.utcnow()
        if check_market_open() and not sent_today:
            send_recommendation_once()
            sent_today = True

        if now.hour == 0 and now.minute == 0:
            sent_today = False  # إعادة السماح للتوصية لليوم الجديد

        if active_trade:
            monitor_active_trade()

        time.sleep(900)  # كل 15 دقيقة

if __name__ == "__main__":
    keep_alive()
    send_telegram_message("✅ تم تشغيل محلل الخيارات للأسهم الأمريكية بنجاح.")
    main_loop()
