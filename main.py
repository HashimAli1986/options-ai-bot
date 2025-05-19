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
    """إرسال رسالة إلى القناة مع معالجة الأخطاء"""
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    data = {"chat_id": CHANNEL_ID, "text": text, "parse_mode": "Markdown"}
    try:
        response = requests.post(url, data=data)
        print(f"تم الإرسال بنجاح: {response.status_code}")
    except Exception as e:
        print(f"خطأ في الإرسال: {e}")

# ---- نظام التواريخ الذكي ----
def get_valid_expirations(symbol):
    """جلب تواريخ انتهاء الخيارات من Yahoo Finance"""
    try:
        url = f"https://query1.finance.yahoo.com/v7/finance/options/{symbol}"
        data = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}).json()
        dates = [
            datetime.fromtimestamp(ts, tz=ny_tz).strftime('%Y-%m-%d')
            for ts in data["optionChain"]["result"][0]["expirationDates"]
            if datetime.fromtimestamp(ts).weekday() == 4  # الجمعة فقط
        ]
        return sorted(dates)
    except Exception as e:
        print(f"خطأ في جلب التواريخ: {e}")
        return []

# ---- التوصيات الإلزامية ----
def generate_forced_recommendation():
    """إنشاء توصية إلزامية مع فحص البيانات"""
    try:
        symbol = random.choice(companies)
        print(f"جاري معالجة: {symbol}")
        
        price = fetch_price(symbol)
        if not price or price < 10:
            print(f"سعر غير صالح لـ {symbol}")
            return None
        
        exp_dates = get_valid_expirations(symbol)
        if not exp_dates:
            print(f"لا توجد تواريخ انتهاء لـ {symbol}")
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
    except Exception as e:
        print(f"خطأ في إنشاء التوصية: {e}")
        return None

# ---- التشغيل الرئيسي مع التتبع ----
def main_loop():
    last_hour = -1
    last_recommendation_date = None
    
    keep_alive()
    send_telegram_message("🚀 النظام يعمل بنجاح | تحديثات مباشرة كل ساعة")
    
    while True:
        now = datetime.now(ny_tz)
        print(f"\n[التنفيذ] الوقت الحالي: {now.strftime('%Y-%m-%d %H:%M')}")
        
        # تحديث الأسعار كل ساعة
        if now.minute == 0 and now.hour != last_hour:
            print("جاري إرسال تحديث الأسعار...")
            send_hourly_prices()
            last_hour = now.hour
            time.sleep(60)
        
        # التوصية الإلزامية اليومية
        if is_market_open():
            print(f"السوق مفتوح. آخر توصية: {last_recommendation_date}")
            if last_recommendation_date != now.date():
                print("إنشاء توصية إلزامية...")
                trade = generate_forced_recommendation()
                if trade:
                    msg = (
                        f"🔥 **توصية إلزامية اليوم**\n"
                        f"▫️ السهم: {trade['symbol']}\n"
                        f"▫️ النوع: {trade['type']} @ {trade['strike']}\n"
                        f"▫️ الانتهاء: {trade['expiry']}\n"
                        f"▫️ السعر: ${trade['entry']}\n"
                        f"🎯 الهدف: ${trade['target']} (+200%)\n"
                        f"⏱ {now.strftime('%Y-%m-%d %H:%M')}"
                    )
                    send_telegram_message(msg)
                    last_recommendation_date = now.date()
                else:
                    print("⚠️ فشل في إنشاء التوصية!")
        
        time.sleep(60)  # تقليل وقت الانتظار لفحص الأخطاء

# ---- اختبار الإرسال يدويًا ----
def send_test_message():
    """إرسال رسالة اختبارية للتأكد من عمل البوت"""
    send_telegram_message("📢 **هذه رسالة اختبارية**\nتم تكوين السكربت بنجاح!")

if __name__ == "__main__":
    send_test_message()  # إرسال رسالة تأكيد عند التشغيل
    main_loop()
