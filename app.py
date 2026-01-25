import os
import requests
from flask import Flask, request
from groq import Groq
import google.generativeai as genai
import threading # للتحكم في توقيت الـ 30 ثانية
import gc

app = Flask(__name__)

# --- [ الإعدادات الأساسية ] ---
RASHED_NUMBER = "0554526287" # رقمك الشخصي لتلقي التنبيهات
GROQ_KEY = os.getenv("GROQ_API_KEY")
GEMINI_KEY = os.getenv("GEMINI_API_KEY")
INSTANCE_ID = "159896"
ULTRA_TOKEN = "3a2kuk39wf15ejiu"

# ذاكرة مؤقتة لتخزين حالة المحادثات (من يراسلنا الآن؟)
active_conversations = {} 

groq_client = Groq(api_key=GROQ_KEY)
genai.configure(api_key=GEMINI_KEY)

SYSTEM_PROMPT = "أنت مساعد 'نجم الإبداع' الرسمي. رد بوقار ورسمية بلسان راشد علي محسن صالح."

def send_whatsapp(to, body):
    url = f"https://api.ultramsg.com/instance{INSTANCE_ID}/messages/chat"
    requests.post(url, data={"token": ULTRA_TOKEN, "to": to, "body": body})

def ai_reply_logic(sender_id, msg_body):
    """منطق توليد الرد من المحركين"""
    try:
        # محاولة عبر Groq أولاً
        res = groq_client.chat.completions.create(
            messages=[{"role": "system", "content": SYSTEM_PROMPT}, {"role": "user", "content": msg_body}],
            model="llama-3.3-70b-versatile"
        )
        return res.choices[0].message.content
    except:
        # احتياطي عبر Gemini
        res = genai.GenerativeModel('gemini-3-flash-preview').generate_content(msg_body)
        return res.text

def delayed_check(sender_id, initial_msg):
    """وظيفة تنتظر 30 ثانية ثم تقرر الرد"""
    import time
    time.sleep(30)
    
    # إذا مرت 30 ثانية ولم يقل راشد "أنا أرد" ولم يقل "راسله" (يعني لم يرد أصلاً)
    if active_conversations.get(sender_id) == "pending":
        reply = ai_reply_logic(sender_id, initial_msg)
        send_whatsapp(sender_id, reply)
        active_conversations[sender_id] = "ai_active"
        print(f"✅ انتهت الـ 30 ثانية: الذكاء الاصطناعي تولى الرد على {sender_id}")

@app.route('/webhook', methods=['POST'])
def whatsapp_webhook():
    data = request.get_json(force=True, silent=True)
    if not data or data.get('event_type') != 'message_received':
        return "OK", 200

    msg_body = data['data'].get('body', '').strip()
    sender_id = data['data'].get('from')

    # --- أولاً: إذا كانت الرسالة منك أنت (راشد) للتحكم ---
    if sender_id == f"{RASHED_NUMBER}@c.us":
        # ابحث عن آخر شخص راسلنا (الذي حالته pending)
        target_sender = next((s for s, status in active_conversations.items() if status == "pending"), None)
        
        if "راسله" in msg_body and target_sender:
            active_conversations[target_sender] = "ai_active"
            send_whatsapp(RASHED_NUMBER, "✅ أبشر، توليت المهمة وسأرد عليه الآن.")
            # توليد رد فوري
            reply = ai_reply_logic(target_sender, "مرحباً") # أو آخر رسالة
            send_whatsapp(target_sender, reply)
            
        elif "انا ارد" in msg_body and target_sender:
            active_conversations[target_sender] = "manual"
            send_whatsapp(RASHED_NUMBER, "✅ تم إيقاف الردود الآلية لهذه المحادثة. تفضل بالرد.")

    # --- ثانياً: إذا كانت الرسالة من شخص غريب ---
    elif not data['data'].get('fromMe'):
        if sender_id not in active_conversations or active_conversations[sender_id] == "pending":
            active_conversations[sender_id] = "pending"
            
            # 1. إشعار فوري لراشد
            notification = f"🔔 {sender_id} قام بمراسلتك.\nالرسالة: {msg_body}\n\nهل تريدني أن أراسل بدلاً منك؟ (أجب بـ 'راسله' أو 'انا ارد')"
            send_whatsapp(RASHED_NUMBER, notification)
            
            # 2. تشغيل مؤقت الـ 30 ثانية في الخلفية
            thread = threading.Thread(target=delayed_check, args=(sender_id, msg_body))
            thread.start()

    gc.collect()
    return "OK", 200

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)
