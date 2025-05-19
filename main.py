‏import requests
import pandas as pd
import time
import random
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
companies = [
    "MSTR", "APP", "AVGO", "SMCI", "GS",
    "MU", "META", "AAPL", "COIN", "TSLA", "LLY"
]
ny_tz = timezone('America/New_York')

# ---- وظائف أساسية ----
def send_telegram_message(text):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    data = {"chat_id": CHANNEL_ID, "text": text, "parse_mode": "Markdown"}
    try:
        requests.post(url, data=data)
    except Exception as e:
        print(f"Telegram Error: {e}")

def fetch_price(symbol):
    try:
        url = f"https://query1.finance.yahoo.com/v8/finance/chart/{symbol}?interval=1m"
        response = requests.get(url, headers={"User-Agent": "Mozilla/5.0"})
        data = response.json()
        return round(data["chart"]["result"][0]["indicators"]["quote"][0]["close"][-1], 2)
    except:
        return None

# ---- التوصية الإلزامية ----
def generate_forced_recommendation():
    symbol = random.choice(companies)
    price = fetch_price(symbol)
    if not price:
        return None
    
    # تحليل بسيط
    option_type = "CALL" if price > fetch_ema(symbol, 50) else "PUT"
    strike = round(price * 1.02, 2) if option_type == "CALL" else round(price * 0.98, 2)
    
    return {
        "symbol": symbol,
        "type": option_type,
        "strike": strike,
        "expiry": next_friday(),
        "entry": round(price * 0.02, 2),
        "target": round(price * 0.06, 2)
    }

def next_friday():
    now = datetime.now(ny_tz)
    return (now + pd.DateOffset(days=(4 - now.weekday()) % 7)).strftime('%Y-%m-%d')

# ---- تحديثات الأسعار ----
def send_hourly_prices():
    prices = {company: fetch_price(company) for company in companies}
    price_list = "\n".join([f"▫️ {k}: ${v}" for k, v in prices.items() if v])
    message = (
        "📊 **تحديث أسعار الساعة**\n"
        f"{price_list}\n"
        f"⏱ {datetime.now(ny_tz).strftime('%Y-%m-%d %H:%M')}"
    )
    send_telegram_message(message)

# ---- التحليل الفني ----
def fetch_historical_data(symbol):
    try:
        url = f"https://query1.finance.yahoo.com/v8/finance/chart/{symbol}?range=2y&interval=1d"
        data = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}).json()
        closes = data["chart"]["result"][0]["indicators"]["quote"][0]["close"]
        timestamps = data["chart"]["result"][0]["timestamp"]
        return pd.DataFrame({"close": closes, "date": pd.to_datetime(timestamps, unit='s')}).dropna()
    except:
        return None

def calculate_ema(series, span):
    return series.ewm(span=span, adjust=False).mean()

def fetch_ema(symbol, period):
    df = fetch_historical_data(symbol)
    return df['close'].ewm(span=period).mean().iloc[-1] if df is not None else None

# ---- التشغيل الرئيسي ----
def main_loop():
    last_hour = -1
    last_recommendation_date = None
    
    keep_alive()
    send_telegram_message("🚀 النظام يعمل بنجاح | تحديثات مباشرة كل ساعة")
    
    while True:
        now = datetime.now(ny_tz)
        
        # تحديث الأسعار كل ساعة
        if now.minute == 0 and now.hour != last_hour:
            send_hourly_prices()
            last_hour = now.hour
            time.sleep(60)
        
        # التوصية الإلزامية اليومية
        if is_market_open() and (last_recommendation_date != now.date()):
            forced_trade = generate_forced_recommendation()
            if forced_trade:
                send_telegram_message(
                    f"🔥 **توصية إلزامية اليوم**\n"
                    f"▫️ السهم: {forced_trade['symbol']}\n"
                    f"▫️ النوع: {forced_trade['type']} @ {forced_trade['strike']}\n"
                    f"▫️ السعر: ${forced_trade['entry']}\n"
                    f"🎯 الهدف: ${forced_trade['target']} (+200%)\n"
                    f"⏱ {now.strftime('%Y-%m-%d %H:%M')}"
                )
                last_recommendation_date = now.date()
        
        time.sleep(300)

def is_market_open():
    now = datetime.now(ny_tz)
    return (now.weekday() < 5 and 
            time(9, 30) <= now.time() <= time(16, 0))

if __name__ == "__main__":
    main_loop()
