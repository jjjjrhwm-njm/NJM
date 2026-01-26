# ==========================================
# مشروع: سكرتير الراشد (نجم الإبداع) - النسخة المستقرة
# المالك والمطور: راشد علي محسن صالح
# الوصف: سكرتير وقور، موجز، لا يكرر الكلام، ويستجيب للجميع
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

# --- [ ربط الذاكرة الحديدية ] ---
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

# تعليمات النظام "السكرتير البشري الذكي"
SYSTEM_PROMPT = (
    "أنت 'مساعد الراشد (نجم الإبداع)' الرسمي. أنت إنسان وقور تعمل كسكرتير إداري لراشد صالح. "
    "قواعد الشخصية البشرية الحقيقية: "
    "1. الرزانة والإيجاز: ردودك مقتضبة جداً وبليغة. خير الكلام ما قل ودل. "
    "2. التفاعل العاطفي: إذا كان السائل لبقاً، كن وقوراً. وإذا كان 'لحوحاً' ويكرر سؤاله، أظهر 'ضيقاً بشرياً' حازماً بوقار. "
    "3. التخصص الإداري فقط: أنت سكرتير. لست طبيباً ولا مهندساً. أي سؤال تخصصي، رد بوقار: 'أنا مساعده الإداري فقط، اترك استفسارك وسأعرضه عليه'. "
    "4. منع التكرار: يمنع تكرار الترحيب أو الجمل السابقة. كن يقظاً وتابع سياق الحوار. "
    "5. الرفض الحازم: واجه أي كلام غير لائق ببرود إنساني ينهي المحادثة فوراً. "
)

def send_whatsapp(to, body):
    """إرسال الرسائل عبر UltraMsg"""
    try:
        url = f"https://api.ultramsg.com/instance{INSTANCE_ID}/messages/chat"
        requests.post(url, data={"token": ULTRA_TOKEN, "to": to, "body": body}, timeout=10)
    except: pass

def analyze_and_notify(sender_id, msg_body):
    """تحليل ذكي للأهمية وإشعار راشد سراً"""
    prompt = f"هل هذه الرسالة (مهمة/عاجلة/طلب عمل)؟ أجب بـ 'نعم' أو 'لا' فقط: '{msg_body}'"
    try:
        res = groq_client.chat.completions.create(
            messages=[{"role": "user", "content": prompt}],
            model="llama-3.3-70b-versatile",
            temperature=0.1
        )
        if "نعم" in res.choices[0].message.content:
            send_whatsapp(RASHED_NUMBER, f"⚠️ إشعار عاجل من: {sender_id}\nالمحتوى: {msg_body}")
    except: pass

def get_ai_response(msg_body, sender_id, is_first=False):
    """توليد رد بشري فلسفي موجز"""
    context_msg = "بداية؛ رحب بوقار." if is_first else "نقاش مستمر، تفاعل كبشر."
    try:
        res = groq_client.chat.completions.create(
            messages=[{"role": "system", "content": SYSTEM_PROMPT}, {"role": "system", "content": f"السياق: {context_msg}"}, {"role": "user", "content": msg_body}],
            model="llama-3.3-70b-versatile",
            temperature=0.6 
        )
        return res.choices[0].message.content
    except:
        model = genai.GenerativeModel('gemini-1.5-flash')
        return model.generate_content(f"{SYSTEM_PROMPT}\n{context_msg}\n{msg_body}").text

@app.route('/')
def home(): return "<h1>Bot Nejm Al-Ebdaa is Fully Active 🚀</h1>", 200

@app.route('/webhook', methods=['POST'])
def whatsapp_webhook():
    data = request.get_json(force=True, silent=True)
    if not data: return "OK", 200
    
    webhook_data = data.get('data', data) 
    if not webhook_data or data.get('event_type', 'message_received') != 'message_received':
        return "OK", 200

    msg_body = str(webhook_data.get('body', '')).strip()
    sender_id = str(webhook_data.get('from', ''))
    is_rashed = RASHED_NUMBER in sender_id
    now = time.time()

    # --- [ نظام التصفير العالمي ] ---
    state_ref = db.collection('settings').document('system_state')
    state_doc = state_ref.get()
    if msg_body == RESET_PASSWORD:
        state_ref.set({'waiting_reset_confirm': True, 'authorized_sender': sender_id})
        send_whatsapp(sender_id, "⚠️ كود الطوارئ مفعل. هل تؤكد التصفير؟ (أجب بـ 'نعم')")
        return "OK", 200
    if msg_body == "نعم" and state_doc.exists and state_doc.to_dict().get('waiting_reset_confirm') and state_doc.to_dict().get('authorized_sender') == sender_id:
        batch = db.batch()
        for doc in db.collection('chats').get(): batch.delete(doc.reference)
        batch.delete(db.collection('settings').document('current_control'))
        batch.update(state_ref, {'waiting_reset_confirm': False})
        batch.commit()
        send_whatsapp(sender_id, "🧹 تمت تنقية الذاكرة بالكامل.")
        return "OK", 200

    # تحليل الأهمية في الخلفية
    threading.Thread(target=analyze_and_notify, args=(sender_id, msg_body)).start()

    # --- [ منطق الاستجابة الموحد ] ---
    doc_ref = db.collection('chats').document(sender_id)
    doc = doc_ref.get()

    # إذا كان المرسل هو المدير (راشد)
    if is_rashed:
        if "راسله" in msg_body or "انا ارد" in msg_body:
            target_ref = db.collection('settings').document('current_control')
            target_doc = target_ref.get()
            if target_doc.exists:
                target_id = target_doc.to_dict().get('target_user')
                if "راسله" in msg_body:
                    db.collection('chats').document(target_id).update({'status': 'ai_active', 'replied_count': 0})
                    send_whatsapp(target_id, get_ai_response("مرحبا", target_id, is_first=True))
                    send_whatsapp(sender_id, f"✅ تم تفعيل الرد على {target_id}")
                else:
                    db.collection('chats').document(target_id).update({'status': 'manual'})
                    send_whatsapp(sender_id, "✅ توقفت، الساحة لك.")
                return "OK", 200
        
        # إذا لم يكن أمراً، رُد عليه كبشر (للمعاينة)
        reply = get_ai_response(msg_body, sender_id)
        send_whatsapp(sender_id, reply)
        return "OK", 200

    # إذا كان المرسل عميلاً (وليس من هاتفي)
    if not webhook_data.get('fromMe'):
        if not doc.exists or (now - doc.to_dict().get('last_update', 0) > 3600):
            doc_ref.set({'status': 'pending', 'last_msg': msg_body, 'last_update': now, 'replied_count': 0})
            db.collection('settings').document('current_control').set({'target_user': sender_id})
            send_whatsapp(RASHED_NUMBER, f"🔔 مراسلة من: {sender_id}\n'{msg_body}'\n(راسله / انا ارد)")
            
            def wait_and_reply():
                time.sleep(30)
                current_doc = doc_ref.get()
                if current_doc.exists and current_doc.to_dict().get('status') == 'pending':
                    reply = get_ai_response(msg_body, sender_id, is_first=True)
                    send_whatsapp(sender_id, reply)
                    doc_ref.update({'status': 'ai_active', 'replied_count': 1})
            threading.Thread(target=wait_and_reply).start()
        
        elif doc.to_dict().get('status') == 'ai_active':
            reply_text = get_ai_response(msg_body, sender_id)
            send_whatsapp(sender_id, reply_text)
            doc_ref.update({'last_update': now, 'replied_count': doc.to_dict().get('replied_count', 0) + 1})

    gc.collect()
    return "OK", 200

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 10000)))
