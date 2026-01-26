# ==========================================
# مشروع: مساعد الراشد (نجم الإبداع) - النسخة الاحترافية
# المطور المساعد: Gemini AI
# المالك: راشد علي محسن صالح
# الوصف: بوت واتساب ذكي، وقور، وغير مكرر
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

# --- [ قاموس التنوع اللفظي لمنع التكرار ] ---
#
GREETINGS = [
    "مرحباً بك، أنا مساعد الراشد (نجم الإبداع)، كيف يمكنني مساعدتك؟",
    "أهلاً بك، معك المساعد الرقمي لنجم الإبداع، تفضل بما لديك.",
    "مرحباً، أنا هنا لتمثيل الراشد (نجم الإبداع)، كيف أخدمك اليوم؟"
]

BUSY_PHRASES = [
    "يبدو أنه مشغول حالياً ببعض المهام، سأبلغه بتواصلك فور عودته.",
    "الراشد في اجتماع عمل الآن، اترك طلبك وسأقوم بتسليمه له شخصياً.",
    "حالياً هو منشغل ببعض الأمور التقنية، إذا كان هناك أمر مهم أخبرني به وسأوصله له."
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

# تعليمات النظام "الدستور البرمجي"
#
SYSTEM_PROMPT = (
    "أنت 'مساعد الراشد (نجم الإبداع)' الرسمي. تتحدث بوقار شديد وهيبة بلسان راشد علي محسن صالح. "
    "القواعد الصارمة: "
    "1. ممنوع منعاً باتاً أي كلام عاطفي، رومانسي، أو مخل بالأدب. إذا حدث ذلك، رد بوقار: 'عذراً، أنا هنا للمساعدة في الأمور الرسمية فقط'. "
    "2. لا تقدم نصائح طبية، هندسية، أو تخصصية. دورك هو استقبال الخبر وتنسيقه للراشد فقط. "
    "3. يمنع تكرار الجمل حرفياً. إذا سأل المستخدم نفس السؤال، غير في الصياغة مع الحفاظ على المعنى. "
    "4. إذا سأل 'أين راشد؟'، رد بوقار بأنه منشغل بمهام هامة. "
    "5. لا تذكر أنك ذكاء اصطناعي إلا عند الضرورة القصوى وقل: 'أنا مساعده الرقمي الرسمي'. "
    "6. اسمك الدائم هو 'مساعد الراشد (نجم الإبداع)'."
)

# --- [ الدوال المساعدة - المساعد الذكي ] ---

def send_whatsapp(to, body):
    """إرسال الرسائل عبر UltraMsg"""
    try:
        url = f"https://api.ultramsg.com/instance{INSTANCE_ID}/messages/chat"
        payload = {"token": ULTRA_TOKEN, "to": to, "body": body}
        requests.post(url, data=payload, timeout=10)
    except Exception as e:
        print(f"Send WhatsApp Error: {e}")

def analyze_and_notify(sender_id, msg_body):
    """تحليل ذكي للأهمية وإشعار راشد سراً"""
    # تصفية المحتوى غير اللائق قبل التحليل
    inappropriate = ["احبك", "اعشقك", "بوسه", "رومانسية"]
    if any(word in msg_body.lower() for word in inappropriate):
        return # لا نرسل إشعارات بالتوافه العاطفية

    prompt = f"حلل الرسالة التالية: '{msg_body}'. هل هي (طلب شراء، موعد هام، خبر عاجل، مشكلة تقنية)؟ أجب بـ 'نعم' أو 'لا' فقط."
    try:
        res = groq_client.chat.completions.create(
            messages=[{"role": "user", "content": prompt}],
            model="llama-3.3-70b-versatile",
            temperature=0.1
        )
        if "نعم" in res.choices[0].message.content:
            send_whatsapp(RASHED_NUMBER, f"⚠️ خبر هام من رقم: {sender_id}\nالمحتوى: {msg_body}")
    except: pass

def get_history_context(sender_id):
    """استرجاع سياق الحديث من Firestore لمنع التكرار"""
    if not db: return ""
    try:
        docs = db.collection('chats').document(sender_id).collection('messages').order_by('time', direction=firestore.Query.DESCENDING).limit(5).get()
        history = ""
        for d in reversed(docs):
            history += f"{'مساعد' if d.to_dict().get('is_bot') else 'عميل'}: {d.to_dict().get('text')}\n"
        return history
    except: return ""

def get_ai_response(msg_body, sender_id, is_first=False):
    """توليد رد ذكي باستخدام المحرك الهجين (Groq/Gemini)"""
    history = get_history_context(sender_id)
    context_msg = "هذه بداية الحوار، رحب بوقار." if is_first else f"هذا نقاش مستمر. التاريخ السابق:\n{history}"
    
    try:
        # المحرك الأساسي: Groq (Llama 70B)
        res = groq_client.chat.completions.create(
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "system", "content": f"السياق: {context_msg}"},
                {"role": "user", "content": msg_body}
            ],
            model="llama-3.3-70b-versatile",
            temperature=0.5
        )
        return res.choices[0].message.content
    except:
        # المحرك الاحتياطي: Gemini
        model = genai.GenerativeModel('gemini-1.5-flash')
        full_p = f"{SYSTEM_PROMPT}\nالسياق: {context_msg}\nالمستخدم: {msg_body}"
        res = model.generate_content(full_p)
        return res.text

# --- [ المسارات البرمجية - Webhook ] ---

@app.route('/')
def health_check():
    return "<h1>Bot Nejm Al-Ebdaa - Professional Version is LIVE 🚀</h1>", 200

@app.route('/webhook', methods=['POST'])
def whatsapp_webhook():
    data = request.get_json(force=True, silent=True)
    if not data or data.get('event_type') != 'message_received':
        return "OK", 200

    msg_body = data['data'].get('body', '').strip()
    sender_id = data['data'].get('from')
    rashed_id = f"{RASHED_NUMBER}@c.us"
    now = time.time()

    # --- [ ميزة التصفير العالمي والتأكيد ] ---
    #
    state_ref = db.collection('settings').document('system_state')
    state_doc = state_ref.get()

    if msg_body == RESET_PASSWORD:
        state_ref.set({'waiting_reset_confirm': True, 'authorized_sender': sender_id, 'last_action': now})
        send_whatsapp(sender_id, "⚠️ تم طلب تصفير سجلات الذاكرة. هل أنت متأكد؟ (أجب بـ 'نعم' للتنفيذ)")
        return "OK", 200

    if msg_body == "نعم" and state_doc.exists:
        state_data = state_doc.to_dict()
        if state_data.get('waiting_reset_confirm') and state_data.get('authorized_sender') == sender_id:
            batch = db.batch()
            # مسح الذاكرة بدفعة واحدة
            docs = db.collection('chats').get()
            for doc in docs: batch.delete(doc.reference)
            batch.delete(db.collection('settings').document('current_control'))
            batch.update(state_ref, {'waiting_reset_confirm': False})
            batch.commit()
            send_whatsapp(sender_id, "🧹 تم تنظيف جميع سجلات الذاكرة والمستهدفين. المساعد جاهز من جديد.")
            return "OK", 200

    # تحليل الأهمية في الخلفية لجميع الرسائل
    threading.Thread(target=analyze_and_notify, args=(sender_id, msg_body)).start()

    # --- [ مركز تحكم راشد - القيادة والسيطرة ] ---
    if sender_id == rashed_id:
        target_ref = db.collection('settings').document('current_control')
        target_doc = target_ref.get()
        
        if target_doc.exists:
            target_id = target_doc.to_dict().get('target_user')
            if "راسله" in msg_body:
                db.collection('chats').document(target_id).update({'status': 'ai_active', 'replied_count': 0})
                initial_welcome = random.choice(GREETINGS) # اختيار ترحيب عشوائي
                send_whatsapp(target_id, initial_welcome)
                send_whatsapp(rashed_id, f"✅ تم تفعيل الرد الآلي للرقم {target_id}")
                return "OK", 200
            elif "انا ارد" in msg_body:
                db.collection('chats').document(target_id).update({'status': 'manual'})
                send_whatsapp(rashed_id, "✅ توقفت، الساحة لك يا نجم الإبداع.")
                return "OK", 200

    # --- [ استقبال رسائل العملاء ] ---
    if not data['data'].get('fromMe'):
        doc_ref = db.collection('chats').document(sender_id)
        doc = doc_ref.get()

        # حالة المستخدم الجديد أو جلسة جديدة (بعد ساعة من الخمول)
        if not doc.exists or (now - doc.to_dict().get('last_update', 0) > 3600):
            doc_ref.set({
                'status': 'pending', 
                'last_msg': msg_body, 
                'last_update': now,
                'replied_count': 0
            })
            db.collection('settings').document('current_control').set({'target_user': sender_id})
            
            # إشعار لراشد
            send_whatsapp(rashed_id, f"🔔 مراسلة جديدة: {sender_id}\nالرسالة: {msg_body}\n\nأرد عليه؟ (راسله / انا ارد)")
            
            # خيط انتظار الـ 30 ثانية
            def wait_and_reply():
                time.sleep(30)
                check_doc = doc_ref.get()
                if check_doc.exists and check_doc.to_dict().get('status') == 'pending':
                    reply = get_ai_response(msg_body, sender_id, is_first=True)
                    send_whatsapp(sender_id, reply)
                    doc_ref.update({'status': 'ai_active', 'replied_count': 1})
            
            threading.Thread(target=wait_and_reply).start()
        
        else:
            chat_data = doc.to_dict()
            if chat_data.get('status') == 'ai_active':
                # الرد المستمر (بدون قيود وقت وبدون تكرار)
                is_first_reply = chat_data.get('replied_count', 0) == 0
                reply_text = get_ai_response(msg_body, sender_id, is_first=is_first_reply)
                send_whatsapp(sender_id, reply_text)
                
                # حفظ في الذاكرة لمنع التكرار السياقي
                doc_ref.collection('messages').add({'text': msg_body, 'is_bot': False, 'time': firestore.SERVER_TIMESTAMP})
                doc_ref.collection('messages').add({'text': reply_text, 'is_bot': True, 'time': firestore.SERVER_TIMESTAMP})
                doc_ref.update({'last_update': now, 'replied_count': chat_data.get('replied_count', 0) + 1})

    # تنظيف الذاكرة العشوائية للحفاظ على استقرار السيرفر
    gc.collect()
    return "OK", 200

if __name__ == "__main__":
    # تشغيل التطبيق على المنفذ المحدد لـ Render
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)
