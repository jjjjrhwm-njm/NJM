import google.generativeai as genai
import requests
from flask import Flask, request
import telebot
import os
from threading import Thread

app = Flask(__name__)

# --- [ إعدادات نجم الإبداع - تأكد من مطابقتها ] ---
#
GEMINI_KEY = "AIzaSyD7z3i-eKGO8_CxSobufqdQgdhlCBBl9xg"
INSTANCE_ID = "159896"
ULTRA_TOKEN = "3a2kuk39wf15ejiu"
TELE_TOKEN = "7917846549:AAGhKz_R96_BBy-6_n-uOly5vIis3T4Wc88"

# إعداد جيمني
genai.configure(api_key=GEMINI_KEY)
model = genai.GenerativeModel('gemini-pro')

# إعداد تليجرام
bot = telebot.TeleBot(TELE_TOKEN)

@app.route('/')
def home():
    return "<h1>سيرفر NJM المطور يعمل بنجاح ✅</h1>", 200

# --- [ مسار الواتساب - Webhook ] ---
@app.route('/webhook', methods=['POST'])
def whatsapp_webhook():
    # استلام البيانات من UltraMsg
    data = request.get_json(force=True, silent=True)
    
    if data and data.get('event_type') == 'message_received':
        msg_body = data['data'].get('body')
        sender_id = data['data'].get('from')
        
        # التأكد أن الرسالة ليست من البوت نفسه
        if not data['data'].get('fromMe') and msg_body:
            print(f"📩 رسالة جديدة من {sender_id}: {msg_body}")
            
            try:
                # 1. توليد الرد من جيمني
                prompt = f"أنت مساعد راشد علي محسن صالح. رد بلهجة سعودية تقنية: {msg_body}"
                ai_res = model.generate_content(prompt)
                reply_text = ai_res.text
                
                # 2. إرسال الرد عبر UltraMsg
                url = f"https://api.ultramsg.com/instance{INSTANCE_ID}/messages/chat"
                payload = {
                    "token": ULTRA_TOKEN,
                    "to": sender_id,
                    "body": reply_text
                }
                
                response = requests.post(url, data=payload)
                
                # طباعة النتيجة في سجلات رندر للتشخيص
                print(f"📡 رد UltraMsg: {response.status_code} - {response.text}")
                
            except Exception as e:
                print(f"❌ خطأ أثناء معالجة الرد: {e}")
                
    return "OK", 200

# --- [ مسار التليجرام ] ---
@bot.message_handler(func=lambda m: True)
def tele_reply(message):
    try:
        res = model.generate_content(message.text)
        bot.reply_to(message, res.text)
        print(f"✅ تم الرد على التليجرام: {message.chat.id}")
    except Exception as e:
        print(f"❌ خطأ تليجرام: {e}")

def run_tele():
    # لضمان عدم حدوث Conflict 409
    bot.infinity_polling(timeout=10, long_polling_timeout=5)

if __name__ == "__main__":
    # تشغيل التليجرام في خلفية السيرفر
    Thread(target=run_tele).start()
    
    # ربط المنفذ الخاص بـ Render
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)
