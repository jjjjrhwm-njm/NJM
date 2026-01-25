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

# --- [ إعدادات نجم الإبداع ] ---
RASHED_NUMBER = "0554526287" # رقمك الشخصي
INSTANCE_ID = "159896"
ULTRA_TOKEN = "3a2kuk39wf15ejiu"

# --- [ ربط الذاكرة الدائمة من بيئة رندر ] ---
firebase_raw = os.getenv("FIREBASE_JSON")
if firebase_raw:
    service_account_info = json.loads(firebase_raw)
    cred = credentials.Certificate(service_account_info)
    if not firebase_admin._apps:
        firebase_admin.initialize_app(cred)
    db = firestore.client()
else:
    print("⚠️ تنبيه: لم يتم العثور على FIREBASE_JSON في رندر!")

# إعداد المحركات
groq_client = Groq(api_key=os.getenv("GROQ_API_KEY"))
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))

SYSTEM_PROMPT = "أنت مساعد 'نجم الإبداع' الرسمي. رد بوقار بلسان راشد علي محسن صالح."

def send_whatsapp(to, body):
    url = f"https://api.ultramsg.com/instance{INSTANCE_ID}/messages/chat"
    requests.post(url, data={"token": ULTRA_TOKEN, "to": to, "body": body})

def get_ai_reply(msg_body):
    try:
        res = groq_client.chat.completions.create(
            messages=[{"role": "system", "content": SYSTEM_PROMPT}, {"role": "user", "content": msg_body}],
            model="llama-3.3-70b-versatile"
        )
        return res.choices[0].message.content
    except:
        res = genai.GenerativeModel('gemini-1.5-flash').generate_content(msg_body)
        return res.text

def delayed_check(sender_id, initial_msg):
    time.sleep(30) # عداد الـ 30 ثانية
    doc_ref = db.collection('chats').document(sender_id)
    doc = doc_ref.get()
    if doc.exists and doc.to_dict().get('status') == 'pending':
        reply = get_ai_reply(initial_msg)
        send_whatsapp(sender_id, reply)
        doc_ref.update({'status': 'ai_active'})

@app.route('/webhook', methods=['POST'])
def whatsapp_webhook():
    data = request.get_json(force=True, silent=True)
    if not data or data.get('event_type') != 'message_received':
        return "OK", 200

    msg_body = data['data'].get('body', '').strip()
    sender_id = data['data'].get('from')

    # تحكم راشد
    if sender_id == f"{RASHED_NUMBER}@c.us":
        docs = db.collection('chats').where('status', '==', 'pending').limit(1).get()
        for doc in docs:
            if "راسله" in msg_body:
                db.collection('chats').document(doc.id).update({'status': 'ai_active'})
                send_whatsapp(doc.id, get_ai_reply("مرحباً"))
                send_whatsapp(RASHED_NUMBER, "✅ تم، بدأت بالرد عليه.")
            elif "انا ارد" in msg_body:
                db.collection('chats').document(doc.id).update({'status': 'manual'})
                send_whatsapp(RASHED_NUMBER, "✅ توقفت عن الرد، الساحة لك.")
    
    # رسائل العملاء
    elif not data['data'].get('fromMe'):
        doc_ref = db.collection('chats').document(sender_id)
        if not doc_ref.get().exists:
            doc_ref.set({'status': 'pending', 'last_msg': msg_body})
            notification = f"🔔 {sender_id} راسلك.\nالرسالة: {msg_body}\n\nأرد عليه؟ (راسله / انا ارد)"
            send_whatsapp(RASHED_NUMBER, notification)
            threading.Thread(target=delayed_check, args=(sender_id, msg_body)).start()

    gc.collect()
    return "OK", 200

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)
