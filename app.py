@app.route('/', methods=['POST'])
def handle_webhook():
    try:
        data = request.get_json()
        msg_body = data.get('message', '').strip()
        sender_id = data.get('sender', 'unknown')

        if not msg_body: return "OK", 200

        # [1] جلب الذاكرة الحالية فوراً
        history = manage_memory(sender_id)
        
        # [2] الفحص الذكي: هل رحبنا بهذا الشخص في آخر 5 رسائل؟
        # نبحث في الذاكرة عن وجود أي جملة من قائمة التراحيب (GREETINGS)
        already_greeted = False
        for h in history:
            if any(greet in h['content'] for greet in GREETINGS):
                already_greeted = True
                break

        # [3] تحديد الشخصية بناءً على "المحتوى" وليس "العدد"
        if not already_greeted:
            # أول مرة: نلزمه بترحيب عشوائي
            chosen_greet = random.choice(GREETINGS)
            context_instruction = f"هذا تواصل جديد. ابدأ بهذا الترحيب بالضبط: {chosen_greet}"
        else:
            # قد رحبنا به: ممنوع يرحب، يدخل في الموضوع فوراً
            context_instruction = "ممنوع الترحيب نهائياً. أنت في وسط محادثة، رد باختصار ووقار كبشر."

        # [4] إرسال الطلب لـ Groq
        payload = {
            "model": "llama-3.3-70b-versatile",
            "messages": [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "system", "content": context_instruction}
            ] + history + [{"role": "user", "content": msg_body}],
            "temperature": 0.5 # خفضنا الحرارة لتقليل "الهذرة" الزائدة
        }

        res = requests.post("https://api.groq.com/openai/v1/chat/completions", 
                            json=payload, 
                            headers={"Authorization": f"Bearer {GROQ_API_KEY}"})
        
        reply_text = res.json()['choices'][0]['message']['content']

        # [5] حفظ الرسائل في Firebase (بعد التأكد من الرد)
        manage_memory(sender_id, "user", msg_body)
        manage_memory(sender_id, "assistant", reply_text)

        return reply_text, 200, {'Content-Type': 'text/plain; charset=utf-8'}

    except Exception as e:
        print(f"Error: {e}")
        return "أبشر، ببلغ راشد.", 200
