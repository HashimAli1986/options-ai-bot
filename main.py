import requests
import pandas as pd
import time
from datetime import datetime
from flask import Flask
from threading import Thread

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

def fetch_all_prices():
    prices = {}
    for company in companies:
        price = fetch_price(company)
        if price:
            prices[company] = price
    return prices

def fetch_historical_data(symbol):
    try:
        url = f"https://query1.finance.yahoo.com/v8/finance/chart/{symbol}?range=1000d&interval=1d"
        headers = {"User-Agent": "Mozilla/5.0"}
        response = requests.get(url, headers=headers)
        data = response.json()["chart"]["result"][0]
        closes = data["indicators"]["quote"][0]["close"]
        timestamps = data["timestamp"]
        df = pd.DataFrame({
            "close": closes,
            "time": pd.to_datetime(timestamps, unit='s')
        }).dropna()
        return df
    except:
        return None

def calculate_rsi(series, period=14):
    delta = series.diff()
    gain = delta.where(delta > 0, 0).rolling(window=period).mean()
    loss = -delta.where(delta < 0, 0).rolling(window=period).mean()
    rs = gain / loss
    return 100 - (100 / (1 + rs))

def fetch_option_strikes(symbol):
    try:
        url = f"https://query1.finance.yahoo.com/v7/finance/options/{symbol}"
        resp = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}).json()
        result = resp.get("optionChain", {}).get("result", [])
        if not result:
            return None, []
        opts = result[0]
        expiry = opts["expirationDates"][0]
        strikes = opts["options"][0]["calls"] + opts["options"][0]["puts"]
        return expiry, strikes
    except:
        return None, []

def generate_option_recommendation(symbol, price):
    try:
        # تحليل آلاف الشمعات اليومية
        df = fetch_historical_data(symbol)
        if df is None or len(df) < 100:
            return None

        df["EMA9"] = df["close"].ewm(span=9).mean()
        df["EMA21"] = df["close"].ewm(span=21).mean()
        df["RSI"] = calculate_rsi(df["close"])

        last = df.iloc[-1]
        ema_cross = last["EMA9"] > last["EMA21"]
        rsi_valid = 50 < last["RSI"] < 70

        if not (ema_cross and rsi_valid):
            return None

        # جلب بيانات الخيارات
        expiry_date, strikes = fetch_option_strikes(symbol)
        if not strikes:
            return None

        # فلترة العقود الحقيقية فقط (مع bid و ask أكبر من 0)
        valid_calls = [
            s for s in strikes
            if s.get("contractSymbol", "").endswith("C")
            and s.get("bid") is not None and s.get("ask") is not None
            and s["bid"] > 0 and s["ask"] > 0
        ]

        valid_puts = [
            s for s in strikes
            if s.get("contractSymbol", "").endswith("P")
            and s.get("bid") is not None and s.get("ask") is not None
            and s["bid"] > 0 and s["ask"] > 0
        ]

        all_valid = valid_calls + valid_puts
        if not all_valid:
            return None

        # اختيار أقرب سترايك نشط
        nearest = min(all_valid, key=lambda x: abs(x["strike"] - price))
        strike_price = nearest["strike"]
        option_type = "CALL" if nearest in valid_calls else "PUT"

        bid = nearest["bid"]
        ask = nearest["ask"]
        contract_price = round((bid + ask) / 2, 2)

        target = round(contract_price * 3, 2)
        expiry = datetime.utcfromtimestamp(expiry_date).strftime('%Y-%m-%d')

        return {
            "symbol": symbol,
            "type": option_type,
            "strike": strike_price,
            "expiry": expiry,
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

    recommended_today = False

    while True:
        now = datetime.utcnow()
        if 13 <= now.hour <= 20:  # السوق الأمريكي 8am - 3pm نيويورك (15:00 - 22:00 السعودية)
            prices = fetch_all_prices()
            send_telegram_message(format_price_list(prices))

            if current_trade is None and not recommended_today:
                for symbol in companies:
                    price = prices.get(symbol)
                    if price:
                        trade = generate_option_recommendation(symbol, price)
                        if trade:
                            current_trade = trade
                            recommended_today = True
                            send_telegram_message(format_trade(trade))
                            break
                if not current_trade:
                    # إذا لم تتحقق الشروط، نرسل أقرب توصية ممكنة بأي شركة
                    fallback = companies[0]
                    fallback_price = prices.get(fallback)
                    if fallback_price:
                        trade = generate_option_recommendation(fallback, fallback_price)
                        if not trade:
                            trade = {
                                "symbol": fallback,
                                "type": "CALL",
                                "strike": round(fallback_price * 1.03, 2),
                                "expiry": datetime.now().strftime('%Y-%m-%d'),
                                "entry": round(fallback_price * 0.01, 2),
                                "target": round(fallback_price * 0.03, 2)
                            }
                        current_trade = trade
                        recommended_today = True
                        send_telegram_message("توصية اضطرارية:\n" + format_trade(trade))

            elif current_trade:
                send_telegram_message("متابعة الصفقة الحالية:\n" + format_trade(current_trade))

        time.sleep(3600)

if __name__ == "__main__":
    main_loop()
