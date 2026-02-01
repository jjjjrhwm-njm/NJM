import os
import sqlite3
import datetime
import requests
from flask import Flask, request

app = Flask(__name__)

# جلب المفتاح من بيئة رندر
API_KEY = os.environ.get("GROQ_API_KEY")
DB_FILE = "rashid_memory.db"

def init_db():
    conn = sqlite3.connect(DB_FILE)
    conn.execute("CREATE TABLE IF NOT EXISTS chat (sender TEXT, role TEXT, content TEXT, ts DATETIME)")
    conn.close()

def save_and_get_history(sender, role, content, get=False):
    conn = sqlite3.connect(DB_FILE)
    if content:
        conn.execute("INSERT INTO chat VALUES (?,?,?,?)", (sender, role, content, datetime.datetime.now()))
        conn.commit()
    history = []
    if get:
        cursor = conn.execute("SELECT role, content FROM chat WHERE sender=? ORDER BY ts DESC LIMIT 6", (sender,))
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

        # جلب الذاكرة قبل الرد لمنع التكرار
        history = save_and_get_history(sender, None, None, get=True)
        has_replied = any(h['role'] == 'assistant' for h in history)

        # تعليمات السكرتير
        system_prompt = (
            "أنت المساعد الشخصي لراشد. سعودي وقور، مختصر جداً. "
            "لا تزد عن 7 كلمات. لا تكرر نفسك. "
            "إذا كانت أول رسالة: (حيّاك الله، راشد مشغول حالياً، وش الموضوع؟). "
            "إذا كان قد سبق ورددت: (أبشر ببلغه) أو (وصلت رسالتك)."
        )

        payload = {
            "model": "llama-3.3-70b-versatile",
            "messages": [{"role": "system", "content": system_prompt}] + history + [{"role": "user", "content": user_msg}],
            "temperature": 0.5
        }

        res = requests.post("https://api.groq.com/openai/v1/chat/completions", 
                            json=payload, headers={"Authorization": f"Bearer {API_KEY}"})
        reply = res.json()['choices'][0]['message']['content']

        # حفظ الرسائل في الذاكرة
        save_and_get_history(sender, "user", user_msg)
        save_and_get_history(sender, "assistant", reply)

        return reply, 200, {'Content-Type': 'text/plain; charset=utf-8'}
    except:
        return "المعذرة، راشد مشغول.", 200

if __name__ == '__main__':
    init_db()
    app.run(host='0.0.0.0', port=10000)
