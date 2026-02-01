import os
from flask import Flask, request
import requests

app = Flask(__name__)

# سحب المفتاح من رندر تلقائياً
API_KEY = os.environ.get("MISTRAL_API_KEY")

@app.route('/', methods=['POST'])
def chat():
    try:
        data = request.get_json()
        user_input = data.get('message', '')

        url = "https://api.mistral.ai/v1/chat/completions"
        headers = {
            "Authorization": f"Bearer {API_KEY}",
            "Content-Type": "application/json"
        }
        
        # --- التعليمات الكاملة للمساعد الشخصي ---
        system_prompt = (
            "أنت المساعد الشخصي لـ 'راشد' (صاحب هذا الجوال وهو رجل أعمال سعودي وقور). "
            "مهمتك هي إدارة الحوار بذكاء وثقل. اتبع القواعد التالية بدقة:\n"
            "1. الشخصية: أنت مساعد رسمي، هادئ، وعملي جداً. "
            "2. أسلوب الرد: إذا بدأ الشخص بالكلام، رحب به باختصار (مثل: حيّاك الله) ثم أخبره أن 'راشد مشغول حالياً'. "
            "3. المراوغة الذكية: لا تعطِ مواعيد محددة، بل قل: 'أخبرني بموضوعك وسأوصله لراشد في أقرب فرصة'. "
            "4. اللهجة: استخدم لهجة بيضاء محترمة (سعودية وقورة). "
            "5. ممنوعات قطعية: يمنع قول 'فهمت' أو 'سأقوم بالرد' أو 'أنا بوت'. "
            "6. الاختصار: لا تزد عن سطر واحد أو سطرين كحد أقصى. "
            "7. الالتزام بالوقار: يمنع أي كلام عاطفي أو رومانسي أو غير لائق."
        )

        payload = {
            "model": "open-mistral-7b", # الموديل الأكرم والمجاني
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_input}
            ],
            "temperature": 0.5 # لجعل الردود أكثر اتزاناً وثباتاً
        }

        response = requests.post(url, headers=headers, json=payload)
        
        if response.status_code == 200:
            result = response.json()
            reply = result['choices'][0]['message']['content']
            # إرسال النص "صافي" ليعمل مع نسخة ماكرودرويد المجانية للأبد
            return reply, 200, {'Content-Type': 'text/plain; charset=utf-8'}
        else:
            return f"خطأ في الاتصال بالمخ: {response.status_code}", 200, {'Content-Type': 'text/plain; charset=utf-8'}

    except Exception as e:
        return "المعذرة، راشد مشغول الآن. تواصل معه لاحقاً.", 200, {'Content-Type': 'text/plain; charset=utf-8'}

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=10000)
