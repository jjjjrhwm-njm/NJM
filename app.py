import os
import json
import datetime
import requests
import random
import firebase_admin
from firebase_admin import credentials, db
from flask import Flask, request

app = Flask(__name__)

# --- [1] إعدادات الذاكرة الحديدية (Realtime Database) ---
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

# --- [2] قاموس التنوع اللفظي (من كودك الشخصي) ---
GREETINGS = [
    "مرحباً بك، مساعد الراشد (نجم الإبداع) معك، كيف الخدمة؟",
    "أهلاً، أنا المساعد الرقمي لنجم الإبداع، تفضل بموجزك.",
    "تحية طيبة، هنا سكرتارية الراشد (نجم الإبداع)، اترك خبرك."
]

# --- [3] الدستور البرمجي للسكرتير البشري (من كودك الشخصي) ---
SYSTEM_PROMPT = (
    "أنت 'مساعد الراشد (نجم الإبداع)' الرسمي. لست روبوتاً، بل سكرتير بشري وقور، موجز، وذكي. "
    "قواعد السلوك: "
    "1. التفاعل النفسي: رد كإنسان؛ لبق مع المحترمين، وحازم مع الملحين. "
    "2. الاختصار والرزانة: ردودك مقتضبة جداً وذات هيبة (لا تزد عن 8 كلمات). "
    "3. منع التكرار: يمنع تكرار الترحيب أو أي جملة قيلت سابقاً. "
    "4. الرفض الحازم: أي كلام غير لائق، واجهه ببرود إنساني حازم ينهي التمادي فوراً. "
    "5. الهوية: أنت 'المساعد الرقمي الرسمي لنجم الإبداع'."
)

# --- [4] إدارة الذاكرة السحابية ومنع التكرار ---
def get_memory(sender):
    try:
        ref = db.reference(f'chats/{sender}')
        snapshot = ref.order_by_child('ts').limit_to_last(6).get()
        if not snapshot: return []
        return [{"role": snapshot[k]['role'], "content": snapshot[k]['content']} for k in sorted(snapshot.keys())]
    except: return []

def save_memory(sender, role, text):
    try:
        db.reference(f'chats/{sender}').push({
            'role': role, 'content': text,
            'ts': datetime.datetime.now().isoformat()
        })
    except: pass

# --- [5] المعالجة الذكية (الرد لمرة واحدة) ---
@app.route('/', methods=['POST'])
def handle_msg():
    try:
        data = request.get_json()
        user_msg = data.get('message', '').strip()
        sender_id = data.get('sender', 'unknown')
        if not user_msg: return "OK", 200

        # جلب الذاكرة أولاً
        history = get_memory(sender_id)
        
        # فحص ذكي جداً: هل يوجد أي ترحيب سابق في الذاكرة؟
        has_greeted = any(any(g in h['content'] for g in GREETINGS) for h in history if h['role'] == 'assistant')

        # بناء التوجيه بناءً على التاريخ
        if not has_greeted:
            # أول مرة يراسلنا: نلزمه بترحيب عشوائي
            instruction = f"ابدأ بترحيب وقور من هذه القائمة: {random.choice(GREETINGS)}"
        else:
            # قد كلمنا: ممنوع يرحب، يدخل في الموضوع فوراً
            instruction = "ممنوع الترحيب نهائياً. أنت في نقاش مستمر، رد باختصار كبشر."

        # إرسال لـ Groq
        payload = {
            "model": "llama-3.3-70b-versatile",
            "messages": [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "system", "content": instruction}
            ] + history + [{"role": "user", "content": user_msg}],
            "temperature": 0.6
        }

        res = requests.post("https://api.groq.com/openai/v1/chat/completions",
                            json=payload, headers={"Authorization": f"Bearer {GROQ_API_KEY}"})
        
        reply = res.json()['choices'][0]['message']['content']

        # حفظ الرسائل (تأكد من الحفظ لكي يعرف في المرة القادمة)
        save_memory(sender_id, "user", user_msg)
        save_memory(sender_id, "assistant", reply)

        return reply, 200, {'Content-Type': 'text/plain; charset=utf-8'}
    except:
        return "أبشر، ببلغ راشد بموضوعك.", 200

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=10000)
