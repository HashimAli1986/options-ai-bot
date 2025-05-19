import requests
import pandas as pd
import time
from datetime import datetime
from flask import Flask
from threading import Thread
import random

app = Flask('')

@app.route('/')
def home():
    return "سكربت توصيات الأسهم الأمريكية يعمل بنجاح"

def run():
    app.run(host='0.0.0.0', port=8080)

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

def get_real_options_data(symbol):
    try:
        url = f"https://query1.finance.yahoo.com/v7/finance/options/{symbol}"
        headers = {"User-Agent": "Mozilla/5.0"}
        response = requests.get(url, headers=headers)
        data = response.json()
        
        expiration_dates = data['optionChain']['result'][0]['expirationDates']
        nearest_expiry = datetime.fromtimestamp(expiration_dates[0]).strftime('%Y-%m-%d')
        
        calls = data['optionChain']['result'][0]['options'][0]['calls']
        puts = data['optionChain']['result'][0]['options'][0]['puts']
        all_strikes = sorted(list({c['strike'] for c in calls} | {p['strike'] for p in puts}))
        
        return {
            'expiry': nearest_expiry,
            'strikes': all_strikes,
            'calls': calls,
            'puts': puts
        }
    except Exception as e:
        print(f"Error fetching options data for {symbol}: {e}")
        return None

def generate_option_recommendation(symbol, price):
    try:
        options_data = get_real_options_data(symbol)
        if not options_data or not options_data['strikes']:
            return None

        min_strike = price * 0.97
        max_strike = price * 1.03
        
        valid_strikes = [s for s in options_data['strikes'] if min_strike <= s <= max_strike]
        if not valid_strikes:
            return None
            
        strike_price = random.choice(valid_strikes)
        option_type = "CALL" if strike_price > price else "PUT"
        
        options_chain = options_data['calls'] if option_type == "CALL" else options_data['puts']
        contract = next((c for c in options_chain if c['strike'] == strike_price), None)
        if not contract:
            return None
            
        contract_price = round(contract['lastPrice'], 2)
        target = round(contract_price * 3, 2)

        return {
            "symbol": symbol,
            "type": option_type,
            "strike": strike_price,
            "expiry": options_data['expiry'],
            "entry": contract_price,
            "target": target
        }
    except Exception as e:
        print(f"generate_option_recommendation error: {e}")
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

def fetch_all_prices():
    prices = {}
    for company in companies:
        price = fetch_price(company)
        if price:
            prices[company] = price
    return prices

if __name__ == "__main__":
    main_loop()
