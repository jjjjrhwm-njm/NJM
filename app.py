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

# تعليمات النظام الصارمة (عقل البوت)
SYSTEM_PROMPT = (
    "أنت 'مساعد الراشد (نجم الإبداع)' الرسمي. تتحدث بوقار بلسان راشد علي محسن صالح. "
    "قواعد الرد الاحترافية: "
    "1. الرد الأول فقط يبدأ بـ: 'مرحباً بك، أنا مساعد الراشد (نجم الإبداع)، كيف يمكنني مساعدتك؟'. "
    "2. يمنع تكرار الترحيب في نفس المحادثة؛ أجب على الأسئلة مباشرة بوقار. "
    "3. إذا سأل السائل 'أين راشد؟' بأي صيغة، رد بوقار: 'يبدو أنه مشغول حالياً، إذا كان هناك أمر مهم أخبرني به وسأقوم بإيصال الخبر له فور عودته'. "
    "4. كن رسمياً، وقوراً، ومهذباً لأقصى درجة. لا تذكر أنك ذكاء اصطناعي إلا إذا سُئلت، وأجب بـ 'أنا مساعده الرقمي الرسمي'. "
    "5. لا تستخدم اسم 'الرشد'، بل استخدم 'الراشد' أو 'نجم الإبداع'."
)

def send_whatsapp(to, body):
    url = f"https://api.ultramsg.com/instance{INSTANCE_ID}/messages/chat"
    requests.post(url, data={"token": ULTRA_TOKEN, "to": to, "body": body})

def check_importance_and_notify(sender_id, msg_body):
    """تحليل سري للأهمية وإخطار راشد فوراً"""
    prompt = f"حلل الرسالة التالية: '{msg_body}'. هل تحتوي على خبر هام، موعد، طلب شراء، أو أمر طارئ؟ أجب بكلمة 'نعم' أو 'لا' فقط."
    try:
        res = groq_client.chat.completions.create(
            messages=[{"role": "user", "content": prompt}],
            model="llama-3.3-70b-versatile",
            temperature=0.1
        )
        if "نعم" in res.choices[0].message.content:
            # إشعار سري لراشد
            send_whatsapp(RASHED_NUMBER, f"⚠️ خبر مهم من رقم: {sender_id}\nالمحتوى: {msg_body}")
            return True
    except: pass
    return False

def get_ai_reply(msg_body, is_first_msg=False):
    # إخبار المحرك بحالة الحوار لمنع التكرار
    context = "هذه بداية الحوار، رحب بالعميل." if is_first_msg else "هذا نقاش مستمر، لا تكرر الترحيب، أجب على المطلوب بوقار."
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

def delayed_check(sender_id, initial_msg):
    """الانتظار لمدة 30 ثانية قبل الرد الآلي"""
    time.sleep(30)
    doc_ref = db.collection('chats').document(sender_id)
    doc = doc_ref.get()
    if doc.exists and doc.to_dict().get('status') == 'pending':
        reply = get_ai_reply(initial_msg, is_first_msg=True)
        send_whatsapp(sender_id, reply)
        doc_ref.update({'status': 'ai_active', 'session_start': time.time(), 'replied_count': 1})

@app.route('/')
def home(): return "<h1>Bot Nejm Al-Ebdaa is Online & Dignified 🚀</h1>", 200

@app.route('/webhook', methods=['POST'])
def whatsapp_webhook():
    data = request.get_json(force=True, silent=True)
    if not data or data.get('event_type') != 'message_received':
        return "OK", 200

    msg_body = data['data'].get('body', '').strip()
    sender_id = data['data'].get('from')
    rashed_id = f"{RASHED_NUMBER}@c.us"
    now = time.time()

    # --- [ نظام التصفير العالمي والتأكيد ] ---
    state_ref = db.collection('settings').document('system_state')
    state_doc = state_ref.get()

    if msg_body == RESET_PASSWORD:
        state_ref.set({'waiting_reset_confirm': True, 'authorized_sender': sender_id, 'last_action': now})
        send_whatsapp(sender_id, "⚠️ تم التعرف على رمز الطوارئ. هل أنت متأكد من تصفير جميع البيانات؟ (أجب بـ 'نعم' للتأكيد)")
        return "OK", 200

    if msg_body == "نعم" and state_doc.exists:
        state_data = state_doc.to_dict()
        if state_data.get('waiting_reset_confirm') and state_data.get('authorized_sender') == sender_id:
            batch = db.batch()
            docs = db.collection('chats').limit(500).get()
            for doc in docs: batch.delete(doc.reference)
            batch.delete(db.collection('settings').document('current_control'))
            batch.update(state_ref, {'waiting_reset_confirm': False})
            batch.commit()
            send_whatsapp(sender_id, "🧹 تم تصفير جميع السجلات. المساعد الآن في وضع الاستعداد.")
            return "OK", 200

    # --- [ معالجة الرسائل والتحكم ] ---
    # تحليل الأهمية في الخلفية لجميع الأرقام
    threading.Thread(target=check_importance_and_notify, args=(sender_id, msg_body)).start()

    # [ مركز التحكم ]
    if sender_id == rashed_id:
        target_ref = db.collection('settings').document('current_control')
        target_doc = target_ref.get()
        if target_doc.exists:
            target_id = target_doc.to_dict().get('target_user')
            if "راسله" in msg_body:
                db.collection('chats').document(target_id).update({'status': 'ai_active', 'replied_count': 0})
                send_whatsapp(target_id, get_ai_reply("أهلاً", is_first_msg=True))
                send_whatsapp(rashed_id, f"✅ تم تفعيل الرد الآلي لـ {target_id}")
                return "OK", 200
            elif "انا ارد" in msg_body:
                db.collection('chats').document(target_id).update({'status': 'manual'})
                send_whatsapp(rashed_id, "✅ توقفت، الميكروفون معك.")
                return "OK", 200

    # [ التعامل مع العميل ] (بما في ذلك رقم راشد لاختبار تجربة المستخدم)
    if not data['data'].get('fromMe'):
        doc_ref = db.collection('chats').document(sender_id)
        doc = doc_ref.get()

        # جلسة جديدة (بعد التصفير أو أول مرة)
        if not doc.exists or (now - doc.to_dict().get('last_update', 0) > 3600):
            doc_ref.set({'status': 'pending', 'last_msg': msg_body, 'last_update': now, 'session_start': now, 'replied_count': 0})
            db.collection('settings').document('current_control').set({'target_user': sender_id})
            
            # إشعار لراشد
            send_whatsapp(rashed_id, f"🔔 مراسلة جديدة من: {sender_id}\nالرسالة: {msg_body}\n\nأرد عليه؟ (راسله / انا ارد)")
            # بدء عداد الـ 30 ثانية
            threading.Thread(target=delayed_check, args=(sender_id, msg_body)).start()
        
        else:
            chat_data = doc.to_dict()
            if chat_data.get('status') == 'ai_active':
                # الرد المستمر (بدون قيود وقت لراشد، وبدون تكرار الترحيب)
                is_first = chat_data.get('replied_count', 0) == 0
                reply = get_ai_reply(msg_body, is_first_msg=is_first)
                send_whatsapp(sender_id, reply)
                doc_ref.update({'last_update': now, 'replied_count': chat_data.get('replied_count', 0) + 1})

    gc.collect()
    return "OK", 200

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 10000)))
