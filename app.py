import os
import json
import requests
import firebase_admin
from firebase_admin import credentials, db
from flask import Flask, request

app = Flask(__name__)

# --- [1] الربط بمخزن فيرباس (Firebase) بدون تعقيد التاريخ ---
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

# --- [2] وظائف الذاكرة (تعتمد على ترتيب الرسائل التلقائي وليس التاريخ) ---
def get_history(sender):
    try:
        ref = db.reference(f'chats/{sender}/messages')
        snapshot = ref.limit_to_last(6).get() # جلب آخر 6 رسائل فقط
        if not snapshot: return []
        # ترتيب الرسائل يتم تلقائياً بناءً على "مفتاح الدفع" في فيرباس
        return [{"role": snapshot[k]['role'], "content": snapshot[k]['content']} for k in sorted(snapshot.keys())]
    except: return []

def save_to_cloud(sender, role, text):
    try:
        # الحفظ هنا بدون حقل 'ts' لإزالة قيد التاريخ تماماً
        db.reference(f'chats/{sender}/messages').push({'role': role, 'content': text})
    except: pass

# --- [3] معالجة الرسائل بالوصايا الخمس الصارمة ---
@app.route('/', methods=['POST'])
def royal_assistant():
    try:
        data = request.get_json()
        user_msg = data.get('message', '').strip()
        sender = data.get('sender', 'unknown')
        if not user_msg: return "OK", 200

        # فحص "قفل الترحيب" بدلاً من فحص التاريخ
        ref_user = db.reference(f'chats/{sender}')
        is_greeted = ref_user.child('greeted').get()
        
        history = get_history(sender)

        # الوصايا الخمس (الدستور الرسمي للمساعد)
        system_rules = (
            "1. أنت مساعد وسكرتير راشد (نجم الإبداع) في نفس الوقت. "
            "2. ردودك مختصره جداً وبدون ذكاء زائد. "
            "3. يمنع تماماً أي كلام رومانسي أو مخل بالآداب. "
            "4. رد على قدر السؤال الموجه لك فقط. "
            "5. إجاباتك فقط في إطار عملك كسكرتير لراشد."
        )

        # منطق الترحيب الارتجالي (يحدث مرة واحدة فقط في العمر لكل رقم)
        if not is_greeted:
            instruction = f"{system_rules} القاعدة: هذه أول مرة تراه، ارتجل ترحيباً وقوراً ومختصراً جداً."
        else:
            instruction = f"{system_rules} القاعدة: ممنوع تكرار الترحيب نهائياً، ادخل في الموضوع بوقار."

        payload = {
            "model": "llama-3.3-70b-versatile",
            "messages": [{"role": "system", "content": instruction}] + history + [{"role": "user", "content": user_msg}],
            "temperature": 0.5 # تقليل العفوية لضمان الالتزام بالرد المختصر
        }

        res = requests.post("https://api.groq.com/openai/v1/chat/completions",
                            json=payload, headers={"Authorization": f"Bearer {GROQ_API_KEY}"})
        
        reply = res.json()['choices'][0]['message']['content']

        # حفظ الرسالة وتفعيل "قفل الترحيب" للأبد لهذا الرقم
        save_to_cloud(sender, "user", user_msg)
        save_to_cloud(sender, "assistant", reply)
        if not is_greeted:
            ref_user.child('greeted').set(True)

        return reply, 200, {'Content-Type': 'text/plain; charset=utf-8'}
    except:
        return "أبشر، ببلغ راشد.", 200

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=10000)
