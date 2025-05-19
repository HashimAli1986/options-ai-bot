import requests
import pandas as pd
import time
from datetime import datetime
from flask import Flask
from threading import Thread

app = Flask('')

@app.route('/')
def home():
    return "بوت توصيات الخيارات يعمل بنجاح."

def run():
    app.run(host='0.0.0.0', port=8080)

def keep_alive():
    t = Thread(target=run)
    t.start()

# إعداد التوكن والقناة
BOT_TOKEN = "7560392852:AAGNoxFGThp04qMKTGEiIJN2eY_cahTv3E8"
CHANNEL_ID = "@hashimAlico"

def send_telegram(text):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    data = {"chat_id": CHANNEL_ID, "text": text}
    try:
        requests.post(url, data=data)
    except Exception as e:
        print(f"Telegram Error: {e}")

companies = ["MSTR", "APP", "AVGO", "SMCI", "GS", "MU", "META", "AAPL", "COIN", "TSLA", "LLY"]
active_trade = None
last_signal_time = None

def fetch_data(symbol):
    try:
        url = f"https://query1.finance.yahoo.com/v8/finance/chart/{symbol}?range=1000d&interval=1d"
        headers = {"User-Agent": "Mozilla/5.0"}
        r = requests.get(url, headers=headers)
        data = r.json()
        result = data["chart"]["result"][0]
        df = pd.DataFrame(result["indicators"]["quote"][0])
        df["Date"] = pd.to_datetime(result["timestamp"], unit="s")
        df.set_index("Date", inplace=True)
        return df.dropna()
    except Exception as e:
        print(f"fetch_data error for {symbol}: {e}")
        return None

def analyze(df):
    df["EMA9"] = df["Close"].ewm(span=9).mean()
    df["EMA21"] = df["Close"].ewm(span=21).mean()
    delta = df["Close"].diff()
    gain = delta.where(delta > 0, 0).rolling(14).mean()
    loss = -delta.where(delta < 0, 0).rolling(14).mean()
    rs = gain / loss
    df["RSI"] = 100 - (100 / (1 + rs))
    return df

def choose_best_company():
    for symbol in companies:
        df = fetch_data(symbol)
        if df is not None and len(df) > 200:
            df = analyze(df)
            last = df.iloc[-1]
            prev = df.iloc[-2]
            if last["RSI"] < 35 and last["EMA9"] > last["EMA21"] and prev["EMA9"] < prev["EMA21"]:
                return symbol, "CALL", last["Close"]
            elif last["RSI"] > 65 and last["EMA9"] < last["EMA21"] and prev["EMA9"] > prev["EMA21"]:
                return symbol, "PUT", last["Close"]
    return None, None, None

def generate_option_recommendation():
    global active_trade, last_signal_time
    if active_trade:
        return
    symbol, direction, price = choose_best_company()
    if symbol:
        entry_price = 2.5
        target_price = entry_price * 3
        active_trade = {
            "symbol": symbol,
            "direction": direction,
            "entry": entry_price,
            "target": target_price,
            "strike_price": price,
            "start_time": datetime.utcnow()
        }
        msg = (
            f"توصية خيارات يومية:\n"
            f"الشركة: {symbol}\n"
            f"الاتجاه: {direction}\n"
            f"سعر العقد: ${entry_price:.2f} → الهدف: ${target_price:.2f} (ربح 200%)\n"
            f"Strike Price: {price:.2f}\n"
            f"الوقت: {datetime.utcnow().strftime('%Y-%m-%d %H:%M')} UTC"
        )
        send_telegram(msg)
        last_signal_time = datetime.utcnow()

def follow_up():
    global active_trade
    if active_trade:
        elapsed = (datetime.utcnow() - active_trade["start_time"]).total_seconds() / 60
        msg = (
            f"متابعة توصية {active_trade['symbol']}:\n"
            f"الاتجاه: {active_trade['direction']} | الهدف: ${active_trade['target']:.2f}\n"
            f"مرت {int(elapsed)} دقيقة على التوصية.\n"
            f"ستستمر حتى تحقق الهدف."
        )
        send_telegram(msg)

def is_market_open():
    now = datetime.utcnow()
    return now.weekday() < 5 and 13 <= now.hour < 20  # من 4 مساءً إلى 11 مساءً بتوقيت السعودية

def main_loop():
    last_follow_up = time.time()
    while True:
        now = datetime.utcnow()
        if is_market_open() and not active_trade:
            generate_option_recommendation()

        if active_trade and time.time() - last_follow_up >= 900:  # كل 15 دقيقة
            follow_up()
            last_follow_up = time.time()

        time.sleep(60)

if __name__ == "__main__":
    keep_alive()
    now = datetime.utcnow().strftime('%Y-%m-%d %H:%M')
    companies_list = ', '.join(companies)
    send_telegram(
        f"✅ تم تشغيل بوت توصيات الخيارات للأسهم الأمريكية.\n"
        f"الشركات المستهدفة: {companies_list}\n"
        f"الوقت الحالي: {now} UTC\n"
        f"سيتم إصدار توصية إلزامية لشركة واحدة عند افتتاح السوق الأمريكي."
    )
    main_loop()
