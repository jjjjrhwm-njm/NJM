import os
import json
import requests
import threading
import time
import gc
import random
from flask import Flask, request, Response # أضفنا Response لعرض الصورة
from groq import Groq
import google.generativeai as genai

app = Flask(__name__)

# --- [ إعدادات محرك WAHA (المجاني) ] ---
WAHA_URL = "https://waha-latest-r55z.onrender.com"
WAHA_API_KEY = "0564b7ccca284292bd555fe8ae91b819" 
HEADERS = {"X-Api-Key": WAHA_API_KEY}

# الإعدادات القديمة (تم الاستغناء عن ULTRA_TOKEN)
RASHED_NUMBER = "966554526287" 

# --- [ قاعدة بيانات المحل ] ---
STORE_INFO = """
معلومات محل بنشر نجم الإبداع:
- الموقع: الأحساء، السعودية.
- التخصص: بيع كفرات بالجملة والتجزئة.
- المخزون: +2000 كفر متنوع.
- العمالة: 15 عامل مختص.
- أوقات العمل: سبت-خميس (صباح ومساء)، الجمعة (عصر).
"""

# --- [ مسار جلب كود QR للربط المجاني ] ---
@app.route('/get_qr')
def get_qr():
    """مسار يعرض كود QR مباشرة في المتصفح لربط الواتساب"""
    try:
        # طلب لقطة الشاشة من سيرفرك
        res = requests.get(f"{WAHA_URL}/api/screenshot?session=default", headers=HEADERS)
        if res.status_code == 200:
            return Response(res.content, mimetype='image/png')
        else:
            return "❌ تأكد من تشغيل الجلسة في سيرفر WAHA أولاً.", 404
    except Exception as e:
        return f"🛑 خطأ في الاتصال بالسيرفر: {str(e)}", 500

# --- [ إرسال الرسائل عبر WAHA ] ---
def send_whatsapp(to, body):
    """إرسال الرسائل عبر سيرفرك الخاص (مجاناً)"""
    time.sleep(random.randint(4, 10)) # تأخير بشري
    try:
        url = f"{WAHA_URL}/api/sendText"
        # واتساب يتطلب الرقم بصيغة معينة في WAHA
        chat_id = f"{to}@c.us" if "@" not in to else to
        payload = {
            "session": "default",
            "chatId": chat_id,
            "text": body
        }
        requests.post(url, json=payload, headers=HEADERS, timeout=10)
    except Exception as e: 
        print(f"Error sending message: {e}")

# --- [ المحرك الذكي والويب هوك - كما هو مع تعديل بسيط ] ---
@app.route('/webhook', methods=['POST'])
def whatsapp_webhook():
    # ملاحظة: سيرفر WAHA يرسل البيانات بتنسيق مختلف عن UltraMsg
    data = request.get_json(force=True, silent=True)
    
    # التحقق من أن الرسالة واردة وليست صادرة
    if not data or 'payload' not in data: return "OK", 200
    
    msg_data = data['payload']
    msg_body = msg_data.get('body', '').strip()
    sender_id = msg_data.get('from') # رقم المرسل
    
    # استثناء رسائل الراشد
    if sender_id and str(RASHED_NUMBER) in sender_id: return "OK", 200

    def handle_reply():
        # هنا تضع دالة get_ai_response الخاصة بك (Gemini/Groq)
        # سأفترض أنها موجودة كما في كودك السابق
        reply = "أهلاً بك في نجم الإبداع، كيف أخدمك؟" # مثال
        send_whatsapp(sender_id, reply)

    threading.Thread(target=handle_reply).start()
    return "OK", 200

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 10000)))
