import requests
import pandas as pd
import time
from datetime import datetime
from flask import Flask
from threading import Thread
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By

app = Flask(__name__)

@app.route('/')
def home():
    return "المحلل الذكي يعمل بنجاح"

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

assets = {
    "MicroStrategy (MSTR)": {"symbol": "MSTR"},
    "AppLovin (APP)": {"symbol": "APP"},
    "Broadcom (AVGO)": {"symbol": "AVGO"},
    "Super Micro Computer (SMCI)": {"symbol": "SMCI"},
    "Goldman Sachs (GS)": {"symbol": "GS"},
    "Micron Technology (MU)": {"symbol": "MU"},
    "Meta Platforms (META)": {"symbol": "META"},
    "Apple (AAPL)": {"symbol": "AAPL"},
    "Coinbase (COIN)": {"symbol": "COIN"},
    "Tesla (TSLA)": {"symbol": "TSLA"},
    "Eli Lilly (LLY)": {"symbol": "LLY"}
}

def fetch_daily_data(symbol):
    try:
        url = f"https://query1.finance.yahoo.com/v8/finance/chart/{symbol}?range=5y&interval=1d"
        headers = {"User-Agent": "Mozilla/5.0"}
        response = requests.get(url, headers=headers)
        data = response.json()
        result = data["chart"]["result"][0]
        timestamps = result["timestamp"]
        prices = result["indicators"]["quote"][0]

        df = pd.DataFrame({
            "Open": prices["open"],
            "High": prices["high"],
            "Low": prices["low"],
            "Close": prices["close"]
        })

        df["Date"] = pd.to_datetime(timestamps, unit="s")
        df.set_index("Date", inplace=True)
        return df.dropna().iloc[-1000:]
    except Exception as e:
        print(f"fetch_data error ({symbol}): {e}")
        return None

def calculate_indicators(df):
    df["EMA9"] = df["Close"].ewm(span=9).mean()
    df["EMA21"] = df["Close"].ewm(span=21).mean()
    delta = df["Close"].diff()
    gain = delta.where(delta > 0, 0).rolling(14).mean()
    loss = -delta.where(delta < 0, 0).rolling(14).mean()
    rs = gain / loss
    df["RSI"] = 100 - (100 / (1 + rs))
    df["Support"] = df["Low"].rolling(50).min()
    df["Resistance"] = df["High"].rolling(50).max()
    return df

def analyze_asset(name, df):
    last = df.iloc[-1]
    prev = df.iloc[-2]
    price = last["Close"]
    direction = "صاعدة" if last["Close"] > last["Open"] else "هابطة"
    ema_cross = "صعود" if prev["EMA9"] < prev["EMA21"] and last["EMA9"] > last["EMA21"] else "هبوط" if prev["EMA9"] > prev["EMA21"] and last["EMA9"] < last["EMA21"] else "جانبي"
    rsi = last["RSI"]
    rsi_zone = "تشبع بيع" if rsi < 30 else "تشبع شراء" if rsi > 70 else "محايد"
    support = last["Support"]
    resistance = last["Resistance"]

    if direction == "صاعدة" and ema_cross == "صعود" and rsi < 70:
        recommendation = f"التوصية: شراء | الدخول: {price:.2f}-{price+1:.2f} | الهدف: {price+5:.2f} | الوقف: {price-3:.2f} | القوة: قوية"
        strength = "قوية"
    elif direction == "هابطة" and rsi > 70:
        recommendation = f"التوصية: بيع | الدخول: {price-1:.2f}-{price+1:.2f} | الهدف: {price-5:.2f} | الوقف: {price+3:.2f} | القوة: قوية"
        strength = "قوية"
    else:
        recommendation = "التوصية: للمراقبة فقط (ضعف في المؤشرات الفنية)"
        strength = "ضعيفة"

    analysis_data = {
        "name": name,
        "symbol": assets[name]["symbol"],
        "price": price,
        "direction": direction,
        "ema_cross": ema_cross,
        "rsi": rsi,
        "support": support,
        "resistance": resistance,
        "strength": strength
    }

    summary = (
        f"{name}:\n"
        f"السعر الحالي: {price:.2f}\n"
        f"الاتجاه المتوقع: {direction}\n"
        f"تقاطع EMA: {ema_cross}\n"
        f"RSI: {rsi:.2f} ({rsi_zone})\n"
        f"الدعم: {support:.2f} | المقاومة: {resistance:.2f}\n"
        f"{recommendation}"
    )
    return summary, analysis_data

def get_webull_options(symbol):
    """استخراج بيانات الخيارات من Webull باستخدام Selenium"""
    try:
        chrome_options = Options()
        chrome_options.add_argument("--headless")
        driver = webdriver.Chrome(options=chrome_options)
        driver.get(f"https://www.webull.com/quote/{symbol}/options")
        time.sleep(5)
        
        options_data = []
        rows = driver.find_elements(By.CSS_SELECTOR, ".options-table tbody tr")
        for row in rows:
            cells = row.find_elements(By.TAG_NAME, "td")
            if len(cells) >= 6:
                strike = float(cells[2].text.replace(',', ''))
                expiration = cells[1].text
                last_price = float(cells[3].text.replace(',', ''))
                options_data.append({
                    "strike": strike,
                    "expiration": expiration,
                    "last_price": last_price
                })
        
        driver.quit()
        return options_data
    except Exception as e:
        print(f"Webull Error: {e}")
        return None

def generate_options_recommendation(analysis, option_type):
    """توليد توصية الخيارات بناءً على تحليل Webull"""
    options = get_webull_options(analysis["symbol"])
    if not options:
        return None
    
    relevant_options = [o for o in options if option_type.lower() in o["expiration"].lower()]
    if not relevant_options:
        return None
    
    nearest_strike = min(relevant_options, key=lambda x: abs(x["strike"] - analysis["price"]))
    
    return {
        "type": "Call" if option_type == "Call" else "Put",
        "strike": nearest_strike["strike"],
        "expiration": nearest_strike["expiration"],
        "premium": nearest_strike["last_price"],
        "target": analysis["resistance"] if option_type == "Call" else analysis["support"],
        "stop_loss": analysis["support"] if option_type == "Call" else analysis["resistance"]
    }

def hourly_price_update():
    last_sent_hour = -1
    while True:
        now = datetime.utcnow()
        if now.hour != last_sent_hour and now.minute >= 0:
            last_sent_hour = now.hour
            try:
                msg = f"تحديث الساعة {now.strftime('%H:%M')} UTC\n\n"
                analyses = []
                
                for name, info in assets.items():
                    df = fetch_daily_data(info["symbol"])
                    if df is not None and len(df) >= 500:
                        df = calculate_indicators(df)
                        summary, analysis = analyze_asset(name, df)
                        msg += summary + "\n\n"
                        analyses.append(analysis)
                    else:
                        msg += f"{name}: البيانات غير متوفرة.\n\n"
                
                strongest_down = max(
                    [a for a in analyses if a["direction"] == "هابطة" and a["rsi"] > 70],
                    key=lambda x: x["rsi"], default=None
                )
                strongest_up = max(
                    [a for a in analyses if a["direction"] == "صاعدة" and a["rsi"] < 30],
                    key=lambda x: -x["rsi"], default=None
                )
                
                if strongest_down:
                    put_rec = generate_options_recommendation(strongest_down, "Put")
                    if put_rec:
                        msg += (
                            f"\n🔥 **أقوى توصية بيع ({strongest_down['name']})**\n"
                            f"الإضراب: {put_rec['strike']:.2f}\n"
                            f"الانتهاء: {put_rec['expiration']}\n"
                            f"العلاوة: {put_rec['premium']:.2f}\n"
                            f"الهدف: {put_rec['target']:.2f}\n"
                            f"الوقف: {put_rec['stop_loss']:.2f}\n"
                        )
                
                if strongest_up:
                    call_rec = generate_options_recommendation(strongest_up, "Call")
                    if call_rec:
                        msg += (
                            f"\n🚀 **أقوى توصية شراء ({strongest_up['name']})**\n"
                            f"الإضراب: {call_rec['strike']:.2f}\n"
                            f"الانتهاء: {call_rec['expiration']}\n"
                            f"العلاوة: {call_rec['premium']:.2f}\n"
                            f"الهدف: {call_rec['target']:.2f}\n"
                            f"الوقف: {call_rec['stop_loss']:.2f}\n"
                        )
                
                send_telegram_message(msg.strip())
                
            except Exception as e:
                send_telegram_message(f"⚠️ خطأ: {e}")
        time.sleep(60)

if __name__ == "__main__":
    keep_alive()
    send_telegram_message("✅ تم تشغيل المحلل الذكي مع توصيات خيارات Webull الدقيقة!")
    Thread(target=hourly_price_update).start()
