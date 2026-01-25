import os
import requests
from flask import Flask, request
import google.generativeai as genai
from groq import Groq
import gc

app = Flask(__name__)

# --- [ إعدادات المحركات ] ---
# تأكد من إضافة المفتاحين في إعدادات رندر (Environment Variables)
GROQ_KEY = os.getenv("GROQ_API_KEY")
GEMINI_KEY = os.getenv("GEMINI_API_KEY")
INSTANCE_ID = "159896"
ULTRA_TOKEN = "3a2kuk39wf15ejiu"

# إعداد الاتصال بالمحركات
groq_client = Groq(api_key=GROQ_KEY)
genai.configure(api_key=GEMINI_KEY)

# الهوية الرسمية (تعليمات النظام الموحدة)
SYSTEM_PROMPT = (
    "أنت مساعد 'نجم الإبداع'. يجب أن تكون ردودك رسمية، مهذبة، ووقورة جداً. "
    "تحدث بلسان صاحب الحساب (راشد علي محسن صالح) وكأنك هو تماماً. "
    "يُمنع منعاً باتاً الحديث عن البرمجة، الأكواد، السيرفرات، أو أي تفاصيل تقنية. "
    "أجب فقط على محتوى سؤال السائل بأسلوب اجتماعي رسمي ووقور. "
    "إذا سألك أحد 'من أنت؟' أو 'من معي؟'، أجب حصراً وباعتزاز: 'أنا مساعد نجم الإبداع'."
)

# إعداد موديل جيمناي الاحتياطي
gemini_model = genai.GenerativeModel(
    model_name='gemini-3-flash-preview',
    system_instruction=SYSTEM_PROMPT
)

@app.route('/')
def home():
    return "<h1>سيرفر NJM: المحرك الأساسي Groq | المحرك الاحتياطي Gemini ✅</h1>", 200

@app.route('/webhook', methods=['POST'])
def whatsapp_webhook():
    data = request.get_json(force=True, silent=True)
    
    if data and data.get('event_type') == 'message_received':
        msg_body = data['data'].get('body')
        sender_id = data['data'].get('from')
        
        # التأكد من عدم الرد على النفس ووجود نص رسالة
        if not data['data'].get('fromMe') and msg_body:
            res_text = ""
            try:
                # المحاولة الأولى: استخدام Groq (الأساسي) لسرعته
                print("🔄 محاولة الرد عبر المحرك الأساسي (Groq)...")
                chat_completion = groq_client.chat.completions.create(
                    messages=[
                        {"role": "system", "content": SYSTEM_PROMPT},
                        {"role": "user", "content": msg_body}
                    ],
                    model="llama-3.3-70b-versatile",
                    temperature=0.5,
                    max_tokens=500
                )
                res_text = chat_completion.choices[0].message.content
                print("✅ تم الرد عبر Groq")

            except Exception as e:
                # إذا فشل Groq، يتدخل Gemini فوراً
                print(f"⚠️ المحرك الأساسي متوقف، التحويل للخدمة الاحتياطية... الخطأ: {e}")
                try:
                    res = gemini_model.generate_content(msg_body)
                    res_text = res.text
                    print("✅ تم الرد عبر المحرك الاحتياطي (Gemini)")
                except Exception as e2:
                    print(f"❌ كلا المحركين واجها مشكلة: {e2}")

            # إرسال الرد النهائي عبر UltraMsg
            if res_text:
                url = f"https://api.ultramsg.com/instance{INSTANCE_ID}/messages/chat"
                requests.post(url, data={"token": ULTRA_TOKEN, "to": sender_id, "body": res_text})
                
                # إخلاء الذاكرة فوراً بعد الإرسال لضمان الاستقرار
                del res_text
                gc.collect()
                
    return "OK", 200

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)
