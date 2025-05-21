import requests
import pandas as pd
import time
from datetime import datetime
from flask import Flask
from threading import Thread

app = Flask('')

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
    data = {"chat_id": CHENNEL_ID, "text": text}
    try:
        requests.post(url, data=data)
    except Exception as e:
        print(f"Telegram Error: {e}")

assets = {
    "MicroStrategy (MSTR)": {"symbol": "MSTR"},
    # ... باقي الأصول كما هي ...
}

def fetch_daily_data(symbol):
    # ... نفس الدالة الأصلية ...

def calculate_indicators(df):
    # ... نفس الدالة الأصلية ...

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

    recommendation_strength = ""
    if direction == "صاعدة" and ema_cross == "صعود" and rsi < 70:
        recommendation = f"التوصية: شراء | الدخول: {price:.2f}-{price+1:.2f} | الهدف: {price+5:.2f} | الوقف: {price-3:.2f} | القوة: قوية"
        recommendation_strength = "قوية"
    elif direction == "هابطة" and rsi > 70:
        recommendation = f"التوصية: بيع | الدخول: {price-1:.2f}-{price+1:.2f} | الهدف: {price-5:.2f} | الوقف: {price+3:.2f} | القوة: قوية"
        recommendation_strength = "قوية"
    else:
        recommendation = "التوصية: للمراقبة فقط (ضعف في المؤشرات الفنية)"
        recommendation_strength = "ضعيفة"

    summary = (
        f"{name}:\n"
        f"السعر الحالي: {price:.2f}\n"
        f"الاتجاه المتوقع: {direction}\n"
        f"تقاطع EMA: {ema_cross}\n"
        f"RSI: {rsi:.2f} ({rsi_zone})\n"
        f"الدعم: {support:.2f} | المقاومة: {resistance:.2f}\n"
        f"{recommendation}"
    )
    
    analysis_data = {
        "name": name,
        "symbol": assets[name]["symbol"],
        "price": price,
        "direction": direction,
        "ema_cross": ema_cross,
        "rsi": rsi,
        "rsi_zone": rsi_zone,
        "recommendation": recommendation,
        "strength": recommendation_strength
    }
    
    return summary, analysis_data

def get_options_chain(symbol):
    try:
        headers = {"User-Agent": "Mozilla/5.0"}
        url = f"https://query1.finance.yahoo.com/v7/finance/options/{symbol}"
        response = requests.get(url, headers=headers)
        data = response.json()
        
        if not data["optionChain"]["result"]:
            return None, None, None
            
        expiration_dates = data["optionChain"]["result"][0]["expirationDates"]
        if not expiration_dates:
            return None, None, None
            
        nearest_expiration = min(expiration_dates)
        url = f"{url}?date={nearest_expiration}"
        response = requests.get(url, headers=headers)
        data = response.json()
        
        options = data["optionChain"]["result"][0]["options"][0]
        return options["calls"], options["puts"], nearest_expiration
        
    except Exception as e:
        print(f"Options Error: {e}")
        return None, None, None

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
                        msg += f"{name}: البيانات غير متوفرة أو غير كافية.\n\n"
                
                # إيجاد أقوى توصية
                strong_analyses = [a for a in analyses if a["strength"] == "قوية"]
                if strong_analyses:
                    strong_analyses.sort(key=lambda x: abs(x["rsi"]-30) if x["direction"] == "صاعدة" else abs(x["rsi"]-70))
                    strongest = strong_analyses[0]
                    
                    # جلب بيانات الخيارات
                    calls, puts, expiration = get_options_chain(strongest["symbol"])
                    if calls and puts and expiration:
                        current_price = strongest["price"]
                        option_type = "Call" if strongest["direction"] == "صاعدة" else "Put"
                        strikes = [c["strike"] for c in (calls if option_type == "Call" else puts)]
                        nearest_strike = min(strikes, key=lambda x: abs(x - current_price))
                        expiration_date = datetime.utcfromtimestamp(expiration).strftime("%Y-%m-%d")
                        
                        options_msg = (
                            f"\n📈 توصية خيارات تلقائية لأقوى شركة ({strongest['name']}):\n"
                            f"نوع الخيار: {option_type}\n"
                            f"الاسترايك: {nearest_strike:.2f}\n"
                            f"التاريخ: {expiration_date}\n"
                            f"السعر الحالي: {current_price:.2f}\n"
                            f"الهدف المتوقع: {current_price + 3 if option_type == 'Call' else current_price - 3:.2f}\n"
                            f"ملاحظة: بناءً على تحليل الاتجاه {strongest['direction']} ومؤشر RSI {strongest['rsi']:.1f}"
                        )
                        msg += options_msg
                
                send_telegram_message(msg.strip())
                
            except Exception as e:
                send_telegram_message(f"⚠️ خطأ في التحديث: {e}")
        time.sleep(60)

if __name__ == "__main__":
    keep_alive()
    send_telegram_message("✅ تم تشغيل المحلل الذكي: تحديث كل ساعة + توصيات خيارات تلقائية.")
    Thread(target=hourly_price_update).start()
