import os
from flask import Flask, request, jsonify
import requests

app = Flask(__name__)

# سيسحب الكود مفتاح غروك من إعدادات البيئة في رندر
GROK_API_KEY = os.getenv("GROK_API_KEY")

@app.route('/', methods=['POST'])
def chat():
    data = request.json
    user_msg = data.get('message', '')

    headers = {
        "Authorization": f"Bearer {GROK_API_KEY}",
        "Content-Type": "application/json"
    }

    payload = {
        "model": "grok-beta",
        "messages": [
            {"role": "system", "content": "أنت بشري ذكي من السعودية ترد بلهجة عامية مختصرة."},
            {"role": "user", "content": user_msg}
        ]
    }

    try:
        response = requests.post("https://api.x.ai/v1/chat/completions", json=payload, headers=headers)
        result = response.json()
        reply_text = result['choices'][0]['message']['content']
        return jsonify({"reply": reply_text})
    except:
        return jsonify({"reply": "عذراً، حدث خطأ في الاتصال بالمخ."})

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=5000)
