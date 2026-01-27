# ==========================================
# مشروع: سكرتير الراشد (نجم الإبداع) - إدارة محل البنشر
# المالك والمطور: راشد علي محسن صالح
# الميزات: اختصار حاد، منع التجاوز، قاعدة بيانات المحل، تأخير بشري
# ==========================================

import os
import json
import requests
import threading
import time
import gc
import random
from flask import Flask, request
from groq import Groq
import google.generativeai as genai
import firebase_admin
from firebase_admin import credentials, firestore

app = Flask(__name__)

# --- [ الإعدادات القيادية ] ---
RASHED_NUMBER = "966554526287" 
INSTANCE_ID = "159896"
ULTRA_TOKEN = "3a2kuk39wf15ejiu"
RESET_PASSWORD = "00001111" 

# --- [ قاعدة بيانات المحل - معلومات حقيقية ] ---
STORE_INFO = """
معلومات محل البنشر الخاص بنا:
- الموقع: السعودية.
- التخصص: بيع كفرات (إطارات) بالجملة والتجزئة.
- المخزون: متوفر أكثر من 2000 كفر من مختلف الأنواع.
- العمالة: يوجد 15 عامل مختص لخدمتكم.
- أوقات العمل: من السبت للخميس (صباحاً ومساءً)، الجمعة (عصراً).
- التعامل: كاش وأجل للشركات المعتمدة.
"""

# --- [ ربط الذاكرة الحديدية - Firestore ] ---
firebase_raw = os.getenv("FIREBASE_JSON")
db = None
if firebase_raw:
    try:
        service_account_info = json.loads(firebase_raw)
        cred = credentials.Certificate(service_account_info)
        if not firebase_admin._apps:
            firebase_admin.initialize_app(cred)
        db = firestore.client()
    except Exception as e: print(f"Firebase Error: {e}")

# --- [ إعداد المحركات الذكية ] ---
groq_client = Groq(api_key=os.getenv("GROQ_API_KEY"))
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))

SYSTEM_PROMPT = (
    f"أنت سكرتير بشري حقيقي لمحل بنشر 'نجم الإبداع' لمالكه الراشد. "
    f"معلوماتك الأساسية: {STORE_INFO} "
    "قواعد صارمة: "
    "1. الاختصار الحاد: رد بحد أقصى 10 كلمات. "
    "2. الحزم الأخلاقي: أي غزل أو قلة أدب، رد بـ 'التزم بالأدب، أنا هنا للعمل' ثم اصمت. "
    "3. الذكاء المهني: إذا سأل عن الكفرات أو المحل، أجب من قاعدة بياناتك باختصار. "
    "4. لا روبوتية: لا تستخدم 'يسعدني مساعدتك'. رد مثل: 'موجودين، تفضل'، 'سأبلغ الراشد بطلبك'."
)

# --- [ الدوال المساعدة ] ---

def send_whatsapp(to, body):
    """إرسال الرسائل مع تأخير بشري عشوائي"""
    # إضافة تأخير بشري (من 4 إلى 10 ثواني) ليوحي بأن هناك شخص يكتب
    time.sleep(random.randint(4, 10))
    try:
        url = f"https://api.ultramsg.com/instance{INSTANCE_ID}/messages/chat"
        payload = {"token": ULTRA_TOKEN, "to": to, "body": body}
        requests.post(url, data=payload, timeout=10)
    except Exception as e: print(f"Error: {e}")

def get_ai_response(msg_body, sender_id):
    """توليد رد سكرتارية ذكي"""
    try:
        res = groq_client.chat.completions.create(
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": msg_body}
            ],
            model="llama-3.3-70b-versatile",
            temperature=0.4
        )
        return res.choices[0].message.content
    except:
        model = genai.GenerativeModel('gemini-1.5-flash')
        res = model.generate_content(f"{SYSTEM_PROMPT}\n\nالزبون يقول: {msg_body}")
        return res.text

# --- [ المسار الرئيسي - Webhook ] ---

@app.route('/webhook', methods=['POST'])
def whatsapp_webhook():
    data = request.get_json(force=True, silent=True)
    if not data or data.get('event_type') != 'message_received':
        return "OK", 200

    msg_body = data['data'].get('body', '').strip()
    sender_id = data['data'].get('from')
    rashed_id = f"{RASHED_NUMBER}@c.us"
    
    # استثناء رسائل الراشد نفسه
    if sender_id == rashed_id: return "OK", 200

    # نظام التصفير
    if msg_body == RESET_PASSWORD:
        send_whatsapp(sender_id, "🧹 تمت تنقية الذاكرة.")
        return "OK", 200

    # تشغيل الرد في خيط منفصل لتجنب تأخير الخادم
    def handle_reply():
        reply = get_ai_response(msg_body, sender_id)
        send_whatsapp(sender_id, reply)

    threading.Thread(target=handle_reply).start()
    
    gc.collect()
    return "OK", 200

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 10000)))
