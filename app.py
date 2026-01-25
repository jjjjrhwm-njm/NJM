import google.generativeai as genai
import requests
from flask import Flask, request
import os

app = Flask(__name__)

# --- [ إعدادات نجم الإبداع - واتساب فقط ] ---
#
GEMINI_KEY = "AIzaSyD9W4yP9Lb_PIxZr6JutAQehm-4kB1v4RA"
INSTANCE_ID = "159896"
ULTRA_TOKEN = "3a2kuk39wf15ejiu"

# إعداد جيمني بالموديل المستقر
genai.configure(api_key=GEMINI_KEY)
model = genai.GenerativeModel('gemini-1.5-flash')

@app.route('/')
def home():
    return "<h1>سيرفر الواتساب NJM متصل ومستقر ✅</h1>", 200

# --- [ مسار الواتساب - Webhook ] ---
@app.route('/webhook', methods=['POST'])
def whatsapp_webhook():
    data = request.get_json(force=True, silent=True)
    
    if data and data.get('event_type') == 'message_received':
        msg_body = data['data'].get('body')
        sender_id = data['data'].get('from')
        
        if not data['data'].get('fromMe') and msg_body:
            print(f"📩 رسالة مستلمة من {sender_id}: {msg_body}")
            try:
                # توليد الرد بلهجة سعودية
                prompt = f"أنت مساعد المطور راشد علي محسن صالح. رد بلهجة سعودية: {msg_body}"
                ai_res = model.generate_content(prompt)
                
                # إرسال الرد عبر UltraMsg
                url = f"https://api.ultramsg.com/instance{INSTANCE_ID}/messages/chat"
                payload = {
                    "token": ULTRA_TOKEN, 
                    "to": sender_id, 
                    "body": ai_res.text
                }
                
                response = requests.post(url, data=payload)
                print(f"📡 نتيجة الإرسال لـ UltraMsg: {response.status_code}")
                
            except Exception as e:
                # طباعة الخطأ الحقيقي للتشخيص
                print(f"❌ خطأ جيمني: {e}")
                
    return "OK", 200

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)
