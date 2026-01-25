import google.generativeai as genai
import requests
from flask import Flask, request
import os

app = Flask(__name__)

# إعدادات نجم الإبداع المحدثة
GEMINI_KEY = "AIzaSyD9W4yP9Lb_PIxZr6JutAQehm-4kB1v4RA"
INSTANCE_ID = "159896"
ULTRA_TOKEN = "3a2kuk39wf15ejiu"

# استخدام الاسم التقني الدقيق الذي وجدته في الموقع
genai.configure(api_key=GEMINI_KEY)
model = genai.GenerativeModel('gemini-3-pro-preview')

@app.route('/')
def home():
    return "<h1>سيرفر NJMwats يعمل بموديل Gemini 3 ✅</h1>", 200

@app.route('/webhook', methods=['POST'])
def whatsapp_webhook():
    data = request.get_json(force=True, silent=True)
    if data and data.get('event_type') == 'message_received':
        msg_body = data['data'].get('body')
        sender_id = data['data'].get('from')
        
        if not data['data'].get('fromMe') and msg_body:
            print(f"📩 رسالة مستلمة: {msg_body}")
            try:
                # توليد الرد بالموديل الجديد
                res = model.generate_content(f"رد بلهجة سعودية: {msg_body}")
                
                # إرسال للواتساب عبر UltraMsg
                url = f"https://api.ultramsg.com/instance{INSTANCE_ID}/messages/chat"
                payload = {"token": ULTRA_TOKEN, "to": sender_id, "body": res.text}
                
                requests.post(url, data=payload)
                print(f"✅ تم الرد بنجاح بموديل Gemini 3")
            except Exception as e:
                print(f"❌ خطأ: {e}")
                
    return "OK", 200

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)
