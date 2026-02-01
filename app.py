import os
import sqlite3
import datetime
import requests
from flask import Flask, request

app = Flask(__name__)

# جلب المفتاح الخاص بك من رندر
API_KEY = os.environ.get("GROQ_API_KEY")
DB_FILE = "rashid_royal_vault.db"

def init_db():
    conn = sqlite3.connect(DB_FILE)
    conn.execute("CREATE TABLE IF NOT EXISTS chat (sender TEXT, role TEXT, content TEXT, ts DATETIME)")
    conn.close()

def get_memory(sender):
    """جلب التاريخ الحقيقي قبل حفظ الرسالة الجديدة"""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.execute("SELECT role, content FROM chat WHERE sender=? ORDER BY ts DESC LIMIT 8", (sender,))
    history = [{"role": r, "content": c} for r, c in reversed(cursor.fetchall())]
    conn.close()
    return history

def save_msg(sender, role, content):
    conn = sqlite3.connect(DB_FILE)
    conn.execute("INSERT INTO chat VALUES (?,?,?,?)", (sender, role, content, datetime.datetime.now()))
    conn.commit()
    conn.close()

@app.route('/', methods=['POST'])
def chat():
    try:
        data = request.get_json()
        msg = data.get('message', '').strip()
        sender = data.get('sender', 'guest')
        
        if not msg: return "OK", 200

        # [1] جلب الذاكرة الحالية (قبل حفظ الرسالة الجديدة)
        chat_history = get_memory(sender)
        
        # [2] حفظ رسالة المستخدم الآن
        save_msg(sender, "user", msg)

        # [3] تحديد الشخصية بناءً على: هل هذه أول رسالة فعلاً؟
        is_first_time = len(chat_history) == 0
        
        system_content = (
            "أنت (مساعد راشد الشخصي). سكرتير سعودي محترم ورزين. "
            "قوانينك الصارمة:\n"
            "1. الرد مختصر جداً (لا يزيد عن 6 كلمات).\n"
            "2. ممنوع تكرار 'راشد مشغول' أو 'راشد في اجتماع' إذا كانت موجودة في الذاكرة.\n"
            f"{'3. هذه أول رسالة للمرسل، رحب به بوقار (حيّاك الله، راشد في اجتماع، وش الموضوع؟).' if is_first_time else '3. لقد رحبت به مسبقاً، الآن تفاعل مع كلامه بذكاء كبشر، مثلاً: (أبشر ببلغه) أو (وصلت رسالتك).'}\n"
            "4. إذا الشخص يمزح أو يقل أدبه مثل 'بطل زنط'، رد بثقل: (راشد فعلاً مشغول، تواصل معه لاحقاً)."
        )

        payload = {
            "model": "llama-3.3-70b-versatile",
            "messages": [{"role": "system", "content": system_content}] + chat_history + [{"role": "user", "content": msg}],
            "temperature": 0.6
        }

        res = requests.post("https://api.groq.com/openai/v1/chat/completions", 
                            json=payload, headers={"Authorization": f"Bearer {API_KEY}"})
        
        reply = res.json()['choices'][0]['message']['content']
        
        # [4] حفظ رد المساعد
        save_msg(sender, "assistant", reply)
        
        return reply, 200, {'Content-Type': 'text/plain; charset=utf-8'}

    except Exception:
        # رد الطوارئ إذا تعطل الذكاء الاصطناعي، لكي لا يسكت البوت
        return "المعذرة، راشد مشغول الآن.", 200

if __name__ == '__main__':
    init_db()
    app.run(host='0.0.0.0', port=10000)
