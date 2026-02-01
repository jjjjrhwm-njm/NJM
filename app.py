import os
import sqlite3
import datetime
import requests
from flask import Flask, request

app = Flask(__name__)

# جلب المفتاح الجديد الذي استخرجته أنت
API_KEY = os.environ.get("GROQ_API_KEY")
DB_FILE = "rashid_royal_vault.db"

def init_db():
    conn = sqlite3.connect(DB_FILE)
    conn.execute("CREATE TABLE IF NOT EXISTS chat (sender TEXT, role TEXT, content TEXT, ts DATETIME)")
    conn.close()

def manage_history(sender, role=None, content=None):
    conn = sqlite3.connect(DB_FILE)
    if content:
        conn.execute("INSERT INTO chat VALUES (?,?,?,?)", (sender, role, content, datetime.datetime.now()))
        conn.commit()
    # جلب آخر 5 رسائل لبناء سياق ذكي
    cursor = conn.execute("SELECT role, content FROM chat WHERE sender=? ORDER BY ts DESC LIMIT 5", (sender,))
    history = [{"role": r, "content": c} for r, c in reversed(cursor.fetchall())]
    conn.close()
    return history

@app.route('/', methods=['POST'])
def chat():
    try:
        data = request.get_json()
        user_msg = data.get('message', '').strip()
        sender = data.get('sender', 'guest')
        
        if not user_msg: return "OK", 200

        # جلب تاريخ المحادثة لهذا الشخص
        history = manage_history(sender)

        # تعليمات الشخصية (السر في جعل الرد بشرياً)
        system_prompt = (
            "أنت (مساعد راشد الشخصي). سكرتير سعودي محنك وذكي. "
            "مهمتك: الرد بوقار واختصار شديد (5-8 كلمات). "
            "قواعدك: 1. لا تكرر نفس الجملة مرتين أبداً. "
            "2. إذا الشخص يمزح أو يلح، رد بذكاء مثل: (وصلت رسالتك، بيشوفها أبو محمد) أو (الشيخ راشد عنده علم، انتظر رده). "
            "3. إذا الشخص قال 'أنت كذاب' أو 'بطل زنط'، لا تعتذر، بل رد بوقار: (راشد فعلاً مشغول، تواصل معه لاحقاً)."
        )

        payload = {
            "model": "llama-3.3-70b-versatile",
            "messages": [{"role": "system", "content": system_prompt}] + history + [{"role": "user", "content": user_msg}],
            "temperature": 0.7 # رفع الحرارة قليلاً ليعطيك تنوع في الكلام
        }

        res = requests.post("https://api.groq.com/openai/v1/chat/completions", 
                            json=payload, headers={"Authorization": f"Bearer {API_KEY}"})
        
        if res.status_code == 200:
            reply = res.json()['choices'][0]['message']['content']
            # حفظ المحادثة لكي لا ينساها في المرة القادمة
            manage_history(sender, "user", user_msg)
            manage_history(sender, "assistant", reply)
            return reply, 200, {'Content-Type': 'text/plain; charset=utf-8'}
        else:
            return "بيكلمك راشد إذا فضي.", 200 # رد طوارئ غير مكرر

    except Exception as e:
        # رد الطوارئ الآن متنوع لكي لا يبدو كببغاء
        return "راشد في اجتماع حالياً، وش الموضوع؟", 200

if __name__ == '__main__':
    init_db()
    app.run(host='0.0.0.0', port=10000)
