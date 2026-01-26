import os
import json
import requests
import threading
import time
import gc
from flask import Flask, request
from groq import Groq
import google.generativeai as genai
import firebase_admin
from firebase_admin import credentials, firestore

app = Flask(__name__)

# --- [ الإعدادات القيادية - نجم الإبداع ] ---
RASHED_NUMBER = "0554526287" # رقمك الشخصي
INSTANCE_ID = "159896"
ULTRA_TOKEN = "3a2kuk39wf15ejiu"

# --- [ ربط الذاكرة الحديدية - Firestore ] ---
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

# تعليمات النظام الصارمة (درع الأخلاق والوقار)
SYSTEM_PROMPT = (
    "أنت 'مساعد نجم الإبداع' الرسمي. تتحدث بوقار بلسان راشد علي محسن صالح. "
    "قواعد الرد الصارمة: "
    "1. الرد الأول دائماً: 'مرحباً بك، أنا مساعد الراشد (نجم الإبداع)، كيف يمكنني مساعدتك؟'. "
    "2. إذا سُئلت 'أين راشد؟': 'يبدو أنه مشغول حالياً، إذا كان هناك أمر مهم أخبرني به وسأقوم بإيصال الخبر له فور عودته'. "
    "3. يمنع منعاً باتاً أي ردود عاطفية، رومانسية، أو تمادٍ في الكلام؛ كن رسمياً ووقوراً. "
    "4. لا تذكر أنك ذكاء اصطناعي إلا عند الضرورة، وقل: 'أنا مساعده الرقمي الرسمي'."
)

def send_whatsapp(to, body):
    url = f"https://api.ultramsg.com/instance{INSTANCE_ID}/messages/chat"
    requests.post(url, data={"token": ULTRA_TOKEN, "to": to, "body": body})

def analyze_and_notify_importance(sender_id, msg_body):
    """تحليل الرسالة لإرسال إشعار سري لراشد إذا كانت هامة جداً"""
    analysis_prompt = f"حلل الرسالة التالية: '{msg_body}'. هل تحتوي على خبر هام، موعد، طلب شراء، أو أمر طارئ؟ أجب بكلمة 'نعم' أو 'لا' فقط."
    try:
        res = groq_client.chat.completions.create(
            messages=[{"role": "user", "content": analysis_prompt}],
            model="llama-3.3-70b-versatile",
            temperature=0.1
        )
        if "نعم" in res.choices[0].message.content:
            secret_msg = f"⚠️ خبر مهم من {sender_id}:\n{msg_body}"
            send_whatsapp(RASHED_NUMBER, secret_msg)
    except:
        pass

def get_ai_reply(msg_body):
    try:
        res = groq_client.chat.completions.create(
            messages=[{"role": "system", "content": SYSTEM_PROMPT}, {"role": "user", "content": msg_body}],
            model="llama-3.3-70b-versatile",
            temperature=0.3
        )
        return res.choices[0].message.content
    except:
        model = genai.GenerativeModel('gemini-1.5-flash')
        res = model.generate_content(SYSTEM_PROMPT + "\n\nالمستخدم: " + msg_body)
        return res.text

def delayed_check(sender_id, initial_msg):
    """الانتظار لمدة 30 ثانية قبل الرد الآلي في حال عدم تدخل راشد"""
    time.sleep(30)
    doc_ref = db.collection('chats').document(sender_id)
    doc = doc_ref.get()
    if doc.exists and doc.to_dict().get('status') == 'pending':
        reply = get_ai_reply(initial_msg)
        send_whatsapp(sender_id, reply)
        doc_ref.update({'status': 'ai_active', 'session_start': time.time()})

@app.route('/')
def home():
    return "<h1>Bot Nejm Al-Ebdaa is Online 🚀</h1>", 200

@app.route('/webhook', methods=['POST'])
def whatsapp_webhook():
    data = request.get_json(force=True, silent=True)
    if not data or data.get('event_type') != 'message_received':
        return "OK", 200

    msg_body = data['data'].get('body', '').strip()
    sender_id = data['data'].get('from')
    rashed_id = f"{RASHED_NUMBER}@c.us"
    now = time.time()

    # [1] مركز تحكم راشد (القيادة والسيطرة)
    if sender_id == rashed_id:
        control_ref = db.collection('settings').document('current_control')
        control_doc = control_ref.get()
        if control_doc.exists:
            target_id = control_doc.to_dict().get('target_user')
            if "راسله" in msg_body:
                db.collection('chats').document(target_id).update({'status': 'ai_active', 'session_start': now})
                send_whatsapp(target_id, get_ai_reply("أهلاً"))
                send_whatsapp(rashed_id, f"✅ تم تفعيل الرد الآلي لـ {target_id}")
            elif "انا ارد" in msg_body:
                db.collection('chats').document(target_id).update({'status': 'manual'})
                send_whatsapp(rashed_id, "✅ تم إيقاف الرد الآلي، الميكروفون معك.")

    # [2] استقبال رسائل العملاء (نظام الحماية والحد الزمني)
    elif not data['data'].get('fromMe'):
        doc_ref = db.collection('chats').document(sender_id)
        doc = doc_ref.get()
        
        # تحليل الأهمية في الخلفية لإشعار راشد سراً
        threading.Thread(target=analyze_and_notify_importance, args=(sender_id, msg_body)).start()

        is_new_session = False
        if doc.exists:
            last_update = doc.to_dict().get('last_update', 0)
            if now - last_update > 3600: # إذا مرت ساعة
                is_new_session = True

        if not doc.exists or is_new_session:
            # بدء محادثة جديدة أو جلسة جديدة بعد انقطاع ساعة
            doc_ref.set({
                'status': 'pending', 
                'last_msg': msg_body, 
                'last_update': now,
                'session_start': now
            })
            db.collection('settings').document('current_control').set({'target_user': sender_id})
            
            notification = f"🔔 مراسلة من {sender_id}\nالرسالة: {msg_body}\n\nأرد عليه؟ (راسله / انا ارد)"
            send_whatsapp(rashed_id, notification)
            threading.Thread(target=delayed_check, args=(sender_id, msg_body)).start()
        
        else:
            chat_data = doc.to_dict()
            current_status = chat_data.get('status')
            session_start = chat_data.get('session_start', now)
            
            if current_status == 'ai_active':
                # فحص الحد الزمني (120 ثانية = دقيقتين)
                if now - session_start > 120:
                    exit_msg = "اعتذر منك، هناك شخص آخر قام بمراسلة نجم الإبداع ولا بد لي من الرد عليه، وسأخبر نجم الإبداع عند عودته بأنك قمت بمراسلته. مع السلامة."
                    send_whatsapp(sender_id, exit_msg)
                    doc_ref.update({'status': 'manual', 'last_update': now})
                else:
                    send_whatsapp(sender_id, get_ai_reply(msg_body))
                    doc_ref.update({'last_update': now})

    gc.collect()
    return "OK", 200

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)
