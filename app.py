import google.generativeai as genai
import requests
from flask import Flask, request
import os

app = Flask(__name__)

# إعدادات نجم الإبداع
GEMINI_KEY = "AIzaSyD9W4yP9Lb_PIxZr6JutAQehm-4kB1v4RA"
INSTANCE_ID = "159896"
ULTRA_TOKEN = "3a2kuk39wf15ejiu"

# إعداد المحرك (استخدام الاسم الأساسي لحل خطأ 404)
genai.configure(api_key=GEMINI_KEY)
model = genai.GenerativeModel('gemini-1.5-flash')

@app.route('/')
def home():
    return "OK", 200

@app.route('/webhook', methods=['POST'])
def whatsapp_webhook():
    data = request.get_json(force=True, silent=True)
    if data and data.get('event_type') == 'message_received':
        msg_body = data['data'].get('body')
        sender_id = data['data'].get('from')
        
        if not data['data'].get('fromMe') and msg_body:
            try:
                # توليد الرد
                res = model.generate_content(f"رد بلهجة سعودية: {msg_body}")
                
                # إرسال للواتساب
                url = f"https://api.ultramsg.com/instance{INSTANCE_ID}/messages/chat"
                requests.post(url, data={"token": ULTRA_TOKEN, "to": sender_id, "body": res.text})
                print(f"✅ تم الرد بنجاح")
            except Exception as e:
                print(f"❌ خطأ جيمني: {e}")
                
    return "OK", 200

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)
