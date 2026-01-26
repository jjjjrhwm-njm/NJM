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
RASHED_NUMBER = "0554526287" 
INSTANCE_ID = "159896"
ULTRA_TOKEN = "3a2kuk39wf15ejiu"
RESET_PASSWORD = "00001111" # كلمة السر الجديدة

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
    """تحليل ذكي لمدى أهمية الرسالة"""
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
    """تمثيلية وهمية لإشعار المرسل بالاهتمام"""
    time.sleep(5)
    send_whatsapp(sender_id, "لحظة من فضلك، سأقوم بمحاولة مراسلته الآن على رقمه الخاص وتنبيهه لأهمية أمرك.. انتظر لحظة.")
    time.sleep(15)
    
    tz = pytz.timezone('Asia/Riyadh')
    hour = datetime.now(tz).hour
    
    if 23 <= hour or hour <= 7:
        final_reply = "اعتذر منك بشدة، حاولت الوصول إليه لكن يبدو أن الوقت متأخر وقد يكون نائماً الآن. سأترك له رسالتك في مقدمة التنبيهات ليرد عليك فور استيقاظه."
    else:
        final_reply = "للأسف لم أجد رداً منه حالياً، يبدو أنه مشغول جداً في اجتماع أو عمل تقني. سأخبره فور عودته بأهمية موضوعك."
    
    send_whatsapp(sender_id, final_reply)

@app.route('/webhook', methods=['POST'])
def whatsapp_webhook():
    data = request.get_json(force=True, silent=True)
    if not data or data.get('event_type') != 'message_received':
        return "OK", 200

    msg_body = data['data'].get('body', '').strip()
    sender_id = data['data'].get('from')
    rashed_id = f"{RASHED_NUMBER}@c.us"
    now = time.time()

    # [1] مركز تحكم راشد
    if sender_id == rashed_id:
        # نظام تصفير البيانات مع التأكيد
        control_ref = db.collection('settings').document('system_state')
        state_doc = control_ref.get()
        
        if msg_body == RESET_PASSWORD:
            control_ref.set({'waiting_reset_confirm': True, 'last_action': now})
            send_whatsapp(rashed_id, "⚠️ هل أنت متأكد من تصفير جميع البيانات وسجلات الذاكرة؟ (أجب بـ 'نعم' للتأكيد)")
            return "OK", 200
            
        if msg_body == "نعم" and state_doc.exists and state_doc.to_dict().get('waiting_reset_confirm'):
            # تنفيذ المسح الشامل
            docs = db.collection('chats').get()
            for doc in docs: doc.reference.delete()
            db.collection('settings').document('current_control').delete()
            control_ref.update({'waiting_reset_confirm': False})
            send_whatsapp(rashed_id, "🧹 تم تصفير جميع سجلات الذاكرة بنجاح. البوت الآن في وضع الاستعداد الجديد.")
            return "OK", 200

        # منطق التحكم التقليدي (راسله/انا ارد)
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
                send_whatsapp(rashed_id, "✅ تم إيقاف الرد الآلي، الميكروفون معك.")

    # [2] استقبال رسائل العملاء
    elif not data['data'].get('fromMe'):
        doc_ref = db.collection('chats').document(sender_id)
        doc = doc_ref.get()
        
        is_important = check_importance(msg_body)
        max_duration = 180 if is_important else 120 
        
        if is_important:
            send_whatsapp(rashed_id, f"🔥 خبر هام جداً من {sender_id}:\n{msg_body}")

        if not doc.exists or (now - doc.to_dict().get('last_update', 0) > 3600):
            doc_ref.set({'status': 'pending', 'last_msg': msg_body, 'last_update': now, 'session_start': now, 'replied_count': 0, 'is_important': is_important})
            db.collection('settings').document('current_control').set({'target_user': sender_id})
            send_whatsapp(rashed_id, f"🔔 مراسلة جديدة ({'هام' if is_important else 'عادي'}): {sender_id}\n{msg_body}")
            threading.Thread(target=lambda: (time.sleep(30), delayed_check(sender_id, msg_body))).start()
        else:
            chat_data = doc.to_dict()
            if chat_data.get('status') == 'ai_active':
                if now - chat_data.get('session_start', now) > max_duration:
                    # رسالة النهاية الجديدة والمحسنة
                    exit_msg = "اعتذر منك على المقاطعة، هناك شخص آخر يراسل ويجب أن أرد عليه، أما بشأن مراسلتك سأخبر الراشد فور عودته. مع السلامة."
                    
                    if chat_data.get('is_important'):
                        threading.Thread(target=handle_important_negotiation, args=(sender_id,)).start()
                    else:
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
