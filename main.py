import yfinance as yf
import requests
import time
from datetime import datetime, timedelta
from flask import Flask
from threading import Thread
import pytz

app = Flask('')

@app.route('/')
def home():
    return "سكربت توصيات خيارات الأسهم الأمريكية يعمل بنجاح"

def run():
    app.run(host='0.0.0.0', port=8080)

def keep_alive():
    t = Thread(target=run)
    t.start()

# إعدادات تيليجرام
BOT_TOKEN = "7560392852:AAGNoxFGThp04qMKTGEiIJN2eY_cahTv3E8"
CHANNEL_ID = "@hashimAlico"

def send_telegram_message(text):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    data = {"chat_id": CHANNEL_ID, "text": text}
    try:
        requests.post(url, data=data)
    except Exception as e:
        print("Telegram error:", e)

companies = ["MSTR", "APP", "AVGO", "SMCI", "GS", "MU", "META", "AAPL", "COIN", "TSLA", "LLY"]
current_trade = None

def fetch_current_price(symbol):
    try:
        ticker = yf.Ticker(symbol)
        data = ticker.history(period="1d", interval="1m")
        if data.empty:
            return None
        return round(data['Close'].iloc[-1], 2)
    except:
        return None

def fetch_options_data(symbol):
    try:
        ticker = yf.Ticker(symbol)
        expirations = ticker.options
        if not expirations:
            return None
        expiry = expirations[0]
        opt_chain = ticker.option_chain(expiry)
        all_options = opt_chain.calls.append(opt_chain.puts)
        valid_options = all_options[(all_options['lastPrice'] >= 1.5) & (all_options['lastPrice'] <= 3)]
        if valid_options.empty:
            return None
        return valid_options.sort_values(by="volume", ascending=False).iloc[0], expiry
    except:
        return None

def format_price_list():
    lines = ["**أسعار الأسهم الحالية**"]
    for symbol in companies:
        price = fetch_current_price(symbol)
        if price:
            lines.append(f"{symbol}: ${price}")
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

def generate_option_trade(symbol):
    result = fetch_options_data(symbol)
    if not result:
        return None
    option, expiry = result
    trade = {
        "symbol": symbol,
        "type": option['contractSymbol'].split(symbol)[-1][:4].replace('C', 'CALL').replace('P', 'PUT'),
        "strike": option['strike'],
        "expiry": expiry,
        "entry": round(option['lastPrice'], 2),
        "target": round(option['lastPrice'] * 3, 2)
    }
    return trade

def main_loop():
    global current_trade
    keep_alive()
    send_telegram_message("✅ تم تشغيل سكربت توصيات خيارات الأسهم الأمريكية.")

    while True:
        now = datetime.now(pytz.timezone("US/Eastern"))
        if now.weekday() < 5 and 9 <= now.hour < 16:  # خلال السوق الأمريكي
            send_telegram_message(format_price_list())

            if current_trade is None:
                for symbol in companies:
                    trade = generate_option_trade(symbol)
                    if trade:
                        current_trade = trade
                        send_telegram_message(format_trade(trade))
                        break
            else:
                send_telegram_message("متابعة الصفقة الحالية:\n" + format_trade(current_trade))
        time.sleep(3600)

if __name__ == "__main__":
    main_loop()
