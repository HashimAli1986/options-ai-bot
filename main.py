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

def get_nearest_friday():
    expiry = datetime.now()
    while expiry.weekday() != 4:  # 4 = Friday
        expiry += pd.Timedelta(days=1)
    return expiry

def fetch_real_option(symbol, expiry_date, current_price):
    try:
        expiry_timestamp = int(time.mktime(expiry_date.timetuple()))
        url = f"https://finance.yahoo.com/quote/{symbol}/options?p={symbol}&date={expiry_timestamp}"
        headers = {"User-Agent": "Mozilla/5.0"}
        response = requests.get(url, headers=headers)
        soup = BeautifulSoup(response.text, 'html.parser')
        table = soup.find('table', {'class': 'puts'})
        rows = table.find_all('tr')[1:]

        for row in rows:
            cols = row.find_all('td')
            if len(cols) >= 10:
                strike = float(cols[2].text.strip())
                last = float(cols[3].text.strip())
                if 1.5 <= last <= 3:
                    return {
                        "strike": strike,
                        "last": last
                    }
        return None
    except Exception as e:
        print(f"fetch_real_option error: {e}")
        return None

def generate_option_recommendation(symbol, price):
    expiry_date = get_nearest_friday()
    option = fetch_real_option(symbol, expiry_date, price)
    if option:
        return {
            "symbol": symbol,
            "type": "PUT" if option["strike"] < price else "CALL",
            "strike": option["strike"],
            "expiry": expiry_date.strftime('%Y-%m-%d'),
            "entry": round(option["last"], 2),
            "target": round(option["last"] * 3, 2)
        }
    return None

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
    send_telegram_message("✅ تم تشغيل سكربت توصيات الخيارات الأمريكية.")

    while True:
        now = datetime.utcnow()
        if 13 <= now.hour <= 20:
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
