import os
from flask import Flask, request
import requests

app = Flask(__name__)

# مخزن مؤقت للذاكرة (سيحفظ المحادثات طالما السيرفر يعمل)
chat_histories = {}

API_KEY = os.environ.get("MISTRAL_API_KEY")

@app.route('/', methods=['POST'])
def chat():
    try:
        data = request.get_json()
        user_input = data.get('message', '')
        # لكي نميز بين الأشخاص، سنستخدم رقم المرسل إذا أرسلته من ماكرودرويد
        sender_id = data.get('sender', 'default_user') 

        # إذا كان الشخص يكلم البوت لأول مرة، ننشئ له سجل
        if sender_id not in chat_histories:
            chat_histories[sender_id] = [
                {
                    "role": "system", 
                    "content": (
                        "أنت المساعد الشخصي لـ 'راشد'. "
                        "في أول رسالة فقط: رحب بالشخص بوقار وأخبره أن راشد مشغول وسيوصل الرسالة. "
                        "في الرسائل التالية: لا تكرر جملة 'راشد مشغول'، بل تفاعل مع ما يقوله الشخص بذكاء وثقل."
                    )
                }
            ]

        # إضافة رسالة المستخدم للذاكرة
        chat_histories[sender_id].append({"role": "user", "content": user_input})

        # إرسال المحادثة كاملة (الذاكرة) لميسترال
        url = "https://api.mistral.ai/v1/chat/completions"
        headers = {"Authorization": f"Bearer {API_KEY}", "Content-Type": "application/json"}
        
        payload = {
            "model": "open-mistral-7b",
            "messages": chat_histories[sender_id],
            "temperature": 0.7
        }

        response = requests.post(url, headers=headers, json=payload)
        result = response.json()
        reply = result['choices'][0]['message']['content']

        # إضافة رد البوت للذاكرة لكي يتذكره في المرة القادمة
        chat_histories[sender_id].append({"role": "assistant", "content": reply})

        # الحفاظ على آخر 10 رسائل فقط لكي لا يثقل السيرفر
        if len(chat_histories[sender_id]) > 10:
            chat_histories[sender_id] = [chat_histories[sender_id][0]] + chat_histories[sender_id][-9:]

        return reply, 200, {'Content-Type': 'text/plain; charset=utf-8'}

    except:
        return "المعذرة، راشد مشغول الآن.", 200, {'Content-Type': 'text/plain; charset=utf-8'}

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=10000)
