import requests
import pandas as pd
import time
from datetime import datetime, time
from flask import Flask
from threading import Thread
from pytz import timezone

app = Flask('')

@app.route('/')
def home():
    return "✅ سكربت توصيات الأسهم الأمريكية يعمل بنجاح"

def run():
    app.run(host='0.0.0.0', port=8080)

def keep_alive():
    t = Thread(target=run)
    t.start()

# إعدادات البوت
BOT_TOKEN = "7560392852:AAGNoxFGThp04qMKTGEiIJN2eY_cahTv3E8"
CHANNEL_ID = "@hashimAlico"

def send_telegram_message(text):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    data = {"chat_id": CHANNEL_ID, "text": text, "parse_mode": "Markdown"}
    try:
        requests.post(url, data=data)
    except Exception as e:
        print(f"Telegram Error: {e}")

# قائمة الشركات
companies = [
    "MSTR", "APP", "AVGO", "SMCI", "GS",
    "MU", "META", "AAPL", "COIN", "TSLA", "LLY"
]

current_trade = None
ny_tz = timezone('America/New_York')

# ---- وظائف جلب البيانات ----
def fetch_price(symbol):
    try:
        url = f"https://query1.finance.yahoo.com/v8/finance/chart/{symbol}?interval=1m"
        response = requests.get(url, headers={"User-Agent": "Mozilla/5.0"})
        data = response.json()
        return round(data["chart"]["result"][0]["indicators"]["quote"][0]["close"][-1], 2)
    except:
        return None

def fetch_historical_data(symbol):
    try:
        url = f"https://query1.finance.yahoo.com/v8/finance/chart/{symbol}?range=2y&interval=1d"
        data = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}).json()
        closes = data["chart"]["result"][0]["indicators"]["quote"][0]["close"]
        timestamps = data["chart"]["result"][0]["timestamp"]
        return pd.DataFrame({"close": closes, "date": pd.to_datetime(timestamps, unit='s')}).dropna()
    except:
        return None

# ---- التحليل الفني ----
def calculate_ema(series, span):
    return series.ewm(span=span, adjust=False).mean()

def calculate_rsi(series, period=14):
    delta = series.diff()
    gain = delta.where(delta > 0, 0).rolling(window=period).mean()
    loss = (-delta).where(delta < 0, 0).rolling(window=period).mean()
    rs = gain / loss
    return 100 - (100 / (1 + rs))

# ---- معالجة الخيارات ----
def fetch_option_chain(symbol):
    try:
        url = f"https://query1.finance.yahoo.com/v7/finance/options/{symbol}"
        data = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}).json()
        expiration_dates = data["optionChain"]["result"][0]["expirationDates"]
        calls = data["optionChain"]["result"][0]["options"][0]["calls"]
        puts = data["optionChain"]["result"][0]["options"][0]["puts"]
        return expiration_dates, calls + puts
    except:
        return None, []

def filter_contracts(contracts, price, option_type):
    return [
        c for c in contracts
        if (c["strike"] > price * 0.97 and c["strike"] < price * 1.03) and
        c["contractSymbol"].endswith("C" if option_type == "CALL" else "P") and
        c["volume"] > 100 and
        (c["ask"] - c["bid"]) / c["ask"] < 0.2
    ]

# ---- توليد التوصيات ----
def generate_recommendation(symbol):
    price = fetch_price(symbol)
    if not price:
        return None

    # التحليل الفني
    df = fetch_historical_data(symbol)
    if df is None or len(df) < 100:
        return None

    df["EMA9"] = calculate_ema(df["close"], 9)
    df["EMA21"] = calculate_ema(df["close"], 21)
    df["RSI"] = calculate_rsi(df["close"])

    last = df.iloc[-1]
    if not (last["EMA9"] > last["EMA21"] and 50 < last["RSI"] < 70):
        return None

    # معالجة الخيارات
    exp_dates, contracts = fetch_option_chain(symbol)
    if not exp_dates:
        return None

    expiry = datetime.fromtimestamp(exp_dates[0], tz=ny_tz).strftime('%Y-%m-%d')
    calls = filter_contracts(contracts, price, "CALL")
    puts = filter_contracts(contracts, price, "PUT")

    best_contract = None
    if calls:
        best_contract = max(calls, key=lambda x: x["volume"])
    elif puts:
        best_contract = max(puts, key=lambda x: x["volume"])

    if not best_contract:
        return None

    return {
        "symbol": symbol,
        "type": "CALL" if best_contract in calls else "PUT",
        "strike": best_contract["strike"],
        "expiry": expiry,
        "entry": round((best_contract["bid"] + best_contract["ask"]) / 2, 2),
        "target": round((best_contract["bid"] + best_contract["ask"]) / 2 * 3, 2)
    }

# ---- إدارة التشغيل ----
def main_loop():
    global current_trade
    keep_alive()
    send_telegram_message("🚀 تم بدء التشغيل بنجاح | نظام التوصيات الذكي")

    while True:
        now = datetime.now(ny_tz)
        if now.weekday() < 5 and time(9, 30) <= now.time() <= time(16, 0):
            recommendations = []
            for symbol in companies:
                rec = generate_recommendation(symbol)
                if rec:
                    recommendations.append(rec)

            if recommendations:
                best_trade = max(recommendations, key=lambda x: x["entry"])
                msg = (
                    f"📊 **توصية مؤكدة**\n"
                    f"▫️ السهم: `{best_trade['symbol']}`\n"
                    f"▫️ النوع: {best_trade['type']} عند ${best_trade['strike']}\n"
                    f"▫️ الانتهاء: {best_trade['expiry']}\n"
                    f"▫️ السعر الحالي: ${best_trade['entry']}\n"
                    f"🎯 الهدف: ${best_trade['target']} (+200%)"
                )
                current_trade = best_trade
                send_telegram_message(msg)
            else:
                send_telegram_message("⚠️ لا توجد توصيات اليوم - الظروف غير مناسبة")

            time.sleep(3600)  # تحديث كل ساعة
        else:
            time.sleep(600)   # تحقق كل 10 دقائق خارج أوقات السوق

if __name__ == "__main__":
    main_loop()
