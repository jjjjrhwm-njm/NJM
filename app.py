import os
from flask import Flask, request
import requests

app = Flask(__name__)

# جلب المفتاح الذي وضعته أنت في رندر باسم GROK_API_KEY
API_KEY = os.environ.get("GROK_API_KEY")

@app.route('/', methods=['POST'])
def chat():
    try:
        # استلام البيانات من الجوال
        data = request.get_json()
        if not data or 'message' not in data:
            return "لم تصل رسالة", 200, {'Content-Type': 'text/plain; charset=utf-8'}
            
        user_input = data.get('message', '')

        # إعدادات الاتصال بمنصة Groq (سريعة جداً وممتازة)
        url = "https://api.groq.com/openai/v1/chat/completions"
        headers = {
            "Authorization": f"Bearer {API_KEY}",
            "Content-Type": "application/json"
        }
        
        # ضبط الشخصية: ثقيل، عاقل، مختصر، ومحترم جداً
        payload = {
            "model": "llama3-8b-8192", # موديل لاما 3 المتوافق مع مفتاحك
            "messages": [
                {
                    "role": "system", 
                    "content": "أنت رجل سعودي وقور، عاقل وثقيل جداً. ردودك مختصرة لأقصى حد ومباشرة. يمنع منعاً باتاً أي كلام رومانسي أو عاطفي أو مخل. إذا سألك أحد عن شيء غير لائق، رد بكلمة واحدة: اعتذر."
                },
                {"role": "user", "content": user_input}
            ]
        }

        # إرسال الطلب
        response = requests.post(url, headers=headers, json=payload)
        
        if response.status_code == 200:
            result = response.json()
            reply = result['choices'][0]['message']['content']
            # نرسل النص "صافي" بدون أقواس برمجية ليفهمه الجوال فوراً
            return reply, 200, {'Content-Type': 'text/plain; charset=utf-8'}
        else:
            return f"خطأ في الاتصال: {response.status_code}", 200, {'Content-Type': 'text/plain; charset=utf-8'}

    except Exception as e:
        return f"عذراً، حصل خطأ تقني.", 200, {'Content-Type': 'text/plain; charset=utf-8'}

if __name__ == '__main__':
    # رندر يستخدم المنفذ 10000
    app.run(host='0.0.0.0', port=10000)
