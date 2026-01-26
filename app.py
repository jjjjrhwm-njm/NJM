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
RASHED_NUMBER = "0554526287" # رقمك الشخصي
INSTANCE_ID = "159896"
ULTRA_TOKEN = "3a2kuk39wf15ejiu"

# --- [ ربط الذاكرة الحديدية ] ---
firebase_raw = os.getenv("FIREBASE_JSON")
if firebase_raw:
    service_account_info = json.loads(firebase_raw)
    cred = credentials.Certificate(service_account_info)
    if not firebase_admin._apps:
        firebase_admin.initialize_app(cred)
    db = firestore.client()

# --- [ إعداد المحركات والقيود الأخلاقية ] ---
groq_client = Groq(api_key=os.getenv("GROQ_API_KEY"))
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))

# تعليمات صارمة للمحرك لضمان الوقار وعدم التمادي
SYSTEM_PROMPT = (
    "أنت 'مساعد نجم الإبداع' الرسمي والذكي. رد بلسان صاحب الحساب (راشد علي محسن صالح). "
    "قواعد صارمة: "
    "1. ممنوع تماماً أي ردود عاطفية، رومانسية، أو مفرطة في اللطافة. "
    "2. لغة الرد هي العربية الفصحى أو البيضاء الوقورة، بأسلوب عملي، اجتماعي، ورسمي جداً. "
    "3. إذا حاول السائل التمادي في مواضيع شخصية أو غير لائقة، اعتذر بوقار واطلب منه الالتزام بموضوع العمل. "
    "4. هدفك هو تمثيل مؤسسة 'نجم الإبداع' بأقصى درجات الاحترام والمهنية."
)

def send_whatsapp(to, body):
    url = f"https://api.ultramsg.com/instance{INSTANCE_ID}/messages/chat"
    requests.post(url, data={"token": ULTRA_TOKEN, "to": to, "body": body})

def get_ai_reply(msg_body):
    try:
        # المحاولة عبر Groq ببارامترات تضمن الجدية
        res = groq_client.chat.completions.create(
            messages=[{"role": "system", "content": SYSTEM_PROMPT}, {"role": "user", "content": msg_body}],
            model="llama-3.3-70b-versatile",
            temperature=0.3 # درجة حرارة منخفضة لتقليل الخيال والتمادي
        )
        return res.choices[0].message.content
    except:
        # احتياطي عبر Gemini
        model = genai.GenerativeModel('gemini-1.5-flash')
        res = model.generate_content(SYSTEM_PROMPT + "\n\nالمستخدم: " + msg_body)
        return res.text

def delayed_check(sender_id, initial_msg):
    time.sleep(30)
    doc_ref = db.collection('chats').document(sender_id)
    doc = doc_ref.get()
    
    if doc.exists and doc.to_dict().get('status') == 'pending':
        reply = get_ai_reply(initial_msg)
        send_whatsapp(sender_id, reply)
        doc_ref.update({'status': 'ai_active'})
        print(f"✅ انتهت الـ 30 ثانية: الذكاء رد على {sender_id}")

@app.route('/webhook', methods=['POST'])
def whatsapp_webhook():
    data = request.get_json(force=True, silent=True)
    if not data or data.get('event_type') != 'message_received':
        return "OK", 200

    msg_body = data['data'].get('body', '').strip()
    sender_id = data['data'].get('from')
    rashed_id = f"{RASHED_NUMBER}@c.us"

    # [1] مركز تحكم راشد - إدارة العمليات
    if sender_id == rashed_id:
        # جلب الشخص الذي أرسلنا لراشد تنبيهاً بشأنه مؤخراً
        control_ref = db.collection('settings').document('current_control')
        control_doc = control_ref.get()
        
        if control_doc.exists:
            target_id = control_doc.to_dict().get('target_user')
            
            if "راسله" in msg_body:
                db.collection('chats').document(target_id).update({'status': 'ai_active'})
                reply = get_ai_reply("أهلاً")
                send_whatsapp(target_id, reply)
                send_whatsapp(rashed_id, f"✅ علم، بدأت الرد الآلي على: {target_id}")
            elif "انا ارد" in msg_body:
                db.collection('chats').document(target_id).update({'status': 'manual'})
                send_whatsapp(rashed_id, f"✅ تم، سأصمت الآن تجاه: {target_id}")

    # [2] استقبال رسائل العملاء (نظام العزل الذكي)
    elif not data['data'].get('fromMe'):
        doc_ref = db.collection('chats').document(sender_id)
        doc = doc_ref.get()

        if not doc.exists:
            # عميل جديد تماماً
            doc_ref.set({'status': 'pending', 'last_msg': msg_body})
            
            # تحديد هذا العميل كـ "مستهدف حالي" لراشد لضمان عدم تداخل الأرقام
            db.collection('settings').document('current_control').set({'target_user': sender_id})
            
            notification = f"🔔 عميل جديد: {sender_id}\nالرسالة: {msg_body}\n\nأرد عليه؟ (راسله / انا ارد)"
            send_whatsapp(rashed_id, notification)
            threading.Thread(target=delayed_check, args=(sender_id, msg_body)).start()
        
        else:
            # عميل مسجل مسبقاً
            current_status = doc.to_dict().get('status')
            if current_status == 'ai_active':
                # رد فوري ومستمر طالما الحالة نشطة
                reply = get_ai_reply(msg_body)
                send_whatsapp(sender_id, reply)
            elif current_status == 'pending':
                # تحديث التنبيه لراشد لضمان بقائه كمستهدف حالي
                db.collection('settings').document('current_control').set({'target_user': sender_id})
                doc_ref.update({'last_msg': msg_body})

    gc.collect()
    return "OK", 200

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)
