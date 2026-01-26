import os
import json
import requests
import threading
import time
import gc
from datetime import datetime
import pytz
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

# --- [ ربط الذاكرة الحديدية ] ---
firebase_raw = os.getenv("FIREBASE_JSON")
if firebase_raw:
    service_account_info = json.loads(firebase_raw)
    cred = credentials.Certificate(service_account_info)
    if not firebase_admin._apps:
        firebase_admin.initialize_app(cred)
    db = firestore.client()

# --- [ إعداد المحركات ] ---
groq_client = Groq(api_key=os.getenv("GROQ_API_KEY"))
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))

SYSTEM_PROMPT = (
    "أنت المساعد الرقمي لـ 'نجم الإبداع' (راشد صالح). رد بوقار وهيبة. "
    "قواعد التفاعل: "
    "1. الرد الأول ترحيبي وقور. "
    "2. إذا سُئلت عن راشد، قل إنه مشغول حالياً وسيقوم بالرد فور تفرغه. "
    "3. يمنع التمادي العاطفي؛ كن رسمياً جداً. "
    "4. هدفك هو إشعار المرسل بأنك مهتم بمساعدته وإيصال خبره لراشد."
)

def send_whatsapp(to, body):
    url = f"https://api.ultramsg.com/instance{INSTANCE_ID}/messages/chat"
    requests.post(url, data={"token": ULTRA_TOKEN, "to": to, "body": body})

def check_importance(msg_body):
    """تحليل فوري للأهمية"""
    prompt = f"حلل هل هذه الرسالة تتضمن عملاً، بيعاً، شراءً، أو خبراً طارئاً؟ '{msg_body}'. أجب بـ (مهم) أو (عادي) فقط."
    try:
        res = groq_client.chat.completions.create(
            messages=[{"role": "user", "content": prompt}],
            model="llama-3.3-70b-versatile",
            temperature=0.1
        )
        return "مهم" in res.choices[0].message.content
    except: return False

def get_ai_reply(msg_body, is_first_msg=False):
    context = "بداية الحوار." if is_first_msg else "نقاش مستمر."
    try:
        res = groq_client.chat.completions.create(
            messages=[{"role": "system", "content": SYSTEM_PROMPT}, {"role": "system", "content": context}, {"role": "user", "content": msg_body}],
            model="llama-3.3-70b-versatile",
            temperature=0.4
        )
        return res.choices[0].message.content
    except:
        model = genai.GenerativeModel('gemini-1.5-flash')
        res = model.generate_content(f"{SYSTEM_PROMPT}\n{context}\nالمستخدم: {msg_body}")
        return res.text

@app.route('/')
def home():
    return "Bot Nejm Al-Ebdaa is Live & Unrestricted 🚀", 200

@app.route('/webhook', methods=['POST'])
def whatsapp_webhook():
    data = request.get_json(force=True, silent=True)
    if not data or data.get('event_type') != 'message_received':
        return "OK", 200

    msg_body = data['data'].get('body', '').strip()
    sender_id = data['data'].get('from')
    rashed_id = f"{RASHED_NUMBER}@c.us"
    now = time.time()

    # [1] نظام التصفير العالمي والتأكيد
    control_ref = db.collection('settings').document('system_state')
    state_doc = control_ref.get()

    if msg_body == RESET_PASSWORD:
        control_ref.set({'waiting_reset_confirm': True, 'authorized_sender': sender_id})
        send_whatsapp(sender_id, "⚠️ تم طلب تصفير الذاكرة. هل أنت متأكد؟ (أجب بـ 'نعم' للتأكيد)")
        return "OK", 200

    if msg_body == "نعم" and state_doc.exists and state_doc.to_dict().get('waiting_reset_confirm'):
        if state_doc.to_dict().get('authorized_sender') == sender_id:
            docs = db.collection('chats').get()
            for doc in docs: doc.reference.delete()
            db.collection('settings').document('current_control').delete()
            control_ref.update({'waiting_reset_confirm': False})
            send_whatsapp(sender_id, "🧹 تمت تنقية الذاكرة بالكامل بنجاح.")
            return "OK", 200

    # [2] معالجة الرسائل (المدير والعملاء)
    is_imp = check_importance(msg_body)
    if is_imp:
        send_whatsapp(rashed_id, f"🔥 تنبيه مهم من {sender_id}:\n{msg_body}")

    # إذا كان المرسل هو راشد (المدير)
    if sender_id == rashed_id:
        target_ref = db.collection('settings').document('current_control')
        target_doc = target_ref.get()
        if "راسله" in msg_body and target_doc.exists:
            target_id = target_doc.to_dict().get('target_user')
            db.collection('chats').document(target_id).update({'status': 'ai_active', 'replied_count': 0})
            send_whatsapp(target_id, get_ai_reply("أهلاً", is_first_msg=True))
            send_whatsapp(rashed_id, f"✅ تم تفعيل الرد على {target_id}")
            return "OK", 200
        elif "انا ارد" in msg_body and target_doc.exists:
            target_id = target_doc.to_dict().get('target_user')
            db.collection('chats').document(target_id).update({'status': 'manual'})
            send_whatsapp(rashed_id, "✅ توقفت، الميكروفون معك.")
            return "OK", 200
        
        # رد آلي مباشر لراشد إذا أرسل رسالة عادية (للاختبار)
        reply = get_ai_reply(msg_body, is_first_msg=False)
        send_whatsapp(rashed_id, reply)
        return "OK", 200

    # إذا كان المرسل عميلاً
    if not data['data'].get('fromMe'):
        doc_ref = db.collection('chats').document(sender_id)
        doc = doc_ref.get()

        if not doc.exists:
            # رد فوري للعملاء الجدد بدون انتظار 30 ثانية
            doc_ref.set({'status': 'ai_active', 'last_msg': msg_body, 'replied_count': 1})
            db.collection('settings').document('current_control').set({'target_user': sender_id})
            send_whatsapp(rashed_id, f"🔔 مراسلة جديدة: {sender_id}\n{msg_body}")
            reply = get_ai_reply(msg_body, is_first_msg=True)
            send_whatsapp(sender_id, reply)
        else:
            chat_data = doc.to_dict()
            if chat_data.get('status') == 'ai_active':
                # رد مستمر بدون أي قيود زمنية
                reply = get_ai_reply(msg_body, is_first_msg=(chat_data.get('replied_count', 0) == 0))
                send_whatsapp(sender_id, reply)
                doc_ref.update({'replied_count': chat_data.get('replied_count', 0) + 1})

    gc.collect()
    return "OK", 200

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 10000)))
