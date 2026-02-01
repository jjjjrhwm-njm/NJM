import os
from flask import Flask, request
import requests

app = Flask(__name__)

# سيسحب الكود المفتاح من رندر تلقائياً
API_KEY = os.environ.get("MISTRAL_API_KEY")

@app.route('/', methods=['POST'])
def chat():
    try:
        data = request.get_json()
        user_input = data.get('message', '')

        # الرابط المباشر لخدمة ميسترال (الأكرم بـ 60 رسالة في الدقيقة)
        url = "https://api.mistral.ai/v1/chat/completions"
        headers = {
            "Authorization": f"Bearer {API_KEY}",
            "Content-Type": "application/json"
        }
        
        # الموديل المجاني السريع (open-mistral-7b)
        payload = {
            "model": "open-mistral-7b", 
            "messages": [
                {
                    "role": "system", 
                    "content": "أنت رجل سعودي وقور وعاقل وثقيل جداً. ردودك مختصرة جداً وبالعربية. يمنع أي كلام رومانسي أو غير لائق."
                },
                {"role": "user", "content": user_input}
            ]
        }

        response = requests.post(url, headers=headers, json=payload)
        result = response.json()
        
        # نرسل الرد "صافي" ليعمل مع نسخة ماكرودرويد المجانية للأبد
        return result['choices'][0]['message']['content'], 200, {'Content-Type': 'text/plain; charset=utf-8'}

    except Exception as e:
        return "عذراً، السيرفر متصل ولكن هناك مشكلة تقنية.", 200, {'Content-Type': 'text/plain; charset=utf-8'}

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=10000)
