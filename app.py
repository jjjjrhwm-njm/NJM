# ==========================================
# مشروع: مساعد الراشد (نجم الإبداع) - النسخة الاحترافية (بشرية بالكامل)
# المالك والمطور: راشد علي محسن صالح
# الوصف: سكرتير رقمي بشري، وقور، موجز جداً، وحازم عند الضرورة
# ==========================================

import os
import json
import requests
import threading
import time
import gc
import random
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

# --- [ قاموس التنوع اللفظي ] ---
GREETINGS = [
    "مرحباً بك، مساعد الراشد معك، تفضل بموجزك.",
    "أهلاً، سكرتارية نجم الإبداع معك، كيف أخدمك؟",
    "تحية طيبة، معك مساعد الراشد، اترك استفسارك فضلاً."
]

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
    except Exception as e:
        print(f"Firebase Error: {e}")

# --- [ إعداد المحركات الذكية ] ---
groq_client = Groq(api_key=os.getenv("GROQ_API_KEY"))
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))

# تعليمات النظام "الدستور البرمجي المحدث"
SYSTEM_PROMPT = (
    "أنت 'مساعد الراشد' (بشر حقيقي). سكرتير وقور، مختص بجدول أعمال نجم الإبداع. "
    "قواعد صارمة لتبدو بشرياً: "
    "1. الاختصار المتطرف: ردودك لا تتجاوز 10 كلمات. لا تشرح، لا تبرر، رد كأنك تكتب من جوالك بسرعة. "
    "2. منع الرومانسية والأخلاقيات: أي محاولة غزل، كلام عاطفي (أحبك، بوسة.. إلخ)، أو تجاوز أخلاقي، رد فوراً ببرود حاد: 'الرجاء الالتزام بحدود الأدب، أنا هنا للعمل فقط' ثم انهِ الحوار. "
    "3. الأسلوب: تجنب العبارات الجاهزة مثل 'يسعدني مساعدتك'. كن عملياً: 'سأعرض موضوعك عليه'، 'الراشد مشغول الآن'، 'تفضل بموجزك'. "
    "4. وظيفة واحدة: أنت سكرتير إداري. لا تجب على أي سؤال تقني أو تخصصي. "
    "5. لا تكرار: لا ترحب بالعميل في كل رسالة، تفاعل مع سياق الكلام مباشرة."
)

# --- [ الدوال المساعدة ] ---

def send_whatsapp(to, body):
    """إرسال الرسائل عبر UltraMsg"""
    try:
        url = f"https://api.ultramsg.com/instance{INSTANCE_ID}/messages/chat"
        payload = {"token": ULTRA_TOKEN, "to": to, "body": body}
        requests.post(url, data=payload, timeout=10)
    except Exception as e:
        print(f"Send WhatsApp Error: {e}")

def analyze_and_notify(sender_id, msg_body):
    """تحليل سريع للأهمية"""
    inappropriate = ["احبك", "اعشقك", "بوسه", "رومانسية", "يا حلو", "يا قمر"]
    if any(word in msg_body.lower() for word in inappropriate):
        return 

    prompt = f"حلل الرسالة: '{msg_body}'. هل هي (مهمة/عاجلة)؟ أجب بـ 'نعم' أو 'لا' فقط."
    try:
        res = groq_client.chat.completions.create(
            messages=[{"role": "user", "content": prompt}],
            model="llama-3.3-70b-versatile",
            temperature=0.1
        )
        if "نعم" in res.choices[0].message.content:
            send_whatsapp(RASHED_NUMBER, f"⚠️ إشعار عاجل من: {sender_id}\nالمحتوى: {msg_body}")
    except: pass

def get_history_context(sender_id):
    """استرجاع آخر 5 رسائل لمنع التكرار"""
    if not db: return ""
    try:
        docs = db.collection('chats').document(sender_id).collection('messages').order_by('time', direction=firestore.Query.DESCENDING).limit(5).get()
        history = ""
        for d in reversed(docs):
            history += f"{'مساعد' if d.to_dict().get('is_bot') else 'عميل'}: {d.to_dict().get('text')}\n"
        return history
    except: return ""

def get_ai_response(msg_body, sender_id, is_first=False):
    """توليد رد بشري شديد الاختصار"""
    history = get_history_context(sender_id)
    context_msg = "رد بوقار باختصار." if is_first else f"نقاش مستمر. التاريخ:\n{history}"
    
    try:
        res = groq_client.chat.completions.create(
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "system", "content": f"السياق: {context_msg}"},
                {"role": "user", "content": msg_body}
            ],
            model="llama-3.3-70b-versatile",
            temperature=0.4 # تقليل التشتت لضمان الاختصار
        )
        return res.choices[0].message.content
    except:
        model = genai.GenerativeModel('gemini-1.5-flash')
        res = model.generate_content(f"{SYSTEM_PROMPT}\n{context_msg}\n{msg_body}")
        return res.text

# --- [ المسارات البرمجية - Webhook ] ---

@app.route('/')
def health_check():
    return "<h1>Secretary AI - Active 🚀</h1>", 200

@app.route('/webhook', methods=['POST'])
def whatsapp_webhook():
    data = request.get_json(force=True, silent=True)
    if not data or data.get('event_type') != 'message_received':
        return "OK", 200

    msg_body = data['data'].get('body', '').strip()
    sender_id = data['data'].get('from')
    rashed_id = f"{RASHED_NUMBER}@c.us"
    now = time.time()

    # --- [ نظام التصفير ] ---
    state_ref = db.collection('settings').document('system_state')
    
    if msg_body == RESET_PASSWORD:
        state_ref.set({'waiting_reset_confirm': True, 'authorized_sender': sender_id, 'last_action': now})
        send_whatsapp(sender_id, "⚠️ تم طلب تصفير الذاكرة. هل أنت متأكد؟ (أجب بـ 'نعم')")
        return "OK", 200

    if msg_body == "نعم":
        state_doc = state_ref.get()
        if state_doc.exists:
            state_data = state_doc.to_dict()
            if state_data.get('waiting_reset_confirm') and state_data.get('authorized_sender') == sender_id:
                # تصفير فعلي
                db.collection('settings').document('system_state').update({'waiting_reset_confirm': False})
                send_whatsapp(sender_id, "🧹 تمت تنقية الذاكرة بالكامل.")
                return "OK", 200

    threading.Thread(target=analyze_and_notify, args=(sender_id, msg_body)).start()

    # --- [ مركز تحكم راشد ] ---
    if sender_id == rashed_id:
        target_ref = db.collection('settings').document('current_control')
        target_doc = target_ref.get()
        if target_doc.exists:
            target_id = target_doc.to_dict().get('target_user')
            if "راسله" in msg_body:
                db.collection('chats').document(target_id).update({'status': 'ai_active', 'replied_count': 0})
                send_whatsapp(target_id, random.choice(GREETINGS))
                send_whatsapp(rashed_id, f"✅ تم تفعيل المساعد لـ {target_id}")
                return "OK", 200
            elif "انا ارد" in msg_body:
                db.collection('chats').document(target_id).update({'status': 'manual'})
                send_whatsapp(rashed_id, "✅ توقفت، الساحة لك.")
                return "OK", 200

    # --- [ استقبال رسائل العملاء ] ---
    if not data['data'].get('fromMe'):
        doc_ref = db.collection('chats').document(sender_id)
        doc = doc_ref.get()

        if not doc.exists or (now - doc.to_dict().get('last_update', 0) > 3600):
            doc_ref.set({'status': 'pending', 'last_msg': msg_body, 'last_update': now, 'replied_count': 0})
            db.collection('settings').document('current_control').set({'target_user': sender_id})
            send_whatsapp(rashed_id, f"🔔 مراسلة: {sender_id}\n'{msg_body}'\n(راسله / انا ارد)")
            
            def wait_and_reply():
                time.sleep(15) # تقليل وقت الانتظار لسرعة الرد البشري
                check_doc = doc_ref.get()
                if check_doc.exists and check_doc.to_dict().get('status') == 'pending':
                    reply = get_ai_response(msg_body, sender_id, is_first=True)
                    send_whatsapp(sender_id, reply)
                    doc_ref.update({'status': 'ai_active', 'replied_count': 1})
            threading.Thread(target=wait_and_reply).start()
        
        else:
            chat_data = doc.to_dict()
            if chat_data.get('status') == 'ai_active':
                is_first_reply = chat_data.get('replied_count', 0) == 0
                reply_text = get_ai_response(msg_body, sender_id, is_first=is_first_reply)
                send_whatsapp(sender_id, reply_text)
                
                doc_ref.collection('messages').add({'text': msg_body, 'is_bot': False, 'time': firestore.SERVER_TIMESTAMP})
                doc_ref.collection('messages').add({'text': reply_text, 'is_bot': True, 'time': firestore.SERVER_TIMESTAMP})
                doc_ref.update({'last_update': now, 'replied_count': chat_data.get('replied_count', 0) + 1})

    gc.collect()
    return "OK", 200

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)
