import google.generativeai as genai
import requests
from flask import Flask, request
import os
import gc  # مكتبة تنظيف الذاكرة لمنع انهيار السيرفر

app = Flask(__name__)

# --- [ إعدادات نجم الإبداع ] ---
# المفتاح مخفي في إعدادات رندر لحمايته من الحظر
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

# إعداد الموديل مع تحديد طول الرد لتوفير الذاكرة
model = genai.GenerativeModel(
    model_name='gemini-3-flash-preview',  # الموديل المعتمد والناجح في حسابك
    system_instruction=instructions,
    generation_config={"max_output_tokens": 500} # تقليل استهلاك الذاكرة عبر تحديد طول النص
)

@app.route('/')
def home():
    return "<h1>سيرفر NJM يعمل بالشخصية الرسمية ونظام حماية الذاكرة ✅</h1>", 200

@app.route('/webhook', methods=['POST'])
def whatsapp_webhook():
    data = request.get_json(force=True, silent=True)
    
    if data and data.get('event_type') == 'message_received':
        msg_body = data['data'].get('body')
        sender_id = data['data'].get('from')
        
        # التأكد من عدم الرد على النفس ووجود نص
        if not data['data'].get('fromMe') and msg_body:
            try:
                # توليد الرد الرسمي
                res = model.generate_content(msg_body)
                
                # إرسال للواتساب عبر UltraMsg
                url = f"https://api.ultramsg.com/instance{INSTANCE_ID}/messages/chat"
                payload = {
                    "token": ULTRA_TOKEN,
                    "to": sender_id,
                    "body": res.text
                }
                requests.post(url, data=payload)
                
                # تنظيف الذاكرة يدوياً فوراً بعد الرد لمنع رسالة SIGKILL
                del res
                gc.collect()
                print(f"✅ تم الرد الرسمي وتنظيف الذاكرة بنجاح")
                
            except Exception as e:
                print(f"❌ خطأ: {e}")
                
    return "OK", 200

if __name__ == "__main__":
    # التشغيل على المنفذ المطلوب في رندر
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)
