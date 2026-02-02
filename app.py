import os
import json
import datetime
import requests
import time
import firebase_admin
from firebase_admin import credentials, db
from flask import Flask, request

app = Flask(__name__)

# --- [1] إعدادات الذاكرة الحديدية (Firebase) ---
try:
    config_raw = os.environ.get("FIREBASE_CONFIG")
    db_url = os.environ.get("FIREBASE_DB_URL")
    if config_raw and db_url:
        cred_dict = json.loads(config_raw)
        cred = credentials.Certificate(cred_dict)
        if not firebase_admin._apps:
            firebase_admin.initialize_app(cred, {'databaseURL': db_url})
except Exception: pass

GROQ_API_KEY = os.environ.get("GROQ_API_KEY")

# --- [2] وظيفة إدارة الذاكرة وحفظ الهوية ---
def manage_memory(sender_id, role=None, content=None):
    try:
        ref = db.reference(f'chats/{sender_id}')
        if content:
            ref.child('messages').push({
                'role': role, 'content': content, 
                'ts': datetime.datetime.now().isoformat()
            })
        
        # جلب آخر 6 رسائل لضمان بقاء السياق (رابعاً: حفظ الموضوع)
        snapshot = ref.child('messages').order_by_child('ts').limit_to_last(6).get()
        if not snapshot: return []
        return [{"role": snapshot[k]['role'], "content": snapshot[k]['content']} for k in sorted(snapshot.keys())]
    except: return []

# --- [3] المعالجة المركزية (الحماية + الارتجال) ---
@app.route('/', methods=['POST'])
def handle_bot():
    try:
        # ثانياً: مهلة تفكير (ثانية واحدة) لضمان عدم تداخل الرسائل
        time.sleep(1)
        
        data = request.get_json()
        msg_body = data.get('message', '').strip()
        sender_id = data.get('sender', 'unknown') # رابعاً: هوية المرسل ثابتة

        if not msg_body: return "OK", 200

        # أولاً: حماية من التكرار (منع معالجة نفس الرسالة مرتين في أقل من ثانيتين)
        ref_status = db.reference(f'chats/{sender_id}/status')
        last_msg_ts = ref_status.child('last_processed_ts').get()
        now_ts = time.time()
        
        if last_msg_ts and (now_ts - last_msg_ts < 2):
            return "OK", 200 # تجاهل الإشعار المكرر

        # فحص هل تم الترحيب مسبقاً (خارج التاريخ لضمان الدقة)
        is_greeted = ref_status.child('is_greeted').get()
        history = manage_memory(sender_id)

        # ثالثاً: الترحيب الارتجالي بناءً على أول رسالة
        if not is_greeted:
            instruction = (
                "هذه أول رسالة للمرسل. ارتجل ترحيباً وقوراً وبشرياً جداً "
                f"بناءً على أسلوب كلامه: '{msg_body}'. لا تكرر جمل معلبة."
            )
        else:
            instruction = "هذا حوار مستمر. ممنوع الترحيب نهائياً. ادخل في الموضوع بذكاء."

        # إرسال الطلب لـ Groq
        payload = {
            "model": "llama-3.3-70b-versatile",
            "messages": [
                {"role": "system", "content": "أنت مساعد راشد (نجم الإبداع). سكرتير سعودي محنك، ردودك وقورة وأقل من 8 كلمات."},
                {"role": "system", "content": instruction}
            ] + history + [{"role": "user", "content": msg_body}],
            "temperature": 0.7 
        }

        res = requests.post("https://api.groq.com/openai/v1/chat/completions",
                            json=payload, headers={"Authorization": f"Bearer {GROQ_API_KEY}"})
        
        reply = res.json()['choices'][0]['message']['content']

        # حفظ الرد وتحديث الحالة والوقت (تفعيل الحماية)
        manage_memory(sender_id, "user", msg_body)
        manage_memory(sender_id, "assistant", reply)
        ref_status.update({
            'is_greeted': True, 
            'last_processed_ts': now_ts 
        })

        return reply, 200, {'Content-Type': 'text/plain; charset=utf-8'}
    except:
        return "أبشر، ببلغ راشد.", 200

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=10000)
