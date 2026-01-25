import google.generativeai as genai
import requests
from flask import Flask, request
import os

app = Flask(__name__)

# --- [ إعدادات نجم الإبداع ] ---
# المفتاح محمي في إعدادات رندر (Environment Variables) لمنع الحظر
GEMINI_KEY = os.getenv("GEMINI_API_KEY")
INSTANCE_ID = "159896"
ULTRA_TOKEN = "3a2kuk39wf15ejiu"

genai.configure(api_key=GEMINI_KEY)

# تعليمات الشخصية الرسمية (تمثيل راشد علي محسن صالح)
instructions = (
    "أنت مساعد 'نجم الإبداع'. يجب أن تكون ردودك رسمية، مهذبة، ووقورة. "
    "تحدث بلسان صاحب الحساب (راشد علي محسن صالح) وكأنك هو تماماً. "
    "يُمنع منعاً باتاً الحديث عن البرمجة، الأكواد، رندر، أو أي تفاصيل تقنية. "
    "أجب فقط على محتوى سؤال السائل بأسلوب اجتماعي رسمي ولبق. "
    "إذا سألك أحد 'من أنت؟' أو 'من معي؟'، أجب حصراً وباعتزاز: 'أنا مساعد نجم الإبداع'."
)

# استخدام الموديل الذي يعمل بنجاح في منطقتك
model = genai.GenerativeModel(
    model_name='gemini-3-flash-preview',
    system_instruction=instructions
)

@app.route('/')
def home():
    return "<h1>NJM Bot is running in Official Mode ✅</h1>", 200

@app.route('/webhook', methods=['POST'])
def whatsapp_webhook():
    # استقبال البيانات من UltraMsg
    data = request.get_json(force=True, silent=True)
    
    if data and data.get('event_type') == 'message_received':
        msg_body = data['data'].get('body')
        sender_id = data['data'].get('from')
        
        # التأكد من أن الرسالة ليست مرسلة من البوت نفسه
        if not data['data'].get('fromMe') and msg_body:
            try:
                # توليد الرد بناءً على التعليمات الرسمية
                res = model.generate_content(msg_body)
                
                # إرسال الرد للواتساب
                url = f"https://api.ultramsg.com/instance{INSTANCE_ID}/messages/chat"
                payload = {
                    "token": ULTRA_TOKEN,
                    "to": sender_id,
                    "body": res.text
                }
                
                requests.post(url, data=payload)
                print(f"✅ تم إرسال الرد الرسمي بنجاح")
            except Exception as e:
                # تسجيل الخطأ لمراجعته في سجلات رندر
                print(f"❌ خطأ في المحرك: {e}")
                
    return "OK", 200

if __name__ == "__main__":
    # التشغيل على المنفذ الذي يحدده سيرفر Render
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)
