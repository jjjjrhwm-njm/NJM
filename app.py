import os
from flask import Flask, request, jsonify
import google.generativeai as genai

app = Flask(__name__)

# إعداد المحرك (Gemini) باستخدام المفتاح الذي وضعته في Render
genai.configure(api_key=os.environ.get("GOOGLE_API_KEY"))
model = genai.GenerativeModel('gemini-1.5-flash')

@app.route('/')
def home():
    return "Najm AI is Live! 🚀"

# هذا هو "المستقبل" الذي سيتلقى رسائل الواتساب
@app.route('/webhook', methods=['POST'])
def webhook():
    data = request.get_json()
    # هنا يستقبل النص القادم من الواتساب
    user_message = data.get('message', '') 
    
    if user_message:
        # إرسال النص لـ Gemini وأخذ الرد
        response = model.generate_content(user_message)
        return jsonify({"reply": response.text})
    
    return jsonify({"status": "no message"}), 400

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=5000)
