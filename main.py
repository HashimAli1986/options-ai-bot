import requests
import pandas as pd
from datetime import datetime, timedelta
from flask import Flask
from threading import Thread
import time

# إعداد البوت
BOT_TOKEN = "7560392852:AAGNoxFGThp04qMKTGEiIJN2eY_cahTv3E8"
CHANNEL_ID = "@hashimAlico"

def send_telegram_message(text):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    data = {"chat_id": CHANNEL_ID, "text": text}
    try:
        requests.post(url, data=data)
    except Exception as e:
        print("Telegram error:", e)

# خادم للتشغيل المستمر
app = Flask('')

@app.route('/')
def home():
    return "Option Signal Bot is Running"

def run():
    app.run(host='0.0.0.0', port=8080)

def keep_alive():
    Thread(target=run).start()

# قائمة الشركات المستهدفة
companies = ["MSTR", "APP", "AVGO", "SMCI", "GS", "MU", "META", "AAPL", "COIN", "TSLA", "LLY"]

# جلب الأسعار الحقيقية
def get_current_prices():
    prices = {}
    for name, data in stock_list.items():
        try:
            url = f"https://query1.finance.yahoo.com/v7/finance/quote?symbols={data['symbol']}"
            headers = {"User-Agent": "Mozilla/5.0"}
            response = requests.get(url, headers=headers)
            response.raise_for_status()
            res = response.json()

            price = res['quoteResponse']['result'][0].get('regularMarketPrice')
            if price is not None:
                prices[name] = f"${price:.2f}"
            else:
                prices[name] = "N/A"
        except Exception as e:
            print(f"[Error] {name}: {e}")
            prices[name] = "N/A"
    return prices

# تنفيذ التوصية اليومية
last_signal_sent = None
current_trade = None

def send_option_signal():
    global last_signal_sent, current_trade

    now = datetime.utcnow()
    if current_trade and current_trade["active"]:
        return  # لا ترسل توصية جديدة إذا هناك توصية فعالة

    if now.hour >= 13 and now.hour <= 20:  # وقت عمل السوق الأمريكي UTC
        selected = None
        prices = get_current_prices()

        for symbol in companies:
            if prices[symbol] != "N/A":
                selected = symbol
                break

        if selected:
            strike_price = round(prices[selected], 2)
            contract_price = 2.5
            option_type = "PUT" if datetime.now().second % 2 == 0 else "CALL"
            expiry = (datetime.now() + timedelta(days=7)).strftime('%Y-%m-%d')
            target = round(contract_price * 3, 2)

            msg = f"""توصية اليوم
السهم: {selected}
الخيار: {option_type} @ {strike_price}
تاريخ الانتهاء: {expiry}
سعر العقد: ${contract_price}
الهدف: ${target} (ربح 200%)
الوقت: {datetime.now().strftime('%Y-%m-%d %H:%M')}
"""
            send_telegram_message(msg)
            last_signal_sent = now
            current_trade = {"symbol": selected, "active": True, "option_type": option_type, "strike": strike_price, "target": target}

def send_hourly_update():
    global current_trade
    prices = get_current_prices()
    msg = "تحديث الأسعار المباشرة:\n"
    for symbol, price in prices.items():
        msg += f"{symbol}: {price}\n"

    if current_trade:
        msg += f"\nتحديث الصفقة المفتوحة:\nالسهم: {current_trade['symbol']} - {current_trade['option_type']} - الهدف: ${current_trade['target']}"

    send_telegram_message(msg)

def main_loop():
    keep_alive()
    while True:
        now = datetime.utcnow()
        if now.minute == 0:
            send_option_signal()
        send_hourly_update()
        time.sleep(3600)

if __name__ == "__main__":
    send_telegram_message("✅ تم تشغيل توصيات الخيارات اليومية بنجاح.")
    main_loop()
