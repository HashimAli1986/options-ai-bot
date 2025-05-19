import requests
import pandas as pd
import time
import random
from datetime import datetime, time, timedelta
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

# الإعدادات الأساسية
BOT_TOKEN = "7560392852:AAGNoxFGThp04qMKTGEiIJN2eY_cahTv3E8"
CHANNEL_ID = "@hashimAlico"
companies = [
    "MSTR", "APP", "AVGO", "SMCI", "GS",
    "MU", "META", "AAPL", "COIN", "TSLA", "LLY"
]
ny_tz = timezone('America/New_York')

# ---- وظائف المراسلة ----
def send_telegram_message(text):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    data = {"chat_id": CHANNEL_ID, "text": text, "parse_mode": "Markdown"}
    try:
        requests.post(url, data=data)
    except Exception as e:
        print(f"Telegram Error: {e}")

# ---- نظام التواريخ الذكي ----
def get_valid_expirations(symbol):
    try:
        url = f"https://query1.finance.yahoo.com/v7/finance/options/{symbol}"
        data = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}).json()
        dates = [
            datetime.fromtimestamp(ts, tz=ny_tz).strftime('%Y-%m-%d')
            for ts in data["optionChain"]["result"][0]["expirationDates"]
            if datetime.fromtimestamp(ts).weekday() == 4  # الجمعة فقط
        ]
        return sorted(dates)
    except:
        return []

def select_expiration(exp_dates):
    if not exp_dates:
        return None
    
    now = datetime.now(ny_tz)
    candidates = [
        exp_dates[0],  # أقرب جمعة
        next((d for d in exp_dates if (datetime.strptime(d, '%Y-%m-%d') - now).days >= 7), None),
        next((d for d in exp_dates if (datetime.strptime(d, '%Y-%m-%d') - now).days >= 21), None)
    ]
    valid_dates = [d for d in candidates if d]
    return random.choice(valid_dates) if valid_dates else exp_dates[0]

# ---- التوصيات الإلزامية ----
def generate_forced_recommendation():
    symbol = random.choice(companies)
    price = fetch_price(symbol)
    if not price or price < 10:
        return None
    
    exp_dates = get_valid_expirations(symbol)
    if not exp_dates:
        return None
    
    expiry = select_expiration(exp_dates)
    ema_50 = fetch_ema(symbol, 50)
    option_type = "CALL" if (ema_50 and price > ema_50) else "PUT"
    
    strike = round(price * 1.02, 2) if option_type == "CALL" else round(price * 0.98, 2)
    entry = round(price * random.uniform(0.015, 0.03), 2)
    
    return {
        "symbol": symbol,
        "type": option_type,
        "strike": strike,
        "expiry": expiry,
        "entry": entry,
        "target": round(entry * 3, 2)
    }

# ---- نظام الأسعار والتحليل ----
def fetch_price(symbol):
    try:
        url = f"https://query1.finance.yahoo.com/v8/finance/chart/{symbol}?interval=1m"
        data = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}).json()
        return round(data["chart"]["result"][0]["indicators"]["quote"][0]["close"][-1], 2)
    except:
        return None

def fetch_ema(symbol, period):
    try:
        url = f"https://query1.finance.yahoo.com/v8/finance/chart/{symbol}?range=2y&interval=1d"
        data = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}).json()
        closes = data["chart"]["result"][0]["indicators"]["quote"][0]["close"]
        series = pd.Series(closes).dropna()
        return series.ewm(span=period).mean().iloc[-1]
    except:
        return None

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
            trade = generate_forced_recommendation()
            if trade:
                send_telegram_message(
                    f"🔥 **توصية إلزامية اليوم**\n"
                    f"▫️ السهم: {trade['symbol']}\n"
                    f"▫️ النوع: {trade['type']} @ {trade['strike']}\n"
                    f"▫️ الانتهاء: {trade['expiry']}\n"
                    f"▫️ السعر: ${trade['entry']}\n"
                    f"🎯 الهدف: ${trade['target']} (+200%)\n"
                    f"⏱ {now.strftime('%Y-%m-%d %H:%M')}"
                )
                last_recommendation_date = now.date()
        
        time.sleep(300)

def is_market_open():
    now = datetime.now(ny_tz)
    return (now.weekday() < 5 and 
            time(9, 30) <= now.time() <= time(16, 0))

def send_hourly_prices():
    prices = {c: fetch_price(c) for c in companies}
    msg = "📊 **تحديث أسعار الساعة**\n" + "\n".join(
        [f"▫️ {k}: ${v}" for k, v in prices.items() if v]
    ) + f"\n⏱ {datetime.now(ny_tz).strftime('%Y-%m-%d %H:%M')}"
    send_telegram_message(msg)

if __name__ == "__main__":
    main_loop()
