import os
import requests
from flask import Flask, request

app = Flask(__name__)

# ضع مفتاح API الخاص بـ X.ai (Grok) هنا أو في إعدادات Render
API_KEY = os.environ.get("XAI_API_KEY", "ضع_مفتاح_API_هنا")

@app.route('/', methods=['POST'])
def chat():
    try:
        data = request.json
        user_message = data.get("message", "")

        # إعدادات الشخصية (ثقيل، عاقل، مختصر، ومحترم)
        system_prompt = (
            "أنت مساعد ذكي بشخصية وقورة، ثقيلة، وعاقلة. "
            "ردودك يجب أن تكون مختصرة جداً ومباشرة. "
            "يمنع منعاً باتاً استخدام أي كلمات رومانسية، عاطفية، أو مخلة بالآداب. "
            "إذا كانت الرسالة غير لائقة، اعتذر بوقار وانتهى."
        )

        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {API_KEY}"
        }

        payload = {
            "model": "grok-beta", # أو الموديل الذي تستخدمه
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_message}
            ]
        }

        response = requests.post("https://api.x.ai/v1/chat/completions", headers=headers, json=payload)
        response_data = response.json()
        
        # استخراج النص فقط
        ai_reply = response_data['choices'][0]['message']['content']

        # إرسال الرد كنص عادي (Plain Text) ليفهمه الماكرو المجاني فوراً
        return ai_reply, 200, {'Content-Type': 'text/plain; charset=utf-8'}

    except Exception as e:
        return "حصل خطأ بسيط، أعد المحاولة.", 200, {'Content-Type': 'text/plain; charset=utf-8'}

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=10000)
