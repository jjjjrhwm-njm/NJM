import os
import json
import datetime
import requests
import firebase_admin
from firebase_admin import credentials, db
from flask import Flask, request

app = Flask(__name__)

# --- [1] الربط بمخزن فيرباس (Firebase) ---
try:
    config_raw = os.environ.get("FIREBASE_CONFIG")
    db_url = os.environ.get("FIREBASE_DB_URL")
    
    if config_raw and db_url:
        cred_dict = json.loads(config_raw)
        cred = credentials.Certificate(cred_dict)
        firebase_admin.initialize_app(cred, {'databaseURL': db_url})
except Exception as e:
    print(f"Firebase Init Error: {e}")

# جلب مفتاح Groq السريع
GROQ_API_KEY = os.environ.get("GROQ_API_KEY")

# --- [2] وظائف الذاكرة الدائمة ---
def get_history(sender):
    try:
        ref = db.reference(f'chats/{sender}')
        # جلب آخر 6 رسائل لضمان عدم التكرار
        snapshot = ref.order_by_child('ts').limit_to_last(6).get()
        if not snapshot: return []
        return [{"role": snapshot[k]['role'], "content": snapshot[k]['content']} for k in sorted(snapshot.keys())]
    except: return []

def save_to_cloud(sender, role, text):
    try:
        db.reference(f'chats/{sender}').push({
            'role': role, 'content': text,
            'ts': datetime.datetime.now().isoformat()
        })
    except: pass

# --- [3] معالجة الرسائل ---
@app.route('/', methods=['POST'])
def royal_assistant():
    try:
        data = request.get_json()
        user_msg = data.get('message', '').strip()
        sender = data.get('sender', 'unknown')
        if not user_msg: return "OK", 200

        # جلب الذاكرة
        history = get_history(sender)
        is_first = len(history) == 0

        # بروتوكول السكرتير السعودي
        system_rules = (
            "أنت (المساعد الشخصي لراشد). سكرتير سعودي وقور، رزين، ومختصر جداً. "
            "ممنوع لغة الآلة (أنا ذكاء، كيف أخدمك). لهجتك سعودية بيضاء ثقيلة. "
            "ردودك لا تتجاوز 8 كلمات. "
            f"{'القاعدة: رحب بوقار (حيّاك الله، راشد في اجتماع حالياً، وش الموضوع؟)' if is_first else 'القاعدة: لا تكرر الترحيب، تفاعل بذكاء (أبشر ببلغه) أو (وصلت رسالتك).'}"
        )

        payload = {
            "model": "llama-3.3-70b-versatile",
            "messages": [{"role": "system", "content": system_rules}] + history + [{"role": "user", "content": user_msg}],
            "temperature": 0.6
        }

        res = requests.post("https://api.groq.com/openai/v1/chat/completions",
                            json=payload, headers={"Authorization": f"Bearer {GROQ_API_KEY}"})
        
        reply = res.json()['choices'][0]['message']['content']

        # حفظ في المخزن السحابي
        save_to_cloud(sender, "user", user_msg)
        save_to_cloud(sender, "assistant", reply)

        return reply, 200, {'Content-Type': 'text/plain; charset=utf-8'}
    except:
        return "أبشر، ببلغ راشد.", 200

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=10000)
