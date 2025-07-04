‏import requests
‏import pandas as pd
‏import numpy as np
‏import time
‏from datetime import datetime
‏from flask import Flask
‏from threading import Thread

‏app = Flask(__name__)

‏@app.route('/')
‏def home():
‏    return "سكربت التحليل الأسبوعي يعمل بنجاح"

‏def run():
‏    app.run(host='0.0.0.0', port=8080)

‏def keep_alive():
‏    t = Thread(target=run)
‏    t.start()

‏BOT_TOKEN = "7560392852:AAGNoxFGThp04qMKTGEiIJN2eY_cahTv3E8"
‏CHANNEL_ID = "@hashimAlico"

‏def send_telegram_message(text):
‏    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
‏    data = {"chat_id": CHANNEL_ID, "text": text}
‏    try:
‏        requests.post(url, data=data)
‏    except Exception as e:
‏        print(f"Telegram Error: {e}")

‏assets = {
‏    "^GSPC": "S&P 500",
‏    "MSTR": "MicroStrategy",
‏    "APP": "AppLovin",
‏    "AVGO": "Broadcom",
‏    "SMCI": "Super Micro Computer",
‏    "GS": "Goldman Sachs",
‏    "MU": "Micron Technology",
‏    "META": "Meta Platforms",
‏    "AAPL": "Apple",
‏    "COIN": "Coinbase",
‏    "TSLA": "Tesla",
‏    "LLY": "Eli Lilly",
‏    "CRWD": "CrowdStrike",
‏    "MSFT": "Microsoft",
‏    "AMD": "Advanced Micro Devices"
}

‏def fetch_weekly_data(symbol):
‏    try:
‏        url = f"https://query1.finance.yahoo.com/v8/finance/chart/{symbol}?range=5y&interval=1wk"
‏        headers = {"User-Agent": "Mozilla/5.0"}
‏        response = requests.get(url, headers=headers)
‏        data = response.json()
‏        result = data["chart"]["result"][0]
‏        timestamps = result["timestamp"]
‏        prices = result["indicators"]["quote"][0]
‏        df = pd.DataFrame({
‏            "Open": prices["open"],
‏            "High": prices["high"],
‏            "Low": prices["low"],
‏            "Close": prices["close"],
‏            "Volume": prices["volume"]
        })
‏        df["Date"] = pd.to_datetime(timestamps, unit="s")
‏        df.set_index("Date", inplace=True)
‏        return df.dropna().iloc[-100:]
‏    except Exception as e:
‏        print(f"fetch_data error ({symbol}): {e}")
‏        return None

‏def calculate_indicators(df):
    # المتوسطات المتحركة
‏    df["EMA9"] = df["Close"].ewm(span=9).mean()
‏    df["EMA21"] = df["Close"].ewm(span=21).mean()
‏    df["EMA50"] = df["Close"].ewm(span=50).mean()
    
‏    # RSI
‏    delta = df["Close"].diff()
‏    gain = delta.clip(lower=0).rolling(14).mean()
‏    loss = -delta.clip(upper=0).rolling(14).mean()
‏    rs = gain / loss
‏    df["RSI"] = 100 - (100 / (1 + rs))
    
‏    # MACD
‏    df["MACD"] = df["Close"].ewm(span=12).mean() - df["Close"].ewm(span=26).mean()
‏    df["Signal"] = df["MACD"].ewm(span=9).mean()
    
    # القنوات السعرية
‏    df['Upper_Band'] = df['High'].rolling(20).max()
‏    df['Lower_Band'] = df['Low'].rolling(20).min()
    
    # حجم التداول
‏    df['Vol_MA20'] = df['Volume'].rolling(20).mean()
    
‏    return df

‏def generate_recommendation(df, is_index=False):
‏    last = df.iloc[-1]
‏    prev = df.iloc[-2]
    
    # تحسين حساب المتوسطات المتحركة
‏    df["EMA9"] = df["Close"].ewm(span=9, min_periods=1).mean()
‏    df["EMA21"] = df["Close"].ewm(span=21, min_periods=1).mean()
‏    df["EMA50"] = df["Close"].ewm(span=50, min_periods=1).mean()
    
    # حساب RSI أكثر دقة
‏    delta = df["Close"].diff(1)
‏    gain = delta.clip(lower=0)
‏    loss = -delta.clip(upper=0)
‏    avg_gain = gain.ewm(alpha=1/14, min_periods=14).mean()
‏    avg_loss = loss.ewm(alpha=1/14, min_periods=14).mean()
‏    rs = avg_gain / avg_loss
‏    df["RSI"] = 100 - (100 / (1 + rs))
    
    # تحسين حساب MACD
‏    exp12 = df["Close"].ewm(span=12, min_periods=1).mean()
‏    exp26 = df["Close"].ewm(span=26, min_periods=1).mean()
‏    df["MACD"] = exp12 - exp26
‏    df["Signal"] = df["MACD"].ewm(span=9, min_periods=1).mean()
    
    # حساب القنوات السعرية مع فترة أطول للمؤشرات
‏    window = 15 if is_index else 20
‏    df['Upper_Band'] = df['High'].rolling(window=window, min_periods=1).max()
‏    df['Lower_Band'] = df['Low'].rolling(window=window, min_periods=1).min()
    
    # حساب المتوسط المتحرك 200 أسبوع بشكل صحيح
‏    if len(df) >= 200:
‏        ma200 = df["Close"].rolling(200).mean().iloc[-1]
‏    else:
‏        ma200 = df["Close"].mean()
    
    # تحليل الإشارات
‏    rsi = df["RSI"].iloc[-1]
‏    rsi_signal = "محايد"
‏    if rsi > 75:
‏        rsi_signal = "تشبع شراء" 
‏    elif rsi < 25:
‏        rsi_signal = "تشبع بيع"
    
‏    macd_signal = "محايد"
‏    macd_cross_up = last["MACD"] > last["Signal"] and prev["MACD"] <= prev["Signal"]
‏    macd_cross_down = last["MACD"] < last["Signal"] and prev["MACD"] >= prev["Signal"]
    
‏    if macd_cross_up:
‏        macd_signal = "إشارة شراء"
‏    elif macd_cross_down:
‏        macd_signal = "إشارة بيع"
    
    # تحليل قوة الاتجاه
‏    trend_strength = 0
‏    if last["Close"] > last["EMA21"] > last["EMA50"]:
‏        trend_strength = min(100, int((last["Close"] - last["EMA50"]) / last["EMA50"] * 1000))
‏    elif last["Close"] < last["EMA21"] < last["EMA50"]:
‏        trend_strength = min(100, int((last["EMA50"] - last["Close"]) / last["EMA50"] * 1000))
    
    # تحليل القوة النسبية للمؤشرات
‏    relative_strength = ""
‏    if is_index:
‏        if last["Close"] > ma200:
‏            relative_strength = f"🔷 فوق المتوسط 200 أسبوع ({ma200:.2f})"
‏        else:
‏            relative_strength = f"🔻 تحت المتوسط 200 أسبوع ({ma200:.2f})"
    
    # تحسين معايير التوصية
‏    recommendation = "محايد"
‏    if is_index:
        # معايير خاصة بالمؤشرات
‏        if trend_strength > 70 and rsi < 75 and macd_cross_up:
‏            recommendation = "شراء قوي"
‏        elif trend_strength > 50 and rsi < 70:
‏            recommendation = "شراء"
‏        elif rsi > 75 and trend_strength > 60:
‏            recommendation = "حذر (تشبع شراء)"
‏        elif trend_strength > 40 and rsi > 40 and macd_cross_down:
‏            recommendation = "بيع"
‏    else:
        # معايير الأسهم
‏        volume_condition = last["Volume"] > df["Volume"].rolling(20).mean().iloc[-1] * 1.2
        
‏        if trend_strength > 60 and rsi < 65 and volume_condition and macd_cross_up:
‏            recommendation = "شراء قوي"
‏        elif trend_strength > 45 and rsi < 70 and volume_condition:
‏            recommendation = "شراء"
‏        elif trend_strength > 50 and rsi > 35 and volume_condition and macd_cross_down:
‏            recommendation = "بيع"
‏        elif rsi > 75 and trend_strength > 60:
‏            recommendation = "حذر (تشبع شراء)"
    
    # حساب التقلب بشكل صحيح
‏    volatility = (df['Upper_Band'].iloc[-1] - df['Lower_Band'].iloc[-1]) / last["Close"]
    
‏    return {
‏        "recommendation": recommendation,
‏        "rsi_signal": rsi_signal,
‏        "macd_signal": macd_signal,
‏        "support": df['Lower_Band'].iloc[-1],
‏        "resistance": df['Upper_Band'].iloc[-1],
‏        "target_price": None,
‏        "trend_strength": trend_strength,
‏        "volatility": f"{(volatility*100):.1f}%",
‏        "relative_strength": relative_strength,
‏        "ma200": ma200
    }

‏def analyze_and_send():
‏    current_time = datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')
‏    msg = f"📊 **تحديث التحليل الأسبوعي المتقدم**\n"
‏    msg += f"⌚ الوقت: {current_time}\n"
‏    msg += "--------------------------------\n\n"
    
    # جلب بيانات S&P500 أولاً للمقارنة
‏    sp500 = fetch_weekly_data("^GSPC")
‏    if sp500 is not None:
‏        sp500 = calculate_indicators(sp500)
‏        sp500_last = sp500.iloc[-1]
‏        sp500_change = ((sp500_last["Close"] - sp500.iloc[-2]["Close"]) / sp500.iloc[-2]["Close"]) * 100
‏        sp500_analysis = generate_recommendation(sp500, is_index=True)
        
        # تحليل S&P500 مفصل
‏        msg += f"**🌎 S&P 500 (^GSPC)**\n"
‏        msg += f"▶️ السعر: {sp500_last['Close']:.2f} ({sp500_change:+.2f}%)\n"
‏        msg += f"▶️ التوصية: **{sp500_analysis['recommendation']}**\n"
‏        msg += f"▶️ RSI: {sp500_last['RSI']:.2f} ({sp500_analysis['rsi_signal']})\n"
‏        msg += f"▶️ قوة الاتجاه: {sp500_analysis['trend_strength']}%\n"
‏        msg += f"▶️ التقلب: {sp500_analysis['volatility']}\n"
‏        msg += f"▶️ {sp500_analysis['relative_strength']}\n"
‏        msg += f"▶️ الدعم: {sp500_analysis['support']:.2f} | المقاومة: {sp500_analysis['resistance']:.2f}\n\n"
‏        msg += "--------------------------------\n\n"
    
‏    for symbol, name in assets.items():
‏        if symbol == "^GSPC":
‏            continue
            
‏        df = fetch_weekly_data(symbol)
‏        if df is None or len(df) < 20:
‏            continue
            
‏        df = calculate_indicators(df)
‏        last = df.iloc[-1]
‏        analysis = generate_recommendation(df)
        
        # حساب الأداء مقابل السوق
‏        market_perf = ""
‏        if sp500 is not None:
‏            stock_perf = (last["Close"] / df.iloc[-2]["Close"] - 1) * 100
‏            relative_strength = stock_perf - sp500_change
‏            strength_icon = "💪" if relative_strength > 0 else "⚠️"
‏            market_perf = f"\n{strength_icon} الأداء النسبي: {relative_strength:+.2f}% vs السوق"
        
        # بناء الرسالة
‏        msg += f"**{name} ({symbol})**\n"
‏        msg += f"▶️ السعر: {last['Close']:.2f}\n"
‏        msg += f"▶️ التوصية: **{analysis['recommendation']}**\n"
‏        msg += f"▶️ RSI: {last['RSI']:.2f} ({analysis['rsi_signal']})\n"
‏        msg += f"▶️ MACD: {analysis['macd_signal']}\n"
‏        msg += f"▶️ قوة الاتجاه: {analysis['trend_strength']}%\n"
        
‏        if analysis['target_price']:
‏            direction = "▲" if "شراء" in analysis['recommendation'] else "▼"
‏            change_pct = ((analysis['target_price'] - last['Close']) / last['Close']) * 100
‏            msg += f"▶️ السعر المستهدف: {direction} {analysis['target_price']:.2f} ({change_pct:+.1f}%)\n"
        
‏        msg += f"▶️ الدعم: {analysis['support']:.2f} | المقاومة: {analysis['resistance']:.2f}\n"
‏        msg += f"▶️ التقلب: {analysis['volatility']}{market_perf}\n"
‏        msg += "--------------------------------\n\n"
    
‏    send_telegram_message(msg)

‏def hourly_loop():
‏    last_sent_hour = -1
‏    while True:
‏        now = datetime.utcnow()
‏        if now.hour != last_sent_hour and now.minute >= 0:
‏            last_sent_hour = now.hour
‏            analyze_and_send()
‏        time.sleep(30)

‏if __name__ == "__main__":
‏    keep_alive()
‏    send_telegram_message("✅ بدأ العمل: نظام التحليل الأسبوعي المتقدم")
‏    Thread(target=hourly_loop).start()
