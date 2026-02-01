# -*- coding: utf-8 -*-
"""
نظام المساعد الشخصي المتقدم لـ (راشد)
إصدار السكرتارية الاحترافية - التوسع الأقصى
المميزات: ذاكرة دائمة (SQLite)، بروتوكول بشري، تمييز دقيق للمرسلين.
"""

import os
import sqlite3
import datetime
import logging
import requests
import json
import time
from flask import Flask, request, jsonify

# ==============================================================================
# 1. إعدادات النظام والبيئة (Configuration)
# ==============================================================================
app = Flask(__name__)

# إعداد السجلات لمراقبة الأداء واكتشاف الأخطاء في Render
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - [%(name)s] - %(message)s'
)
logger = logging.getLogger("RashidAssistant")

# مفتاح ميسترال (Mistral API)
MISTRAL_API_KEY = os.environ.get("MISTRAL_API_KEY")
MISTRAL_ENDPOINT = "https://api.mistral.ai/v1/chat/completions"

# مسار قاعدة البيانات لحفظ الذاكرة للأبد
DATABASE_NAME = "rashid_memory.db"

# ==============================================================================
# 2. إدارة قاعدة البيانات والذاكرة الدائمة (Database Layer)
# ==============================================================================

def get_db_connection():
    """إنشاء اتصال آمن بقاعدة البيانات"""
    conn = sqlite3.connect(DATABASE_NAME)
    conn.row_factory = sqlite3.Row
    return conn

def init_memory_system():
    """تهيئة نظام الذاكرة عند تشغيل السيرفر لأول مرة"""
    logger.info("جاري تهيئة نظام الذاكرة الدائمة...")
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # جدول المحادثات: لحفظ تاريخ كل شخص بشكل منفصل تماماً
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            sender_id TEXT NOT NULL,
            role TEXT NOT NULL,
            content TEXT NOT NULL,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # جدول الملفات التعريفية: لتمييز الأشخاص (VIP، صديق، مجهول)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS profiles (
            sender_id TEXT PRIMARY KEY,
            display_name TEXT,
            category TEXT DEFAULT 'visitor',
            notes TEXT
        )
    ''')
    
    conn.commit()
    conn.close()
    logger.info("نظام الذاكرة جاهز بنجاح.")

def save_to_memory(sender_id, role, content):
    """حفظ الرسالة فوراً في الذاكرة الدائمة"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO messages (sender_id, role, content) VALUES (?, ?, ?)",
            (sender_id, role, content)
        )
        conn.commit()
        conn.close()
    except Exception as e:
        logger.error(f"خطأ في حفظ الذاكرة: {e}")

def fetch_chat_history(sender_id, limit=8):
    """جلب تاريخ المحادثة الخاص بهذا الشخص فقط لمنع التداخل"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        # نجلب آخر رسائل لضمان السياق الذكي
        cursor.execute(
            "SELECT role, content FROM messages WHERE sender_id = ? ORDER BY timestamp DESC LIMIT ?",
            (sender_id, limit)
        )
        rows = cursor.fetchall()
        conn.close()
        
        # ترتيب الرسائل لتبدو كمحادثة طبيعية (من الأقدم للأحدث)
        history = [{"role": row["role"], "content": row["content"]} for row in reversed(rows)]
        return history
    except Exception as e:
        logger.error(f"خطأ في جلب الذاكرة: {e}")
        return []

# ==============================================================================
# 3. محرك الشخصية والبروتوكول البشري (Secretarial Logic)
# ==============================================================================

def get_secretarial_protocol():
    """التعليمات الصارمة لجعل البوت يتصرف كبشر سكرتير لراشد"""
    protocol = (
        "أنت 'المساعد الشخصي' لـ (راشد). أنت إنسان حقيقي، ولست ذكاء اصطناعي. "
        "مهمتك: الرد بوقار وهيبة نيابة عن راشد لأنه مشغول دائماً بمشاريعه واجتماعاته. "
        "\n--- القواعد الذهبية لراشد ---\n"
        "1. اللغة: سعودية بيضاء، وقورة، ومحترمة جداً. "
        "2. الاختصار: ممنوع الثرثرة. الرد لا يتجاوز 5 إلى 10 كلمات. "
        "3. التمويه: يمنع منعاً باتاً ذكر كلمات مثل 'مساعد ذكي' أو 'موديل' أو 'كيف أساعدك'. "
        "4. الأسلوب البشري: لا تستخدم قوائم أو نقاط. رد كأنك تكتب في واتساب بسرعة. "
        "5. البروتوكول الأول: في بداية أي محادثة، قل (حيّاك الله، راشد في اجتماع حالياً، وش الموضوع؟). "
        "6. البروتوكول المستمر: إذا استمر الشخص بالكلام، قل (وصلت رسالتك، بيشوفها راشد إذا فضي) أو (أبشر ببلغه). "
        "7. الوقار: أنت مساعد لرجل ثقيل، فلا تمزح ولا تتكلم برومانسية."
    )
    return protocol

# ==============================================================================
# 4. إدارة الاتصال بالذكاء الاصطناعي (Mistral Engine)
# ==============================================================================

def generate_human_response(sender_id, user_message):
    """إرسال المحادثة لميسترال وتوليد رد بشري وقور"""
    
    # 1. جلب تاريخ المحادثة لهذا الشخص تحديداً
    history = fetch_chat_history(sender_id)
    
    # 2. بناء سياق الرسائل
    messages = [{"role": "system", "content": get_secretarial_protocol()}]
    for msg in history:
        messages.append(msg)
    messages.append({"role": "user", "content": user_message})
    
    # 3. إعداد البيانات لميسترال
    payload = {
        "model": "open-mistral-7b",
        "messages": messages,
        "temperature": 0.4, # لجعل الرد رزيناً وغير مهذار
        "max_tokens": 50,
        "top_p": 0.9
    }
    
    headers = {
        "Authorization": f"Bearer {MISTRAL_API_KEY}",
        "Content-Type": "application/json"
    }

    try:
        response = requests.post(MISTRAL_ENDPOINT, json=payload, headers=headers, timeout=15)
        if response.status_code == 200:
            result = response.json()
            return result['choices'][0]['message']['content'].strip()
        else:
            logger.error(f"API Error: {response.status_code} - {response.text}")
            return "حيّاك الله، راشد مشغول الآن."
    except Exception as e:
        logger.error(f"Request Exception: {e}")
        return "المعذرة، راشد مشغول."

# ==============================================================================
# 5. الواجهة البرمجية (Flask Routes)
# ==============================================================================

@app.route('/', methods=['POST'])
def rashid_assistant_gateway():
    """البوابة الرئيسية لاستقبال رسائل واتساب"""
    start_time = time.time()
    
    try:
        # استلام البيانات من MacroDroid
        data = request.get_json()
        if not data:
            return "No JSON provided", 400

        user_input = data.get('message', '').strip()
        # هنا الحل الجذري لمشكلة التداخل: نأخذ المعرف الفريد للمرسل
        sender_id = data.get('sender', 'unknown_visitor')

        if not user_input:
            return "Empty message received", 200

        logger.info(f"رسالة جديدة من [{sender_id}]: {user_input}")

        # 1. حفظ رسالة المستخدم في الذاكرة
        save_to_memory(sender_id, "user", user_input)

        # 2. توليد الرد من خلال بروتوكول السكرتارية
        ai_reply = generate_human_response(sender_id, user_input)

        # 3. حفظ رد المساعد في الذاكرة
        save_to_memory(sender_id, "assistant", ai_reply)

        process_time = time.time() - start_time
        logger.info(f"تم الرد في {process_time:.2f} ثانية.")

        # إرسال النص الصافي تماماً ليعمل مع ماكرودرويد المجاني
        return ai_reply, 200, {'Content-Type': 'text/plain; charset=utf-8'}

    except Exception as e:
        logger.error(f"خطأ كارثي في السيرفر: {e}")
        return "راشد مشغول حالياً.", 200

@app.route('/health', methods=['GET'])
def health_check():
    """للتأكد من أن السيرفر يعمل بكامل طاقته"""
    return jsonify({
        "status": "online",
        "owner": "Rashid",
        "system": "Advanced Secretary v5.0",
        "memory_status": "Active (SQLite)"
    }), 200

# ==============================================================================
# 6. التشغيل (Main Entry Point)
# ==============================================================================

if __name__ == '__main__':
    # تهيئة قاعدة البيانات عند أول تشغيل
    init_memory_system()
    
    # التشغيل على بورت 10000 المتوافق مع Render
    app.run(host='0.0.0.0', port=10000, debug=False)
