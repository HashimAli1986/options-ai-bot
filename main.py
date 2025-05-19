import requests
import pandas as pd
import time
from datetime import datetime
from flask import Flask
from threading import Thread
from bs4 import BeautifulSoup

app = Flask('')

@app.route('/')
def home():
    return "سكربت توصيات الأسهم الأمريكية يعمل بنجاح"

def run():
    app.run(host='0.0.0.0', port=8081)  # غيرنا البورت لتفادي التعارض

def keep_alive():
    t = Thread(target=run)
    t.start()

# إعداد التوكن والقناة
BOT_TOKEN = "7560392852:AAGNoxFGThp04qMKTGEiIJN2eY_cahTv3E8"
CHANNEL_ID = "@hashimAlico"

def send_telegram_message(text):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    data = {"chat_id": CHANNEL_ID, "text": text}
    try:
        requests.post(url, data=data)
    except Exception as e:
        print(f"Telegram Error: {e}")

companies = [
    "MSTR", "APP", "AVGO", "SMCI", "GS",
    "MU", "META", "AAPL", "COIN", "TSLA", "LLY"
]

current_trade = None

def fetch_price(symbol):
    try:
        url = f"https://query1.finance.yahoo.com/v8/finance/chart/{symbol}?range=1d&interval=1m"
        headers = {"User-Agent": "Mozilla/5.0"}
        response = requests.get(url, headers=headers)
        data = response.json()
        close_price = data["chart"]["result"][0]["indicators"]["quote"][0]["close"][-1]
        return round(close_price, 2)
    except:
        return None

def fetch_all_prices():
    prices = {}
    for company in companies:
        price = fetch_price(company)
        if price:
            prices[company] = price
    return prices

def get_next_friday():
    d = datetime.now()
    while d.weekday() != 4:
        d += pd.Timedelta(days=1)
    return int(time.mktime(d.timetuple()))

def fetch_option_data(symbol, expiry_unix):
    try:
        url = f"https://finance.yahoo.com/quote/{symbol}/options?p={symbol}&date={expiry_unix}"
        headers = {"User-Agent": "Mozilla/5.0"}
        r = requests.get(url, headers=headers)
        soup = BeautifulSoup(r.text, 'html.parser')
        table = soup.find('table', {'class': 'puts'})
        if not table:
            return []
        rows = table.find_all('tr')[1:]
        options = []
        for row in rows:
            cols = row.find_all('td')
            if len(cols) >= 6:
                options.append({
                    "strike": float(cols[2].text.strip().replace(',', '')),
                    "last": float(cols[3].text.strip().replace(',', '')),
                    "bid": float(cols[4].text.strip().replace(',', '')),
                    "ask": float(cols[5].text.strip().replace(',', ''))
                })
        return options
    except Exception as e:
        print(f"fetch_option_data error: {e}")
        return []

def generate_option_recommendation(symbol, price):
    expiry_unix = get_next_friday()
    options = fetch_option_data(symbol, expiry_unix)
    valid_options = [
        opt for opt in options
        if opt["strike"] < price and 1.5 <= opt["ask"] <= 3
    ]
    if not valid_options:
        return None
    option = valid_options[0]  # نأخذ أول واحدة تنطبق
    expiry_date = datetime.fromtimestamp(expiry_unix).strftime('%Y-%m-%d')
    return {
        "symbol": symbol,
        "type": "PUT",
        "strike": option["strike"],
        "expiry": expiry_date,
        "entry": option["ask"],
        "target": round(option["ask"] * 3, 2)
    }

def format_price_list(prices):
    lines = ["**أسعار الأسهم الحالية**"]
    for k, v in prices.items():
        lines.append(f"{k}: ${v}")
    return "\n".join(lines)

def format_trade(trade):
    return (
        f"توصية اليوم\n"
        f"السهم: {trade['symbol']}\n"
        f"الخيار: {trade['type']} @ {trade['strike']}\n"
        f"تاريخ الانتهاء: {trade['expiry']}\n"
        f"سعر العقد: ${trade['entry']}\n"
        f"الهدف: ${trade['target']} (ربح 200%)\n"
        f"الوقت: {datetime.now().strftime('%Y-%m-%d %H:%M')}"
    )

def main_loop():
    global current_trade
    keep_alive()
    send_telegram_message("✅ تم تشغيل سكربت توصيات الخيارات الأمريكية (بيانات حقيقية).")

    while True:
        now = datetime.utcnow()
        if 13 <= now.hour <= 20:  # السوق الأمريكي مفتوح (8am - 3pm بتوقيت نيويورك)
            prices = fetch_all_prices()
            send_telegram_message(format_price_list(prices))

            if current_trade is None:
                for symbol in companies:
                    price = prices.get(symbol)
                    if price:
                        trade = generate_option_recommendation(symbol, price)
                        if trade:
                            current_trade = trade
                            send_telegram_message(format_trade(trade))
                            break
            else:
                send_telegram_message("متابعة الصفقة الحالية:\n" + format_trade(current_trade))

        time.sleep(3600)

if __name__ == "__main__":
    main_loop()
