# --- [ تحديث المحرك لحل مشكلة 404 ] ---
# بدلاً من gemini-pro، نستخدم الإصدار الأحدث
model = genai.GenerativeModel('gemini-1.5-flash') 

@app.route('/webhook', methods=['POST'])
def whatsapp_webhook():
    data = request.get_json(force=True, silent=True)
    if data and data.get('event_type') == 'message_received':
        msg_body = data['data'].get('body')
        sender_id = data['data'].get('from')
        if not data['data'].get('fromMe') and msg_body:
            try:
                # محاولة توليد المحتوى بالموديل الجديد
                res = model.generate_content(f"أجب بلهجة سعودية: {msg_body}")
                
                # إرسال الرد عبر UltraMsg
                url = f"https://api.ultramsg.com/instance{INSTANCE_ID}/messages/chat"
                requests.post(url, data={"token": ULTRA_TOKEN, "to": sender_id, "body": res.text})
                print(f"✅ تم إرسال الرد بنجاح لـ {sender_id}")
            except Exception as e:
                # طباعة الخطأ الحقيقي في السجلات للتشخيص
                print(f"❌ خطأ جيمني: {e}")
