import os
from flask import Flask, request
import requests

app = Flask(__name__)

# نستخدم نفس المفتاح الذي وضعته أنت مسبقاً في إعدادات رندر
GROK_API_KEY = os.getenv("GROK_API_KEY")

@app.route('/', methods=['POST'])
def chat():
    try:
        data = request.json
        user_msg = data.get('message', '')

        headers = {
            "Authorization": f"Bearer {GROK_API_KEY}",
            "Content-Type": "application/json"
        }

        # هنا ضبطنا الشخصية: ثقيل، عاقل، مختصر، ومحترم جداً
        payload = {
            "model": "grok-beta",
            "messages": [
                {
                    "role": "system", 
                    "content": "أنت رجل سعودي وقور، عاقل وثقيل جداً. ردودك مختصرة لأقصى حد ومباشرة. يمنع منعاً باتاً أي كلام رومانسي أو عاطفي أو مخل. إذا سألك أحد عن شيء غير لائق، رد بكلمة واحدة: اعتذر."
                },
                {"role": "user", "content": user_msg}
            ]
        }

        response = requests.post("https://api.x.ai/v1/chat/completions", json=payload, headers=headers)
        result = response.json()
        
        # استخراج النص الصافي من رد غروك
        reply_text = result['choices'][0]['message']['content']
        
        # التعديل الأهم: نرسل النص "خام" بدون JSON عشان يوصل للواتساب عربي واضح فوراً
        return reply_text, 200, {'Content-Type': 'text/plain; charset=utf-8'}
    
    except:
        return "عذراً، حصل خطأ.", 200, {'Content-Type': 'text/plain; charset=utf-8'}

if __name__ == "__main__":
    # رندر يستخدم المنفذ 10000 بشكل افتراضي
    app.run(host='0.0.0.0', port=10000)
