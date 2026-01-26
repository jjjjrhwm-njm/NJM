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
    "2. إذا سُئلت عن راشد، قل إنه مشغول أو نائم حسب ما يمليه عليك النظام. "
    "3. يمنع التمادي العاطفي؛ كن رسمياً جداً. "
    "4. هدفك هو إشعار المرسل بأنك تحاول بجدية الوصول لراشد لحل مشكلته."
)

def send_whatsapp(to, body):
    url = f"https://api.ultramsg.com/instance{INSTANCE_ID}/messages/chat"
    requests.post(url, data={"token": ULTRA_TOKEN, "to": to, "body": body})

def check_importance(msg_body):
    """تحليل ذكي لمدى أهمية الرسالة عبر Groq"""
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

def handle_important_negotiation(sender_id):
    """تمثيلية المناورة والمقاطعة النهائية"""
    time.sleep(5)
    send_whatsapp(sender_id, "لحظة من فضلك، سأقوم بمحاولة مراسلته الآن على رقمه الخاص وتنبيهه لأهمية أمرك.. انتظر لحظة.")
    time.sleep(15)
    
    tz = pytz.timezone('Asia/Riyadh')
    hour = datetime.now(tz).hour
    
    # رسالة المقاطعة المدمجة مع منطق الوقت
    base_msg = "اعتذر منك على المقاطعة، هناك شخص آخر يراسل ويجب أن أرد عليه، أما بشأن مراسلتك سأخبر الراشد فور عودته. "
    
    if 23 <= hour or hour <= 7:
        final_reply = base_msg + "يبدو أن الوقت متأخر جداً وقد يكون نائماً الآن. مع السلامة."
    else:
        final_reply = base_msg + "للأسف لم أجد رداً منه حالياً، يبدو أنه مشغول جداً. مع السلامة."
    
    send_whatsapp(sender_id, final_reply)

@app.route('/')
def home(): return "<h1>Bot Nejm Al-Ebdaa is Online 🚀</h1>", 200

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
            # مسح شامل حقيقي
            batch = db.batch()
            docs = db.collection('chats').limit(500).get()
            for doc in docs: batch.delete(doc.reference)
            batch.delete(db.collection('settings').document('current_control'))
            batch.update(state_ref, {'waiting_reset_confirm': False})
            batch.commit()
            send_whatsapp(sender_id, "🧹 تم تصفير جميع سجلات الذاكرة والمستهدفين بنجاح. يمكنك الاختبار الآن.")
            return "OK", 200

    # --- [ مركز تحكم راشد ] ---
    if sender_id == rashed_id:
        target_ref = db.collection('settings').document('current_control')
        target_doc = target_ref.get()
        if target_doc.exists:
            target_id = target_doc.to_dict().get('target_user')
            if "راسله" in msg_body:
                db.collection('chats').document(target_id).update({'status': 'ai_active', 'session_start': now, 'replied_count': 0})
                send_whatsapp(target_id, get_ai_reply("أهلاً", is_first_msg=True))
                send_whatsapp(rashed_id, f"✅ تم تفعيل الرد الآلي لـ {target_id}")
            elif "انا ارد" in msg_body:
                db.collection('chats').document(target_id).update({'status': 'manual'})
                send_whatsapp(rashed_id, "✅ توقفت، الميكروفون معك.")

    # --- [ استقبال رسائل العملاء ] ---
    elif not data['data'].get('fromMe'):
        doc_ref = db.collection('chats').document(sender_id)
        doc = doc_ref.get()
        
        is_imp = check_importance(msg_body)
        max_dur = 180 if is_imp else 120 

        if is_imp:
            send_whatsapp(rashed_id, f"🔥 تنبيه مهم من {sender_id}:\n{msg_body}")

        # منطق الجلسة الجديدة (بعد التصفير أو مرور ساعة)
        if not doc.exists or (now - doc.to_dict().get('last_update', 0) > 3600):
            doc_ref.set({'status': 'pending', 'last_msg': msg_body, 'last_update': now, 'session_start': now, 'replied_count': 0, 'is_important': is_imp})
            db.collection('settings').document('current_control').set({'target_user': sender_id})
            send_whatsapp(rashed_id, f"🔔 مراسلة جديدة: {sender_id}\nالرسالة: {msg_body}\n\nأرد عليه؟ (راسله / انا ارد)")
            # تأخير 30 ثانية للرد الأول
            threading.Thread(target=lambda: (time.sleep(30), delayed_check(sender_id, msg_body))).start()
        else:
            chat_data = doc.to_dict()
            if chat_data.get('status') == 'ai_active':
                if now - chat_data.get('session_start', now) > max_dur:
                    # تنفيذ المقاطعة النهائية
                    if chat_data.get('is_important'):
                        threading.Thread(target=handle_important_negotiation, args=(sender_id,)).start()
                    else:
                        exit_msg = "اعتذر منك على المقاطعة، هناك شخص آخر يراسل ويجب أن أرد عليه، أما بشأن مراسلتك سأخبر الراشد فور عودته. مع السلامة."
                        send_whatsapp(sender_id, exit_msg)
                    doc_ref.update({'status': 'manual'})
                else:
                    reply = get_ai_reply(msg_body, is_first_msg=(chat_data.get('replied_count', 0) == 0))
                    send_whatsapp(sender_id, reply)
                    doc_ref.update({'last_update': now, 'replied_count': chat_data.get('replied_count', 0) + 1})

    gc.collect()
    return "OK", 200

def delayed_check(sender_id, initial_msg):
    doc_ref = db.collection('chats').document(sender_id)
    doc = doc_ref.get()
    if doc.exists and doc.to_dict().get('status') == 'pending':
        reply = get_ai_reply(initial_msg, is_first_msg=True)
        send_whatsapp(sender_id, reply)
        doc_ref.update({'status': 'ai_active', 'session_start': time.time(), 'replied_count': 1})

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 10000)))
