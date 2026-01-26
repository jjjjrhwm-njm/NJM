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

# --- [ الإعدادات القيادية ] ---
RASHED_NUMBER = "0554526287"
INSTANCE_ID = "159896"
ULTRA_TOKEN = "3a2kuk39wf15ejiu"
RESET_PASSWORD = "راشد1997" # كلمة السر لتصفير البيانات

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

# تعليمات النظام المتطورة لمنع التكرار
SYSTEM_PROMPT = (
    "أنت المساعد الرقمي الرسمي لـ 'نجم الإبداع' (راشد علي محسن صالح). رد بوقار وهيبة. "
    "قواعد التفاعل الذكي: "
    "1. إذا كانت هذه بداية الحوار (مثل قول المستخدم 'الو' أو 'أهلاً')، رحب به بعبارة: 'مرحباً بك، أنا مساعد الراشد (نجم الإبداع)، كيف يمكنني مساعدتك؟'. "
    "2. إذا كان المستخدم يتحدث عن موضوع محدد (مثل مرض، طلب خدمة، أو سؤال)، أجب عليه بذكاء ووقار دون تكرار رسالة الترحيب. "
    "3. إذا سُئلت 'أين راشد؟': 'يبدو أنه مشغول حالياً، اترك خبرك هنا وسأبلغه فور عودته'. "
    "4. يُمنع منعاً باتاً أي تمادٍ عاطفي أو رومانسي؛ كن رسمياً جداً. "
    "5. لا تذكر أنك ذكاء اصطناعي إلا إذا سُئلت مباشرة."
)

def send_whatsapp(to, body):
    url = f"https://api.ultramsg.com/instance{INSTANCE_ID}/messages/chat"
    requests.post(url, data={"token": ULTRA_TOKEN, "to": to, "body": body})

def analyze_importance(sender_id, msg_body):
    """إشعار راشد سراً بالأنباء الهامة"""
    prompt = f"هل هذه الرسالة تحتوي خبراً هاماً أو طارئاً؟ '{msg_body}'. أجب بـ نعم أو لا فقط."
    try:
        res = groq_client.chat.completions.create(
            messages=[{"role": "user", "content": prompt}],
            model="llama-3.3-70b-versatile",
            temperature=0.1
        )
        if "نعم" in res.choices[0].message.content:
            send_whatsapp(RASHED_NUMBER, f"⚠️ تنبيه مهم من {sender_id}:\n{msg_body}")
    except: pass

def get_ai_reply(msg_body, is_first_msg=False):
    # إضافة سياق للبوت ليعرف هل يحتاج للترحيب أم للرد المباشر
    context = "هذه بداية الحوار، ابدأ بالترحيب الرسمي." if is_first_msg else "هذا نقاش مستمر، أجب على المحتوى مباشرة بوقار."
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
    time.sleep(30)
    doc_ref = db.collection('chats').document(sender_id)
    doc = doc_ref.get()
    if doc.exists and doc.to_dict().get('status') == 'pending':
        reply = get_ai_reply(initial_msg, is_first_msg=True)
        send_whatsapp(sender_id, reply)
        doc_ref.update({'status': 'ai_active', 'session_start': time.time(), 'replied_count': 1})

@app.route('/webhook', methods=['POST'])
def whatsapp_webhook():
    data = request.get_json(force=True, silent=True)
    if not data or data.get('event_type') != 'message_received':
        return "OK", 200

    msg_body = data['data'].get('body', '').strip()
    sender_id = data['data'].get('from')
    rashed_id = f"{RASHED_NUMBER}@c.us"
    now = time.time()

    # [1] أوامر التحكم الخاصة براشد
    if sender_id == rashed_id:
        if msg_body == RESET_PASSWORD: # أمر التصفير السري
            docs = db.collection('chats').get()
            for doc in docs: doc.reference.delete()
            send_whatsapp(rashed_id, "🧹 تم تصفير جميع البيانات وسجلات المحادثات بنجاح.")
            return "OK", 200

        control_ref = db.collection('settings').document('current_control')
        control_doc = control_ref.get()
        if control_doc.exists:
            target_id = control_doc.to_dict().get('target_user')
            if "راسله" in msg_body:
                db.collection('chats').document(target_id).update({'status': 'ai_active', 'session_start': now, 'replied_count': 0})
                send_whatsapp(target_id, get_ai_reply("أهلاً", is_first_msg=True))
                send_whatsapp(rashed_id, f"✅ تم تفعيل الرد على {target_id}")
            elif "انا ارد" in msg_body:
                db.collection('chats').document(target_id).update({'status': 'manual'})
                send_whatsapp(rashed_id, "✅ توقفت، الميكروفون معك.")

    # [2] استقبال رسائل العملاء
    elif not data['data'].get('fromMe'):
        doc_ref = db.collection('chats').document(sender_id)
        doc = doc_ref.get()
        threading.Thread(target=analyze_importance, args=(sender_id, msg_body)).start()

        if not doc.exists or (now - doc.to_dict().get('last_update', 0) > 3600):
            doc_ref.set({'status': 'pending', 'last_msg': msg_body, 'last_update': now, 'session_start': now, 'replied_count': 0})
            db.collection('settings').document('current_control').set({'target_user': sender_id})
            send_whatsapp(rashed_id, f"🔔 مراسلة جديدة: {sender_id}\n{msg_body}\n(راسله / انا ارد)")
            threading.Thread(target=delayed_check, args=(sender_id, msg_body)).start()
        else:
            chat_data = doc.to_dict()
            if chat_data.get('status') == 'ai_active':
                if now - chat_data.get('session_start', now) > 120:
                    send_whatsapp(sender_id, "اعتذر، سأخبر نجم الإبداع بطلبك فور عودته. مع السلامة.")
                    doc_ref.update({'status': 'manual'})
                else:
                    # التحقق هل أرسل البوت ترحيباً سابقاً؟
                    is_first = chat_data.get('replied_count', 0) == 0
                    reply = get_ai_reply(msg_body, is_first_msg=is_first)
                    send_whatsapp(sender_id, reply)
                    doc_ref.update({'last_update': now, 'replied_count': chat_data.get('replied_count', 0) + 1})

    gc.collect()
    return "OK", 200

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 10000)))
