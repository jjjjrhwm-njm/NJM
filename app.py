import google.generativeai as genai
import requests
from flask import Flask, request
import os

app = Flask(__name__)

# --- [ إعدادات نجم الإبداع - واتساب فقط ] ---
# تم استخدام المفتاح الجديد والموديل الأحدث لضمان الاستقرار
GEMINI_KEY = "AIzaSyD9W4yP9Lb_PIxZr6JutAQehm-4kB1v4RA"
INSTANCE_ID = "159896"
ULTRA_TOKEN = "3a2kuk39wf15ejiu"

# إعداد جيمني بالموديل الأحدث
genai.configure(api_key=GEMINI_KEY)
model = genai.GenerativeModel('gemini-1.5-flash-latest')

@app.route('/')
def home():
    return "<h1>سيرفر الواتساب NJM يعمل بنجاح (بدون تليجرام) ✅</h1>", 200

# --- [ مسار الواتساب - Webhook ] ---
@app.route('/webhook', methods=['POST'])
def whatsapp_webhook():
    # استلام البيانات من UltraMsg
    data = request.get_json(force=True, silent=True)
    
    if data and data.get('event_type') == 'message_received':
        msg_body = data['data'].get('body')
        sender_id = data['data'].get('from')
        
        # التأكد من أن الرسالة ليست مرسلة من البوت
        if not data['data'].get('fromMe') and msg_body:
            print(f"📩 رسالة واتساب من {sender_id}: {msg_body}")
            try:
                # توليد الرد بلهجة سعودية تقنية
                prompt = f"أنت مساعد راشد علي محسن صالح. رد بلهجة سعودية: {msg_body}"
                ai_res = model.generate_content(prompt)
                
                # إرسال الرد عبر UltraMsg
                url = f"https://api.ultramsg.com/instance{INSTANCE_ID}/messages/chat"
                payload = {
                    "token": ULTRA_TOKEN, 
                    "to": sender_id, 
                    "body": ai_res.text
                }
                
                response = requests.post(url, data=payload)
                print(f"📡 نتيجة الإرسال: {response.status_code}")
                
            except Exception as e:
                print(f"❌ خطأ في معالجة جيمني: {e}")
                
    return "OK", 200

if __name__ == "__main__":
    # تشغيل السيرفر على المنفذ المخصص لـ Render
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)
