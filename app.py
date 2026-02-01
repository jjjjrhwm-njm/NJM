# -*- coding: utf-8 -*-
"""
====================================================================================================
نظام الإدارة المكتبية الرقمية المتكامل (الإصدار 7.5 - المساعد الملكي الذكي)
====================================================================================================
تعديل خاص لراشد: منع التكرار وتعزيز الذاكرة التفاعلية.
"""

import os
import sys
import json
import time
import sqlite3
import logging
import datetime
import requests
from flask import Flask, request, jsonify, make_response

app = Flask(__name__)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - [%(levelname)s] - %(message)s',
    stream=sys.stdout
)
logger = logging.getLogger("Rashid_Smart_Assistant")

MISTRAL_API_KEY = os.environ.get("MISTRAL_API_KEY")
MISTRAL_API_URL = "https://api.mistral.ai/v1/chat/completions"
DATABASE_FILE = "rashid_royal_vault.db"

# --------------------------------------------------------------------------------------------------
# [1] إدارة الذاكرة (Memory Engine)
# --------------------------------------------------------------------------------------------------

class MemoryEngine:
    @staticmethod
    def connect():
        return sqlite3.connect(DATABASE_FILE)

    @classmethod
    def initialize_vault(cls):
        conn = cls.connect()
        cursor = conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS conversation_history (
                msg_id INTEGER PRIMARY KEY AUTOINCREMENT,
                sender_token TEXT NOT NULL,
                actor_role TEXT NOT NULL,
                message_content TEXT NOT NULL,
                recorded_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        conn.commit()
        conn.close()

    @classmethod
    def commit_to_memory(cls, sender, role, text):
        conn = cls.connect()
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO conversation_history (sender_token, actor_role, message_content) VALUES (?, ?, ?)",
            (sender, role, text)
        )
        conn.commit()
        conn.close()

    @classmethod
    def retrieve_context(cls, sender, depth=6):
        conn = cls.connect()
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute(
            "SELECT actor_role, message_content FROM conversation_history WHERE sender_token = ? "
            "ORDER BY recorded_at DESC LIMIT ?",
            (sender, depth)
        )
        records = cursor.fetchall()
        conn.close()
        return [{"role": r["actor_role"], "content": r["message_content"]} for r in reversed(records)]

# --------------------------------------------------------------------------------------------------
# [2] بروتوكول السكرتارية (Smart Protocol)
# --------------------------------------------------------------------------------------------------

def construct_dynamic_protocol(has_history=False):
    """تغيير التعليمات بناءً على وجود تاريخ للمحادثة لمنع التكرار"""
    
    base_rules = (
        "أنت 'المساعد الشخصي' لـ (راشد). إنسان سعودي وقور، رزين، ومختصر جداً. "
        "ممنوع لغة الآلة (ذكاء، مساعد، كيف أخدمك). لهجتك سعودية بيضاء ثقيلة. "
        "ردودك لا تتجاوز 7 كلمات أبداً. "
    )
    
    if not has_history:
        # تعليمات المحادثة الجديدة
        protocol = base_rules + "هذه أول مرة يرسل الشخص، قل دائماً: (حيّاك الله، راشد في اجتماع حالياً، وش الموضوع؟)."
    else:
        # تعليمات المحادثة المستمرة (لمنع التكرار)
        protocol = base_rules + "لقد رحبت بالشخص مسبقاً. الآن تفاعل مع كلامه بذكاء دون تكرار جملة 'راشد في اجتماع'. رد كأنك سكرتير يتابع الموضوع."
        
    return protocol

# --------------------------------------------------------------------------------------------------
# [3] معالجة الطلبات (Core Logic)
# --------------------------------------------------------------------------------------------------

def perform_intelligence_request(sender, input_text):
    context_window = MemoryEngine.retrieve_context(sender)
    
    # تحديد البروتوكول المناسب: هل توجد محادثة سابقة؟
    has_history = len(context_window) > 0
    system_prompt = construct_dynamic_protocol(has_history)
    
    messages_payload = [
        {"role": "system", "content": system_prompt}
    ] + context_window + [
        {"role": "user", "content": input_text}
    ]
    
    api_request_data = {
        "model": "open-mistral-7b",
        "messages": messages_payload,
        "temperature": 0.3, # رزانة عالية لمنع التكرار
        "max_tokens": 50
    }
    
    api_headers = {
        "Authorization": f"Bearer {MISTRAL_API_KEY}",
        "Content-Type": "application/json"
    }

    try:
        response = requests.post(MISTRAL_API_URL, json=api_request_data, headers=api_headers, timeout=12)
        if response.status_code == 200:
            return response.json()['choices'][0]['message']['content'].strip()
        return "أبشر ببلغه إذا خلص راشد."
    except:
        return "راشد مشغول حالياً."

@app.route('/', methods=['POST'])
def gateway_entry():
    try:
        raw_payload = request.get_json()
        msg_body = raw_payload.get('message', '').strip()
        sender_identity = raw_payload.get('sender', 'guest')

        if not msg_body: return "Empty", 200

        # [أ] حفظ رسالة المستخدم
        MemoryEngine.commit_to_memory(sender_identity, "user", msg_body)

        # [ب] جلب الرد
        humanized_reply = perform_intelligence_request(sender_identity, msg_body)

        # [ج] حفظ رد المساعد
        MemoryEngine.commit_to_memory(sender_identity, "assistant", humanized_reply)

        return humanized_reply, 200, {'Content-Type': 'text/plain; charset=utf-8'}
    except:
        return "المعذرة، راشد مشغول.", 200

if __name__ == '__main__':
    MemoryEngine.initialize_vault()
    app.run(host='0.0.0.0', port=10000)
