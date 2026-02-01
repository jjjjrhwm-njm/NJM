import os
import json
import datetime
import requests
import random
import firebase_admin
from firebase_admin import credentials, db
from flask import Flask, request

app = Flask(__name__)

# --- [1] الربط بمخزن فيرباس (Firebase) لضمان عدم نسيان المحادثات للأبد ---
try:
    config_raw = os.environ.get("FIREBASE_CONFIG")
    db_url = os.environ.get("FIREBASE_DB_URL")
    if config_raw and db_url:
        cred_dict = json.loads(config_raw)
        cred = credentials.Certificate(cred_dict)
        if not firebase_admin._apps:
            firebase_admin.initialize_app(cred, {'databaseURL': db_url})
except Exception as e:
    print(f"Firebase Error: {e}")

GROQ_API_KEY = os.environ.get("GROQ_API_KEY")

# --- [2] مصفوفة التنوع اللفظي (اقتباس من كودك لمنع التكرار) ---
GREETINGS = [
    "مرحباً بك، مساعد الراشد (نجم الإبداع) معك، كيف الخدمة؟",
    "أهلاً، أنا المساعد الرقمي لنجم الإبداع، تفضل بموجزك.",
    "تحية طيبة، هنا سكرتارية الراشد (نجم الإبداع)، اترك خبرك."
]

# --- [3] الدستور البرمجي للسكرتير البشري (من منطق كودك) ---
SYSTEM_PROMPT = (
    "أنت 'مساعد الراشد (نجم الإبداع)' الرسمي. لست روبوتاً، بل سكرتير بشري وقور. "
    "قواعدك البشرية: "
    "1. التفاعل النفسي: كن لبقاً مع المحترمين، وحازماً مع الملحين. "
    "2. رد فعل العصبية: إذا كرر العميل سؤاله أو كان لحوحاً، أظهر ضيقاً بشرياً وقوراً. "
    "3. الاختصار: ردودك مقتضبة جداً وذات هيبة (7 كلمات كحد أقصى). "
    "4. منع التكرار: يمنع تكرار الترحيب أو أي جملة قيلت سابقاً. غير صياغتك دائماً. "
    "5. لا تقل 'أنا ذكاء اصطناعي' أو 'نموذج'. أنت سكرتير حقيقي."
)

def manage_firebase(sender, role=None, content=None):
    try:
        ref = db.reference(f'chats/{sender}')
        if content:
            ref.push({'role': role, 'content': content, 'ts': datetime.datetime.now().isoformat()})
        snapshot = ref.order_by_child('ts').limit_to_last(6).get()
        if not snapshot: return []
        return [{"role": snapshot[k]['role'], "content": snapshot[k]['content']} for k in sorted(snapshot.keys())]
    except: return []

@app.route('/', methods=['POST'])
def handle_msg():
    try:
        data = request.get_json()
        user_msg = data.get('message', '').strip()
        sender = data.get('sender', 'unknown')
        if not user_msg: return "OK", 200

        # جلب الذاكرة
        history = manage_firebase(sender)
        is_first = len(history) == 0

        # منطق التنوع اللفظي: إذا كانت أول مرة، اختر ترحيباً عشوائياً
        first_reply_context = f"هذا ترحيبك الأول، اختر أسلوباً من: {random.choice(GREETINGS)}" if is_first else "هذا نقاش مستمر، لا ترحب ثانية."

        payload = {
            "model": "llama-3.3-70b-versatile",
            "messages": [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "system", "content": f"السياق الحالي: {first_reply_context}"}
            ] + history + [{"role": "user", "content": user_msg}],
            "temperature": 0.7 # رفع الحرارة لزيادة التنوع البشري
        }

        res = requests.post("https://api.groq.com/openai/v1/chat/completions",
                            json=payload, headers={"Authorization": f"Bearer {GROQ_API_KEY}"})
        
        reply = res.json()['choices'][0]['message']['content']

        # حفظ الذاكرة
        manage_firebase(sender, "user", user_msg)
        manage_firebase(sender, "assistant", reply)

        return reply, 200, {'Content-Type': 'text/plain; charset=utf-8'}
    except:
        return "أبشر، ببلغ راشد.", 200

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=10000)
