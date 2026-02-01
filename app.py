import os
from flask import Flask, request
import requests

app = Flask(__name__)

# مخزن الذاكرة لكل شخص على حدة
chat_histories = {}

API_KEY = os.environ.get("MISTRAL_API_KEY")

@app.route('/', methods=['POST'])
def chat():
    try:
        data = request.get_json()
        user_input = data.get('message', '')
        # هنا السر: سحب رقم المرسل لكي لا تختلط المحادثات
        sender_id = data.get('sender', 'guest') 

        if sender_id not in chat_histories:
            chat_histories[sender_id] = [
                {
                    "role": "system", 
                    "content": (
                        "أنت المساعد الشخصي لـ 'راشد'. "
                        "أسلوبك: سعودي، وقور، مختصر جداً (لا تزد عن 10 كلمات). "
                        "أول رسالة: (حيّاك الله، راشد مشغول حالياً، وش الموضوع؟). "
                        "الرسائل التالية: رد بذكاء كأنك توصل كلام لراشد، بلهجة بيضاء محترمة. "
                        "يمنع منعاً باتاً لغة الذكاء الاصطناعي مثل 'أنا هنا لمساعدتك' أو القوائم الطويلة."
                    )
                }
            ]

        chat_histories[sender_id].append({"role": "user", "content": user_input})

        url = "https://api.mistral.ai/v1/chat/completions"
        headers = {"Authorization": f"Bearer {API_KEY}", "Content-Type": "application/json"}
        
        payload = {
            "model": "open-mistral-7b",
            "messages": chat_histories[sender_id],
            "temperature": 0.5 # لتقليل الهذرة الزائدة
        }

        response = requests.post(url, headers=headers, json=payload)
        result = response.json()
        reply = result['choices'][0]['message']['content']

        chat_histories[sender_id].append({"role": "assistant", "content": reply})

        # تنظيف الذاكرة ليبقى السيرفر سريعاً
        if len(chat_histories[sender_id]) > 6:
            chat_histories[sender_id] = [chat_histories[sender_id][0]] + chat_histories[sender_id][-5:]

        return reply, 200, {'Content-Type': 'text/plain; charset=utf-8'}

    except:
        return "المعذرة، راشد مشغول.", 200, {'Content-Type': 'text/plain; charset=utf-8'}

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=10000)
