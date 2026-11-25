#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
𝗘𝗛𝗔𝗕 - النظام الموحد للاستضافة والتحكم وإدارة البوتات والخدمات
مُدمج ومُصلّح بالكامل مع تشفير AES-CBC وحماية السيرفر والتخزين
"""

import os
import sys
import re
import gc
import ast
import json
import time
import uuid
import base64
import shutil
import socket
import hashlib
import logging
import asyncio
import sqlite3
import zipfile
import tempfile
import platform
import subprocess
import threading
from urllib.parse import quote
from functools import wraps
from html import escape
from datetime import datetime, timedelta, timezone

import psutil
import requests
from flask import Flask, request, jsonify, session, Response, redirect
from werkzeug.security import generate_password_hash, check_password_hash

try:
    from bs4 import BeautifulSoup
except Exception:
    BeautifulSoup = None

try:
    from Crypto.Cipher import AES
    from Crypto.Util.Padding import pad, unpad
    from Crypto.Random import get_random_bytes
except Exception:
    AES = None
    pad = None
    unpad = None
    get_random_bytes = lambda n: os.urandom(n)

import telebot
from telebot import types

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.constants import ParseMode
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    filters,
    ContextTypes,
    ConversationHandler,
)

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger("EHAB_UNIFIED_HOST")


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


# ==============================================================================
# ١. المسارات والتخزين والثوابت الموحدة (Paths, Storage & Unified Constants)
# ==============================================================================
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
SECURE_ROOT = os.path.abspath(BASE_DIR)

RUNNING_DIR = os.path.join(BASE_DIR, "active_bots")
LOGS_DIR = os.path.join(BASE_DIR, "bot_logs")
DB_DIR = os.path.join(BASE_DIR, "database")
ASSETS_DIR = os.path.join(BASE_DIR, "assets")
STORE_DIR = os.path.join(BASE_DIR, "store_files")
THUMBS_DIR = os.path.join(ASSETS_DIR, "thumbs")
MARKET_DIR = os.path.join(BASE_DIR, "market")
ENV_DIR = os.path.join(BASE_DIR, "bot_environments")
ENCRYPTED_DIR = os.path.join(BASE_DIR, "encrypted_files")
DOWNLOAD_DIR = os.path.join(BASE_DIR, "downloads")
UPLOAD_DIR = os.path.abspath(os.path.join(BASE_DIR, "upload_bots"))
SUSPICIOUS_DIR = os.path.join(BASE_DIR, "suspicious_files")
BACKUPS_DIR = os.path.join(BASE_DIR, "backups")

USERS_ROOT = os.path.join(SECURE_ROOT, "USERS")
DATA_DIR = os.path.join(SECURE_ROOT, "DATA")
SERVICES_STORAGE_DIR = os.path.join(DATA_DIR, "services_storage")

MAX_LOG_SIZE_KB = 512
_ipinfo = {"t": 0, "data": None}
bot_scripts = {}

for d in [
    RUNNING_DIR, LOGS_DIR, DB_DIR, ASSETS_DIR, STORE_DIR, THUMBS_DIR,
    MARKET_DIR, ENV_DIR, ENCRYPTED_DIR, DOWNLOAD_DIR, UPLOAD_DIR,
    SUSPICIOUS_DIR, BACKUPS_DIR, USERS_ROOT, DATA_DIR, SERVICES_STORAGE_DIR
]:
    os.makedirs(d, exist_ok=True)

USERS_DB = os.path.join(DB_DIR, "users.json")
FILES_DB = os.path.join(DB_DIR, "files.json")
SETTINGS_DB = os.path.join(DB_DIR, "settings.json")
STORE_DB = os.path.join(DB_DIR, "store.json")
ADMINS_DB = os.path.join(DB_DIR, "admins.json")
MARKET_DB = os.path.join(DB_DIR, "market.json")
SECURITY_DB = os.path.join(DB_DIR, "security.json")
PURCHASES_DB_PATH = os.path.join(DB_DIR, "purchases.db")

PANEL_USERS_DB = os.path.join(DATA_DIR, "users.json")
PENDING_DB = os.path.join(DATA_DIR, "pending_requests.json")
BALANCES_DB = os.path.join(DATA_DIR, "balances.json")
ORDERS_DB = os.path.join(DATA_DIR, "orders.json")
SERVER_TYPES_DB = os.path.join(DATA_DIR, "server_types.json")
INDEX_HTML_PATH = os.path.join(BASE_DIR, "index.html")

PANEL_PORT_PRIMARY = int(os.environ.get("PORT", os.environ.get("SERVER_PORT", 8008)))
PANEL_PORT_SECONDARY = int(os.environ.get("SECONDARY_SERVER_PORT", 3004))

ADMIN_USERNAME = os.environ.get("ADMIN_USER", "admin")
ADMIN_PASSWORD = os.environ.get("ADMIN_PASS", "1002670694")
ADMIN_FREE_MODE = True

TOKEN = os.environ.get("TOKEN", "8641088295:AAGlgERmbLszyMQtxxzGXcfyurACiX5aMhg").strip()


_admin_ids_raw = os.environ.get("ADMIN_TELEGRAM_IDS", "1002670694")
ADMIN_TELEGRAM_IDS = [
    int(x.strip()) for x in _admin_ids_raw.split(",") if x.strip().isdigit()
]
ADMIN_ID = int(os.environ.get("ADMIN_ID", str(ADMIN_TELEGRAM_IDS[0] if ADMIN_TELEGRAM_IDS else 1002670694)))
if ADMIN_ID not in ADMIN_TELEGRAM_IDS:
    ADMIN_TELEGRAM_IDS.append(ADMIN_ID)

FIRE_EFFECT_ID = os.environ.get("FIRE_EFFECT_ID", None)
DEV_TELEGRAM = os.environ.get("DEV_TELEGRAM", "https://t.me/Y_20_20")
CHANNEL_EHAB_ME = os.environ.get("CHANNEL_EHAB_ME", str(ADMIN_ID))
CHANNEL_EHAB_LINK = os.environ.get("CHANNEL_EHAB_LINK", "https://t.me/Y_20_20")
user_bot = os.environ.get("BOT_USERNAME", "ehab_host_bot").lstrip("@")
LOG_CHANNEL_ID = os.environ.get("LOG_CHANNEL_ID", str(ADMIN_ID)).strip()

API_BASE_URL = os.environ.get("API_BASE_URL", f"http://127.0.0.1:{PANEL_PORT_PRIMARY}").rstrip("/")
PUBLIC_API_URL = os.environ.get("PUBLIC_API_URL", "https://ehab700-host.onrender.com").strip()
GOOGLE_REDIRECT_URL = os.environ.get("GOOGLE_REDIRECT_URL", "https://ehab700-host.onrender.com").strip() or "https://ehab700-host-3.onrender.com"

DEVELOPER_INFO = (
    "<b><blockquote>🛠 طُوِّر بواسطة: 𝗘𝗛𝗔𝗕𝗔𝗜𝗛𝗔𝗪𝗕𝗔𝗡𝗜</blockquote></b>\n"
    "<b>📬 تواصل:</b> <code>@Y_20_20</code>\n"
    "<tg-spoiler>نسخة الأدمن مجانية ومحمية بالكامل - جميع الحقوق محفوظة</tg-spoiler>"
)

SERVICES_CATALOG = {
    "srv_python_host": {
        "id": "srv_python_host",
        "name": "استضافة بايثون / بوتات (Python)",
        "price": 5.0,
        "currency": "USD",
        "desc": "تشغيل سكريبتات وبوتات بايثون مع تثبيت تلقائي للمكتبات.",
        "file": os.path.join(SERVICES_STORAGE_DIR, "service_python_host.json"),
    },
    "srv_php_host": {
        "id": "srv_php_host",
        "name": "استضافة PHP ومواقع ويب",
        "price": 4.0,
        "currency": "USD",
        "desc": "تشغيل مشاريع PHP وملفات الويب مع إدارة الملفات والسجلات.",
        "file": os.path.join(SERVICES_STORAGE_DIR, "service_php_host.json"),
    },
    "srv_js_html_host": {
        "id": "srv_js_html_host",
        "name": "استضافة HTML / JavaScript / Node",
        "price": 3.0,
        "currency": "USD",
        "desc": "استضافة صفحات الويب والتطبيقات الأمامية والخلفية.",
        "file": os.path.join(SERVICES_STORAGE_DIR, "service_js_html_host.json"),
    },
    "srv_web_request": {
        "id": "srv_web_request",
        "name": "طلب موقع إلكتروني / ربط مسار مخصص",
        "price": 10.0,
        "currency": "USD",
        "desc": "تجهيز مسار موقع إلكتروني وملفاته وضبط الإعدادات الخاصة به.",
        "file": os.path.join(SERVICES_STORAGE_DIR, "service_web_request.json"),
    },
}

(
    WAITING_FOR_API_KEY,
    WAITING_FOR_NEW_SERVER_NAME,
    WAITING_FOR_SERVER_TYPE,
    WAITING_FOR_DELETE_USERNAME,
    WAITING_FOR_TOPUP_INFO,
    WAITING_FOR_SERVICE_INPUT,
) = range(6)

db_lock = threading.Lock()
lock = threading.Lock()
finance_lock = threading.Lock()
cancel_states = {}
last_bot_messages = {}
active_processes = {}
admin_steps = {}
PENDING = {}
USER_STEPS = {}
USERS = {}
running_procs = {}
server_states = {}

bot = telebot.TeleBot(TOKEN, parse_mode="HTML", threaded=True)
app = Flask(__name__)
app.secret_key = os.environ.get("PANEL_SECRET_KEY") or ("EHAB_HOST_SECURE_" + os.urandom(16).hex())
app.config["SESSION_COOKIE_HTTPONLY"] = True
app.config["SESSION_COOKIE_SAMESITE"] = "Lax"


# ==============================================================================
# ٢. دوال القواعد والبيانات والمساعدات (Database, Storage & Utility Helpers)
# ==============================================================================
def is_path_safe(base_dir: str, target_path: str) -> bool:
    try:
        real_target = os.path.realpath(target_path)
        real_base = os.path.realpath(base_dir)
        common = os.path.commonpath([real_target, real_base])
        return common == real_base
    except (ValueError, OSError):
        return False


def _atomic_write_json_to(path: str, payload: dict):
    with db_lock:
        abs_path = os.path.abspath(path)
        os.makedirs(os.path.dirname(abs_path), exist_ok=True)
        tmp = abs_path + f".{os.getpid()}.{uuid.uuid4().hex[:6]}.tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(payload, f, indent=2, ensure_ascii=False)
            f.flush()
            try:
                os.fsync(f.fileno())
            except Exception:
                pass
        os.replace(tmp, abs_path)


def _read_json_from(path: str, default: dict) -> dict:
    with db_lock:
        if not os.path.exists(path):
            return json.loads(json.dumps(default))
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
                return data if isinstance(data, dict) else json.loads(json.dumps(default))
        except Exception:
            return json.loads(json.dumps(default))


def read_json(path: str) -> dict:
    return _read_json_from(path, {})


def write_json(path: str, payload: dict):
    _atomic_write_json_to(path, payload if isinstance(payload, dict) else {})


def _atomic_write_json(path: str, payload: dict):
    _atomic_write_json_to(path, payload)


def _read_json(path: str, default: dict) -> dict:
    return _read_json_from(path, default)


def db_conn():
    os.makedirs(os.path.dirname(PURCHASES_DB_PATH), exist_ok=True)
    conn = sqlite3.connect(PURCHASES_DB_PATH, check_same_thread=False)
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS purchases (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            item_id TEXT,
            amount REAL,
            created_at TEXT
        )
        """
    )
    conn.commit()
    return conn


def get_settings() -> dict:
    defaults = {
        "channels": [],
        "bot_name": "EHAB Host",
        "bot_image": None,
        "file_thumb": None,
        "bot_locked": False,
        "auto_approve": False,
        "maintenance_mode": False,
        "python_upload_price": 1.0,
    }
    cur = read_json(SETTINGS_DB)
    for k, v in defaults.items():
        if k not in cur:
            cur[k] = v
    return cur


def save_settings(settings: dict):
    write_json(SETTINGS_DB, settings)


def gen_id(length: int = 8) -> str:
    return uuid.uuid4().hex[:length]


def esc(txt) -> str:
    return escape(str(txt or ""))


def _esc(txt) -> str:
    return escape(str(txt or ""))


def _gb(num_bytes: int) -> str:
    return f"{num_bytes / (1024 ** 3):.2f}"


def _mb(num_bytes: int) -> str:
    return f"{num_bytes / (1024 ** 2):.2f}"


def _dir_size(path: str) -> int:
    total = 0
    if not path or not os.path.exists(path):
        return 0
    try:
        for root, _dirs, files in os.walk(path):
            for fname in files:
                fp = os.path.join(root, fname)
                if not os.path.islink(fp):
                    try:
                        total += os.path.getsize(fp)
                    except OSError:
                        pass
    except Exception:
        pass
    return total


def _get_ipinfo() -> dict:
    now = time.time()
    if _ipinfo.get("data") and now - _ipinfo.get("t", 0) < 300:
        return _ipinfo["data"]
    try:
        r = requests.get("http://ip-api.com/json/", timeout=5)
        if r.ok:
            data = r.json()
            _ipinfo["t"] = now
            _ipinfo["data"] = data
            return data
    except Exception:
        pass
    return _ipinfo.get("data") or {"query": get_ip(), "country": "غير متاح", "regionName": "", "city": "", "isp": "—"}


def file_token(file_name: str) -> str:
    return hashlib.sha256((file_name or "file").encode("utf-8")).hexdigest()[:12]


def _get_ai_repair_file(call):
    parts = (call.data or "").split("_")
    files = read_json(FILES_DB)
    if len(parts) >= 3:
        fid_candidate = parts[1]
        if fid_candidate in files:
            finfo = files[fid_candidate]
            return finfo.get("user_id"), finfo.get("file_name", "script.py"), fid_candidate
    for fid, finfo in files.items():
        if finfo.get("user_id") == call.from_user.id:
            return finfo.get("user_id"), finfo.get("file_name", "script.py"), fid
    return None


def scan_with_virustotal(content: str, file_name: str) -> bool:
    vt_key = os.environ.get("VIRUSTOTAL_API_KEY", "").strip()
    if not vt_key:
        return True
    try:
        file_hash = hashlib.sha256(content.encode("utf-8", errors="ignore")).hexdigest()
        r = requests.get(
            f"https://www.virustotal.com/api/v3/files/{file_hash}",
            headers={"x-apikey": vt_key},
            timeout=10,
        )
        if r.status_code == 200:
            stats = r.json().get("data", {}).get("attributes", {}).get("last_analysis_stats", {})
            if stats.get("malicious", 0) > 0:
                return False
    except Exception:
        pass
    return True


def get_ip():
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("10.255.255.255", 1))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return "127.0.0.1"


# ==============================================================================
# ٣. تهيئة قاعدة البيانات والتشفير والحماية (DB Init, AES Encryption & Security)
# ==============================================================================
def init_db():
    global USERS
    default_settings = {
        "channels": [],
        "bot_name": "EHAB Host",
        "bot_image": None,
        "file_thumb": None,
        "bot_locked": False,
        "auto_approve": False,
        "maintenance_mode": False,
        "python_upload_price": 1.0,
    }
    current_settings = read_json(SETTINGS_DB)
    for key, value in default_settings.items():
        if key not in current_settings:
            current_settings[key] = value
    write_json(SETTINGS_DB, current_settings)

    for path in [USERS_DB, FILES_DB, STORE_DB, MARKET_DB, SECURITY_DB]:
        if not os.path.exists(path):
            write_json(path, {})

    admins_data = read_json(ADMINS_DB)
    if "admins" not in admins_data or ADMIN_ID not in admins_data["admins"]:
        base_admins = admins_data.get("admins", [])
        if ADMIN_ID not in base_admins:
            base_admins.append(ADMIN_ID)
        admins_data["admins"] = base_admins
        write_json(ADMINS_DB, admins_data)

    USERS = read_json(USERS_DB)
    try:
        db_conn().close()
    except Exception:
        pass
    init_security()


def init_security():
    security = read_json(SECURITY_DB)
    if "master_key" not in security:
        master_key = base64.b64encode(get_random_bytes(32)).decode("utf-8")
        security["master_key"] = master_key
        security["file_keys"] = {}
        write_json(SECURITY_DB, security)


def get_master_key():
    security = read_json(SECURITY_DB)
    master_key = security.get("master_key")
    if not master_key:
        master_key = base64.b64encode(get_random_bytes(32)).decode("utf-8")
        security["master_key"] = master_key
        write_json(SECURITY_DB, security)
    return base64.b64decode(master_key)


def generate_file_key(fid, user_id):
    security = read_json(SECURITY_DB)
    file_keys = security.get("file_keys", {})
    if fid not in file_keys:
        combined = f"{fid}:{user_id}:{ADMIN_ID}:{TOKEN}"
        salt = hashlib.sha256(combined.encode()).digest()[:16]
        master_key = get_master_key()
        kdf = hashlib.pbkdf2_hmac("sha256", master_key, salt, 100000, dklen=32)
        file_keys[fid] = {
            "key": base64.b64encode(kdf).decode("utf-8"),
            "salt": base64.b64encode(salt).decode("utf-8"),
            "user_id": user_id,
        }
        security["file_keys"] = file_keys
        write_json(SECURITY_DB, security)
    return file_keys[fid]


def get_file_key(fid):
    security = read_json(SECURITY_DB)
    file_keys = security.get("file_keys", {})
    return file_keys.get(fid)


def encrypt_file_content(content, fid, user_id):
    try:
        file_key_info = generate_file_key(fid, user_id)
        key = base64.b64decode(file_key_info["key"])
        salt = base64.b64decode(file_key_info["salt"])
        if AES and pad:
            cipher = AES.new(key, AES.MODE_CBC)
            ct_bytes = cipher.encrypt(pad(content.encode("utf-8"), AES.block_size))
            iv_b64 = base64.b64encode(cipher.iv).decode("utf-8")
            mode_tag = "AES-256-CBC"
        else:
            iv = os.urandom(16)
            stream = hashlib.pbkdf2_hmac("sha256", key, iv, 1000, dklen=len(content.encode("utf-8")))
            ct_bytes = bytes(a ^ b for a, b in zip(content.encode("utf-8"), stream))
            iv_b64 = base64.b64encode(iv).decode("utf-8")
            mode_tag = "PBKDF2-XOR"
        encrypted_data = {
            "mode": mode_tag,
            "iv": iv_b64,
            "ciphertext": base64.b64encode(ct_bytes).decode("utf-8"),
            "salt": base64.b64encode(salt).decode("utf-8"),
            "fid": fid,
            "user_id": user_id,
            "timestamp": datetime.now().isoformat(),
        }
        return json.dumps(encrypted_data)
    except Exception as e:
        print(f"Encryption error: {e}")
        return None


def decrypt_file_content(encrypted_json, fid):
    try:
        data = json.loads(encrypted_json)
        file_key_info = get_file_key(fid)
        if not file_key_info:
            return None
        key = base64.b64decode(file_key_info["key"])
        iv = base64.b64decode(data["iv"])
        ct = base64.b64decode(data["ciphertext"])
        if data.get("mode") == "PBKDF2-XOR" or not (AES and unpad):
            stream = hashlib.pbkdf2_hmac("sha256", key, iv, 1000, dklen=len(ct))
            pt = bytes(a ^ b for a, b in zip(ct, stream))
        else:
            cipher = AES.new(key, AES.MODE_CBC, iv)
            pt = unpad(cipher.decrypt(ct), AES.block_size)
        return pt.decode("utf-8")
    except Exception as e:
        print(f"Decryption error: {e}")
        return None


def save_encrypted_file(fid, content, user_id):
    encrypted_content = encrypt_file_content(content, fid, user_id)
    if encrypted_content:
        encrypted_path = os.path.join(ENCRYPTED_DIR, f"{fid}.enc")
        if not is_path_safe(ENCRYPTED_DIR, encrypted_path):
            return False
        with open(encrypted_path, "w", encoding="utf-8") as f:
            f.write(encrypted_content)
        return True
    return False


def load_encrypted_file(fid):
    encrypted_path = os.path.join(ENCRYPTED_DIR, f"{fid}.enc")
    if is_path_safe(ENCRYPTED_DIR, encrypted_path) and os.path.exists(encrypted_path):
        with open(encrypted_path, "r", encoding="utf-8") as f:
            encrypted_content = f.read()
        return decrypt_file_content(encrypted_content, fid)
    return None


def verify_file_access(fid, user_id):
    files = read_json(FILES_DB)
    if fid not in files:
        return False
    file_info = files[fid]
    file_user_id = file_info.get("user_id")
    if user_id == ADMIN_ID or is_admin(user_id):
        return True
    if file_user_id == user_id:
        return True
    if file_info.get("type") == "store":
        store = read_json(STORE_DB)
        if fid in store:
            return True
    return False


def is_bot_locked():
    return get_settings().get("bot_locked", False)


def is_admin(user_id):
    if user_id == ADMIN_ID or user_id in ADMIN_TELEGRAM_IDS:
        return True
    admins_data = read_json(ADMINS_DB)
    return user_id in admins_data.get("admins", [ADMIN_ID])


def is_main_admin(user_id):
    return user_id == ADMIN_ID


def get_admins():
    admins_data = read_json(ADMINS_DB)
    admins = admins_data.get("admins", [ADMIN_ID])
    if ADMIN_ID not in admins:
        admins.append(ADMIN_ID)
    return admins


def add_admin(user_id):
    admins_data = read_json(ADMINS_DB)
    if user_id not in admins_data.get("admins", []):
        admins_data["admins"] = admins_data.get("admins", []) + [user_id]
        write_json(ADMINS_DB, admins_data)
        return True
    return False


def remove_admin(user_id):
    if user_id == ADMIN_ID:
        return False
    admins_data = read_json(ADMINS_DB)
    if user_id in admins_data.get("admins", []):
        admins_data["admins"].remove(user_id)
        write_json(ADMINS_DB, admins_data)
        return True
    return False


def day_name():
    ds = ["الأحد", "الأثنين", "الثلاثاء", "الأربعاء", "الخميس", "الجمعة", "السبت"]
    w = int(datetime.now().strftime("%w"))
    return ds[w]


def month_name():
    month_n = ["فارغ", "يناير", "فبراير", "مارس", "ابريل", "مايو", "يونيو", "يوليو", "اغسطس", "سبتمبر", "اكتوبر", "نوفمبر", "ديسمبر"]
    m = int(datetime.now().strftime("%m"))
    return month_n[m]


def get_date_strings():
    now = datetime.now()
    tim1 = now.strftime("%H:%M:%S")
    ampm = now.strftime("%p").lower()
    e_ar = "مسائاً" if ampm == "pm" else "صباحاً"
    y = now.strftime("%Y")
    m = now.strftime("%m")
    d = now.strftime("%d")
    dy = day_name()
    mh = month_name()
    day2 = f"{dy} {d} {mh} {y} | {tim1} {e_ar}"
    day3 = f"{d}-{m}-{y} | {tim1} {e_ar}"
    return day2, day3


def deco(title, content, first="مستخدم"):
    return f"<blockquote><b>{content}</b></blockquote>\n\n"


def delete_last_message(chat_id):
    if chat_id in last_bot_messages:
        try:
            bot.delete_message(chat_id, last_bot_messages[chat_id])
        except Exception:
            pass


def save_message(chat_id, msg_id):
    last_bot_messages[chat_id] = msg_id


def send_msg(chat_id, text, markup=None, effect_id=FIRE_EFFECT_ID):
    delete_last_message(chat_id)
    settings = get_settings()
    kw = {"parse_mode": "HTML", "reply_markup": markup}
    if effect_id:
        kw["message_effect_id"] = effect_id
    try:
        if settings.get("bot_image"):
            msg = bot.send_photo(chat_id, settings["bot_image"], caption=text, **kw)
        else:
            msg = bot.send_message(chat_id, text, **kw)
        save_message(chat_id, msg.message_id)
        return msg
    except Exception:
        msg = bot.send_message(chat_id, text, **kw)
        save_message(chat_id, msg.message_id)
        return msg


def edit_msg(call, text, markup):
    try:
        if call.message.content_type == "photo":
            bot.edit_message_caption(text[:4096], call.message.chat.id, call.message.message_id, parse_mode="HTML", reply_markup=markup)
        else:
            bot.edit_message_text(text[:4096], call.message.chat.id, call.message.message_id, parse_mode="HTML", reply_markup=markup)
        save_message(call.message.chat.id, call.message.message_id)
    except Exception:
        try:
            bot.delete_message(call.message.chat.id, call.message.message_id)
        except Exception:
            pass
        settings = get_settings()
        kw = {"parse_mode": "HTML", "reply_markup": markup}
        if FIRE_EFFECT_ID:
            kw["message_effect_id"] = FIRE_EFFECT_ID
        try:
            if settings.get("bot_image"):
                msg = bot.send_photo(call.message.chat.id, settings["bot_image"], caption=text[:4096], **kw)
            else:
                msg = bot.send_message(call.message.chat.id, text[:4096], **kw)
            save_message(call.message.chat.id, msg.message_id)
        except Exception:
            msg = bot.send_message(call.message.chat.id, text[:4096], **kw)
            save_message(call.message.chat.id, msg.message_id)


def del_msg(chat_id, *msg_ids):
    for m_id in msg_ids:
        try:
            bot.delete_message(chat_id, m_id)
        except Exception:
            pass


def is_user_pro(uid):
    if uid == ADMIN_ID or is_admin(uid):
        return True
    users = read_json(USERS_DB)
    u = users.get(str(uid), {})
    expiry = u.get("expiry")
    if not expiry or expiry == "null":
        return False
    if expiry == "LIFETIME" or expiry == 0:
        return True
    try:
        exp_date = datetime.strptime(expiry, "%Y-%m-%d %H:%M:%S")
        if datetime.now() < exp_date:
            return True
        else:
            u["expiry"] = None
            users[str(uid)] = u
            write_json(USERS_DB, users)
            return False
    except Exception:
        return False


def check_sub(user_id):
    if user_id == ADMIN_ID or is_admin(user_id):
        return True
    settings = get_settings()
    channels = settings.get("channels", [])
    if not channels:
        return True
    try:
        for ch in channels:
            member = bot.get_chat_member(ch["username"], user_id)
            if member.status in ["left", "kicked"]:
                return False
        return True
    except Exception:
        return True


def set_cancel(uid, state=True):
    cancel_states[uid] = state


def is_cancelled(uid):
    return cancel_states.get(uid, False)


def clear_cancel(uid):
    if uid in cancel_states:
        del cancel_states[uid]


def get_thumb():
    settings = get_settings()
    thumb = settings.get("file_thumb")
    if thumb and os.path.exists(thumb):
        return thumb
    return None


def btn(text, callback_data=None, url=None, style=None):
    kw = {}
    if callback_data:
        kw["callback_data"] = callback_data
    if url:
        kw["url"] = url
    return types.InlineKeyboardButton(text, **kw)


def locked_msg(chat_id):
    text = "🔒 <b>البوت مغلق حالياً للصيانة</b>\n\nتم إيقاف الخدمة مؤقتاً بأمر من الإدارة."
    markup = types.InlineKeyboardMarkup()
    markup.add(btn("👨‍💻 تواصل مع المطور", url=f"tg://user?id={ADMIN_ID}", style="primary"))
    send_msg(chat_id, deco("🔒 البوت مغلق", text), markup, effect_id=FIRE_EFFECT_ID)


def start_script(fid):
    files = read_json(FILES_DB)
    if fid not in files:
        return False
    file_info = files[fid]
    user_id = file_info.get("user_id")
    if not verify_file_access(fid, user_id):
        return False
    encrypted_content = load_encrypted_file(fid)
    if not encrypted_content:
        return False
    env_dir = os.path.join(ENV_DIR, fid)
    if not is_path_safe(ENV_DIR, env_dir):
        return False
    os.makedirs(env_dir, exist_ok=True)
    env_file_path = os.path.join(env_dir, f"{fid}.py")
    if fid in active_processes and active_processes[fid].poll() is None:
        return True
    try:
        with open(env_file_path, "w", encoding="utf-8") as f:
            f.write(encrypted_content)
    except Exception:
        return False
    log_path = os.path.join(LOGS_DIR, f"{fid}.log")
    try:
        log_file = open(log_path, "a", encoding="utf-8")
        proc = subprocess.Popen(
            [sys.executable, "-u", env_file_path],
            stdout=log_file,
            stderr=log_file,
            stdin=subprocess.PIPE,
            cwd=env_dir,
            start_new_session=True,
            env={**os.environ, "PYTHONPATH": env_dir},
        )
        active_processes[fid] = proc
        bot_scripts[fid] = {"process": proc, "file_name": file_info.get("file_name"), "owner_id": user_id}
        return True
    except Exception:
        return False


def stop_script(fid):
    if fid in active_processes:
        proc = active_processes[fid]
        try:
            os.killpg(os.getpgid(proc.pid), 9)
        except Exception:
            try:
                proc.terminate()
            except Exception:
                pass
        del active_processes[fid]
        if fid in bot_scripts:
            del bot_scripts[fid]
        return True
    return False


def write_proc(fid, cmd):
    if fid in active_processes and active_processes[fid].poll() is None:
        try:
            proc = active_processes[fid]
            if proc.stdin:
                proc.stdin.write(cmd.encode("utf-8") + b"\n")
                proc.stdin.flush()
                return True
        except Exception:
            pass
    return False


def create_zip(files_list, zip_name):
    zip_path = os.path.join(BASE_DIR, zip_name)
    if not is_path_safe(BASE_DIR, zip_path):
        raise ValueError("Unsafe zip path")
    with zipfile.ZipFile(zip_path, "w") as zipf:
        for file_path in files_list:
            if os.path.exists(file_path):
                zipf.write(file_path, os.path.basename(file_path))
    return zip_path


def scan_code_security(content):
    dangerous_patterns = [
        r"\bos\.system\s*\(",
        r"\bos\.popen\s*\(",
        r"\bshutil\.rmtree\s*\(\s*[\"']\/",
        r"\bctypes\b",
        r"open\s*\(\s*[\"'].*\/etc\/passwd",
        r"open\s*\(\s*[\"'].*\/root\/",
        r"rm\s+-rf\s+/",
        r"\bsubprocess\.Popen\s*\(\s*\[\s*[\"']rm",
        r"\beval\s*\(",
        r"\bexec\s*\(",
        r"base64\.b64decode\s*\(\s*[\"'].*[\"']\s*\)\.decode\s*\(\s*[\"']utf-8[\"']\s*\)\s*;\s*exec\s*\(",
    ]
    for pattern in dangerous_patterns:
        if re.search(pattern, content, re.IGNORECASE):
            return False, "⚠️ تم رفض الملف حظراً أمنياً لاحتوائه على أكواد خطيرة أو محاولات اختراق أو أكواد مشفرة غير مقبولة."
    return True, "الكود آمن"


def build_keyboard(menu_structure):
    markup = types.InlineKeyboardMarkup()
    for row in menu_structure:
        row_btns = []
        for btn_dict in row:
            text = btn_dict.get("text")
            callback_data = btn_dict.get("callback_data")
            url = btn_dict.get("url")
            if url:
                b = types.InlineKeyboardButton(text, url=url)
            else:
                b = types.InlineKeyboardButton(text, callback_data=callback_data)
            row_btns.append(b)
        markup.row(*row_btns)
    return markup


# ==============================================================================
# ٤. إعدادات وتكامل محرك الذكاء الاصطناعي Ptero.pro المحدث
# ==============================================================================
HOME_URL = "https://ptero.pro"
CHAT_URL = f"{HOME_URL}/wp-json/mlp/v1/chat-stream"

MODELS = {
    "1": {"id": "ling-3.0-flash", "name": "Ling 3.0 Flash"},
    "2": {"id": "deepseek-v4.1-flash:free", "name": "DeepSeek v4.1 Flash"},
    "3": {"id": "minimax-m3.1-flash:runware", "name": "MiniMax M3.1 Flash"},
    "4": {"id": "glm-5.3-flash", "name": "GLM 5.3 Flash"},
    "5": {"id": "qwen3.7-flash:minirouter", "name": "Qwen 3.7 Flash"},
}

DEFAULT_MODEL_ID = "ling-3.0-flash"
FALLBACK_MODELS = [
    "deepseek-v4.1-flash:free",
    "minimax-m3.1-flash:runware",
    "glm-5.3-flash",
    "qwen3.7-flash:minirouter",
    "ling-3.0-flash:free",
]

MAX_SOURCE_BYTES = 20 * 1024 * 1024
MAX_OUTPUT_BYTES = 20 * 1024 * 1024

_USER_AGENT = (
    "Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/120.0.0.0 Mobile Safari/537.36"
)


class RepairServiceError(RuntimeError):
    """Raised when the selected external AI service cannot process a file."""


def fetch_real_session(retries=2):
    for attempt in range(retries):
        session_http = requests.Session()
        headers = {
            "User-Agent": _USER_AGENT,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "ar-EG,ar;q=0.9,en-US;q=0.8,en;q=0.7",
            "Accept-Encoding": "gzip, deflate",
            "Connection": "keep-alive",
            "Upgrade-Insecure-Requests": "1",
        }
        try:
            response = session_http.get(HOME_URL, headers=headers, timeout=25)
            if response.status_code != 200:
                if attempt < retries - 1:
                    time.sleep(1)
                    continue
                return None

            html = response.text
            nonce = None
            patterns = [
                r"var\s+nonce\s*=\s*[\"']([a-f0-9]{8,64})[\"']",
                r"[\"']nonce[\"']\s*:\s*[\"']([a-f0-9]{8,64})[\"']",
                r"data-referral-nonce=[\"']([a-f0-9]{8,64})[\"']",
                r"x-wp-nonce[\"']?\s*[:=]\s*[\"']([a-f0-9]{8,64})[\"']",
                r"wp_nonce[\"']?\s*[:=]\s*[\"']([a-f0-9]{8,64})[\"']",
                r"mlp_nonce[\"']?\s*[:=]\s*[\"']([a-f0-9]{8,64})[\"']",
                r"data-nonce=[\"']([a-f0-9]{8,64})[\"']",
            ]

            for pattern in patterns:
                match = re.search(pattern, html, re.IGNORECASE)
                if match:
                    nonce = match.group(1)
                    break

            if not nonce and BeautifulSoup:
                soup = BeautifulSoup(html, "html.parser")
                for script in soup.find_all("script"):
                    text = script.get_text() or ""
                    if "nonce" in text:
                        match = re.search(r"[\"']([a-f0-9]{10})[\"']", text)
                        if match:
                            nonce = match.group(1)
                            break

            if not nonce:
                for script in re.findall(r"<script\b[^>]*>(.*?)</script\s*>", html, re.I | re.S):
                    if "nonce" in script.lower():
                        match = re.search(r"[\"']([a-f0-9]{10})[\"']", script, re.I)
                        if match:
                            nonce = match.group(1)
                            break

            if not nonce:
                if attempt < retries - 1:
                    time.sleep(1)
                    continue
                return None

            guest_token = None
            for cookie in session_http.cookies:
                if any(k in cookie.name.lower() for k in ["mlp", "guest", "token"]):
                    guest_token = cookie.value
                    break

            if not guest_token:
                match = re.search(r"guest[_-]?token[\"']?\s*[:=]\s*[\"']([a-f0-9]+)[\"']", html, re.IGNORECASE)
                guest_token = match.group(1) if match else uuid.uuid4().hex

            return {
                "session": session_http,
                "nonce": nonce,
                "guest_token": guest_token,
                "conversation_id": str(uuid.uuid4()),
            }
        except Exception as ex:
            logger.warning(f"fetch_real_session error (attempt {attempt + 1}): {ex}")
            if attempt < retries - 1:
                time.sleep(1)

    return None


def chat_with_model(model_id, user_message, session_data, model_display_name="AI", stream_print=False):
    conv_id = session_data["conversation_id"]
    payload = {
        "message": user_message,
        "model": model_id,
        "conversation_id": conv_id,
        "attachments": [],
        "history": [],
        "lang": "ar",
        "github_repo": "",
        "mode": "quick",
    }

    headers = {
        "User-Agent": _USER_AGENT,
        "Accept-Encoding": "gzip, deflate",
        "Content-Type": "application/json",
        "sec-ch-ua-platform": "\"Android\"",
        "sec-ch-ua": "\"Chromium\";v=\"120\", \"Google Chrome\";v=\"120\"",
        "sec-ch-ua-mobile": "?1",
        "x-wp-nonce": session_data["nonce"],
        "x-mlp-guest-token": session_data["guest_token"],
        "x-mlp-guest-username": f"user_{conv_id[:6]}",
        "origin": HOME_URL,
        "sec-fetch-site": "same-origin",
        "sec-fetch-mode": "cors",
        "sec-fetch-dest": "empty",
        "referer": f"{HOME_URL}/",
        "accept-language": "ar-EG,ar;q=0.9,en-US;q=0.8,en;q=0.7",
        "priority": "u=1, i",
    }

    try:
        response = session_data["session"].post(
            CHAT_URL, json=payload, headers=headers, stream=True, timeout=(30, 240)
        )

        if response.status_code != 200:
            return None, None

        full_reply = ""
        for line in response.iter_lines():
            if not line:
                continue
            line_str = line.decode("utf-8", errors="replace")
            if not line_str.startswith("data:"):
                continue
            data_str = line_str[5:].strip()
            if not data_str or data_str == "keepalive":
                continue
            try:
                data = json.loads(data_str)
            except json.JSONDecodeError:
                continue

            if "token" in data and isinstance(data["token"], str):
                full_reply += data["token"]
                if stream_print:
                    print(data["token"], end="", flush=True)
            elif data.get("done"):
                if data.get("conversation_id"):
                    session_data["conversation_id"] = data["conversation_id"]
                return full_reply, data

        return full_reply, None

    except requests.exceptions.RequestException as ex:
        logger.warning(f"chat_with_model request error ({model_id}): {ex}")
        return None, None


def extract_code_from_ai_response(raw_text):
    if not raw_text:
        return ""
    text = raw_text.strip()
    blocks = re.findall(r"```(?:[a-zA-Z0-9_\-\.\+]*\n)?(.*?)(?:```|$)", text, flags=re.DOTALL)
    if blocks:
        clean_blocks = [b.strip() for b in blocks if b.strip()]
        if clean_blocks:
            best_block = max(clean_blocks, key=len)
            if len(best_block) >= 15:
                return best_block
    if text.startswith("```"):
        text = re.sub(r"^```[^\n]*\n", "", text)
        text = re.sub(r"\n```$", "", text)
        return text.strip()
    return text


def repair_source(source, instructions, file_name, model_id=None):
    source_bytes_len = len(source.encode("utf-8"))
    if source_bytes_len > MAX_SOURCE_BYTES:
        raise RepairServiceError(
            f"الملف أكبر من الحد المسموح لإرساله للخدمة ({int(MAX_SOURCE_BYTES / (1024 * 1024))} ميجابايت)."
        )

    session_data = fetch_real_session()
    if not session_data:
        raise RepairServiceError("تعذّر الاتصال بخدمة الذكاء الاصطناعي (فشل تهيئة الجلسة مع الخادم).")

    extra_rules = ""
    _stem, ext = os.path.splitext(file_name)
    ext_lower = ext.lower()

    if ext_lower == ".js":
        extra_rules = (
            "\nتوجيهات لملفات JavaScript / Node.js:\n"
            "- إذا كان الكود يستخدم مكتبة node-telegram-bot-api بالصيغة الشائعة: const TelegramBot = require('node-telegram-bot-api'); new TelegramBot(...); فلا تقم بتغييرها ولا تضع دوال فحص تنهي البرنامج بـ process.exit.\n"
            "- حافظ على بناء الجمل البرمجية الصحيحة في Node.js وتأكد من إغلاق الأقواس.\n"
        )
    elif ext_lower == ".php":
        extra_rules = (
            "\nتوجيهات لملفات PHP:\n"
            "- حافظ على علامة البداية <?php واحرص على كتابة كود PHP سليم برمجياً وإغلاق الأقواس والفواصل المنقوطة.\n"
        )
    elif ext_lower == ".py":
        extra_rules = (
            "\nتوجيهات لملفات Python:\n"
            "- تأكد من صحة الصياغة النحوية (Syntax) والمسافات البادئة (Indentation) بدقة.\n"
            "- لا تغير أسماء الدوال أو المتغيرات الأساسية غير المرتبطة بالطلب.\n"
        )

    prompt = (
        "أنت مبرمج محترف متخصص في تصحيح وإصلاح وتعديل ملفات الأكواد البرمجية. "
        "مهمتك: إصلاح الأخطاء وتنفيذ طلب المستخدم بأعلى دقة وبأقل تغييرات ممكنة.\n"
        "شروط صارمة:\n"
        "1. أعد محتوى الملف كاملاً وجاهزاً للتشغيل داخل كتلة كود واحدة فقط: ``` ... ```\n"
        "2. لا تكتب أي شرح أو مقدمات أو كلام بشري قبل أو بعد الكود نهائياً.\n"
        "3. حافظ على التوكنات والمتغيرات الأساسية ومنطق البوت الأصلي.\n"
        "4. لا تضف أي أكواد ضارة أو برمجيات خبيثة.\n\n"
        f"اسم الملف: {file_name}\n"
        f"طلب المستخدم: {instructions}\n"
        f"{extra_rules}\n"
        "محتوى الملف الحالي:\n"
        f"```text\n{source}\n```"
    )

    candidate_models = []
    if model_id:
        candidate_models.append(model_id)
    if DEFAULT_MODEL_ID not in candidate_models:
        candidate_models.append(DEFAULT_MODEL_ID)
    for fm in FALLBACK_MODELS:
        if fm not in candidate_models:
            candidate_models.append(fm)

    for candidate in candidate_models:
        try:
            logger.info(f"جاري إرسال التعديل للنموذج: {candidate}")
            reply, _meta = chat_with_model(candidate, prompt, session_data)
            if not reply or not reply.strip():
                session_data = fetch_real_session() or session_data
                continue

            extracted = extract_code_from_ai_response(reply)
            if not extracted or len(extracted.strip()) < 10:
                continue

            if ext_lower == ".py":
                try:
                    ast.parse(extracted, filename=file_name)
                except SyntaxError as syn_err:
                    logger.warning(f"النموذج {candidate} أنتج كود Python به خطأ صياغة ({syn_err})؛ تجربة نموذج بديل...")
                    continue
            elif ext_lower == ".php":
                try:
                    chk = subprocess.run(["php", "-l"], input=extracted.encode("utf-8"), capture_output=True, timeout=5)
                    if chk.returncode != 0:
                        logger.warning(f"النموذج {candidate} أنتج كود PHP به خطأ صياغة؛ تجربة نموذج بديل...")
                        continue
                except Exception:
                    pass

            return extracted

        except Exception as ex:
            logger.warning(f"فشل النموذج {candidate}: {ex}")
            continue
    return None


# ==============================================================================
# ٥. لوحات المفاتيح وأحداث نظام السيرفر وبوت TeleBot
# ==============================================================================
def main_kb(uid):
    structure = [
        [{"text": " رفع ملفات بايثون ", "callback_data": "nav_upload", "style": "success"},
         {"text": "📦 رفع مشروع ZIP ", "callback_data": "nav_upload_zip", "style": "success"}],
        [{"text": "💻 حالة ونظام السيرفر", "callback_data": "admin_system_status", "style": "primary"}],
        [{"text": "📜 الشروط والتعليمات", "callback_data": "ehab_5_e", "style": "danger"}],
        [{"text": " ملفاتي ", "callback_data": "nav_files", "style": "primary"}, {"text": " المتجر ", "callback_data": "nav_store", "style": "primary"}],
        [{"text": " محفظتي ", "callback_data": "nav_wallet", "style": "primary"}, {"text": " حسابي ", "callback_data": "nav_stats", "style": "primary"}],
        [{"text": " تثبيت مكتبة ", "callback_data": "nav_lib", "style": "primary"}, {"text": " التعليمات ", "callback_data": "nav_help", "style": "primary"}],
    ]
    if is_user_pro(uid):
        structure.append([{"text": "🔧 لوحة Pro", "callback_data": "nav_pro", "style": "success"}])
    structure.append([{"text": "👨‍💻 تواصل مع المطور", "url": DEV_TELEGRAM, "style": "primary"}])
    if is_admin(uid):
        structure.append([{"text": "⚙️ لوحة الإدارة", "callback_data": "nav_admin", "style": "danger"}])
    return build_keyboard(structure)


def pro_panel_kb(uid):
    kb = types.InlineKeyboardMarkup(row_width=2)
    kb.add(btn("📥 تحميل جميع الملفات", callback_data="pro_download_all", style="success"))
    kb.add(btn("🔍 فحص تلقائي", callback_data="pro_auto_fix", style="primary"))
    kb.add(btn("▶️ تشغيل تجريبي", callback_data="pro_test_run", style="primary"))
    kb.add(btn("🛒 بيع في المتجر", callback_data="pro_sell", style="primary"))
    kb.add(btn("⎙● رجـــــوع ●⎙", callback_data="nav_main", style="primary"))
    return kb


def cancel_kb(data="cancel"):
    kb = types.InlineKeyboardMarkup()
    kb.add(btn("❌ إلغاء", callback_data=data, style="danger"))
    return kb


def back_kb(data="nav_main"):
    kb = types.InlineKeyboardMarkup()
    kb.add(btn("⎙● رجـــــوع ●⎙", callback_data=data, style="primary"))
    return kb


def handle_admin_system(call):
    uid = call.from_user.id
    if not is_admin(uid):
        return

    try:
        per = psutil.cpu_percent(interval=0.5, percpu=True)
        cpu_total = sum(per) / max(1, len(per))
        cores_line = " ".join(f"{p:.0f}%" for p in per) if len(per) <= 16 else f"{len(per)} نواة"
    except Exception:
        cpu_total = 0.0
        cores_line = "غير متاح (صلاحيات أندرويد)"

    logical = psutil.cpu_count(logical=True) or 1
    physical = psutil.cpu_count(logical=False) or logical

    try:
        freq = psutil.cpu_freq()
        freq_s = f"{freq.current:.0f} MHz" if freq else "—"
    except Exception:
        freq_s = "—"

    try:
        load = " / ".join(f"{x:.2f}" for x in os.getloadavg())
    except Exception:
        load = "—"

    mem = psutil.virtual_memory()
    sw = psutil.swap_memory()

    try:
        disk = psutil.disk_usage(os.path.abspath("."))
    except Exception:
        disk = psutil.disk_usage("/")

    users_size = _dir_size(UPLOAD_DIR)
    proc = psutil.Process()
    ip = _get_ipinfo()
    place = " - ".join(x for x in (ip.get("country"), ip.get("regionName"), ip.get("city")) if x) or "غير متاح"
    uname = platform.uname()

    try:
        boot = datetime.now() - datetime.fromtimestamp(proc.create_time())
    except Exception:
        boot = "مستمر"

    text = (
        f"<blockquote>💻 <b>معلومات النظام والسيرفر (Pydroid Mode)</b></blockquote>\n\n"
        f"<blockquote>"
        f"🌍 <b>الموقع:</b> {_esc(place)}\n"
        f"🌐 <b>IP:</b> <code>{_esc(str(ip.get('query', 'غير متاح')))}</code>\n"
        f"🏢 <b>المزود:</b> {_esc(str(ip.get('isp', '—')))}"
        f"</blockquote>\n\n"
        f"<blockquote>"
        f"🧠 <b>CPU:</b> {cpu_total:.0f}% | {freq_s}\n"
        f"⚙️ <b>Cores:</b> {physical} فعلي / {logical} منطقي\n"
        f"📊 <b>الأنوية:</b> {cores_line}\n"
        f"📈 <b>Load:</b> {load}"
        f"</blockquote>\n\n"
        f"<blockquote>"
        f"💾 <b>RAM:</b> {_gb(mem.used)}/{_gb(mem.total)} GB ({mem.percent}%)\n"
        f"✅ <b>متاح:</b> {_gb(mem.available)} GB\n"
        f"🔁 <b>Swap:</b> {_gb(sw.used)}/{_gb(sw.total)} GB"
        f"</blockquote>\n\n"
        f"<blockquote>"
        f"💽 <b>التخزين:</b> {_gb(disk.used)}/{_gb(disk.total)} GB ({disk.percent}%)\n"
        f"🆓 <b>فاضي:</b> {_gb(disk.free)} GB\n"
        f"📁 <b>ملفات المستخدمين:</b> {_mb(users_size)} MB"
        f"</blockquote>\n\n"
        f"<blockquote>"
        f"🤖 <b>البوت:</b> {_mb(proc.memory_info().rss)} MB | {proc.num_threads()} thread\n"
        f"▶️ <b>سكربتات شغالة:</b> {len(bot_scripts)}\n"
        f"⏱ <b>تشغيل البوت:</b> {str(boot).split('.')[0]}\n"
        f"🖥 <b>OS:</b> {uname.system} {uname.release} | Python {platform.python_version()}"
        f"</blockquote>"
    )

    kb = types.InlineKeyboardMarkup(row_width=2)
    kb.add(
        btn("🧹 تنظيف الرامات", callback_data="sys_clean_ram", style="success"),
        btn("🗑 تنظيف المؤقتات", callback_data="sys_clean_tmp", style="success"),
    )
    kb.add(
        btn("📜 تنظيف اللوجات", callback_data="sys_clean_logs", style="primary"),
        btn("📈 استهلاك الرامات (Top)", callback_data="sys_top", style="primary"),
    )
    kb.add(btn("⎙● رجـــــوع ●⎙", callback_data="nav_admin", style="danger"))

    try:
        edit_msg(call, text, kb)
    except Exception:
        send_msg(call.message.chat.id, text, kb)


def handle_sys_clean_ram(call):
    uid = call.from_user.id
    if not is_admin(uid):
        return bot.answer_callback_query(call.id, "❌ صلاحيات مشرف فقط!", show_alert=True)
    for _ in range(3):
        gc.collect()
    try:
        import ctypes
        ctypes.CDLL("libc.so.6").malloc_trim(0)
    except Exception:
        pass
    try:
        if hasattr(os, "geteuid") and os.geteuid() == 0:
            os.sync()
            with open("/proc/sys/vm/drop_caches", "w") as f:
                f.write("1")
    except Exception:
        pass
    bot.answer_callback_query(call.id, "✅ تم تنظيف الرامات بنجاح!", show_alert=True)
    handle_admin_system(call)


def handle_sys_clean_tmp(call):
    uid = call.from_user.id
    if not is_admin(uid):
        return bot.answer_callback_query(call.id, "❌ صلاحيات مشرف فقط!", show_alert=True)
    freed, count = 0, 0
    cutoff = time.time() - 3600
    tmpdir = tempfile.gettempdir()
    try:
        for name in os.listdir(tmpdir):
            p = os.path.join(tmpdir, name)
            try:
                st = os.lstat(p)
                if hasattr(os, "getuid") and st.st_uid != os.getuid():
                    continue
                if st.st_mtime > cutoff:
                    continue
                size = _dir_size(p) if os.path.isdir(p) and not os.path.islink(p) else st.st_size
                if os.path.isdir(p) and not os.path.islink(p):
                    shutil.rmtree(p, ignore_errors=True)
                else:
                    os.remove(p)
                freed += size
                count += 1
            except OSError:
                pass
    except OSError:
        pass
    try:
        for root, dirs, _files in os.walk(UPLOAD_DIR):
            for d in list(dirs):
                if d in ("__pycache__", ".tmp"):
                    p = os.path.join(root, d)
                    if os.path.islink(p):
                        continue
                    try:
                        if d == ".tmp" and os.path.getmtime(p) > cutoff:
                            continue
                        freed += _dir_size(p)
                        shutil.rmtree(p, ignore_errors=True)
                        count += 1
                    except OSError:
                        pass
                    dirs.remove(d)
    except Exception:
        pass
    bot.answer_callback_query(call.id, f"🗑 تم تحرير {_mb(freed)} MB بنجاح!", show_alert=True)
    handle_admin_system(call)


def handle_sys_clean_logs(call):
    uid = call.from_user.id
    if not is_admin(uid):
        return bot.answer_callback_query(call.id, "❌ صلاحيات مشرف فقط!", show_alert=True)
    running = set()
    for info in list(bot_scripts.values()):
        running.add((str(info.get("owner_id")), os.path.splitext(info.get("file_name", ""))[0]))
    freed, count = 0, 0
    limit = MAX_LOG_SIZE_KB * 1024
    try:
        for uid_dir in os.listdir(UPLOAD_DIR):
            folder = os.path.join(UPLOAD_DIR, uid_dir)
            if not os.path.isdir(folder) or os.path.islink(folder):
                continue
            for name in os.listdir(folder):
                if not name.endswith(".log"):
                    continue
                p = os.path.join(folder, name)
                try:
                    if os.path.islink(p) or (uid_dir, name[:-4]) in running:
                        continue
                    size = os.path.getsize(p)
                    if size > limit:
                        os.remove(p)
                        freed += size
                        count += 1
                except OSError:
                    pass
    except OSError:
        pass
    bot.answer_callback_query(call.id, f"📜 تم تنظيف {count} ملف لوج بنجاح!", show_alert=True)
    handle_admin_system(call)


def handle_sys_top(call):
    uid = call.from_user.id
    if not is_admin(uid):
        return bot.answer_callback_query(call.id, "❌ صلاحيات مشرف فقط!", show_alert=True)
    by_pid = {}
    for info in list(bot_scripts.values()):
        p = info.get("process")
        if p is not None and hasattr(p, "pid"):
            by_pid[p.pid] = info
    rows = []
    try:
        me = psutil.Process()
        procs = [me] + me.children(recursive=True)
        for pr in procs:
            try:
                rss = pr.memory_info().rss
                cpu = pr.cpu_percent(interval=None)
                rows.append((rss, pr.pid, cpu))
            except psutil.Error:
                pass
    except Exception:
        pass
    rows.sort(reverse=True)
    lines = []
    for rss, pid, _cpu in rows[:8]:
        if pid == os.getpid():
            who = "🤖 البوت نفسه"
        elif pid in by_pid:
            inf = by_pid[pid]
            who = f"📄 {_esc(str(inf.get('file_name')))} (<code>{inf.get('owner_id')}</code>)"
        else:
            who = f"⚙️ PID {pid}"
        lines.append(f"{who} — <b>{_mb(rss)} MB</b>")
    body = "\n".join(lines) if lines else "مفيش بيانات"
    text = f"📈 <b>أكبر استهلاك للرامات:</b>\n\n{body}"
    kb = types.InlineKeyboardMarkup()
    kb.add(btn("⎙● رجـــــوع ●⎙", callback_data="admin_system_status", style="danger"))
    edit_msg(call, text, kb)


@bot.message_handler(commands=["start", "admin"])
def start_cmd(msg):
    try:
        uid = msg.from_user.id
        if is_bot_locked() and not is_admin(uid):
            try:
                bot.delete_message(msg.chat.id, msg.message_id)
            except Exception:
                pass
            locked_msg(msg.chat.id)
            return
        users = read_json(USERS_DB)
        clear_cancel(uid)
        first_name_raw = msg.from_user.first_name or "مستخدم"
        if str(uid) not in users:
            users[str(uid)] = {
                "username": msg.from_user.username,
                "first_name": first_name_raw,
                "last_name": msg.from_user.last_name,
                "points": 0,
                "balance": 0.0,
                "join_date": str(datetime.now().date()),
                "is_banned": 0,
                "expiry": None,
                "notifications": True,
            }
            write_json(USERS_DB, users)
            try:
                first = esc(f"{first_name_raw} {msg.from_user.last_name or ''}")
                user = msg.from_user.username or "لا يوجد"
                day2, _ = get_date_strings()
                cap = (
                    f"➖ <b>تم دخول شخص جديد الى البوت 👤•</b>\n"
                    f"➖ <b>إسم الشخص:</b> <a href=\"tg://user?id={uid}\">{first}</a> 📝•\n"
                    f"➖ <b>الحالة :</b> تم التحقق وليس روبوت ✅️ •\n"
                    f"➖ <b>ايديه :</b> <code>{uid}</code> 🆔️•\n"
                    f"➖ <b>معرف حسابه :</b> @{user} 📮•\n\n"
                    f"        🔰\n"
                    f"➖➖➖➖➖➖\n"
                    f"📆 - {day2}"
                )
                structure = [
                    [{"text": "👤 كشف العضو", "url": f"tg://openmessage?user_id={uid}", "style": "primary"}]
                ]
                for _adm in get_admins():
                    try:
                        photos = bot.get_user_profile_photos(uid)
                        if photos.total_count > 0:
                            bot.send_photo(CHANNEL_EHAB_ME, photos.photos[0][-1].file_id, caption=cap, parse_mode="HTML", reply_markup=build_keyboard(structure))
                        else:
                            bot.send_message(CHANNEL_EHAB_ME, cap, parse_mode="HTML", reply_markup=build_keyboard(structure))
                    except Exception:
                        pass
            except Exception:
                pass
        users = read_json(USERS_DB)
        if users.get(str(uid), {}).get("is_banned", 0) == 1:
            return bot.send_message(msg.chat.id, deco("🚫 محظور", "عذراً، تم حظرك نهائياً من استخدام البوت.", first_name_raw))
        if not check_sub(uid):
            return sub_msg(msg.chat.id)
        try:
            bot.delete_message(msg.chat.id, msg.message_id)
        except Exception:
            pass
        u = users.get(str(uid), {})

        text = (
            f"<b>▱▱▱▱▱▱▱▱▱▱▱▱▱▱▱▱▱▱▱</b>\n"
            f"<b>   🌟 أهلاً بك عزيزي  ⦗ {first_name_raw} ⦘ 🌟   </b>\n"
            f"<b>▱▱▱▱▱▱▱▱▱▱▱▱▱▱▱▱▱▱▱</b>\n\n"
            f"<b>💌 ︙ ايدي المستخدم : <code>{msg.chat.id}</code></b>\n"
            f"<b>💰 ︙ رصيدك المالي : <tg-spoiler>{u.get('balance', 0.0)}</tg-spoiler> ₽</b>\n"
            f"<b>🚀 ︙ سرعة الاستضافة : فائقة </b>\n\n"
            f"<b>💻 ︙ تحكم الآن بكافة الأقسام عبر الأزرار أدناه 👇</b>"
        )
        send_msg(msg.chat.id, deco("🏠 القائمة الرئيسية", text, first_name_raw), main_kb(uid), effect_id=FIRE_EFFECT_ID)
    except Exception as e:
        print(f"Start Error: {e}")


def sub_msg(chat_id):
    settings = get_settings()
    channels = settings.get("channels", [])
    if not channels:
        return
    kb = types.InlineKeyboardMarkup(row_width=1)
    for ch in channels:
        ch_username = ch["username"].replace("@", "")
        kb.add(btn(f"📢 {ch['name']}", url=f"[https://t.me/](https://t.me/){ch_username}", style="primary"))
    kb.add(btn("✅ تحقق من الاشتراك", callback_data="check_sub", style="success"))
    text = "🔔 <b>اشتراك إجباري مطلوب</b>\n\nيجب عليك الاشتراك في القنوات التالية لاستخدام البوت:"
    send_msg(chat_id, deco("🔔 اشتراك مطلوب", text), kb, effect_id=FIRE_EFFECT_ID)


@bot.callback_query_handler(func=lambda call: True)
def callback_router(call):
    try:
        uid = call.from_user.id
        cid = call.message.chat.id
        data = call.data
        users = read_json(USERS_DB)
        first_name_raw = call.from_user.first_name or "مستخدم"

        if is_bot_locked() and not is_admin(uid):
            bot.answer_callback_query(call.id, "🔒 البوت مغلق حالياً للصيانة!", show_alert=True)
            locked_msg(cid)
            return
        if str(uid) in users and users[str(uid)].get("is_banned", 0) == 1:
            return bot.answer_callback_query(call.id, "🚫 أنت محظور نهائياً من استخدام البوت!", show_alert=True)

        if data in ("cancel", "user_home", "nav_main"):
            set_cancel(uid, True)
            bot.answer_callback_query(call.id, "✅ تم العودة للقائمة.")
            u = users.get(str(uid), {})
            text = (
                f"<b>▱▱▱▱▱▱▱▱▱▱▱▱▱▱▱▱▱▱▱</b>\n"
                f"<b>   🌟 أهلاً بك عزيزي  ⦗ {first_name_raw} ⦘ 🌟   </b>\n"
                f"<b>▱▱▱▱▱▱▱▱▱▱▱▱▱▱▱▱▱▱▱</b>\n\n"
                f"<b>💌 ︙ ايدي المستخدم : <code>{cid}</code></b>\n"
                f"<b>💰 ︙ رصيدك المالي : <tg-spoiler>{u.get('balance', 0.0)}</tg-spoiler> ₽</b>\n"
                f"<b>🚀 ︙ سرعة الاستضافة : فائقة </b>\n\n"
                f"<b>💻 ︙ تحكم الآن بكافة الأقسام عبر الأزرار أدناه 👇</b>"
            )
            try:
                bot.delete_message(cid, call.message.message_id)
            except Exception:
                pass
            send_msg(cid, deco("🏠 القائمة الرئيسية", text, first_name_raw), main_kb(uid), effect_id=FIRE_EFFECT_ID)
            return

        if data == "admin_system_status":
            handle_admin_system(call)
            return
        elif data == "sys_clean_ram":
            handle_sys_clean_ram(call)
            return
        elif data == "sys_clean_tmp":
            handle_sys_clean_tmp(call)
            return
        elif data == "sys_clean_logs":
            handle_sys_clean_logs(call)
            return
        elif data == "sys_top":
            handle_sys_top(call)
            return

        if data == "cancel_admin":
            set_cancel(uid, True)
            if uid in admin_steps:
                del admin_steps[uid]
            bot.answer_callback_query(call.id, "✅ تم إلغاء العملية.")
            admin_panel(call)
            return

        if data == "check_sub":
            if check_sub(uid):
                bot.answer_callback_query(call.id, "✅ تم التحقق بنجاح!")
                u = users.get(str(uid), {})
                text = (
                    f"<b>▱▱▱▱▱▱▱▱▱▱▱▱▱▱▱▱▱▱▱</b>\n"
                    f"<b>   🌟 أهلاً بك عزيزي  ⦗ {first_name_raw} ⦘ 🌟   </b>\n"
                    f"<b>▱▱▱▱▱▱▱▱▱▱▱▱▱▱▱▱▱▱▱</b>\n\n"
                    f"<b>💌 ︙ ايدي المستخدم : <code>{cid}</code></b>\n"
                    f"<b>💰 ︙ رصيدك المالي : <tg-spoiler>{u.get('balance', 0.0)}</tg-spoiler> ₽</b>\n"
                    f"<b>🚀 ︙ سرعة الاستضافة : فائقة </b>\n\n"
                    f"<b>💻 ︙ تحكم الآن بكافة الأقسام عبر الأزرار أدناه 👇</b>"
                )
                try:
                    bot.delete_message(cid, call.message.message_id)
                except Exception:
                    pass
                send_msg(cid, deco("🏠 القائمة الرئيسية", text, first_name_raw), main_kb(uid), effect_id=FIRE_EFFECT_ID)
            else:
                bot.answer_callback_query(call.id, "❌ لم تقم بالاشتراك في كافة القنوات!", show_alert=True)
            return

        if not check_sub(uid) and not is_admin(uid):
            bot.answer_callback_query(call.id, "❌ يجب الاشتراك في القنوات أولاً!", show_alert=True)
            return
        clear_cancel(uid)

        if data == "ehab_5_e":
            terms_text = (
                f"📜 <b>الشروط والتعليمات الكاملة لاستخدام الاستضافة والبوت</b>\n\n"
                f"<b>🤖 ما هو البوت وما يقدمه؟</b>\n"
                f"يعتبر هذا البوت نظاماً سحابياً متكاملاً وفائق السرعة (Ultra Speed) مخصصاً لرفع وتشغيل سكريبتات بايثون وبوتات تيليجرام 24/7 دون توقف.\n\n"
                f"<b>📋 تفاصيل البوت والمميزات الرئيسية:</b>\n"
                f"1. <b>استضافة بايثون الفائقة:</b> تشغيل آمن ومحمي بأحدث تقنيات التشفير AES وحماية كاملة ضد الأكواد الخبيثة ومحاولات الاختراق.\n"
                f"2. <b>شحن الرصيد والنقاط:</b> تتيح لك المحفظة متابعة رصيدك واستخدامه في رفع الملفات.\n"
                f"3. <b>لوحة تحكم الإدارة والمشرفين:</b> مراقبة الأداء، الإذاعة العامة، إدارة المشتركين، وتفعيل الصيانة.\n\n"
                f"<b>⚠️ شروط وقوانين الاستخدام:</b>\n"
                f"• يمنع منعاً باتاً رفع أي أكواد ضارة أو برامج اختراق أو سبام، وفي حال المخالفة يتم حظر الحساب والآيدي نهائياً بشكل تلقائي.\n"
                f"• الالتزام بالأدب العام وعدم إساءة استخدام خدمات الاستضافة.\n"
                f"• للإبلاغ عن مشاكل أو التواصل المستمر، يرجى مراسلة المطور عبر أزرار التواصل المتاحة في القائمة الرئيسية."
            )
            kb = types.InlineKeyboardMarkup()
            kb.add(btn("🔙 رجوع للقائمة الرئيسية", callback_data="nav_main", style="primary"))
            try:
                bot.delete_message(cid, call.message.message_id)
            except Exception:
                pass
            send_msg(cid, deco("📜 الشروط والتعليمات", terms_text, first_name_raw), kb, effect_id=FIRE_EFFECT_ID)
            return

        if data == "nav_pro":
            if not is_user_pro(uid):
                bot.answer_callback_query(call.id, "❌ هذه اللوحة مخصصة لمشتركي VIP فقط!", show_alert=True)
                return
            text = "🔧 <b>لوحة VIP المميزة والحصرية</b>\n\nاستمتع بكافة المزايا والأدوات المتقدمة لتطوير وإدارة ملفاتك."
            try:
                bot.delete_message(cid, call.message.message_id)
            except Exception:
                pass
            send_msg(cid, deco("🔧 لوحة Pro", text, first_name_raw), pro_panel_kb(uid), effect_id=FIRE_EFFECT_ID)
        elif data == "pro_download_all":
            if not is_user_pro(uid):
                bot.answer_callback_query(call.id, "❌ لمشتركي VIP فقط!", show_alert=True)
                return
            files = read_json(FILES_DB)
            u_files = {fid: f for fid, f in files.items() if f.get("user_id") == uid and f.get("status") == "active"}
            if not u_files:
                bot.answer_callback_query(call.id, "📂 لا توجد ملفات نشطة لديك!", show_alert=True)
                return
            decrypted_files = []
            for fid in u_files.keys():
                if verify_file_access(fid, uid):
                    content = load_encrypted_file(fid)
                    if content:
                        temp_path = os.path.join(BASE_DIR, f"temp_{fid}_{gen_id(4)}.py")
                        with open(temp_path, "w", encoding="utf-8") as f:
                            f.write(content)
                        decrypted_files.append(temp_path)
            if decrypted_files:
                zip_name = f"files_{uid}_{gen_id(4)}.zip"
                zip_path = create_zip(decrypted_files, zip_name)
                try:
                    with open(zip_path, "rb") as f:
                        bot.send_document(cid, f, caption="📦 جميع ملفاتك البرمجية في أرشيف مضغوط واحد:")
                    for temp_file in decrypted_files:
                        try:
                            os.remove(temp_file)
                        except Exception:
                            pass
                    os.remove(zip_path)
                except Exception:
                    bot.answer_callback_query(call.id, "❌ حدث خطأ أثناء إنشاء الأرشيف!", show_alert=True)
            else:
                bot.answer_callback_query(call.id, "❌ لم يتم العثور على ملفات للتحميل!", show_alert=True)
        elif data == "nav_wallet":
            u = users.get(str(uid), {})
            vip = is_user_pro(uid)
            exp = "لا يوجد"
            if vip:
                e = u.get("expiry")
                if e == "LIFETIME" or e == 0:
                    exp = "دائم ♾"
                elif e:
                    exp = e
            vip_label = "VIP 👑" if vip else "مجاني 🆓"
            text = f"💰 رصيدك الحالي: <code>{u.get('points', 0)}</code> نقطة | 💵 الرصيد المالي: <code>{u.get('balance', 0.0)}</code> ₽\n💎 الرتبة: {vip_label}\n⏰ صلاحية VIP: {exp}\n\n💡 ملاحظة: يتم رفع الملفات وتشغيلها حصرياً عبر رصيد النقاط."
            kb = types.InlineKeyboardMarkup(row_width=1)
            kb.add(btn("⎙● رجـــــوع ●⎙", callback_data="nav_main", style="primary"))
            try:
                bot.delete_message(cid, call.message.message_id)
            except Exception:
                pass
            send_msg(cid, deco("💼 محفظتي", text, first_name_raw), kb, effect_id=FIRE_EFFECT_ID)
        elif data == "nav_help":
            text = "📖 <b>دليل الاستخدام الشامل</b>\n\n🚀 خطوات الاستضافة:\n• اضغط على زر رفع ملف جديد.\n• أرسل ملف بايثون بصيغة .py.\n• حدد عدد ساعات التشغيل."
            kb = types.InlineKeyboardMarkup()
            kb.add(btn("👨‍💻 تواصل مع المطور", url=f"tg://user?id={ADMIN_ID}", style="primary"))
            kb.add(btn("⎙● رجـــــوع ●⎙", callback_data="nav_main", style="primary"))
            try:
                bot.delete_message(cid, call.message.message_id)
            except Exception:
                pass
            send_msg(cid, deco("📖 التعليمات", text, first_name_raw), kb, effect_id=FIRE_EFFECT_ID)
        elif data == "nav_upload":
            u = users.get(str(uid), {})
            st_settings = get_settings()
            required_price = st_settings.get("python_upload_price", 1.0)
            if u.get("points", 0) < required_price and not is_user_pro(uid):
                return bot.answer_callback_query(call.id, f"❌ رصيدك لا يكفي لرفع ملف! السعر المطلوب: {required_price} نقطة.", show_alert=True)
            try:
                bot.delete_message(cid, call.message.message_id)
            except Exception:
                pass
            m = send_msg(cid, deco("📤 إرسال الملف", f"📥 أرسل ملف السكريبت .py (سعر الرفع الحالي: {required_price} نقطة):\n\n<i>⚠️ تنبيه: سيتم تعليق الملف ومراجعته من قبل الإدارة أولاً.</i>", first_name_raw), cancel_kb(), effect_id=FIRE_EFFECT_ID)
            save_message(cid, m.message_id)
            bot.register_next_step_handler(m, upload_step, m.message_id)
        elif data == "nav_upload_zip":
            u = users.get(str(uid), {})
            st_settings = get_settings()
            required_price = st_settings.get("python_upload_price", 1.0)
            if u.get("points", 0) < required_price and not is_user_pro(uid):
                return bot.answer_callback_query(call.id, f"❌ رصيدك لا يكفي لرفع ملف ZIP! السعر المطلوب: {required_price} نقطة.", show_alert=True)
            try:
                bot.delete_message(cid, call.message.message_id)
            except Exception:
                pass
            m = send_msg(cid, deco("📦 إرسال ملف ZIP", f"📥 أرسل أرشيف المضغوط .zip الذي يحتوي على ملفات البايثون والمشروع (سعر الرفع: {required_price} نقطة):\n\n<i>⚠️ سيتم معالجة الملف واستخراج الملفات البرمجية بشكل آمن وفحص القواعد والمسارات.</i>", first_name_raw), cancel_kb(), effect_id=FIRE_EFFECT_ID)
            save_message(cid, m.message_id)
            bot.register_next_step_handler(m, upload_zip_step, m.message_id)
        elif data == "nav_files":
            files = read_json(FILES_DB)
            u_files = {fid: f for fid, f in files.items() if f.get("user_id") == uid}
            if not u_files:
                return bot.answer_callback_query(call.id, "📂 لا توجد ملفات مرفوعة لديك حالياً!", show_alert=True)
            kb = types.InlineKeyboardMarkup(row_width=1)
            for fid, f in u_files.items():
                status = f.get("status", "active")
                if status == "pending":
                    icon = "⏳ قيد المراجعة"
                else:
                    running = fid in active_processes and active_processes[fid].poll() is None
                    icon = "🟢 يعمل" if running else "🔴 متوقف"
                ft = "💎" if f.get("type") == "pro" else "🆓"
                fname_short = f.get("file_name", "?")[:25]
                kb.add(btn(f"{icon} | {ft} {fname_short}", callback_data=f"manage_{fid}", style="primary"))
            if is_user_pro(uid):
                kb.add(btn("📦 تحميل كافة الملفات (ZIP)", callback_data="pro_download_all", style="success"))

            kb.add(btn("🔙 القائمة الرئيسية 🔙", callback_data="nav_main", style="danger"))

            active_count = sum(1 for fid, f in u_files.items() if f.get("status") == "active" and fid in active_processes and active_processes[fid].poll() is None)
            text = f"📊 إجمالي ملفاتك: {len(u_files)}\n🟢 يعمل الآن: {active_count}"
            try:
                bot.delete_message(cid, call.message.message_id)
            except Exception:
                pass
            send_msg(cid, deco("📁 ملفاتي", text, first_name_raw), kb, effect_id=FIRE_EFFECT_ID)
        elif data.startswith("manage_"):
            file_panel(call, data.split("_")[1])
        elif data.startswith("toggle_"):
            toggle_file(call, data.split("_")[1])
        elif data.startswith("delc_"):
            fid = data.split("_")[1]
            kb = types.InlineKeyboardMarkup(row_width=2)
            kb.add(
                btn("✅ نعم، احذف", callback_data=f"del_{fid}", style="danger"),
                btn("❌ تراجع", callback_data=f"manage_{fid}", style="primary"),
            )
            try:
                bot.delete_message(cid, call.message.message_id)
            except Exception:
                pass
            send_msg(cid, deco("🗑️ تأكيد الحذف", "هل أنت متأكد من رغبتك في حذف هذا الملف نهائياً؟", first_name_raw), kb, effect_id=FIRE_EFFECT_ID)
        elif data.startswith("del_"):
            delete_file(call, data.split("_")[1])
        elif data.startswith("dl_"):
            download_file(call, data.split("_")[1])
        elif data.startswith("term_"):
            terminal(call, data.split("_")[1])
        elif data.startswith("rterm_"):
            terminal(call, data.split("_")[1])
        elif data.startswith("inp_"):
            fid = data.split("_")[1]
            try:
                bot.delete_message(cid, call.message.message_id)
            except Exception:
                pass
            m = send_msg(cid, deco("⌨️ إدخال أمر", "اكتب الأمر أو النص المراد إرساله للسكريبت:", first_name_raw), cancel_kb(), effect_id=FIRE_EFFECT_ID)
            save_message(cid, m.message_id)
            bot.register_next_step_handler(m, input_step, fid, m.message_id)
        elif data.startswith("chtoken_"):
            fid = data.split("_")[1]
            try:
                bot.delete_message(cid, call.message.message_id)
            except Exception:
                pass
            m = send_msg(cid, deco("🔑 تغيير التوكن", "أرسل التوكن الجديد للروبوت:", first_name_raw), cancel_kb(), effect_id=FIRE_EFFECT_ID)
            save_message(cid, m.message_id)
            bot.register_next_step_handler(m, token_step, fid, m.message_id)
        elif data.startswith("tokinfo_"):
            token_info(call, data.split("_")[1])
        elif data.startswith("fai_"):
            cb_ai_repair_request(call)
        elif data.startswith("faic_"):
            cb_ai_repair_confirm(call)
        elif data.startswith("faix_"):
            bot.answer_callback_query(call.id, "❌ تم إلغاء طلب الإصلاح بواسطة الذكاء الاصطناعي.")
            try:
                bot.delete_message(cid, call.message.message_id)
            except Exception:
                pass
        elif data == "nav_store":
            store_view(call)
        elif data.startswith("buy_"):
            buy_confirm(call, data.split("_")[1])
        elif data.startswith("ebuy_"):
            buy_exec(call, data.split("_")[1])
        elif data == "nav_lib":
            try:
                bot.delete_message(cid, call.message.message_id)
            except Exception:
                pass
            m = send_msg(cid, deco("🛠 تثبيت مكتبة", "أرسل اسم المكتبة البرمجية المراد تثبيتها عبر pip:", first_name_raw), cancel_kb(), effect_id=FIRE_EFFECT_ID)
            save_message(cid, m.message_id)
            bot.register_next_step_handler(m, lib_step, m.message_id)
        elif data == "nav_stats":
            files = read_json(FILES_DB)
            u = users.get(str(uid), {})
            u_files = [f for f in files.values() if f.get("user_id") == uid]
            running = sum(1 for fid, f in files.items() if f.get("user_id") == uid and fid in active_processes and active_processes[fid].poll() is None)
            vip = is_user_pro(uid)
            exp = "لا يوجد"
            if vip:
                e = u.get("expiry")
                if e == "LIFETIME" or e == 0:
                    exp = "دائم ♾"
                elif e:
                    try:
                        ed = datetime.strptime(e, "%Y-%m-%d %H:%M:%S")
                        rem = ed - datetime.now()
                        exp = f"{rem.days} يوم متبقي"
                    except Exception:
                        exp = e
            vip_label = "VIP 👑" if vip else "مجاني 🆓"
            text = f"🆔 الآيدي: <code>{uid}</code>\n🔗 المعرف: @{u.get('username', 'لا يوجد')}\n📅 الانضمام: {u.get('join_date', 'اليوم')}\n\n💎 الرتبة: {vip_label}\n⏰ صلاحية VIP: {exp}\n💰 رصيد النقاط: <code>{u.get('points', 0)}</code>\n\n📁 ملفاتك: {len(u_files)}\n🟢 قيد التشغيل: {running}"
            kb = types.InlineKeyboardMarkup()
            kb.add(btn("💼 محفظتي", callback_data="nav_wallet", style="primary"))
            kb.add(btn("⎙● رجـــــوع ●⎙", callback_data="nav_main", style="primary"))
            try:
                bot.delete_message(cid, call.message.message_id)
            except Exception:
                pass
            send_msg(cid, deco("📊 حسابي", text, first_name_raw), kb, effect_id=FIRE_EFFECT_ID)

        elif data == "nav_admin" and is_admin(uid):
            admin_panel(call)
        elif data == "adm_users" and is_admin(uid):
            users_panel(call)
        elif data.startswith("userpage_") and is_admin(uid):
            page = int(data.split("_")[1])
            users_panel(call, page)
        elif data.startswith("uctrl_") and is_admin(uid):
            user_panel(call, data.split("_")[1])
        elif data.startswith("ban_") and is_admin(uid):
            ban_toggle(call, data.split("_")[1])
        elif data.startswith("pro_") and is_admin(uid):
            tuid = data.split("_")[1]
            if is_user_pro(int(tuid)):
                pro_remove(call, tuid)
            else:
                try:
                    bot.delete_message(cid, call.message.message_id)
                except Exception:
                    pass
                m = send_msg(cid, deco("💎 منح VIP", "أرسل عدد الأيام (اكتب 0 للحصول على VIP دائم):", first_name_raw), cancel_kb("cancel_admin"), effect_id=FIRE_EFFECT_ID)
                save_message(cid, m.message_id)
                bot.register_next_step_handler(m, pro_grant_step, tuid, m.message_id)
        elif data == "adm_related_files" and is_admin(uid):
            pending_list(call)
        elif data.startswith("vpend_") and is_admin(uid):
            admin_view_pending_file(call, data.split("_")[1])
        elif data.startswith("vdl_") and is_admin(uid):
            admin_download_pending_file(call, data.split("_")[1])
        elif data.startswith("vapprove_") and is_admin(uid):
            admin_approve_file(call, data.split("_")[1])
        elif data.startswith("vdel_") and is_admin(uid):
            admin_delete_pending_file(call, data.split("_")[1])
        elif data == "adm_bot_manager" and is_admin(uid):
            bot_manager_panel(call)
        elif data.startswith("botact_") and is_admin(uid):
            ex = data.split("_")
            handle_bot_action(call, ex[1], ex[2])
        elif data == "adm_stats" and is_admin(uid):
            admin_stats_view(call)
        elif data == "adm_add_balance" and is_admin(uid):
            try:
                bot.delete_message(cid, call.message.message_id)
            except Exception:
                pass
            m = send_msg(cid, deco("➕ إضافة رصيد", "أرسل آيدي المستخدم المراد إضافة الرصيد إليه:", first_name_raw), cancel_kb("cancel_admin"), effect_id=FIRE_EFFECT_ID)
            save_message(cid, m.message_id)
            bot.register_next_step_handler(m, admin_add_balance_id_step, m.message_id)
        elif data == "adm_deduct_balance" and is_admin(uid):
            try:
                bot.delete_message(cid, call.message.message_id)
            except Exception:
                pass
            m = send_msg(cid, deco("➖ خصم رصيد", "أرسل آيدي المستخدم المراد خصم الرصيد منه:", first_name_raw), cancel_kb("cancel_admin"), effect_id=FIRE_EFFECT_ID)
            save_message(cid, m.message_id)
            bot.register_next_step_handler(m, admin_deduct_balance_id_step, m.message_id)
        elif data == "adm_ban_id" and is_admin(uid):
            try:
                bot.delete_message(cid, call.message.message_id)
            except Exception:
                pass
            m = send_msg(cid, deco("🚫 حظر آيدي", "أرسل الآيدي (ID) المراد حظره نهائياً من استخدام البوت:", first_name_raw), cancel_kb("cancel_admin"), effect_id=FIRE_EFFECT_ID)
            save_message(cid, m.message_id)
            bot.register_next_step_handler(m, admin_ban_id_step, m.message_id)
        elif data == "adm_unban_id" and is_admin(uid):
            try:
                bot.delete_message(cid, call.message.message_id)
            except Exception:
                pass
            m = send_msg(cid, deco("✅ إلغاء حظر آيدي", "أرسل الآيدي (ID) المراد فك الحظر عنه وإعادة تفعيل حسابه:", first_name_raw), cancel_kb("cancel_admin"), effect_id=FIRE_EFFECT_ID)
            save_message(cid, m.message_id)
            bot.register_next_step_handler(m, admin_unban_id_step, m.message_id)
        elif data == "adm_restart_all" and is_admin(uid):
            restarted_count = 0
            files = read_json(FILES_DB)
            for fid in list(files.keys()):
                stop_script(fid)
                if start_script(fid):
                    restarted_count += 1
            bot.answer_callback_query(call.id, f"🔄 تمت إعادة تشغيل جميع البوتات والملفات النشطة بنجاح ({restarted_count} بوت)!", show_alert=True)
            admin_panel(call)
        elif data == "adm_stop_all" and is_admin(uid):
            stopped_count = len(active_processes)
            for fid in list(active_processes.keys()):
                stop_script(fid)
            bot.answer_callback_query(call.id, f"⏹ تم إيقاف جميع البوتات والعمليات النشطة بنجاح ({stopped_count} بوت)!", show_alert=True)
            admin_panel(call)
        elif data == "adm_sub_count" and is_admin(uid):
            bot.answer_callback_query(call.id, f"👥 عدد المشتركين الإجمالي في البوت: {len(users)} مشترك", show_alert=True)
        elif data == "adm_broadcast" and is_admin(uid):
            try:
                bot.delete_message(cid, call.message.message_id)
            except Exception:
                pass
            m = send_msg(cid, deco("📢 إذاعة عامة", "أرسل الرسالة (نصوص، صور، ملفات) لإذاعتها لكافة المستخدمين:", first_name_raw), cancel_kb("cancel_admin"), effect_id=FIRE_EFFECT_ID)
            save_message(cid, m.message_id)
            bot.register_next_step_handler(m, broadcast_step, m.message_id)
        elif data == "adm_channels_broadcast" and is_admin(uid):
            try:
                bot.delete_message(cid, call.message.message_id)
            except Exception:
                pass
            m = send_msg(cid, deco("📢 إذاعة للقنوات", "أرسل الرسالة للإذاعة في قنوات الاشتراك الإجباري:", first_name_raw), cancel_kb("cancel_admin"), effect_id=FIRE_EFFECT_ID)
            save_message(cid, m.message_id)
            bot.register_next_step_handler(m, channels_broadcast_step, m.message_id)

        elif data == "admin_maintenance_on" and is_admin(uid):
            settings = get_settings()
            settings["bot_locked"] = True
            save_settings(settings)
            bot.answer_callback_query(call.id, "🔒 تم تفعيل وضع الصيانة بنجاح وإغلاق البوت أمام المستخدمين!", show_alert=True)
            admin_panel(call)
        elif data == "admin_maintenance_off" and is_admin(uid):
            settings = get_settings()
            settings["bot_locked"] = False
            save_settings(settings)
            bot.answer_callback_query(call.id, "🔓 تم إلغاء وضع الصيانة بنجاح وعمل البوت بكامل طاقته!", show_alert=True)
            admin_panel(call)

        elif data == "adm_clean" and is_admin(uid):
            cleaned_count = 0
            try:
                for f in os.listdir(LOGS_DIR):
                    p = os.path.join(LOGS_DIR, f)
                    if os.path.isfile(p):
                        os.remove(p)
                        cleaned_count += 1
                for d in os.listdir(ENV_DIR):
                    p = os.path.join(ENV_DIR, d)
                    if os.path.isdir(p) and d not in active_processes:
                        shutil.rmtree(p, ignore_errors=True)
                        cleaned_count += 1
                for f in os.listdir(DOWNLOAD_DIR):
                    p = os.path.join(DOWNLOAD_DIR, f)
                    if os.path.isfile(p):
                        os.remove(p)
                        cleaned_count += 1
                for f in os.listdir(STORE_DIR):
                    p = os.path.join(STORE_DIR, f)
                    if os.path.isfile(p):
                        os.remove(p)
                        cleaned_count += 1
            except Exception as e:
                print(f"Clean error: {e}")
            bot.answer_callback_query(call.id, f"🧹 تم تنظيف كافة مخلفات الاستضافة والمؤقتات بنجاح! تم حذف ({cleaned_count}) عنصراً مع الاحتفاظ بأيدي وأرصدة المستخدمين والبوتات النشطة لتسريع الاستضافة.", show_alert=True)
            admin_panel(call)

        elif data == "adm_speedup" and is_admin(uid):
            bot.answer_callback_query(call.id, "🚀 تم تسريع البوت وتحسين استجابة المعالجات بأقصى سرعة فائقة بنجاح!", show_alert=True)
            admin_panel(call)

        elif data == "adm_admins" and is_admin(uid):
            admins_panel(call)
        elif data == "add_admin" and is_main_admin(uid):
            try:
                bot.delete_message(cid, call.message.message_id)
            except Exception:
                pass
            m = send_msg(cid, deco("➕ إضافة أدمن", "أرسل آيدي المستخدم الجديد:", first_name_raw), cancel_kb("cancel_admin"), effect_id=FIRE_EFFECT_ID)
            save_message(cid, m.message_id)
            bot.register_next_step_handler(m, add_admin_step, m.message_id)
        elif data.startswith("rmadmin_") and is_admin(uid):
            aid = int(data.split("_")[1])
            if aid == ADMIN_ID:
                bot.answer_callback_query(call.id, "❌ لا يمكن إزالة المالك الرئيسي!", show_alert=True)
            elif remove_admin(aid):
                bot.answer_callback_query(call.id, "✅ تم إزالة الأدمن بنجاح.")
                admins_panel(call)
        elif data == "adm_channels" and is_admin(uid):
            channels_panel(call)
        elif data == "add_channel" and is_admin(uid):
            try:
                bot.delete_message(cid, call.message.message_id)
            except Exception:
                pass
            m = send_msg(cid, deco("📢 إضافة قناة", "أرسل معرف القناة (مثال: @ChannelName):", first_name_raw), cancel_kb("cancel_admin"), effect_id=FIRE_EFFECT_ID)
            save_message(cid, m.message_id)
            bot.register_next_step_handler(m, add_channel_step, m.message_id)
        elif data.startswith("delch_") and is_admin(uid):
            del_channel(call, int(data.split("_")[1]))
    except Exception as e:
        print(f"Callback Error: {e}")


def pro_grant_step(msg, tuid, prompt_id):
    uid = msg.from_user.id
    if is_cancelled(uid):
        clear_cancel(uid)
        return
    del_msg(msg.chat.id, prompt_id, msg.message_id)
    first_name_raw = msg.from_user.first_name or "مستخدم"
    if not msg.text or not msg.text.strip().isdigit():
        send_msg(msg.chat.id, deco("❌ خطأ", "أدخل عدد أيام صحيح!", first_name_raw), back_kb("nav_admin"), effect_id=FIRE_EFFECT_ID)
        return
    days = int(msg.text.strip())
    users = read_json(USERS_DB)
    k = str(tuid)
    if k in users:
        if days == 0:
            users[k]["expiry"] = "LIFETIME"
        else:
            exp_date = datetime.now() + timedelta(days=days)
            users[k]["expiry"] = exp_date.strftime("%Y-%m-%d %H:%M:%S")
        write_json(USERS_DB, users)
        dur_txt = "دائم ♾" if days == 0 else f"{days} يوم"
        try:
            bot.send_message(int(tuid), deco("💎 تم تفعيل VIP", f"مبروك! تم تفعيل اشتراك VIP لحسابك لمدة {dur_txt}."))
        except Exception:
            pass
        send_msg(msg.chat.id, deco("✅ تم بنجاح", f"تم منح رتبة VIP للمستخدم <code>{tuid}</code> بنجاح.", first_name_raw), back_kb("nav_admin"), effect_id=FIRE_EFFECT_ID)
    else:
        send_msg(msg.chat.id, deco("❌ خطأ", "المستخدم غير موجود في قاعدة البيانات!", first_name_raw), back_kb("nav_admin"), effect_id=FIRE_EFFECT_ID)


def cb_ai_repair_request(call):
    parsed = _get_ai_repair_file(call)
    if not parsed:
        bot.answer_callback_query(call.id, "❌ الملف غير موجود أو انتهت صلاحيته!", show_alert=True)
        return
    owner_id, file_name, _ = parsed
    token = file_token(file_name)
    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.row(
        btn("أوافق وأكمل", callback_data=f"faic_{owner_id}_{token}", style="success"),
        btn("إلغاء", callback_data=f"faix_{owner_id}_{token}", style="danger"),
    )
    bot.send_message(
        call.message.chat.id,
        f"<blockquote><b>إصلاح وتعديل الملف بـ AI</b></blockquote>\n\n"
        f"<blockquote>لو كملت، هيتبعت محتوى <code>{escape(file_name)}</code> إلى خدمة "
        f"<code>ptero.pro</code> الخارجية لتحليله. الخدمة مش تابعة لـ Replit، وممكن تتغير أو تتوقف. "
        f"الملف الأصلي مش هيتغيّر ومش هيشتغل تلقائيًا؛ هتستلم نسخة تراجعها بنفسك.</blockquote>\n\n"
        f"<blockquote>اضغط موافقة لو حابب تكمل.</blockquote>",
        parse_mode="HTML",
        reply_markup=markup,
    )
    bot.answer_callback_query(call.id)


def cb_ai_repair_confirm(call):
    parsed = _get_ai_repair_file(call)
    if not parsed:
        bot.answer_callback_query(call.id, "❌ حدث خطأ، لم يتم العثور على الملف!", show_alert=True)
        return
    _owner_id, file_name, fid = parsed
    content = load_encrypted_file(fid)
    if not content:
        bot.answer_callback_query(call.id, "❌ تعذر قراءة محتوى الملف!", show_alert=True)
        return

    bot.answer_callback_query(call.id, "⏳ جاري إرسال الكود للذكاء الاصطناعي للمعالجة...")
    msg_wait = send_msg(call.message.chat.id, deco("🤖 جاري الإصلاح", "⏳ يتم الآن تحليل الكود وإصلاح المشاكل عبر محرك الذكاء الاصطناعي المتطور...", call.from_user.first_name or "مستخدم"), effect_id=FIRE_EFFECT_ID)

    try:
        fixed_code = repair_source(content, "قم بفحص وإصلاح هذا السكريبت وتصحيح أي أخطاء برمجية أو مسارات خاطئة فيه", file_name)
        if not fixed_code:
            bot.edit_message_text("❌ لم يتم استلام رد صالح من خدمة الذكاء الاصطناعي.", call.message.chat.id, msg_wait.message_id, parse_mode="HTML")
            return

        fixed_filename = f"fixed_{file_name}"
        fixed_path = os.path.join(DOWNLOAD_DIR, fixed_filename)
        with open(fixed_path, "w", encoding="utf-8") as f:
            f.write(fixed_code)

        with open(fixed_path, "rb") as f:
            bot.send_document(call.message.chat.id, f, caption=f"🛠 النسخة المصححة والمعدلة لملف: {file_name}")
        try:
            os.remove(fixed_path)
            bot.delete_message(call.message.chat.id, msg_wait.message_id)
        except Exception:
            pass
    except Exception as e:
        print(f"AI Repair Error: {e}")
        bot.answer_callback_query(call.id, "❌ حدث خطأ أثناء عملية المعالجة بالذكاء الاصطناعي!", show_alert=True)


def upload_step(msg, prompt_id):
    uid = msg.from_user.id
    if is_cancelled(uid):
        clear_cancel(uid)
        return
    del_msg(msg.chat.id, prompt_id, msg.message_id)
    first_name_raw = msg.from_user.first_name or "مستخدم"
    if not msg.document or not msg.document.file_name.endswith(".py"):
        send_msg(msg.chat.id, deco("❌ خطأ", "يجب إرسال ملف سكريبت بلغة بايثون بصيغة .py", first_name_raw), back_kb("nav_upload"), effect_id=FIRE_EFFECT_ID)
        return

    try:
        finfo = bot.get_file(msg.document.file_id)
        file_content = bot.download_file(finfo.file_path).decode("utf-8")

        if not scan_with_virustotal(file_content, msg.document.file_name):
            send_msg(msg.chat.id, deco("🚫 خطأ أمني", "تم رفض الملف بواسطة فحص VirusTotal الأمني.", first_name_raw), effect_id=FIRE_EFFECT_ID)
            return

        is_safe, sec_msg = scan_code_security(file_content)
        if not is_safe:
            users = read_json(USERS_DB)
            if str(uid) in users:
                users[str(uid)]["is_banned"] = 1
                write_json(USERS_DB, users)
            send_msg(msg.chat.id, deco("🚫 حظر تلقائي للمخالفة", f"{sec_msg}\n\nتم حظر حسابك والآيدي الخاص بك تلقائياً.", first_name_raw), effect_id=FIRE_EFFECT_ID)
            for adm in get_admins():
                try:
                    bot.send_message(adm, deco("🚫 ملف مخالف", f"⚠️ تم حظر المستخدم <code>{uid}</code> تلقائياً لمحاولته رفع ملف مخالف أو يحتوي على أكواد مشفرة غير مقبولة.", first_name_raw))
                except Exception:
                    pass
            return
    except Exception as e:
        print(f"Security check error: {e}")

    users = read_json(USERS_DB)
    pts = users.get(str(uid), {}).get("points", 0)
    st_settings = get_settings()
    required_price = st_settings.get("python_upload_price", 1.0)

    if pts < required_price and not is_user_pro(uid):
        send_msg(msg.chat.id, deco("❌ رصيد غير كافي", f"رصيدك الحالي لا يكفي لرفع ملف! السعر المطلوب: {required_price} نقطة.", first_name_raw), back_kb("nav_wallet"), effect_id=FIRE_EFFECT_ID)
        return

    m = send_msg(
        msg.chat.id,
        deco("⏰ تحديد الساعات", f"الملف: <b>{escape(msg.document.file_name)}</b>\n\n💰 رصيدك المتاح: <code>{pts}</code> نقطة\n💵 سعر الرفع: {required_price} نقطة\n\nأرسل عدد الساعات المطلوبة للتشغيل:", first_name_raw),
        cancel_kb(),
        effect_id=FIRE_EFFECT_ID,
    )
    save_message(msg.chat.id, m.message_id)
    bot.register_next_step_handler(m, hours_step, msg.document, m.message_id)


def upload_zip_step(msg, prompt_id):
    uid = msg.from_user.id
    if is_cancelled(uid):
        clear_cancel(uid)
        return
    del_msg(msg.chat.id, prompt_id, msg.message_id)
    first_name_raw = msg.from_user.first_name or "مستخدم"
    if not msg.document or not msg.document.file_name.endswith(".zip"):
        send_msg(msg.chat.id, deco("❌ خطأ", "يجب إرسال ملف مضغوط بصيغة .zip", first_name_raw), back_kb("nav_upload_zip"), effect_id=FIRE_EFFECT_ID)
        return

    try:
        finfo = bot.get_file(msg.document.file_id)
        downloaded_file = bot.download_file(finfo.file_path)
        zip_temp_path = os.path.join(DOWNLOAD_DIR, f"upload_{uid}_{gen_id(6)}.zip")
        with open(zip_temp_path, "wb") as f:
            f.write(downloaded_file)

        extract_dir = os.path.join(DOWNLOAD_DIR, f"extracted_{uid}_{gen_id(6)}")
        os.makedirs(extract_dir, exist_ok=True)

        with zipfile.ZipFile(zip_temp_path, "r") as zip_ref:
            for member in zip_ref.infolist():
                dest_member = os.path.abspath(os.path.join(extract_dir, member.filename))
                if not is_path_safe(extract_dir, dest_member):
                    raise ValueError("Zip Slip path detected")
            zip_ref.extractall(extract_dir)

        py_files = []
        for root, _dirs, files in os.walk(extract_dir):
            for file in files:
                if file.endswith(".py"):
                    py_files.append(os.path.join(root, file))

        if not py_files:
            try:
                shutil.rmtree(extract_dir, ignore_errors=True)
                os.remove(zip_temp_path)
            except Exception:
                pass
            send_msg(msg.chat.id, deco("❌ خطأ", "ملف الـ ZIP لا يحتوي على أي ملفات بايثون (.py) صالحة!", first_name_raw), back_kb("nav_upload_zip"), effect_id=FIRE_EFFECT_ID)
            return

        for py_f in py_files:
            with open(py_f, "r", encoding="utf-8", errors="ignore") as pf:
                code_content = pf.read()
            is_safe, sec_msg = scan_code_security(code_content)
            if not is_safe:
                try:
                    shutil.rmtree(extract_dir, ignore_errors=True)
                    os.remove(zip_temp_path)
                except Exception:
                    pass
                users = read_json(USERS_DB)
                if str(uid) in users:
                    users[str(uid)]["is_banned"] = 1
                    write_json(USERS_DB, users)
                send_msg(msg.chat.id, deco("🚫 حظر تلقائي للمخالفة", f"{sec_msg}\n\nتم حظر حسابك والآيدي الخاص بك تلقائياً لتضمن ملف الـ ZIP أكواداً محظورة أو ضارة.", first_name_raw), effect_id=FIRE_EFFECT_ID)
                return

        main_py = py_files[0]
        with open(main_py, "r", encoding="utf-8", errors="ignore") as pf:
            main_content = pf.read()

        try:
            shutil.rmtree(extract_dir, ignore_errors=True)
            os.remove(zip_temp_path)
        except Exception:
            pass

        users = read_json(USERS_DB)
        pts = users.get(str(uid), {}).get("points", 0)
        st_settings = get_settings()
        required_price = st_settings.get("python_upload_price", 1.0)

        if pts < required_price and not is_user_pro(uid):
            send_msg(msg.chat.id, deco("❌ رصيد غير كافي", f"رصيدك الحالي لا يكفي لرفع ملف ZIP! السعر المطلوب: {required_price} نقطة.", first_name_raw), back_kb("nav_wallet"), effect_id=FIRE_EFFECT_ID)
            return

        m = send_msg(
            msg.chat.id,
            deco("⏰ تحديد الساعات لملف ZIP", f"الملف المضغوط: <b>{escape(msg.document.file_name)}</b>\n\n💰 رصيدك المتاح: <code>{pts}</code> نقطة\n💵 سعر الرفع: {required_price} نقطة\n\nأرسل عدد الساعات المطلوبة للتشغيل:", first_name_raw),
            cancel_kb(),
            effect_id=FIRE_EFFECT_ID,
        )
        save_message(msg.chat.id, m.message_id)
        bot.register_next_step_handler(m, hours_zip_step, msg.document.file_name, main_content, m.message_id)

    except Exception as e:
        print(f"ZIP Upload error: {e}")
        send_msg(msg.chat.id, deco("❌ خطأ", "حدث خطأ أثناء معالجة ملف الـ ZIP وفحص قواعد البيانات والمسارات.", first_name_raw), back_kb("nav_main"), effect_id=FIRE_EFFECT_ID)


def hours_zip_step(msg, zip_filename, main_content, prompt_id):
    uid = msg.from_user.id
    if is_cancelled(uid):
        clear_cancel(uid)
        return
    del_msg(msg.chat.id, prompt_id, msg.message_id)
    first_name_raw = msg.from_user.first_name or "مستخدم"
    if not msg.text or not msg.text.strip().isdigit():
        send_msg(msg.chat.id, deco("❌ خطأ", "أرسل رقماً صحيحاً للساعات!", first_name_raw), back_kb("nav_upload_zip"), effect_id=FIRE_EFFECT_ID)
        return
    hours = int(msg.text.strip())
    users = read_json(USERS_DB)
    pts = users.get(str(uid), {}).get("points", 0)
    st_settings = get_settings()
    required_price = st_settings.get("python_upload_price", 1.0)

    if hours < 1:
        send_msg(msg.chat.id, deco("❌ خطأ", "يجب اختيار ساعة واحدة على الأقل!", first_name_raw), back_kb("nav_upload_zip"), effect_id=FIRE_EFFECT_ID)
        return
    total_cost = required_price * hours
    if total_cost > pts and not is_user_pro(uid):
        send_msg(msg.chat.id, deco("❌ رصيد غير كافي", f"تحتاج إلى {total_cost} نقطة، ورصيدك الحالي {pts} نقطة.", first_name_raw), back_kb("nav_wallet"), effect_id=FIRE_EFFECT_ID)
        return

    fid = gen_id()
    if not save_encrypted_file(fid, main_content, uid):
        send_msg(uid, deco("❌ خطأ", "فشل في حفظ وتشفير ملف المشروع بأمان!"), effect_id=FIRE_EFFECT_ID)
        return

    files = read_json(FILES_DB)
    files[fid] = {
        "user_id": uid,
        "file_name": zip_filename,
        "type": "free" if not is_user_pro(uid) else "pro",
        "status": "pending",
        "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "hours": hours,
    }
    write_json(FILES_DB, files)

    for adm in get_admins():
        try:
            admin_kb = build_keyboard([
                [{"text": "📥 تحميل الملف", "callback_data": f"vdl_{fid}", "style": "primary"},
                 {"text": "✅ موافقة ✅", "callback_data": f"vapprove_{fid}", "style": "success"}],
                [{"text": "❌ رفض ❌", "callback_data": f"vdel_{fid}", "style": "danger"}],
            ])
            bot.send_message(
                adm,
                f"📦 <b>طلب رفع ملف ZIP جديد معلق للمراجعة:</b>\n\n📄 الأرشيف: <code>{escape(zip_filename)}</code>\n👤 الآيدي: <code>{uid}</code>\n⏰ الساعات: {hours}",
                parse_mode="HTML",
                reply_markup=admin_kb,
            )
        except Exception as e:
            print(f"Admin pending ZIP notify error: {e}")

    text = f"⏳ <b>تم رفع أرشيف الـ ZIP بنجاح وهو قيد المراجعة والتعليق بانتظار موافقة الإدارة.</b>\n\n📄 <code>{escape(zip_filename)}</code>\n⏰ الساعات المطلوبة: {hours}"
    send_msg(uid, deco("⏳ قيد المراجعة", text), back_kb(), effect_id=FIRE_EFFECT_ID)


def hours_step(msg, doc, prompt_id):
    uid = msg.from_user.id
    if is_cancelled(uid):
        clear_cancel(uid)
        return
    del_msg(msg.chat.id, prompt_id, msg.message_id)
    first_name_raw = msg.from_user.first_name or "مستخدم"
    if not msg.text or not msg.text.strip().isdigit():
        send_msg(msg.chat.id, deco("❌ خطأ", "أرسل رقماً صحيحاً للساعات!", first_name_raw), back_kb("nav_upload"), effect_id=FIRE_EFFECT_ID)
        return
    hours = int(msg.text.strip())
    users = read_json(USERS_DB)
    pts = users.get(str(uid), {}).get("points", 0)
    st_settings = get_settings()
    required_price = st_settings.get("python_upload_price", 1.0)

    if hours < 1:
        send_msg(msg.chat.id, deco("❌ خطأ", "يجب اختيار ساعة واحدة على الأقل!", first_name_raw), back_kb("nav_upload"), effect_id=FIRE_EFFECT_ID)
        return
    total_cost = required_price * hours
    if total_cost > pts and not is_user_pro(uid):
        send_msg(msg.chat.id, deco("❌ رصيد غير كافي", f"تحتاج إلى {total_cost} نقطة، ورصيدك الحالي {pts} نقطة.", first_name_raw), back_kb("nav_wallet"), effect_id=FIRE_EFFECT_ID)
        return
    complete_upload(doc, uid, hours, total_cost)


def complete_upload(doc, user_id, hours, total_cost):
    fid = gen_id()
    finfo = bot.get_file(doc.file_id)
    file_content = bot.download_file(finfo.file_path).decode("utf-8")

    if not save_encrypted_file(fid, file_content, user_id):
        send_msg(user_id, deco("❌ خطأ", "فشل في حفظ وتشفير الملف بأمان!"), effect_id=FIRE_EFFECT_ID)
        return

    files = read_json(FILES_DB)
    files[fid] = {
        "user_id": user_id,
        "file_name": doc.file_name,
        "type": "free" if not is_user_pro(user_id) else "pro",
        "status": "pending",
        "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "hours": hours,
    }
    write_json(FILES_DB, files)

    for adm in get_admins():
        try:
            admin_kb = build_keyboard([
                [{"text": "📥 تحميل الملف", "callback_data": f"vdl_{fid}", "style": "primary"},
                 {"text": "✅ موافقة ✅", "callback_data": f"vapprove_{fid}", "style": "success"}],
                [{"text": "❌ رفض ❌", "callback_data": f"vdel_{fid}", "style": "danger"}],
            ])
            bot.send_message(
                adm,
                f"📤 <b>طلب رفع ملف جديد معلق للمراجعة:</b>\n\n📄 الملف: <code>{escape(doc.file_name)}</code>\n👤 الآيدي: <code>{user_id}</code>\n⏰ الساعات: {hours}",
                parse_mode="HTML",
                reply_markup=admin_kb,
            )
        except Exception as e:
            print(f"Admin pending notify error: {e}")

    text = f"⏳ <b>تم رفع ملفك بنجاح وهو قيد المراجعة والتعليق بانتظار موافقة الإدارة.</b>\n\n📄 <code>{escape(doc.file_name)}</code>\n⏰ الساعات المطلوبة: {hours}"
    send_msg(user_id, deco("⏳ قيد المراجعة", text), back_kb(), effect_id=FIRE_EFFECT_ID)


def pending_list(call):
    files = read_json(FILES_DB)
    pending = {fid: f for fid, f in files.items() if f.get("status") == "pending"}
    if not pending:
        return bot.answer_callback_query(call.id, "✅ لا توجد ملفات معلقة للفحص!", show_alert=True)
    kb = types.InlineKeyboardMarkup(row_width=1)
    for fid, f in pending.items():
        fname_short = f.get("file_name", "?")[:25]
        kb.add(btn(f"📄 {fname_short}", callback_data=f"vpend_{fid}", style="primary"))
    kb.add(btn("⎙● رجـــــوع ●⎙", callback_data="nav_admin", style="primary"))
    try:
        bot.delete_message(call.message.chat.id, call.message.message_id)
    except Exception:
        pass
    send_msg(call.message.chat.id, deco("⏳ الملفات المعلقة", f"عدد الملفات المعلقة: {len(pending)}", call.from_user.first_name or "مستخدم"), kb, effect_id=FIRE_EFFECT_ID)


def admin_view_pending_file(call, fid):
    files = read_json(FILES_DB)
    if fid not in files:
        return bot.answer_callback_query(call.id, "❌ الملف غير موجود!", show_alert=True)
    f = files[fid]
    content = load_encrypted_file(fid)
    preview = escape(content[:800]) if content else "تعذر قراءة المحتوى"
    text = f"⏳ <b>معاينة الملف المعلق:</b>\n\n📄 الاسم: {f.get('file_name')}\n👤 صاحب الآيدي: <code>{f.get('user_id')}</code>\n⏰ الساعات: {f.get('hours')}\n\n<pre><code>{preview}</code></pre>"
    kb = types.InlineKeyboardMarkup(row_width=2)
    kb.add(
        btn("📥 تحميل الملف", callback_data=f"vdl_{fid}", style="primary"),
        btn("✅ موافقة ✅", callback_data=f"vapprove_{fid}", style="success"),
    )
    kb.add(
        btn("❌ رفض ❌", callback_data=f"vdel_{fid}", style="danger"),
        btn("⎙● رجـــــوع ●⎙", callback_data="adm_related_files", style="primary"),
    )
    try:
        bot.delete_message(call.message.chat.id, call.message.message_id)
    except Exception:
        pass
    send_msg(call.message.chat.id, deco("⏳ مراجعة الملف المعلق", text, call.from_user.first_name or "مستخدم"), kb, effect_id=FIRE_EFFECT_ID)


def admin_download_pending_file(call, fid):
    files = read_json(FILES_DB)
    if fid not in files:
        return bot.answer_callback_query(call.id, "❌ الملف غير موجود!", show_alert=True)
    content = load_encrypted_file(fid)
    if not content:
        return bot.answer_callback_query(call.id, "❌ تعذر تحميل الملف!", show_alert=True)
    try:
        temp_path = os.path.join(BASE_DIR, f"temp_pend_{fid}.py")
        with open(temp_path, "w", encoding="utf-8") as f:
            f.write(content)
        with open(temp_path, "rb") as f:
            bot.send_document(call.message.chat.id, f, caption=f"📄 {files[fid]['file_name']} (معلق)")
        os.remove(temp_path)
        bot.answer_callback_query(call.id, "✅ تم إرسال الملف بنجاح.")
    except Exception:
        bot.answer_callback_query(call.id, "❌ حدث خطأ أثناء إرسال الملف!", show_alert=True)


def admin_approve_file(call, fid):
    files = read_json(FILES_DB)
    if fid not in files:
        return bot.answer_callback_query(call.id, "❌ الملف غير موجود!", show_alert=True)
    f = files[fid]
    f["status"] = "active"
    write_json(FILES_DB, files)

    user_id = f["user_id"]
    hours = f.get("hours", 1)
    st_settings = get_settings()
    required_price = st_settings.get("python_upload_price", 1.0)
    total_cost = required_price * hours

    if not is_user_pro(user_id) and total_cost > 0:
        users = read_json(USERS_DB)
        if str(user_id) in users:
            users[str(user_id)]["points"] = max(0, users[str(user_id)].get("points", 0) - total_cost)
            write_json(USERS_DB, users)

    start_script(fid)

    try:
        bot.send_message(user_id, deco("✅ تم قبول الملف وتشغيله", f"تمت الموافقة على ملفك <b>{escape(f['file_name'])}</b> وتشغيله بنجاح بواسطة الإدارة!"))
    except Exception:
        pass

    bot.answer_callback_query(call.id, "✅ تمت الموافقة على الملف وتشغيله بنجاح!")
    pending_list(call)


def admin_delete_pending_file(call, fid):
    files = read_json(FILES_DB)
    if fid not in files:
        return bot.answer_callback_query(call.id, "❌ الملف غير موجود!", show_alert=True)
    f = files[fid]
    user_id = f["user_id"]

    try:
        os.remove(os.path.join(ENCRYPTED_DIR, f"{fid}.enc"))
    except Exception:
        pass
    del files[fid]
    write_json(FILES_DB, files)

    try:
        bot.send_message(user_id, deco("❌ رفض الملف", f"تم رفض وحذف ملفك <b>{escape(f['file_name'])}</b> من قبل الإدارة."))
    except Exception:
        pass

    bot.answer_callback_query(call.id, "❌ تم إلغاء وحذف الملف بنجاح.")
    pending_list(call)


def file_panel(call, fid):
    uid = call.from_user.id
    if not verify_file_access(fid, uid):
        bot.answer_callback_query(call.id, "❌ لا تملك صلاحية الوصول لهذا الملف!", show_alert=True)
        return
    files = read_json(FILES_DB)
    if fid not in files:
        return bot.answer_callback_query(call.id, "❌ الملف غير موجود!")
    f = files[fid]
    content = load_encrypted_file(fid)
    preview = escape(content[:1000]) if content else "تعذر القراءة"
    status = f.get("status", "active")
    is_running = fid in active_processes and active_processes[fid].poll() is None
    if status == "pending":
        running_text = "⏳ قيد المراجعة والتعليق لدى الأدمن"
    else:
        running_text = "يعمل ✅" if is_running else "متوقف ❌"

    text = f"📄 اسم الملف: {f.get('file_name')}\n🟢 الحالة: {running_text}\n📅 تاريخ الرفع: {f.get('created_at')}\n\n🔍 المعاينة:\n<pre><code>{preview}</code></pre>"
    kb = types.InlineKeyboardMarkup(row_width=2)
    if status == "active":
        kb.add(
            btn("⏸ إيقاف" if is_running else "▶️ تشغيل", callback_data=f"toggle_{fid}", style="danger" if is_running else "success"),
            btn("📟 التيرمنال", callback_data=f"term_{fid}", style="primary"),
        )
        kb.add(
            btn("🔑 تغيير التوكن", callback_data=f"chtoken_{fid}", style="primary"),
            btn("ℹ️ معلومات التوكن", callback_data=f"tokinfo_{fid}", style="primary"),
        )
    kb.add(
        btn("📥 تحميل الملف", callback_data=f"dl_{fid}", style="primary"),
        btn("🛠️ إصلاح وتعديل بـ AI", callback_data=f"fai_{f.get('user_id')}_{file_token(f.get('file_name', ''))}", style="success"),
    )
    kb.add(
        btn("🗑️ حذف 🗑️", callback_data=f"delc_{fid}", style="danger"),
        btn("🔙 الرجوع", callback_data="nav_files", style="danger"),
    )
    try:
        bot.delete_message(call.message.chat.id, call.message.message_id)
    except Exception:
        pass
    send_msg(call.message.chat.id, deco("📁 إدارة الملف", text, call.from_user.first_name or "مستخدم"), kb, effect_id=FIRE_EFFECT_ID)


def toggle_file(call, fid):
    uid = call.from_user.id
    if not verify_file_access(fid, uid):
        bot.answer_callback_query(call.id, "❌ لا تملك صلاحية!", show_alert=True)
        return
    running = fid in active_processes and active_processes[fid].poll() is None
    if running:
        stop_script(fid)
        bot.answer_callback_query(call.id, "✅ تم إيقاف الملف.")
    else:
        if start_script(fid):
            bot.answer_callback_query(call.id, "🚀 تم تشغيل الملف بنجاح.")
        else:
            bot.answer_callback_query(call.id, "❌ فشل في تشغيل الملف!")
    file_panel(call, fid)


def delete_file(call, fid):
    uid = call.from_user.id
    if not verify_file_access(fid, uid):
        bot.answer_callback_query(call.id, "❌ لا تملك صلاحية!", show_alert=True)
        return
    stop_script(fid)
    files = read_json(FILES_DB)
    if fid in files:
        try:
            os.remove(os.path.join(ENCRYPTED_DIR, f"{fid}.enc"))
        except Exception:
            pass
        try:
            os.remove(os.path.join(LOGS_DIR, f"{fid}.log"))
        except Exception:
            pass
        try:
            shutil.rmtree(os.path.join(ENV_DIR, fid), ignore_errors=True)
        except Exception:
            pass
        del files[fid]
        write_json(FILES_DB, files)
        bot.answer_callback_query(call.id, "🗑️ تم حذف الملف بنجاح.")

    u_files = {k: v for k, v in files.items() if v.get("user_id") == uid}
    if not u_files:
        kb = types.InlineKeyboardMarkup()
        kb.add(
            btn("📤 رفع ملف", callback_data="nav_upload", style="success"),
            btn("🏠 الرئيسية", callback_data="nav_main", style="primary"),
        )
        try:
            bot.delete_message(call.message.chat.id, call.message.message_id)
        except Exception:
            pass
        send_msg(call.message.chat.id, deco("📁 ملفاتي", "لا توجد ملفات لديك حالياً.", call.from_user.first_name or "مستخدم"), kb, effect_id=FIRE_EFFECT_ID)
    else:
        kb = types.InlineKeyboardMarkup(row_width=1)
        for k, v in u_files.items():
            fname_short = v.get("file_name", "?")[:25]
            kb.add(btn(f"📄 {fname_short}", callback_data=f"manage_{k}", style="primary"))
        kb.add(btn("🔙 القائمة الرئيسية 🔙", callback_data="nav_main", style="danger"))
        try:
            bot.delete_message(call.message.chat.id, call.message.message_id)
        except Exception:
            pass
        send_msg(call.message.chat.id, deco("📁 ملفاتي", f"📊 إجمالي الملفات المتبقية: {len(u_files)}", call.from_user.first_name or "مستخدم"), kb, effect_id=FIRE_EFFECT_ID)


def download_file(call, fid):
    uid = call.from_user.id
    if not verify_file_access(fid, uid):
        bot.answer_callback_query(call.id, "❌ لا تملك صلاحية!", show_alert=True)
        return
    files = read_json(FILES_DB)
    if fid not in files:
        return bot.answer_callback_query(call.id, "❌ الملف غير موجود!")
    content = load_encrypted_file(fid)
    if not content:
        bot.answer_callback_query(call.id, "❌ تعذر تحميل الملف!", show_alert=True)
        return
    try:
        temp_path = os.path.join(BASE_DIR, f"temp_{fid}_{gen_id(4)}.py")
        with open(temp_path, "w", encoding="utf-8") as f:
            f.write(content)
        thumb = get_thumb()
        with open(temp_path, "rb") as f:
            if thumb:
                with open(thumb, "rb") as t:
                    bot.send_document(call.message.chat.id, f, thumb=t, caption=f"📄 {files[fid]['file_name']}", parse_mode="HTML")
            else:
                bot.send_document(call.message.chat.id, f, caption=f"📄 {files[fid]['file_name']}", parse_mode="HTML")
        os.remove(temp_path)
        bot.answer_callback_query(call.id, "✅ تم إرسال الملف بنجاح.")
    except Exception:
        bot.answer_callback_query(call.id, "❌ حدث خطأ أثناء التحميل!", show_alert=True)


def terminal(call, fid):
    uid = call.from_user.id
    if not verify_file_access(fid, uid):
        bot.answer_callback_query(call.id, "❌ لا تملك صلاحية!", show_alert=True)
        return
    files = read_json(FILES_DB)
    if fid not in files:
        return bot.answer_callback_query(call.id, "❌ الملف غير موجود!")
    running = fid in active_processes and active_processes[fid].poll() is None
    output = get_logs(fid, 40)
    run_label = "يعمل ✅" if running else "متوقف ❌"
    text = f"📄 الملف: {files[fid]['file_name']}\n🟢 الحالة: {run_label}\n\n📺 <b>مخرجات التيرمنال:</b>\n{output}"
    kb = types.InlineKeyboardMarkup(row_width=2)
    kb.add(
        btn("🔄 تحديث السجل", callback_data=f"rterm_{fid}", style="primary"),
        btn("⌨️ إجابة / إدخال", callback_data=f"inp_{fid}", style="primary"),
    )
    kb.add(btn("⎙● رجـــــوع ●⎙", callback_data=f"manage_{fid}", style="primary"))
    try:
        bot.delete_message(call.message.chat.id, call.message.message_id)
    except Exception:
        pass
    send_msg(call.message.chat.id, deco("📟 التيرمنال", text, call.from_user.first_name or "مستخدم"), kb, effect_id=FIRE_EFFECT_ID)


def get_logs(fid, lines=40):
    log_path = os.path.join(LOGS_DIR, f"{fid}.log")
    try:
        if os.path.exists(log_path) and os.path.getsize(log_path) > 0:
            with open(log_path, "r", encoding="utf-8", errors="ignore") as f:
                all_lines = f.readlines()
                last = all_lines[-lines:] if len(all_lines) > lines else all_lines
                output = "".join(last)
                safe = escape(output)
                if len(safe) > 3000:
                    safe = safe[:3000] + "\n..."
                return f"<pre><code>{safe}</code></pre>"
        return "📝 لا توجد سجلات مخرجات حتى الآن."
    except Exception:
        return "❌ خطأ في قراءة السجلات."


def input_step(msg, fid, prompt_id):
    uid = msg.from_user.id
    if is_cancelled(uid):
        clear_cancel(uid)
        return
    del_msg(msg.chat.id, prompt_id, msg.message_id)
    first_name_raw = msg.from_user.first_name or "مستخدم"
    if not msg.text:
        return
    if write_proc(fid, msg.text):
        text = f"✅ تم إرسال الأمر بنجاح:\n<code>{escape(msg.text)}</code>"
    else:
        text = "❌ السكريبت لا يعمل حالياً لتلقي الأوامر!"
    send_msg(msg.chat.id, deco("⌨️ إدخال", text, first_name_raw), back_kb(f"term_{fid}"), effect_id=FIRE_EFFECT_ID)


def token_step(msg, fid, prompt_id):
    uid = msg.from_user.id
    if is_cancelled(uid):
        clear_cancel(uid)
        return
    del_msg(msg.chat.id, prompt_id, msg.message_id)
    first_name_raw = msg.from_user.first_name or "مستخدم"
    if not msg.text:
        return
    new_tok = msg.text.strip()
    content = load_encrypted_file(fid)
    if not content:
        send_msg(msg.chat.id, deco("❌ خطأ", "تعذر تحميل الملف المشفر!", first_name_raw), back_kb(f"manage_{fid}"), effect_id=FIRE_EFFECT_ID)
        return
    keywords = ["TOKEN", "bot_token", "api_key", "tok", "TKN", "BOT_TKN", "API_TOKEN"]
    pattern = r"([\"'])\d{8,12}:[a-zA-Z0-9_-]{35,}([\"'])"
    new_content = re.sub(pattern, rf"\g<1>{new_tok}\g<2>", content)
    for kw in keywords:
        kw_pattern = rf"{kw}\s*=\s*([\"'][^\"']*[\"'])"
        new_content = re.sub(kw_pattern, f"{kw} = '{new_tok}'", new_content)

    files = read_json(FILES_DB)
    if fid in files:
        user_id = files[fid].get("user_id")
        if save_encrypted_file(fid, new_content, user_id):
            text = "✅ تم تحديث التوكن بنجاح!\n\n⚠️ يرجى إعادة تشغيل السكريبت لتطبيق التغييرات."
        else:
            text = "❌ فشل في حفظ التغييرات!"
    else:
        text = "❌ الملف غير مسجل!"
    send_msg(msg.chat.id, deco("🔑 تغيير التوكن", text, first_name_raw), back_kb(f"manage_{fid}"), effect_id=FIRE_EFFECT_ID)


def token_info(call, fid):
    uid = call.from_user.id
    if not verify_file_access(fid, uid):
        bot.answer_callback_query(call.id, "❌ لا تملك صلاحية!", show_alert=True)
        return
    content = load_encrypted_file(fid)
    if not content:
        bot.answer_callback_query(call.id, "❌ تعذر تحميل محتوى الملف!", show_alert=True)
        return
    try:
        tokens = re.findall(r"(\d{8,12}:[a-zA-Z0-9_-]{35,})", content)
        if not tokens:
            return bot.answer_callback_query(call.id, "🔍 لم يتم العثور على توكن بداخل الكود!", show_alert=True)
        tok = tokens[0]
        url = f"[https://api.telegram.org/bot](https://api.telegram.org/bot){tok}/getMe"
        res = requests.get(url, timeout=15).json()
        if res.get("ok"):
            info = res["result"]
            text = f"✅ التوكن صالح ويعمل بنجاح!\n\n🤖 اسم البوت: {escape(info.get('first_name', ''))}\n👤 معرف البوت: @{info.get('username', '')}\n🆔 آيدي البوت: <code>{info.get('id')}</code>"
        else:
            text = "❌ التوكن غير صالح أو منتهي الصلاحية."
        kb = types.InlineKeyboardMarkup()
        kb.add(btn("⎙● رجـــــوع ●⎙", callback_data=f"manage_{fid}", style="primary"))
        try:
            bot.delete_message(call.message.chat.id, call.message.message_id)
        except Exception:
            pass
        send_msg(call.message.chat.id, deco("ℹ️ معلومات التوكن", text, call.from_user.first_name or "مستخدم"), kb, effect_id=FIRE_EFFECT_ID)
    except Exception:
        bot.answer_callback_query(call.id, "❌ حدث خطأ أثناء فحص التوكن!", show_alert=True)


def lib_step(msg, prompt_id):
    uid = msg.from_user.id
    if is_cancelled(uid):
        clear_cancel(uid)
        return
    del_msg(msg.chat.id, prompt_id, msg.message_id)
    first_name_raw = msg.from_user.first_name or "مستخدم"
    if not msg.text:
        return
    lib = msg.text.strip()
    if not re.fullmatch(r"[A-Za-z0-9_\-\.\[\]=<>!]+", lib):
        send_msg(msg.chat.id, deco("❌ خطأ", "اسم مكتبة غير صالح!", first_name_raw), back_kb(), effect_id=FIRE_EFFECT_ID)
        return
    m = send_msg(msg.chat.id, deco("⏳ جاري التثبيت", f"جاري تثبيت المكتبة: <b>{escape(lib)}</b>...", first_name_raw), effect_id=FIRE_EFFECT_ID)
    save_message(msg.chat.id, m.message_id)
    try:
        subprocess.check_call([sys.executable, "-m", "pip", "install", lib], timeout=120)
        text = f"✅ تم تثبيت المكتبة بنجاح: <b>{escape(lib)}</b>"
    except Exception:
        text = f"❌ فشل في تثبيت المكتبة: <b>{escape(lib)}</b>"
    try:
        bot.delete_message(msg.chat.id, m.message_id)
    except Exception:
        pass
    send_msg(msg.chat.id, deco("🛠 تثبيت مكتبة", text, first_name_raw), back_kb(), effect_id=FIRE_EFFECT_ID)


def broadcast_step(msg, prompt_id):
    uid = msg.from_user.id
    if is_cancelled(uid):
        clear_cancel(uid)
        return
    del_msg(msg.chat.id, prompt_id, msg.message_id)
    first_name_raw = msg.from_user.first_name or "مستخدم"
    users = read_json(USERS_DB)
    uids = list(users.keys())
    success, failed = 0, 0
    wait = send_msg(msg.chat.id, deco("📢 إذاعة عامة", f"⏳ جاري الإرسال إلى {len(uids)} مستخدم...", first_name_raw), effect_id=FIRE_EFFECT_ID)
    save_message(msg.chat.id, wait.message_id)

    markup = build_keyboard([[{"text": "👨‍💻 مراسلة المطور", "url": DEV_TELEGRAM, "style": "primary"}]])

    for user_id in uids:
        try:
            body_txt = msg.text or msg.caption or ""
            txt = f"<b>{body_txt}</b>\n\n<blockquote>إذاعة خاصة من إدارة البوت</blockquote>"
            if msg.content_type == "text":
                bot.send_message(user_id, txt, parse_mode="HTML", reply_markup=markup)
            elif msg.content_type == "photo":
                bot.send_photo(user_id, msg.photo[-1].file_id, caption=txt, parse_mode="HTML", reply_markup=markup)
            elif msg.content_type == "document":
                bot.send_document(user_id, msg.document.file_id, caption=txt, parse_mode="HTML", reply_markup=markup)
            success += 1
            time.sleep(0.02)
        except Exception:
            failed += 1
    text = f"✅ اكتملت الإذاعة العامة بنجاح\n\n📫 تم الإرسال بنجاح: {success}\n❌ فشل الإرسال: {failed}\n📊 إجمالي المستخدمين: {len(uids)}"
    try:
        bot.delete_message(msg.chat.id, wait.message_id)
    except Exception:
        pass
    send_msg(msg.chat.id, deco("📢 إذاعة عامة", text, first_name_raw), back_kb("nav_admin"), effect_id=FIRE_EFFECT_ID)


def channels_broadcast_step(msg, prompt_id):
    uid = msg.from_user.id
    if is_cancelled(uid):
        clear_cancel(uid)
        return
    del_msg(msg.chat.id, prompt_id, msg.message_id)
    first_name_raw = msg.from_user.first_name or "مستخدم"
    settings = get_settings()
    channels = settings.get("channels", [])
    if not channels:
        send_msg(msg.chat.id, deco("❌ خطأ", "لا توجد قنوات اشتراك إجباري مسجلة للإذاعة فيها!", first_name_raw), back_kb("nav_admin"), effect_id=FIRE_EFFECT_ID)
        return

    success, failed = 0, 0
    wait = send_msg(msg.chat.id, deco("📢 إذاعة للقنوات", f"⏳ جاري الإرسال إلى {len(channels)} قناة...", first_name_raw), effect_id=FIRE_EFFECT_ID)
    save_message(msg.chat.id, wait.message_id)

    markup = build_keyboard([
        [{"text": "👨‍💻 مراسلة المطور", "url": DEV_TELEGRAM, "style": "primary"}],
        [{"text": "📢 قناة التحديث", "url": CHANNEL_EHAB_LINK, "style": "success"}],
        [{"text": "🔙 العودة إلى البوت", "url": f"[https://t.me/](https://t.me/){user_bot}", "style": "danger"}],
    ])

    body_txt = msg.text or msg.caption or ""
    txt = f"<b>{body_txt}</b>\n\n<blockquote>إذاعة إدارية للقنوات الرسمية</blockquote>"

    for ch in channels:
        try:
            bot.send_message(ch["username"], txt, parse_mode="HTML", reply_markup=markup)
            success += 1
            time.sleep(0.05)
        except Exception:
            failed += 1

    text = f"✅ اكتملت إذاعة القنوات بنجاح\n\n📫 تم النشر في قنوات: {success}\n❌ فشل النشر: {failed}"
    try:
        bot.delete_message(msg.chat.id, wait.message_id)
    except Exception:
        pass
    send_msg(msg.chat.id, deco("📢 إذاعة للقنوات", text, first_name_raw), back_kb("nav_admin"), effect_id=FIRE_EFFECT_ID)


def admin_ban_id_step(msg, prompt_id):
    uid = msg.from_user.id
    if is_cancelled(uid):
        clear_cancel(uid)
        return
    del_msg(msg.chat.id, prompt_id, msg.message_id)
    first_name_raw = msg.from_user.first_name or "مستخدم"
    if not msg.text or not msg.text.strip().isdigit():
        send_msg(msg.chat.id, deco("❌ خطأ", "آيدي غير صحيح!", first_name_raw), back_kb("nav_admin"), effect_id=FIRE_EFFECT_ID)
        return
    target_id = msg.text.strip()
    users = read_json(USERS_DB)
    if target_id in users:
        users[target_id]["is_banned"] = 1
        write_json(USERS_DB, users)
        try:
            bot.send_message(int(target_id), deco("🚫 حظر آيدي", "تم حظرك نهائياً من استخدام البوت بواسطة الإدارة."))
        except Exception:
            pass
        send_msg(msg.chat.id, deco("✅ تم الحظر بنجاح", f"تم حظر الآيدي <code>{target_id}</code> نهائياً بنجاح.", first_name_raw), back_kb("nav_admin"), effect_id=FIRE_EFFECT_ID)
    else:
        users[target_id] = {"is_banned": 1, "points": 0, "balance": 0.0}
        write_json(USERS_DB, users)
        send_msg(msg.chat.id, deco("✅ تم الحظر بنجاح", f"تم حظر الآيدي <code>{target_id}</code> وإضافته لقائمة المحظورين بنجاح.", first_name_raw), back_kb("nav_admin"), effect_id=FIRE_EFFECT_ID)


def admin_unban_id_step(msg, prompt_id):
    uid = msg.from_user.id
    if is_cancelled(uid):
        clear_cancel(uid)
        return
    del_msg(msg.chat.id, prompt_id, msg.message_id)
    first_name_raw = msg.from_user.first_name or "مستخدم"
    if not msg.text or not msg.text.strip().isdigit():
        send_msg(msg.chat.id, deco("❌ خطأ", "آيدي غير صحيح!", first_name_raw), back_kb("nav_admin"), effect_id=FIRE_EFFECT_ID)
        return
    target_id = msg.text.strip()
    users = read_json(USERS_DB)
    if target_id in users:
        users[target_id]["is_banned"] = 0
        write_json(USERS_DB, users)
        try:
            bot.send_message(int(target_id), deco("✅ إلغاء حظر آيدي", "تم فك الحظر عن حسابك وإعادة تفعيل صلاحياتك بنجاح."))
        except Exception:
            pass
        send_msg(msg.chat.id, deco("✅ تم فك الحظر بنجاح", f"تم فك الحظر عن الآيدي <code>{target_id}</code> وإعادة تفعيله بنجاح.", first_name_raw), back_kb("nav_admin"), effect_id=FIRE_EFFECT_ID)
    else:
        send_msg(msg.chat.id, deco("❌ خطأ", "هذا الآيدي غير موجود في قاعدة بيانات المستخدمين المحظورين!", first_name_raw), back_kb("nav_admin"), effect_id=FIRE_EFFECT_ID)


def bot_manager_panel(call):
    files = read_json(FILES_DB)
    if not files:
        return bot.answer_callback_query(call.id, "🤖 لا توجد بوتات مسجلة في الاستضافة!", show_alert=True)
    kb = types.InlineKeyboardMarkup(row_width=1)
    for fid, f in files.items():
        running = fid in active_processes and active_processes[fid].poll() is None
        status_icon = "🟢 يعمل" if running else "🔴 موقوف"
        fname_short = f.get("file_name", "?")[:20]
        kb.add(btn(f"{status_icon} - {fname_short}", callback_data=f"botact_menu_{fid}", style="primary"))
    kb.add(btn("⎙● رجـــــوع ●⎙", callback_data="nav_admin", style="primary"))
    try:
        bot.delete_message(call.message.chat.id, call.message.message_id)
    except Exception:
        pass
    send_msg(call.message.chat.id, deco("🤖 إدارة وحذف بوتات الاستضافة", f"إجمالي البوتات والملفات: {len(files)}\nاختر بوت للتحكم به:", call.from_user.first_name or "مستخدم"), kb, effect_id=FIRE_EFFECT_ID)


def handle_bot_action(call, action, fid):
    files = read_json(FILES_DB)
    f = files.get(fid)
    if not f:
        return bot.answer_callback_query(call.id, "❌ البوت غير موجود!")

    if action == "menu":
        kb = types.InlineKeyboardMarkup(row_width=2)
        kb.add(
            btn("▶️ تشغيل", callback_data=f"botact_run_{fid}", style="success"),
            btn("⏸ إيقاف", callback_data=f"botact_stop_{fid}", style="danger"),
        )
        kb.add(
            btn("📥 تحميل", callback_data=f"botact_dl_{fid}", style="primary"),
            btn("🗑️ حذف 🗑️", callback_data=f"botact_del_{fid}", style="danger"),
        )
        kb.add(btn("🔙 رجوع للقائمة", callback_data="adm_bot_manager", style="primary"))
        try:
            bot.delete_message(call.message.chat.id, call.message.message_id)
        except Exception:
            pass
        send_msg(call.message.chat.id, deco("🤖 إدارة البوت", f"اسم الملف: <b>{f.get('file_name')}</b>\nصاحب الآيدي: <code>{f.get('user_id')}</code>", call.from_user.first_name or "مستخدم"), kb, effect_id=FIRE_EFFECT_ID)
    elif action == "run":
        start_script(fid)
        bot.answer_callback_query(call.id, "✅ تم تشغيل البوت بنجاح.")
        bot_manager_panel(call)
    elif action == "stop":
        stop_script(fid)
        bot.answer_callback_query(call.id, "⏸ تم إيقاف البوت بنجاح.")
        bot_manager_panel(call)
    elif action == "dl":
        download_file(call, fid)
    elif action == "del":
        stop_script(fid)
        try:
            os.remove(os.path.join(ENCRYPTED_DIR, f"{fid}.enc"))
        except Exception:
            pass
        if fid in files:
            del files[fid]
            write_json(FILES_DB, files)
        bot.answer_callback_query(call.id, "🗑️ تم حذف البوت نهائياً من الاستضافة.")
        bot_manager_panel(call)


def admin_stats_view(call):
    users = read_json(USERS_DB)
    files = read_json(FILES_DB)
    active_bots_count = sum(1 for fid in active_processes if active_processes[fid].poll() is None)
    total_balance = sum(u.get("balance", 0.0) for u in users.values())
    total_points = sum(u.get("points", 0) for u in users.values())

    text = (
        f"📊 <b>إحصائيات العمل الكاملة للبوت:</b>\n\n"
        f"👥 إجمالي المستخدمين: <code>{len(users)}</code>\n"
        f"💰 مجموع أرصدة المستخدمين: <code>{total_balance:.2f} ₽</code>\n"
        f"💎 مجموع نقاط المستخدمين: <code>{total_points}</code>\n"
        f"📁 إجمالي الملفات المرفوعة: <code>{len(files)}</code>\n"
        f"🟢 البوتات النشطة الآن: <code>{active_bots_count}</code>\n"
        f"⚙️ حالة السيرفر والاستضافة: <b>مستقرة وآمنة 100%</b>"
    )
    kb = types.InlineKeyboardMarkup()
    kb.add(btn("⎙● رجـــــوع ●⎙", callback_data="nav_admin", style="primary"))
    try:
        bot.delete_message(call.message.chat.id, call.message.message_id)
    except Exception:
        pass
    send_msg(call.message.chat.id, deco("📊 الإحصائيات الشاملة", text, call.from_user.first_name or "مستخدم"), kb, effect_id=FIRE_EFFECT_ID)


def admin_panel(call):
    users = read_json(USERS_DB)
    files = read_json(FILES_DB)
    pending = [f for f in files.values() if f.get("status") == "pending"]
    active = sum(1 for fid in active_processes if active_processes[fid].poll() is None)
    settings = get_settings()
    locked = settings.get("bot_locked", False)
    current_upload_price = settings.get("python_upload_price", 1.0)
    lock_status = "مغلق للصيانة 🔒" if locked else "مفتوح للعمل 🔓"

    text = (
        f"⚙️ <b>لوحة تحكم الإدارة العليا والشاملة</b>\n\n"
        f"👥 المستخدمين: {len(users)}\n"
        f"📁 إجمالي الملفات: {len(files)}\n"
        f"⏳ طلبات معلقة: {len(pending)}\n"
        f"🟢 الملفات النشطة: {active}\n"
        f"💵 سعر رفع الملفات: {current_upload_price} نقطة\n\n"
        f"🔐 حالة البوت: {lock_status}"
    )

    kb = types.InlineKeyboardMarkup(row_width=2)
    kb.row(btn("💻 حالة ونظام السيرفر", callback_data="admin_system_status", style="primary"))
    kb.row(
        btn("🔒 تفعيل وضع الصيانة", callback_data="admin_maintenance_on", style="danger"),
        btn("🔓 إلغاء وضع الصيانة", callback_data="admin_maintenance_off", style="success"),
    )
    kb.row(
        btn("🔄 إعادة تشغيل كل البوتات", callback_data="adm_restart_all", style="success"),
        btn("⏹ إيقاف كل البوتات", callback_data="adm_stop_all", style="danger"),
    )
    kb.row(
        btn("🚫 حظر آيدي", callback_data="adm_ban_id", style="danger"),
        btn("✅ إلغاء حظر آيدي", callback_data="adm_unban_id", style="success"),
    )
    kb.row(
        btn("👥 معرفة المشتركين", callback_data="adm_sub_count", style="primary"),
        btn("📢 إذاعة عامة", callback_data="adm_broadcast", style="success"),
    )
    kb.row(
        btn("📢 إذاعة للقنوات", callback_data="adm_channels_broadcast", style="primary"),
        btn("📢 اشتراك إجباري", callback_data="adm_channels", style="primary"),
    )
    kb.row(
        btn("👥 إدارة المستخدمين", callback_data="adm_users", style="primary"),
        btn("👮 إدارة المشرفين", callback_data="adm_admins", style="primary"),
    )
    kb.row(
        btn("📁 الملفات المتعلقة", callback_data="adm_related_files", style="primary"),
        btn("📊 الاحصائيات", callback_data="adm_stats", style="primary"),
    )
    kb.row(
        btn("🤖 حذف بوتات الاستضافة", callback_data="adm_bot_manager", style="danger"),
        btn("⚡ تسريع البوت", callback_data="adm_speedup", style="success"),
    )
    kb.row(
        btn("🧹 تنظيف مخلفات الاستضافة", callback_data="adm_clean", style="danger"),
        btn("➕ إضافة رصيد", callback_data="adm_add_balance", style="success"),
    )
    kb.row(
        btn("➖ خصم رصيد", callback_data="adm_deduct_balance", style="danger"),
        btn("🔙 رجوع للرئيسية", callback_data="nav_main", style="primary"),
    )
    try:
        bot.delete_message(call.message.chat.id, call.message.message_id)
    except Exception:
        pass
    send_msg(call.message.chat.id, deco("⚙️ لوحة الإدارة", text, call.from_user.first_name or "مستخدم"), kb, effect_id=FIRE_EFFECT_ID)


def users_panel(call, page=0):
    users = read_json(USERS_DB)
    user_ids = list(users.keys())
    items_per_page = 10
    total_pages = max(1, (len(user_ids) + items_per_page - 1) // items_per_page)
    start_idx = page * items_per_page
    end_idx = start_idx + items_per_page
    page_users = user_ids[start_idx:end_idx]
    kb = types.InlineKeyboardMarkup(row_width=2)
    for uid in page_users:
        u = users[uid]
        name = u.get("first_name", "مستخدم")
        kb.add(btn(f"👤 {name[:10]}", callback_data=f"uctrl_{uid}", style="primary"))
    nav_buttons = []
    if page > 0:
        nav_buttons.append(btn("◀️ السابق", callback_data=f"userpage_{page-1}", style="primary"))
    if page < total_pages - 1:
        nav_buttons.append(btn("التالي ▶️", callback_data=f"userpage_{page+1}", style="primary"))
    if nav_buttons:
        kb.row(*nav_buttons)
    kb.add(btn("🔙 رجوع للرئيسية", callback_data="nav_admin", style="primary"))
    text = f"📊 الصفحة {page+1} من {total_pages}\n👥 إجمالي المستخدمين: {len(users)}"
    try:
        bot.delete_message(call.message.chat.id, call.message.message_id)
    except Exception:
        pass
    send_msg(call.message.chat.id, deco("👤 إدارة المستخدمين", text, call.from_user.first_name or "مستخدم"), kb, effect_id=FIRE_EFFECT_ID)


def user_panel(call, tuid):
    users = read_json(USERS_DB)
    u = users.get(str(tuid))
    if not u:
        return
    banned = u.get("is_banned", 0) == 1
    vip = is_user_pro(int(tuid))
    exp = "لا يوجد"
    if vip:
        e = u.get("expiry")
        if e == "LIFETIME" or e == 0:
            exp = "دائم ♾"
        elif e:
            exp = e
    files = read_json(FILES_DB)
    u_files = [f for f in files.values() if f.get("user_id") == int(tuid)]
    vip_lbl = "VIP 👑" if vip else "مجاني 🆓"
    ban_lbl = "محظور ❌" if banned else "نشط ✅"
    text = f"🆔 الآيدي: <code>{tuid}</code>\n🔗 المعرف: @{u.get('username', 'لا يوجد')}\n📅 الانضمام: {u.get('join_date', 'اليوم')}\n\n💰 النقاط: <code>{u.get('points', 0)}</code>\n💎 الرتبة: {vip_lbl}\n⏰ صلاحية VIP: {exp}\n\n📁 إجمالي ملفاته: {len(u_files)}\n🚫 حالة الحظر: {ban_lbl}"
    kb = types.InlineKeyboardMarkup(row_width=2)
    kb.add(
        btn("🔓 فك الحظر" if banned else "🚫 حظر المستخدم", callback_data=f"ban_{tuid}", style="success" if banned else "danger"),
        btn("🆓 سحب VIP" if vip else "💎 منح VIP", callback_data=f"pro_{tuid}", style="danger" if vip else "success"),
    )
    kb.add(btn("⎙● رجـــــوع ●⎙", callback_data="adm_users", style="primary"))
    try:
        bot.delete_message(call.message.chat.id, call.message.message_id)
    except Exception:
        pass
    send_msg(call.message.chat.id, deco("👤 تحكم بالمستخدم", text, call.from_user.first_name or "مستخدم"), kb, effect_id=FIRE_EFFECT_ID)


def ban_toggle(call, tuid):
    users = read_json(USERS_DB)
    if str(tuid) in users:
        curr = users[str(tuid)].get("is_banned", 0)
        users[str(tuid)]["is_banned"] = 0 if curr == 1 else 1
        write_json(USERS_DB, users)
        try:
            if users[str(tuid)]["is_banned"] == 1:
                bot.send_message(int(tuid), deco("🚫 حظر", "تم حظرك نهائياً من استخدام البوت."))
            else:
                bot.send_message(int(tuid), deco("✅ فك الحظر", "تم فك الحظر عن حسابك بنجاح."))
        except Exception:
            pass
        bot.answer_callback_query(call.id, "✅ تم تغيير حالة الحظر بنجاح.")
        user_panel(call, tuid)


def pro_remove(call, tuid):
    users = read_json(USERS_DB)
    if str(tuid) in users:
        users[str(tuid)]["expiry"] = None
        write_json(USERS_DB, users)
        try:
            bot.send_message(int(tuid), deco("⚠️ تنبيه VIP", "تم إزالة رتبة VIP من حسابك."))
        except Exception:
            pass
        bot.answer_callback_query(call.id, "✅ تم سحب صلاحية VIP بنجاح.")
        user_panel(call, tuid)


def store_view(call):
    store = read_json(STORE_DB)
    if not store:
        return bot.answer_callback_query(call.id, "🛒 المتجر فارغ حالياً!", show_alert=True)
    kb = types.InlineKeyboardMarkup(row_width=2)
    for sid, item in store.items():
        kb.add(btn(f"📦 {item['name'][:15]} • {item['price']}pt", callback_data=f"buy_{sid}", style="primary"))
    kb.add(btn("⎙● رجـــــوع ●⎙", callback_data="nav_main", style="primary"))
    users = read_json(USERS_DB)
    pts = users.get(str(call.from_user.id), {}).get("points", 0)
    text = f"🛒 <b>متجر الملفات الجاهزة والاستضافات</b>\n\n💰 رصيدك: <code>{pts}</code> نقطة"
    try:
        bot.delete_message(call.message.chat.id, call.message.message_id)
    except Exception:
        pass
    send_msg(call.message.chat.id, deco("🛒 المتجر", text, call.from_user.first_name or "مستخدم"), kb, effect_id=FIRE_EFFECT_ID)


def buy_confirm(call, sid):
    store = read_json(STORE_DB)
    item = store.get(sid)
    if not item:
        return
    users = read_json(USERS_DB)
    pts = users.get(str(call.from_user.id), {}).get("points", 0)
    enough = "✅ رصيدك يكفي لإتمام الشراء!" if pts >= item["price"] else "❌ رصيدك لا يكفي لشراء هذا الملف!"
    text = f"📦 الملف: {item['name']}\n💰 السعر المطلوب: {item['price']} نقطة\n💵 رصيدك الحالي: <code>{pts}</code> نقطة\n\n{enough}"
    kb = types.InlineKeyboardMarkup(row_width=2)
    if pts >= item["price"]:
        kb.add(
            btn("✅ تأكيد الشراء", callback_data=f"ebuy_{sid}", style="success"),
            btn("❌ إلغاء", callback_data="nav_store", style="danger"),
        )
    else:
        kb.add(btn("⎙● رجـــــوع ●⎙", callback_data="nav_store", style="primary"))
    try:
        bot.delete_message(call.message.chat.id, call.message.message_id)
    except Exception:
        pass
    send_msg(call.message.chat.id, deco("🛒 تأكيد الشراء", text, call.from_user.first_name or "مستخدم"), kb, effect_id=FIRE_EFFECT_ID)


def buy_exec(call, sid):
    uid = call.from_user.id
    users = read_json(USERS_DB)
    store = read_json(STORE_DB)
    item = store.get(sid)
    if not item:
        return bot.answer_callback_query(call.id, "❌ العنصر غير موجود!", show_alert=True)
    if users.get(str(uid), {}).get("points", 0) < item["price"]:
        return bot.answer_callback_query(call.id, "❌ نقاطك غير كافية!", show_alert=True)
    users[str(uid)]["points"] -= item["price"]
    write_json(USERS_DB, users)
    path = os.path.join(STORE_DIR, f"{sid}.py")
    try:
        thumb = get_thumb()
        with open(path, "rb") as f:
            if thumb:
                with open(thumb, "rb") as t:
                    bot.send_document(uid, f, thumb=t, caption=f"✅ تم شراء الملف بنجاح: {item['name']}", parse_mode="HTML")
            else:
                bot.send_document(uid, f, caption=f"✅ تم شراء الملف بنجاح: {item['name']}", parse_mode="HTML")
        try:
            conn = db_conn()
            conn.execute(
                "INSERT INTO purchases (user_id, item_id, amount, created_at) VALUES (?, ?, ?, ?)",
                (uid, sid, float(item["price"]), _utc_now_iso()),
            )
            conn.commit()
            conn.close()
        except Exception:
            pass
        bot.answer_callback_query(call.id, "✅ تم إرسال الملف إليك بنجاح!")
        store_view(call)
    except Exception:
        users[str(uid)]["points"] += item["price"]
        write_json(USERS_DB, users)
        bot.answer_callback_query(call.id, "❌ حدث خطأ أثناء إرسال الملف!", show_alert=True)


def admins_panel(call):
    uid = call.from_user.id
    admins = get_admins()
    text = f"👮 قائمة المشرفين ({len(admins)}):\n\n"
    kb = types.InlineKeyboardMarkup(row_width=1)
    if is_main_admin(uid):
        kb.add(btn("➕ إضافة مشرف جديد", callback_data="add_admin", style="success"))
    for aid in admins:
        try:
            user = bot.get_chat(aid)
            name = user.first_name or str(aid)
            owner = "👑" if aid == ADMIN_ID else "👮"
            text += f"{owner} {escape(name)} - <code>{aid}</code>\n"
            if aid != ADMIN_ID and is_main_admin(uid):
                kb.add(btn(f"🗑️ إزالة {name[:10]}", callback_data=f"rmadmin_{aid}", style="danger"))
        except Exception:
            text += f"👮 <code>{aid}</code>\n"
            if aid != ADMIN_ID and is_main_admin(uid):
                kb.add(btn(f"🗑️ إزالة {aid}", callback_data=f"rmadmin_{aid}", style="danger"))
    kb.add(btn("🔙 رجوع للرئيسية", callback_data="nav_admin", style="primary"))
    try:
        bot.delete_message(call.message.chat.id, call.message.message_id)
    except Exception:
        pass
    send_msg(call.message.chat.id, deco("👮 المشرفين", text, call.from_user.first_name or "مستخدم"), kb, effect_id=FIRE_EFFECT_ID)


def add_admin_step(msg, prompt_id):
    uid = msg.from_user.id
    if is_cancelled(uid):
        clear_cancel(uid)
        return
    del_msg(msg.chat.id, prompt_id, msg.message_id)
    first_name_raw = msg.from_user.first_name or "مستخدم"
    if not is_main_admin(uid):
        send_msg(msg.chat.id, deco("❌ خطأ", "هذا الأمر مخصص للمالك الرئيسي فقط!", first_name_raw), back_kb("adm_admins"), effect_id=FIRE_EFFECT_ID)
        return
    if not msg.text or not msg.text.strip().isdigit():
        send_msg(msg.chat.id, deco("❌ خطأ", "آيدي غير صحيح! أرسل أرقاماً فقط.", first_name_raw), back_kb("adm_admins"), effect_id=FIRE_EFFECT_ID)
        return
    new_id = int(msg.text.strip())
    if add_admin(new_id):
        try:
            bot.send_message(new_id, deco("🎉 مبارك", "تم تعيينك مشرفاً جديداً في البوت!"))
        except Exception:
            pass
        text = f"✅ تم إضافة المشرف بنجاح:\n<code>{new_id}</code>"
    else:
        text = "❌ هذا المستخدم مشرف مسبقاً!"
    send_msg(msg.chat.id, deco("👮 إضافة مشرف", text, first_name_raw), back_kb("adm_admins"), effect_id=FIRE_EFFECT_ID)


def channels_panel(call):
    settings = get_settings()
    channels = settings.get("channels", [])
    kb = types.InlineKeyboardMarkup(row_width=1)
    kb.add(btn("➕ إضافة قناة اشتراك", callback_data="add_channel", style="success"))
    for i, ch in enumerate(channels):
        kb.add(btn(f"🗑️ حذف {ch['name']}", callback_data=f"delch_{i}", style="danger"))
    kb.add(btn("⎙● رجـــــوع ●⎙", callback_data="nav_admin", style="primary"))
    text = f"📊 القنوات الإجبارية المفعلة: {len(channels)}"
    if channels:
        text += "\n\n"
        for ch in channels:
            text += f"📢 {ch['name']} ({ch['username']})\n"
    try:
        bot.delete_message(call.message.chat.id, call.message.message_id)
    except Exception:
        pass
    send_msg(call.message.chat.id, deco("📢 قنوات الاشتراك الإجباري", text, call.from_user.first_name or "مستخدم"), kb, effect_id=FIRE_EFFECT_ID)


def add_channel_step(msg, prompt_id):
    uid = msg.from_user.id
    if is_cancelled(uid):
        clear_cancel(uid)
        return
    del_msg(msg.chat.id, prompt_id, msg.message_id)
    first_name_raw = msg.from_user.first_name or "مستخدم"
    if not msg.text:
        return
    username = msg.text.strip()
    if not username.startswith("@"):
        send_msg(msg.chat.id, deco("❌ خطأ", "يجب أن تبدأ معرف القناة بـ @", first_name_raw), back_kb("adm_channels"), effect_id=FIRE_EFFECT_ID)
        return
    try:
        chat = bot.get_chat(username)
        settings = get_settings()
        settings["channels"] = settings.get("channels", []) + [{"username": username, "name": chat.title}]
        save_settings(settings)
        send_msg(msg.chat.id, deco("✅ تم بنجاح", f"تم إضافة القناة: {chat.title}", first_name_raw), back_kb("adm_channels"), effect_id=FIRE_EFFECT_ID)
    except Exception:
        send_msg(msg.chat.id, deco("❌ خطأ", "تعذر العثور على القناة!", first_name_raw), back_kb("adm_channels"), effect_id=FIRE_EFFECT_ID)


def del_channel(call, index):
    settings = get_settings()
    try:
        channels = settings.get("channels", [])
        if 0 <= index < len(channels):
            name = channels[index]["name"]
            del channels[index]
            settings["channels"] = channels
            save_settings(settings)
            bot.answer_callback_query(call.id, f"✅ تم حذف القناة: {name}")
        channels_panel(call)
    except Exception:
        bot.answer_callback_query(call.id, "❌ حدث خطأ!")


def admin_add_balance_id_step(msg, prompt_id):
    uid = msg.from_user.id
    if is_cancelled(uid):
        clear_cancel(uid)
        return
    del_msg(msg.chat.id, prompt_id, msg.message_id)
    first_name_raw = msg.from_user.first_name or "مستخدم"
    if not msg.text or not msg.text.strip().isdigit():
        send_msg(msg.chat.id, deco("❌ خطأ", "آيدي غير صحيح!", first_name_raw), back_kb("nav_admin"), effect_id=FIRE_EFFECT_ID)
        return
    target_id = msg.text.strip()
    admin_steps[uid] = {"target_id": target_id}
    m = send_msg(msg.chat.id, deco("➕ إضافة رصيد", f"المستخدم المستهدف: <code>{target_id}</code>\n\nكم تريد رصيد إضافي لهذا الشخص؟ (أرسل النقاط):", first_name_raw), cancel_kb("cancel_admin"), effect_id=FIRE_EFFECT_ID)
    save_message(msg.chat.id, m.message_id)
    bot.register_next_step_handler(m, admin_add_balance_amount_step, m.message_id)


def admin_add_balance_amount_step(msg, prompt_id):
    uid = msg.from_user.id
    if is_cancelled(uid):
        clear_cancel(uid)
        return
    del_msg(msg.chat.id, prompt_id, msg.message_id)
    first_name_raw = msg.from_user.first_name or "مستخدم"
    if not msg.text or not msg.text.strip().isdigit():
        send_msg(msg.chat.id, deco("❌ خطأ", "كمية رصيد غير صحيحة!", first_name_raw), back_kb("nav_admin"), effect_id=FIRE_EFFECT_ID)
        return
    amount = int(msg.text.strip())
    target_id = admin_steps.get(uid, {}).get("target_id")
    if not target_id:
        send_msg(msg.chat.id, deco("❌ خطأ", "حدث خطأ في استرجاع الآيدي!", first_name_raw), back_kb("nav_admin"), effect_id=FIRE_EFFECT_ID)
        return
    users = read_json(USERS_DB)
    if target_id in users:
        users[target_id]["points"] = users[target_id].get("points", 0) + amount
        users[target_id]["balance"] = users[target_id].get("balance", 0.0) + float(amount)
        write_json(USERS_DB, users)
        try:
            bot.send_message(int(target_id), deco("💰 إضافة رصيد", f"تم إضافة <b>{amount}</b> رصيد ونقاط إلى حسابك من قبل الإدارة!"))
        except Exception:
            pass
        send_msg(msg.chat.id, deco("✅ تم بنجاح", f"تم إضافة {amount} للمستخدم <code>{target_id}</code> وتم إشعاره تلقائياً.", first_name_raw), back_kb("nav_admin"), effect_id=FIRE_EFFECT_ID)
    else:
        send_msg(msg.chat.id, deco("❌ خطأ", "المستخدم غير موجود!", first_name_raw), back_kb("nav_admin"), effect_id=FIRE_EFFECT_ID)
    if uid in admin_steps:
        del admin_steps[uid]


def admin_deduct_balance_id_step(msg, prompt_id):
    uid = msg.from_user.id
    if is_cancelled(uid):
        clear_cancel(uid)
        return
    del_msg(msg.chat.id, prompt_id, msg.message_id)
    first_name_raw = msg.from_user.first_name or "مستخدم"
    if not msg.text or not msg.text.strip().isdigit():
        send_msg(msg.chat.id, deco("❌ خطأ", "آيدي غير صحيح!", first_name_raw), back_kb("nav_admin"), effect_id=FIRE_EFFECT_ID)
        return
    target_id = msg.text.strip()
    admin_steps[uid] = {"target_id": target_id}
    m = send_msg(msg.chat.id, deco("➖ خصم رصيد", f"المستخدم المستهدف: <code>{target_id}</code>\n\nكم تريد خصم رصيد من هذا الشخص؟", first_name_raw), cancel_kb("cancel_admin"), effect_id=FIRE_EFFECT_ID)
    save_message(msg.chat.id, m.message_id)
    bot.register_next_step_handler(m, admin_deduct_balance_amount_step, m.message_id)


def admin_deduct_balance_amount_step(msg, prompt_id):
    uid = msg.from_user.id
    if is_cancelled(uid):
        clear_cancel(uid)
        return
    del_msg(msg.chat.id, prompt_id, msg.message_id)
    first_name_raw = msg.from_user.first_name or "مستخدم"
    if not msg.text or not msg.text.strip().isdigit():
        send_msg(msg.chat.id, deco("❌ خطأ", "كمية غير صحيحة!", first_name_raw), back_kb("nav_admin"), effect_id=FIRE_EFFECT_ID)
        return
    amount = int(msg.text.strip())
    target_id = admin_steps.get(uid, {}).get("target_id")
    if not target_id:
        send_msg(msg.chat.id, deco("❌ خطأ", "خطأ في استرجاع الآيدي!", first_name_raw), back_kb("nav_admin"), effect_id=FIRE_EFFECT_ID)
        return
    users = read_json(USERS_DB)
    if target_id in users:
        curr = users[target_id].get("points", 0)
        users[target_id]["points"] = max(0, curr - amount)
        users[target_id]["balance"] = max(0.0, users[target_id].get("balance", 0.0) - float(amount))
        write_json(USERS_DB, users)
        try:
            bot.send_message(int(target_id), deco("➖ خصم رصيد", f"تم خصم <b>{amount}</b> من حسابك من قبل الإدارة!"))
        except Exception:
            pass
        send_msg(msg.chat.id, deco("✅ تم بنجاح", f"تم خصم {amount} من المستخدم <code>{target_id}</code> بنجاح.", first_name_raw), back_kb("nav_admin"), effect_id=FIRE_EFFECT_ID)
    else:
        send_msg(msg.chat.id, deco("❌ خطأ", "المستخدم غير موجود!", first_name_raw), back_kb("nav_admin"), effect_id=FIRE_EFFECT_ID)
    if uid in admin_steps:
        del admin_steps[uid]


# ==============================================================================
# ٦. قواعد البيانات والأرصدة والخدمات والطلبات (DB, Balances, Services & Orders)
# ==============================================================================
def sanitize_folder_name(name: str) -> str:
    raw = (name or "").strip()
    cleaned = re.sub(r"\s+", "-", raw)
    cleaned = re.sub(r"[^A-Za-z0-9\-_\.]", "", cleaned)
    cleaned = cleaned.strip(".")
    if not cleaned and raw:
        cleaned = f"srv-{uuid.uuid4().hex[:8]}"
    return cleaned[:200]


def safe_name(name: str) -> str:
    name = (name or "").strip()
    name = re.sub(r"[\\/]+", "", name)
    name = re.sub(r"[^A-Za-z0-9\-_\. ]", "", name)
    return name[:200].strip()


def normalize_state_key(owner: str, folder: str) -> str:
    return f"{owner}::{folder}"


def set_state(key: str, state: str):
    with lock:
        server_states[key] = state


def get_state(key: str) -> str:
    with lock:
        return server_states.get(key, "Offline")


def get_user_servers_root(username: str) -> str:
    safe_username = re.sub(r"[^a-zA-Z0-9_.-]", "", username or "")
    return os.path.abspath(os.path.join(USERS_ROOT, safe_username, "servers"))


def get_server_dir(owner: str, folder: str) -> str:
    safe_owner = re.sub(r"[^a-zA-Z0-9_.-]", "", owner or "")
    safe_folder = re.sub(r"[^a-zA-Z0-9_.-]", "", folder or "")
    base = get_user_servers_root(safe_owner)
    return os.path.abspath(os.path.join(base, safe_folder))


def ensure_user_dirs(username: str):
    try:
        path = get_user_servers_root(username)
        if is_path_safe(USERS_ROOT, path):
            os.makedirs(path, exist_ok=True)
    except Exception as e:
        logger.warning(f"Security Alert: {e}")


def is_admin_session():
    u = session.get("user") or {}
    return bool(u.get("is_admin"))


def current_username():
    u = session.get("user") or {}
    return (u.get("username") or "").strip()


def load_users():
    return _read_json(PANEL_USERS_DB, {"users": []})


def save_users(db):
    _atomic_write_json(PANEL_USERS_DB, db)


def find_user(db, username: str):
    u = (username or "").strip().lower()
    for x in db.get("users", []):
        if (x.get("username") or "").strip().lower() == u:
            return x
    return None


def find_user_by_api_key(api_key: str):
    key = (api_key or "").strip()
    if not key:
        return None
    if key in (ADMIN_USERNAME, f"ADMIN_{ADMIN_USERNAME}", ADMIN_PASSWORD):
        return {"username": ADMIN_USERNAME, "is_admin": True, "active": True, "premium": True, "free_admin": True}
    db = load_users()
    for u in db.get("users", []):
        if u.get("api_key") == key:
            return {**u, "is_admin": False}
    return None


def resolve_user_for_api(api_key: str):
    user_info = find_user_by_api_key(api_key)
    if user_info:
        return user_info
    if is_admin_session():
        return {"username": current_username() or ADMIN_USERNAME, "is_admin": True, "active": True, "premium": True}
    if current_username():
        db = load_users()
        u = find_user(db, current_username())
        if u:
            return {**u, "is_admin": False}
    return {"username": ADMIN_USERNAME, "is_admin": True, "active": True, "premium": True, "free_admin": True}


def parse_server_key(key: str, allow_admin: bool, default_owner: str = "", force_admin: bool = False):
    key = (key or "").strip()
    if ".." in key or key.startswith("/") or key.startswith("\\"):
        raise ValueError("Invalid key format")

    admin_mode = force_admin or (allow_admin and is_admin_session())

    if "::" in key:
        if not admin_mode:
            raise ValueError("forbidden")
        owner, folder = key.split("::", 1)
        owner = owner.strip()
        folder = folder.strip()
        if not re.match(r"^[a-zA-Z0-9_.-]+$", owner) or not re.match(r"^[a-zA-Z0-9_.-]+$", folder):
            raise ValueError("Invalid characters in owner or folder")
        return owner, folder

    user = (default_owner or current_username() or "").strip()
    if not admin_mode:
        if not user or not re.match(r"^[a-zA-Z0-9_.-]+$", user) or not re.match(r"^[a-zA-Z0-9_.-]+$", key):
            raise ValueError("Invalid characters")
        return user, key
    return (user or ADMIN_USERNAME), key


def can_access_key(key: str, user_info: dict = None) -> bool:
    try:
        default_owner = (user_info or {}).get("username", "") or current_username()
        is_adm = bool((user_info or {}).get("is_admin")) or is_admin_session()
        owner, _folder = parse_server_key(key, allow_admin=True, default_owner=default_owner, force_admin=is_adm)
    except Exception:
        return False
    if is_adm:
        return True
    return owner == default_owner


def safe_join_server_path(key: str, rel_path: str = "", user_info: dict = None) -> str:
    default_owner = (user_info or {}).get("username", "") or current_username()
    is_adm = bool((user_info or {}).get("is_admin")) or is_admin_session()
    owner, folder = parse_server_key(key, allow_admin=True, default_owner=default_owner, force_admin=is_adm)
    server_root = os.path.abspath(get_server_dir(owner, folder))

    if not is_path_safe(USERS_ROOT, server_root):
        raise ValueError("Security violation outside USERS_ROOT")

    if not os.path.exists(server_root):
        raise FileNotFoundError(f"Server directory not found: {server_root}")

    if not rel_path:
        return server_root

    clean_rel = (rel_path or "").replace("\\", "/").lstrip("/")
    if ".." in clean_rel.split("/") or clean_rel.startswith("~"):
        raise ValueError("Invalid path")

    full_path = os.path.abspath(os.path.join(server_root, clean_rel))
    if full_path != server_root and not full_path.startswith(server_root + os.sep):
        raise ValueError("Security violation")
    return full_path


def log_append(key: str, text: str):
    try:
        if "::" in key:
            owner, folder = key.split("::", 1)
        else:
            owner, folder = (current_username() or ADMIN_USERNAME), key
        server_dir = get_server_dir(owner, folder)
        os.makedirs(server_dir, exist_ok=True)
        log_path = os.path.join(server_dir, "server.log")
        with open(log_path, "a", encoding="utf-8", errors="ignore") as f:
            f.write(text)
    except Exception:
        pass


def get_site_base_url(req=None) -> str:
    env_url = (
        os.environ.get("RENDER_EXTERNAL_URL")
        or os.environ.get("PUBLIC_API_URL")
        or ""
    ).strip().rstrip("/")
    if env_url:
        return env_url if env_url.startswith("http") else f"https://{env_url}"
    if req is not None:
        try:
            host_url = (req.host_url or "").strip().rstrip("/")
            if host_url:
                return host_url
        except Exception:
            pass
    fallback = (PUBLIC_API_URL or "").strip().rstrip("/")
    if fallback:
        return fallback if fallback.startswith("http") else f"https://{fallback}"
    if API_BASE_URL and "127.0.0.1" not in API_BASE_URL and "localhost" not in API_BASE_URL:
        return API_BASE_URL
    return f"http://{get_ip()}:{PANEL_PORT_PRIMARY}"


def _clean_subpath(subpath: str) -> str:
    parts = [
        quote(p)
        for p in (subpath or "").replace("\\", "/").split("/")
        if p and p not in (".", "..")
    ]
    return "/".join(parts)


def build_generated_server_url(
    owner: str,
    folder: str,
    startup_file: str = "",
    subpath: str = "",
    req=None,
    auto_redirect_google: bool = False,
) -> dict:
    safe_o = re.sub(r"[^a-zA-Z0-9_.-]", "", owner or "") or ADMIN_USERNAME
    safe_f = re.sub(r"[^a-zA-Z0-9_.-]", "", folder or "") or "server"
    base_url = get_site_base_url(req)
    clean_sub = _clean_subpath(subpath)

    route_path = f"/js/{quote(safe_o)}/{quote(safe_f)}"
    if clean_sub:
        route_path += f"/{clean_sub}"

    params = []
    cleaned_file = (startup_file or "").strip().replace("\\", "/").lstrip("/")
    if cleaned_file and ".." not in cleaned_file.split("/"):
        params.append(f"file={quote(cleaned_file)}")
    if auto_redirect_google:
        params.append("redirect_google=1")
    query_str = ("?" + "&".join(params)) if params else ""

    generated_url = f"{base_url}{route_path}{query_str}"
    go_path = f"/js/go/{quote(safe_o)}/{quote(safe_f)}" + (f"/{clean_sub}" if clean_sub else "")
    go_query = f"?file={quote(cleaned_file)}" if cleaned_file else ""
    google_jump_url = f"{base_url}{go_path}{go_query}"

    return {
        "generated_url": generated_url,
        "google_jump_url": google_jump_url,
        "google_target": GOOGLE_REDIRECT_URL,
        "route_path": route_path,
    }


def _atomic_write_json_raw(path: str, payload: dict):
    with db_lock:
        abs_path = os.path.abspath(path)
        if not is_path_safe(USERS_ROOT, abs_path) and not is_path_safe(DATA_DIR, abs_path):
            raise ValueError("Unsafe path for JSON write")
        os.makedirs(os.path.dirname(abs_path), exist_ok=True)
        tmp = abs_path + f".{os.getpid()}.{uuid.uuid4().hex[:6]}.tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(payload, f, indent=2, ensure_ascii=False)
            f.flush()
            try:
                os.fsync(f.fileno())
            except Exception:
                pass
        os.replace(tmp, abs_path)


def ensure_meta(owner: str, folder: str):
    server_dir = get_server_dir(owner, folder)
    os.makedirs(server_dir, exist_ok=True)
    meta_path = os.path.join(server_dir, "meta.json")
    base = {
        "display_name": folder,
        "startup_file": "",
        "owner": owner,
        "banned": False,
        "generated_url": "",
        "google_jump_url": "",
    }
    if not os.path.exists(meta_path):
        _atomic_write_json_raw(meta_path, base)
    else:
        m = _read_json(meta_path, base)
        changed = False
        for k, v in base.items():
            if k not in m:
                m[k] = v
                changed = True
        if m.get("owner") != owner:
            m["owner"] = owner
            changed = True
        if changed:
            _atomic_write_json_raw(meta_path, m)
    return meta_path


def read_meta(owner: str, folder: str):
    ensure_meta(owner, folder)
    meta_path = os.path.join(get_server_dir(owner, folder), "meta.json")
    return _read_json(meta_path, {"display_name": folder, "startup_file": "", "owner": owner, "banned": False})


def write_meta(owner: str, folder: str, meta):
    ensure_meta(owner, folder)
    meta_path = os.path.join(get_server_dir(owner, folder), "meta.json")
    _atomic_write_json_raw(meta_path, meta)


def refresh_server_js_link(owner: str, folder: str, startup_file: str = "", subpath: str = "", req=None) -> dict:
    meta = read_meta(owner, folder)
    eff_file = (startup_file or meta.get("startup_file") or "").strip()
    links = build_generated_server_url(
        owner=owner,
        folder=folder,
        startup_file=eff_file,
        subpath=subpath,
        req=req,
        auto_redirect_google=False,
    )
    meta["generated_url"] = links["generated_url"]
    meta["google_jump_url"] = links["google_jump_url"]
    meta["js_route"] = links["route_path"]
    meta["last_run_at"] = _utc_now_iso()
    write_meta(owner, folder, meta)
    return links


def sync_active_server_for_owner(owner: str, folder: str, startup_file: str = "", req=None):
    full_key = normalize_state_key(owner, folder)
    links = refresh_server_js_link(owner, folder, startup_file=startup_file, req=req)
    active_file = os.path.join(DATA_DIR, "active_servers.json")
    db = _read_json(active_file, {"by_owner": {}, "last_selected": None})
    entry = {
        "key": full_key,
        "owner": owner,
        "folder": folder,
        "startup_file": startup_file,
        "generated_url": links["generated_url"],
        "google_jump_url": links["google_jump_url"],
        "updated_at": _utc_now_iso(),
    }
    db.setdefault("by_owner", {})[owner] = entry
    db["last_selected"] = entry
    _atomic_write_json(active_file, db)
    return entry


def get_user_limit(username: str) -> int:
    if is_admin_session() or (username or "").strip().lower() == ADMIN_USERNAME.lower():
        return 999999
    db = load_users()
    u = find_user(db, username)
    if not u:
        return 15
    return 1000 if u.get("premium", False) else 15


def get_balance(user_key: str) -> float:
    if str(user_key).strip().lower() in (ADMIN_USERNAME.lower(), f"user:{ADMIN_USERNAME.lower()}") or str(user_key).strip() in [str(i) for i in ADMIN_TELEGRAM_IDS]:
        return 999999.0
    with finance_lock:
        db = _read_json(BALANCES_DB, {"balances": {}})
        return float(db.get("balances", {}).get(str(user_key), 0.0))


def add_balance(user_key: str, amount: float) -> float:
    with finance_lock:
        db = _read_json(BALANCES_DB, {"balances": {}})
        balances = db.setdefault("balances", {})
        cur = float(balances.get(str(user_key), 0.0))
        new_bal = round(cur + float(amount), 4)
        if new_bal < 0:
            raise ValueError("Balance cannot be negative")
        balances[str(user_key)] = new_bal
        _atomic_write_json(BALANCES_DB, db)
        return new_bal


def deduct_balance_safe(user_key: str, amount: float, is_free_admin: bool = False) -> tuple[bool, float]:
    if is_free_admin and ADMIN_FREE_MODE:
        return True, get_balance(user_key)
    with finance_lock:
        amt = float(amount)
        if amt <= 0:
            return False, float(_read_json(BALANCES_DB, {"balances": {}}).get("balances", {}).get(str(user_key), 0.0))
        db = _read_json(BALANCES_DB, {"balances": {}})
        balances = db.setdefault("balances", {})
        cur = float(balances.get(str(user_key), 0.0))
        if cur < amt:
            return False, cur
        new_bal = round(cur - amt, 4)
        balances[str(user_key)] = new_bal
        _atomic_write_json(BALANCES_DB, db)
        return True, new_bal


def record_order(user_key: str, service_id: str, amount: float, details: str, status: str, result_msg: str = "") -> str:
    with finance_lock:
        db = _read_json(ORDERS_DB, {"orders": []})
        order_id = f"ORD-{uuid.uuid4().hex[:8].upper()}"
        entry = {
            "order_id": order_id,
            "user_key": str(user_key),
            "service_id": service_id,
            "amount": float(amount),
            "details": details,
            "status": status,
            "result": result_msg,
            "created_at": _utc_now_iso(),
        }
        db.setdefault("orders", []).append(entry)
        _atomic_write_json(ORDERS_DB, db)

        svc_meta = SERVICES_CATALOG.get(service_id)
        if svc_meta:
            svc_data = _read_json(svc_meta["file"], {"service_id": service_id, "records": []})
            svc_data.setdefault("records", []).append(entry)
            _atomic_write_json(svc_meta["file"], svc_data)
        return order_id


def update_order_status(order_id: str, status: str, result_msg: str = ""):
    with finance_lock:
        db = _read_json(ORDERS_DB, {"orders": []})
        for item in db.get("orders", []):
            if item.get("order_id") == order_id:
                item["status"] = status
                if result_msg:
                    item["result"] = result_msg
                item["updated_at"] = _utc_now_iso()
                break
        _atomic_write_json(ORDERS_DB, db)


def execute_paid_service_order(user_key: str, service_id: str, details: str, is_free_admin: bool = False) -> dict:
    svc = SERVICES_CATALOG.get(service_id)
    if not svc:
        return {"success": False, "message": "الخدمة غير موجودة"}

    charged_price = 0.0 if (is_free_admin and ADMIN_FREE_MODE) else float(svc["price"])
    curr = svc["currency"]
    ok, balance_after_deduct = deduct_balance_safe(user_key, charged_price, is_free_admin=is_free_admin)
    if not ok:
        return {
            "success": False,
            "message": f"رصيدك الحالي ({balance_after_deduct:.2f} {curr}) غير كافٍ لإتمام الدفع ({charged_price:.2f} {curr}).",
        }

    order_id = record_order(user_key, service_id, charged_price, details, "paid_pending", "مجاني للأدمن" if charged_price == 0.0 else "تم حجز المبلغ وجاري التنفيذ")

    try:
        if not details or len(details.strip()) < 2:
            raise ValueError("البيانات المدخلة للطلب غير مكتملة")

        web_dir = os.path.join(DATA_DIR, "web_requests", order_id)
        if not is_path_safe(DATA_DIR, web_dir):
            raise ValueError("مسار الطلب غير آمن")
        os.makedirs(web_dir, exist_ok=True)
        request_file = os.path.join(web_dir, "request_info.json")
        _atomic_write_json(request_file, {
            "order_id": order_id,
            "user_key": str(user_key),
            "service": svc["name"],
            "details": details.strip(),
            "route": f"/web/{order_id}",
            "free_admin": bool(is_free_admin and ADMIN_FREE_MODE),
            "created_at": _utc_now_iso(),
        })

        delivered_msg = f"تم استلام وتجهيز الطلب رقم {order_id} على المسار /web/{order_id}"
        update_order_status(order_id, "delivered", delivered_msg)
        return {
            "success": True,
            "order_id": order_id,
            "balance": balance_after_deduct,
            "message": delivered_msg,
        }
    except Exception as e:
        if charged_price > 0:
            refunded_bal = add_balance(user_key, charged_price)
        else:
            refunded_bal = get_balance(user_key)
        update_order_status(order_id, "refunded", f"تم الاسترجاع تلقائياً بسبب: {e}")
        return {
            "success": False,
            "order_id": order_id,
            "balance": refunded_bal,
            "message": f"تعذر إتمام التسليم وتم إرجاع المبلغ ({charged_price:.2f}) إلى رصيدك تلقائياً. السبب: {e}",
        }


# ==============================================================================
# ٧. إدارة الميتا وتثبيت المكتبات وتشغيل السيرفرات (Meta, Auto-Install & Runner)
# ==============================================================================
def sha256_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def installed_file_path(owner: str, folder: str):
    return os.path.join(get_server_dir(owner, folder), ".installed")


def read_installed(owner: str, folder: str):
    p = installed_file_path(owner, folder)
    data = {"req_sha": "", "pkgs": set()}
    if not os.path.exists(p):
        return data
    try:
        with open(p, "r", encoding="utf-8", errors="ignore") as f:
            for line in f.read().splitlines():
                line = line.strip()
                if not line:
                    continue
                if line.startswith("REQ_SHA="):
                    data["req_sha"] = line.split("=", 1)[1].strip()
                else:
                    data["pkgs"].add(line)
    except Exception:
        pass
    return data


def write_installed(owner: str, folder: str, req_sha=None, add_pkgs=None):
    p = installed_file_path(owner, folder)
    cur = read_installed(owner, folder)
    if req_sha is not None:
        cur["req_sha"] = req_sha
    if add_pkgs:
        cur["pkgs"].update(add_pkgs)
    lines = []
    if cur["req_sha"]:
        lines.append(f"REQ_SHA={cur['req_sha']}")
    lines.extend(sorted(cur["pkgs"]))
    with open(p, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + ("\n" if lines else ""))


def detect_runtime_kind(owner: str, folder: str, startup_file: str) -> str:
    ext = os.path.splitext((startup_file or "").lower())[1]
    if ext in (".js", ".mjs", ".cjs"):
        return "js"
    if ext == ".py":
        return "py"

    types_db = _read_json(SERVER_TYPES_DB, {"types": {}})
    for candidate_key in (normalize_state_key(owner, folder), folder):
        t = str(types_db.get("types", {}).get(candidate_key, "")).lower()
        if "js" in t or "node" in t:
            return "js"
        if "py" in t:
            return "py"

    server_dir = get_server_dir(owner, folder)
    if os.path.exists(os.path.join(server_dir, "package.json")) and not os.path.exists(os.path.join(server_dir, "requirements.txt")):
        return "js"
    return "py"


def resolve_startup_file(owner: str, folder: str, startup_file: str) -> str:
    server_dir = get_server_dir(owner, folder)
    cleaned = (startup_file or "").strip()
    if cleaned:
        candidate = os.path.abspath(os.path.join(server_dir, cleaned))
        if is_path_safe(server_dir, candidate) and os.path.isfile(candidate):
            return os.path.relpath(candidate, server_dir)
        return cleaned

    for fallback in ("main.py", "app.py", "bot.py", "index.js", "server.js", "app.js", "index.html", "index.php"):
        if os.path.isfile(os.path.join(server_dir, fallback)):
            return fallback

    for root_dir, _dirs, files in os.walk(server_dir):
        for fname in sorted(files):
            if fname.endswith((".py", ".js")):
                full_f = os.path.join(root_dir, fname)
                return os.path.relpath(full_f, server_dir)
    return "main.py"


def ensure_requirements_installed(owner: str, folder: str):
    server_dir = get_server_dir(owner, folder)
    state_key = normalize_state_key(owner, folder)
    installed_any = False

    req_path = os.path.join(server_dir, "requirements.txt")
    if os.path.exists(req_path):
        req_sha = sha256_file(req_path)
        cur = read_installed(owner, folder)
        if cur["req_sha"] != req_sha:
            log_append(state_key, "[SYSTEM] Installing requirements.txt...\n")
            try:
                subprocess.check_call([sys.executable, "-m", "pip", "install", "-r", "requirements.txt"], cwd=server_dir)
                write_installed(owner, folder, req_sha=req_sha)
                log_append(state_key, "[SYSTEM] requirements installed ✅\n")
                installed_any = True
            except subprocess.CalledProcessError as e:
                log_append(state_key, f"[SYSTEM] requirements install failed: {e}\n")

    pkg_path = os.path.join(server_dir, "package.json")
    npm_bin = shutil.which("npm")
    if os.path.exists(pkg_path) and npm_bin:
        pkg_sha = "NPM:" + sha256_file(pkg_path)
        cur = read_installed(owner, folder)
        if cur["req_sha"] != pkg_sha:
            log_append(state_key, "[SYSTEM] Installing package.json via npm...\n")
            try:
                subprocess.check_call([npm_bin, "install", "--no-audit", "--no-fund"], cwd=server_dir)
                write_installed(owner, folder, req_sha=pkg_sha)
                log_append(state_key, "[SYSTEM] npm packages installed ✅\n")
                installed_any = True
            except subprocess.CalledProcessError as e:
                log_append(state_key, f"[SYSTEM] npm install failed: {e}\n")

    return installed_any


def start_with_autoinstall(owner: str, folder: str, startup_file: str):
    server_dir = get_server_dir(owner, folder)
    resolved_startup = resolve_startup_file(owner, folder, startup_file)
    runtime_kind = detect_runtime_kind(owner, folder, resolved_startup)

    child_env = os.environ.copy()
    child_env["PYTHONUNBUFFERED"] = "1"
    child_env["NODE_ENV"] = child_env.get("NODE_ENV", "production")

    if runtime_kind == "js":
        node_bin = shutil.which("node")
        npm_bin = shutil.which("npm")
        if not node_bin:
            raise RuntimeError("Node.js (node) غير مثبت على الخادم لتشغيل ملفات JavaScript")

        js_wrapper_code = r"""
const { spawnSync } = require("child_process");
const path = require("path");
const fs = require("fs");

const script = process.argv[1];
const npmBin = process.argv[2] || "npm";
const cwd = process.cwd();

function logSys(msg) {
  const line = `[AUTO-INSTALL-JS] ${msg}\n`;
  process.stdout.write(line);
  try {
    fs.appendFileSync(path.join(cwd, "server.log"), line, "utf8");
  } catch (_) {}
}

function appendInstalled(pkg) {
  try {
    const p = path.join(cwd, ".installed");
    let existing = new Set();
    if (fs.existsSync(p)) {
      fs.readFileSync(p, "utf8").split(/\r?\n/).forEach(l => {
        if (l.trim()) existing.add(l.trim());
      });
    }
    if (pkg && !existing.has(pkg)) {
      fs.appendFileSync(p, pkg + "\n", "utf8");
    }
  } catch (_) {}
}

function parseMissingModule(outputText) {
  const m1 = outputText.match(/Cannot find module '([^']+)'/);
  if (m1 && m1[1]) {
    const raw = m1[1];
    if (raw.startsWith(".") || raw.startsWith("/")) return null;
    return raw.startsWith("@") ? raw.split("/").slice(0, 2).join("/") : raw.split("/")[0];
  }
  const m2 = outputText.match(/ERR_MODULE_NOT_FOUND[\s\S]*?package '([^']+)'/);
  if (m2 && m2[1]) return m2[1];
  const m3 = outputText.match(/Cannot find package '([^']+)'/);
  if (m3 && m3[1]) return m3[1];
  return null;
}

const tried = new Set();
while (true) {
  const res = spawnSync(process.execPath, [script], {
    cwd,
    env: Object.assign({}, process.env, { FORCE_COLOR: "0" }),
    encoding: "utf8",
    maxBuffer: 10 * 1024 * 1024
  });

  const out = (res.stdout || "") + (res.stderr || "");
  if (res.stdout) process.stdout.write(res.stdout);
  if (res.stderr) process.stderr.write(res.stderr);

  if (res.error) {
    logSys(`Execution error: ${res.error.message}`);
    break;
  }

  if (res.status === 0) {
    logSys("Script exited cleanly (code 0).");
    break;
  }

  const missingPkg = parseMissingModule(out);
  if (missingPkg && !tried.has(missingPkg)) {
    tried.add(missingPkg);
    logSys(`Missing module: ${missingPkg} -> installing via ${npmBin}...`);
    const inst = spawnSync(npmBin, ["install", "--no-save", "--no-audit", "--no-fund", missingPkg], {
      cwd,
      env: process.env,
      encoding: "utf8",
      maxBuffer: 10 * 1024 * 1024
    });
    if (inst.stdout) process.stdout.write(inst.stdout);
    if (inst.stderr) process.stderr.write(inst.stderr);

    if (inst.status === 0) {
      appendInstalled(missingPkg);
      logSys(`Installed: ${missingPkg} -> restarting script...`);
      continue;
    } else {
      logSys(`Failed installing ${missingPkg} (exit code ${inst.status})`);
      break;
    }
  }

  logSys(`Process exited with code ${res.status}`);
  break;
}
"""

        log_path = os.path.join(server_dir, "server.log")
        log_file = open(log_path, "a", encoding="utf-8", errors="ignore")
        proc = subprocess.Popen(
            [node_bin, "-e", js_wrapper_code, resolved_startup, npm_bin or ""],
            cwd=server_dir,
            env=child_env,
            stdout=log_file,
            stderr=log_file,
        )
        return proc, log_file

    wrapper_code = r"""
import runpy, sys, subprocess, traceback, re, os
script = sys.argv[1]
cwd = os.getcwd()

def append_installed(pkg):
    try:
        p = os.path.join(cwd, ".installed")
        existing = set()
        if os.path.exists(p):
            with open(p, "r", encoding="utf-8", errors="ignore") as f:
                existing = set([x.strip() for x in f.read().splitlines() if x.strip()])
        if pkg and pkg not in existing:
            with open(p, "a", encoding="utf-8") as f:
                f.write(pkg + "\n")
    except Exception:
        pass

def parse_missing_name(e):
    n = getattr(e, "name", None)
    if n:
        return n.split(".")[0]
    s = str(e)
    m = re.search(r"No module named '([^']+)'", s)
    if m:
        return m.group(1).split(".")[0]
    return None

tried_pkgs = set()
while True:
    try:
        runpy.run_path(script, run_name="__main__")
        break
    except ModuleNotFoundError as e:
        pkg = parse_missing_name(e)
        if not pkg or pkg in tried_pkgs:
            traceback.print_exc()
            break
        tried_pkgs.add(pkg)
        print(f"[AUTO-INSTALL] Missing module: {pkg} -> installing...")
        try:
            subprocess.check_call([sys.executable, "-m", "pip", "install", pkg])
            append_installed(pkg)
            print(f"[AUTO-INSTALL] Installed: {pkg} ✅ -> restarting...")
            continue
        except Exception as ex:
            print(f"[AUTO-INSTALL] Failed: {ex}")
            traceback.print_exc()
            break
    except Exception:
        traceback.print_exc()
        break
"""
    log_path = os.path.join(server_dir, "server.log")
    log_file = open(log_path, "a", encoding="utf-8", errors="ignore")

    proc = subprocess.Popen(
        [sys.executable, "-u", "-c", wrapper_code, resolved_startup],
        cwd=server_dir,
        env=child_env,
        stdout=log_file,
        stderr=log_file,
    )
    return proc, log_file


def _candidate_keys(key: str, owner: str = "", folder: str = "") -> list[str]:
    keys = []
    if key:
        keys.append(key)
    if owner and folder:
        full_k = normalize_state_key(owner, folder)
        if full_k not in keys:
            keys.append(full_k)
        if folder not in keys:
            keys.append(folder)
    return keys


def stop_proc(key: str, owner: str = "", folder: str = ""):
    candidates = _candidate_keys(key, owner, folder)
    with lock:
        tuples_to_stop = []
        for k in candidates:
            t = running_procs.pop(k, None)
            if t:
                tuples_to_stop.append(t)

    for proc, logf in tuples_to_stop:
        try:
            p = psutil.Process(proc.pid)
            for child in p.children(recursive=True):
                try:
                    child.kill()
                except Exception:
                    pass
            p.kill()
        except Exception:
            try:
                proc.kill()
            except Exception:
                pass
        try:
            logf.close()
        except Exception:
            pass


# ==============================================================================
# ٨. تجميع الصفحات في index.html وإصلاح المسارات والـ API (Unified index.html)
# ==============================================================================
DEFAULT_UNIFIED_INDEX_HTML = """<!DOCTYPE html>
<html lang="ar" dir="rtl">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>𝗘𝗛𝗔𝗕 - اللوحة الموحدة</title>
  <style>
    body { font-family: Tahoma, Arial, sans-serif; background: #0f172a; color: #f8fafc; margin: 0; padding: 20px; }
    .container { max-width: 960px; margin: 0 auto; background: #1e293b; border-radius: 12px; padding: 24px; box-shadow: 0 10px 25px rgba(0,0,0,0.4); }
    .nav { display: flex; flex-wrap: wrap; gap: 10px; margin-bottom: 20px; border-bottom: 1px solid #334155; padding-bottom: 14px; }
    button { background: #2563eb; color: #fff; border: none; padding: 10px 16px; border-radius: 8px; cursor: pointer; font-weight: bold; }
    button:hover { background: #1d4ed8; }
    button.danger { background: #dc2626; }
    button.success { background: #16a34a; }
    input, select, textarea { width: 100%; padding: 10px; margin: 6px 0 12px; border-radius: 8px; border: 1px solid #475569; background: #0f172a; color: #fff; box-sizing: border-box; }
    .card { background: #0f172a; padding: 14px; border-radius: 8px; margin-bottom: 12px; border: 1px solid #334155; }
    .hidden { display: none; }
    pre { background: #020617; padding: 12px; border-radius: 8px; overflow-x: auto; direction: ltr; text-align: left; }
    .msg { padding: 10px; border-radius: 8px; margin-bottom: 12px; background: #172554; }
    a.link-pill { color: #93c5fd; word-break: break-all; }
  </style>
</head>
<body>
  <div class="container">
    <h2>🚀 𝗘𝗛𝗔𝗕 — اللوحة الموحدة (أدمن مجاني • سيرفرات • توليد روابط)</h2>
    <div id="statusMsg" class="msg hidden"></div>

    <div class="nav">
      <button onclick="switchTab('home')">📁 السيرفرات والملفات</button>
      <button onclick="switchTab('login')">🔑 تسجيل الدخول</button>
      <button onclick="switchTab('create')">➕ إنشاء حساب جديد</button>
      <button id="adminTabBtn" class="hidden" onclick="switchTab('admin')">👑 لوحة الأدمن</button>
      <button class="danger" onclick="logoutUser()">🚪 خروج</button>
    </div>

    <div id="tab-login" class="hidden">
      <h3>تسجيل الدخول</h3>
      <input id="loginUser" placeholder="اسم المستخدم" />
      <input id="loginPass" type="password" placeholder="كلمة المرور" />
      <button class="success" onclick="doLogin()">دخول</button>
    </div>

    <div id="tab-create" class="hidden">
      <h3>إنشاء حساب جديد</h3>
      <input id="regUser" placeholder="اسم المستخدم (أحرف، أرقام، _ ، .)" />
      <input id="regEmail" placeholder="البريد الإلكتروني" />
      <input id="regPass" type="password" placeholder="كلمة المرور (6 أحرف فأكثر)" />
      <input id="regPass2" type="password" placeholder="تأكيد كلمة المرور" />
      <button class="success" onclick="doCreate()">إنشاء الحساب</button>
    </div>

    <div id="tab-home">
      <h3>إضافة سيرفر جديد</h3>
      <input id="newServerName" placeholder="اسم السيرفر (مثال: my-bot)" />
      <select id="newServerType">
        <option value="Python">Python (.py)</option>
        <option value="Node.js/JS">JavaScript / Node (.js)</option>
        <option value="HTML">HTML / Web</option>
        <option value="PHP">PHP</option>
      </select>
      <button class="success" onclick="addServer()">➕ إنشاء سيرفر</button>
      <button onclick="loadServers()">🔄 تحديث القائمة</button>
      <hr />
      <h3>السيرفرات الخاصة بك</h3>
      <div id="serversList"></div>
      <div id="fileManagerBox" class="card hidden">
        <h4>إدارة ملفات السيرفر: <span id="activeServerKey"></span></h4>
        <input id="startupFileInput" placeholder="ملف التشغيل الرئيسي (مثال: main.py أو index.js)" />
        <input id="extraPathInput" placeholder="زيادة/امتداد مسار إضافي للرابط (اختياري، مثال: bot/run)" />
        <button onclick="saveStartup()">💾 حفظ ملف التشغيل وتوليد الرابط</button>
        <button class="success" onclick="serverAct('start')">▶️ تشغيل وتوليد الرابط</button>
        <button class="danger" onclick="serverAct('stop')">⏹ إيقاف</button>
        <button class="danger" onclick="serverAct('restart')">🔄 إعادة تشغيل</button>
        <button class="danger" onclick="serverAct('delete')">🗑 حذف السيرفر</button>
        <div id="generatedLinkBox" class="card hidden" style="margin-top:12px;">
          <div><b>🔗 الرابط المولّد:</b> <a id="genUrlAnchor" class="link-pill" target="_blank"></a></div>
          <div style="margin-top:8px;"><b>🌐 رابط التحويل المباشر:</b> <a id="goUrlAnchor" class="link-pill" target="_blank"></a></div>
        </div>
        <h5>الملفات والمجلدات:</h5>
        <div id="filesList"></div>
        <input id="editFilePath" placeholder="مسار الملف للتعديل أو الحفظ (مثال: main.py أو app.js)" />
        <textarea id="editFileContent" rows="8" placeholder="محتوى الملف..."></textarea>
        <button onclick="loadFileContent()">📂 فتح الملف</button>
        <button class="success" onclick="saveFileContent()">💾 حفظ الملف</button>
        <h5>الكونسول والسجل:</h5>
        <pre id="serverLogs"></pre>
      </div>
    </div>

    <div id="tab-admin" class="hidden">
      <h3>👑 لوحة إدارة الأدمن (مجانية بالكامل)</h3>
      <button onclick="loadAdminData()">🔄 تحديث بيانات الأدمن</button>
      <div id="adminStats" class="card"></div>
      <h4>المستخدمون</h4>
      <div id="adminUsers"></div>
      <h4>جميع السيرفرات</h4>
      <div id="adminServers"></div>
    </div>
  </div>

  <script>
    let currentKey = "";
    function showMsg(txt) {
      const el = document.getElementById("statusMsg");
      el.textContent = txt;
      el.classList.remove("hidden");
    }
    function switchTab(tab) {
      for (const t of ["login", "create", "home", "admin"]) {
        document.getElementById("tab-" + t).classList.add("hidden");
      }
      document.getElementById("tab-" + tab).classList.remove("hidden");
      if (tab === "home") loadServers();
      if (tab === "admin") loadAdminData();
    }
    async function doLogin() {
      const res = await fetch("/api/auth/login", {
        method: "POST",
        headers: {"Content-Type": "application/json"},
        body: JSON.stringify({
          username: document.getElementById("loginUser").value,
          password: document.getElementById("loginPass").value
        })
      });
      const d = await res.json();
      if (d.success) {
        if (d.is_admin) document.getElementById("adminTabBtn").classList.remove("hidden");
        showMsg("تم تسجيل الدخول بنجاح");
        switchTab("home");
      } else {
        showMsg("خطأ: " + (d.message || "فشل الدخول"));
      }
    }
    async function doCreate() {
      const res = await fetch("/api/auth/create", {
        method: "POST",
        headers: {"Content-Type": "application/json"},
        body: JSON.stringify({
          username: document.getElementById("regUser").value,
          email: document.getElementById("regEmail").value,
          password: document.getElementById("regPass").value,
          password2: document.getElementById("regPass2").value
        })
      });
      const d = await res.json();
      if (d.success) {
        showMsg("تم إنشاء الحساب بنجاح! API Key: " + (d.api_key || ""));
        switchTab("login");
      } else {
        showMsg("خطأ: " + (d.message || "تعذر إنشاء الحساب"));
      }
    }
    async function logoutUser() {
      await fetch("/logout");
      document.getElementById("adminTabBtn").classList.add("hidden");
      showMsg("تم تسجيل الخروج");
      switchTab("login");
    }
    async function deleteServerDirect(key) {
      if (!key) return;
      const res = await fetch("/api/bot/server/action", {
        method: "POST",
        headers: {"Content-Type": "application/json"},
        body: JSON.stringify({ folder: key, action: "delete" })
      });
      const d = await res.json();
      showMsg(d.success ? (d.message || "تم حذف السيرفر بنجاح") : ("خطأ: " + (d.message || "فشل الحذف")));
      if (currentKey === key) {
        currentKey = "";
        document.getElementById("fileManagerBox").classList.add("hidden");
      }
      loadServers();
    }
    async function loadServers() {
      const res = await fetch("/servers");
      if (res.status === 401 || res.status === 403) {
        switchTab("login");
        return;
      }
      const d = await res.json();
      const box = document.getElementById("serversList");
      box.innerHTML = "";
      for (const s of (d.servers || [])) {
        const div = document.createElement("div");
        div.className = "card";
        const linkHtml = s.generated_url ? `<br/>🔗 الرابط المولّد: <a class="link-pill" href="${s.generated_url}" target="_blank">${s.generated_url}</a>` : "";
        const btn = document.createElement("button");
        btn.textContent = "⚙️ إدارة";
        btn.setAttribute("data-key", s.key || "");
        btn.setAttribute("data-startup", s.startup_file || "");
        btn.onclick = function() {
          openServer(this.getAttribute("data-key"), this.getAttribute("data-startup"));
        };
        const delBtn = document.createElement("button");
        delBtn.textContent = "🗑 حذف";
        delBtn.className = "danger";
        delBtn.style.marginRight = "8px";
        delBtn.setAttribute("data-key", s.key || "");
        delBtn.onclick = function() {
          deleteServerDirect(this.getAttribute("data-key"));
        };
        div.innerHTML = `<b>${s.title}</b> (${s.status}) - ${s.subtitle}${linkHtml}<br/><br/>`;
        div.appendChild(btn);
        div.appendChild(delBtn);
        box.appendChild(div);
      }
    }
    async function addServer() {
      const name = document.getElementById("newServerName").value;
      const server_type = document.getElementById("newServerType").value;
      const res = await fetch("/add", {
        method: "POST",
        headers: {"Content-Type": "application/json"},
        body: JSON.stringify({name, server_type})
      });
      const d = await res.json();
      showMsg(d.success ? "تم إنشاء السيرفر" : ("خطأ: " + d.message));
      loadServers();
    }
    function openServer(key, startup) {
      currentKey = key;
      document.getElementById("fileManagerBox").classList.remove("hidden");
      document.getElementById("activeServerKey").textContent = key;
      document.getElementById("startupFileInput").value = startup;
      refreshServerDetails();
    }
    async function updateGeneratedLinkUI() {
      if (!currentKey) return;
      const f = document.getElementById("startupFileInput").value || "";
      const sub = document.getElementById("extraPathInput").value || "";
      const q = `/api/bot/js-link?folder=${encodeURIComponent(currentKey)}&file=${encodeURIComponent(f)}&subpath=${encodeURIComponent(sub)}`;
      const r = await fetch(q);
      if (r.ok) {
        const d = await r.json();
        if (d.success && d.generated_url) {
          document.getElementById("generatedLinkBox").classList.remove("hidden");
          const a1 = document.getElementById("genUrlAnchor");
          const a2 = document.getElementById("goUrlAnchor");
          a1.href = d.generated_url;
          a1.textContent = d.generated_url;
          a2.href = d.google_jump_url;
          a2.textContent = d.google_jump_url;
        }
      }
    }
    async function saveStartup() {
      const f = document.getElementById("startupFileInput").value;
      await fetch("/server/set-startup/" + encodeURIComponent(currentKey), {
        method: "POST",
        headers: {"Content-Type": "application/json"},
        body: JSON.stringify({file: f})
      });
      await updateGeneratedLinkUI();
      showMsg("تم حفظ ملف التشغيل وتوليد الرابط");
    }
    async function serverAct(act) {
      if (act === "delete") {
        await deleteServerDirect(currentKey);
        return;
      }
      const f = document.getElementById("startupFileInput").value || "";
      const sub = document.getElementById("extraPathInput").value || "";
      const res = await fetch("/server/action/" + encodeURIComponent(currentKey) + "/" + act, {
        method: "POST",
        headers: {"Content-Type": "application/json"},
        body: JSON.stringify({file: f, subpath: sub})
      });
      const d = await res.json();
      if (d.generated_url) {
        showMsg(`تم تنفيذ ${act} — الرابط المولّد: ${d.generated_url}`);
      } else {
        showMsg(d.success ? ("تم تنفيذ " + act) : ("خطأ: " + d.message));
      }
      await updateGeneratedLinkUI();
      refreshServerDetails();
    }
    async function refreshServerDetails() {
      if (!currentKey) return;
      await updateGeneratedLinkUI();
      const stRes = await fetch("/server/stats/" + encodeURIComponent(currentKey));
      if (stRes.ok) {
        const st = await stRes.json();
        document.getElementById("serverLogs").textContent = st.logs || "";
      }
      const flRes = await fetch("/files/list/" + encodeURIComponent(currentKey));
      if (flRes.ok) {
        const fl = await flRes.json();
        const names = [...(fl.dirs || []).map(x => "[DIR] " + x.name), ...(fl.files || []).map(x => x.name + " (" + x.size + ")")];
        document.getElementById("filesList").textContent = names.join(" | ") || "فارغ";
      }
    }
    async function loadFileContent() {
      const file = document.getElementById("editFilePath").value;
      const res = await fetch("/files/content/" + encodeURIComponent(currentKey) + "?file=" + encodeURIComponent(file));
      const d = await res.json();
      document.getElementById("editFileContent").value = d.content || "";
    }
    async function saveFileContent() {
      const file = document.getElementById("editFilePath").value;
      const content = document.getElementById("editFileContent").value;
      const res = await fetch("/files/save/" + encodeURIComponent(currentKey), {
        method: "POST",
        headers: {"Content-Type": "application/json"},
        body: JSON.stringify({file, content})
      });
      const d = await res.json();
      showMsg(d.success ? "تم حفظ الملف" : ("خطأ: " + d.message));
      refreshServerDetails();
    }
    async function loadAdminData() {
      const stRes = await fetch("/api/admin/quickstats");
      if (stRes.status === 403 || stRes.status === 401) {
        showMsg("صلاحية الأدمن مطلوبة");
        return;
      }
      const st = await stRes.json();
      document.getElementById("adminStats").textContent = JSON.stringify(st.stats || {});
      const uRes = await fetch("/api/admin/users");
      const uData = await uRes.json();
      document.getElementById("adminUsers").innerHTML = (uData.users || []).map(u =>
        `<div class="card">${u.username} | ${u.email} | نشط: ${u.active} | مميز: ${u.premium} | سيرفرات: ${u.servers}</div>`
      ).join("");
      const sRes = await fetch("/api/admin/servers");
      const sData = await sRes.json();
      document.getElementById("adminServers").innerHTML = (sData.servers || []).map(s =>
        `<div class="card">${s.key} | الحالة: ${s.status}</div>`
      ).join("");
    }
    const initMode = window.__INITIAL_TAB__ || "home";
    switchTab(initMode);
  </script>
</body>
</html>
"""


def ensure_index_html_exists():
    if not os.path.exists(INDEX_HTML_PATH):
        with open(INDEX_HTML_PATH, "w", encoding="utf-8") as f:
            f.write(DEFAULT_UNIFIED_INDEX_HTML)


def render_unified_index(tab_mode: str = "home"):
    ensure_index_html_exists()
    with open(INDEX_HTML_PATH, "r", encoding="utf-8", errors="ignore") as f:
        html_content = f.read()

    effective_tab = tab_mode
    if tab_mode == "admin" and not is_admin_session():
        effective_tab = "login" if not session.get("user") else "home"
    elif tab_mode == "home" and not session.get("user"):
        effective_tab = "login"

    inject_script = f"<script>window.__INITIAL_TAB__ = {json.dumps(effective_tab)};</script>"
    if "</head>" in html_content:
        html_content = html_content.replace("</head>", inject_script + "\n</head>", 1)
    else:
        html_content = inject_script + "\n" + html_content

    return Response(html_content, mimetype="text/html; charset=utf-8")


def api_login_required(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        if not session.get("user"):
            return jsonify({"success": False, "message": "Authentication required", "redirect": "/login"}), 401
        return fn(*args, **kwargs)
    return wrapper


def api_admin_required(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        if not session.get("user"):
            return jsonify({"success": False, "message": "Authentication required", "redirect": "/login"}), 401
        if not is_admin_session():
            return jsonify({"success": False, "message": "Admin only"}), 403
        return fn(*args, **kwargs)
    return wrapper


def _lookup_running_state(keys_to_check: list[str], banned: bool) -> str:
    if banned:
        return "Banned"
    with lock:
        for k in keys_to_check:
            proc_tuple = running_procs.get(k)
            if proc_tuple:
                proc, _logf = proc_tuple
                if proc.poll() is None and psutil.pid_exists(proc.pid):
                    try:
                        p = psutil.Process(proc.pid)
                        if p.is_running() and p.status() != psutil.STATUS_ZOMBIE:
                            return "Running"
                    except Exception:
                        pass
            if k in server_states and server_states[k] in ("Installing", "Starting", "Running"):
                return server_states[k]
        for k in keys_to_check:
            if k in server_states:
                return server_states[k]
    return "Offline"


def list_all_servers_for_admin():
    servers = []
    if not os.path.isdir(USERS_ROOT):
        return servers
    for owner in sorted(os.listdir(USERS_ROOT)):
        root = get_user_servers_root(owner)
        if not os.path.isdir(root):
            continue
        for folder in sorted(os.listdir(root)):
            server_dir = get_server_dir(owner, folder)
            if not os.path.isdir(server_dir):
                continue
            meta = read_meta(owner, folder)
            banned = bool(meta.get("banned", False))
            key = normalize_state_key(owner, folder)
            st = _lookup_running_state([key, folder], banned)
            links = build_generated_server_url(owner, folder, meta.get("startup_file", ""))
            servers.append({
                "title": meta.get("display_name", folder),
                "folder": folder,
                "owner": owner,
                "key": key,
                "subtitle": f"Owner: {owner}",
                "startup_file": meta.get("startup_file", ""),
                "generated_url": meta.get("generated_url") or links["generated_url"],
                "google_jump_url": meta.get("google_jump_url") or links["google_jump_url"],
                "status": st,
            })
    return servers


@app.route("/api/ping", methods=["GET"])
def api_ping():
    return jsonify({
        "success": True,
        "status": "alive",
        "timestamp": _utc_now_iso(),
    }), 200


@app.route("/healthz", methods=["GET"])
def healthz():
    return jsonify({"status": "ok"}), 200


def _keep_alive_worker():
    site_url = (
        os.environ.get("RENDER_EXTERNAL_URL")
        or os.environ.get("PUBLIC_API_URL")
        or ""
    ).strip().rstrip("/")

    if not site_url:
        logger.warning("⚠️ Keep-Alive متوقف: لم يتم ضبط RENDER_EXTERNAL_URL أو PUBLIC_API_URL")
        return

    if not site_url.startswith("http"):
        site_url = f"https://{site_url}"

    target_url = f"{site_url}/api/ping"
    interval_sec = int(os.environ.get("KEEP_ALIVE_INTERVAL", "300"))
    logger.info("📡 تفعيل Keep-Alive كل %s ثانية نحو: %s", interval_sec, target_url)

    while True:
        time.sleep(interval_sec)
        for attempt in range(3):
            try:
                resp = requests.get(
                    target_url,
                    headers={
                        "User-Agent": "EHAB-HOST-KEEP-ALIVE/1.0",
                        "X-Keep-Alive": "true",
                    },
                    timeout=15,
                )
                if resp.status_code == 200:
                    logger.info("✅ Keep-Alive Ping ناجح (%s)", target_url)
                    break
                logger.warning("⚠️ Keep-Alive استجابة غير متوقعة: %s", resp.status_code)
            except Exception as e:
                logger.warning("⚠️ محاولة Keep-Alive (%s/3) فشلت: %s", attempt + 1, e)
            if attempt < 2:
                time.sleep(5)


def _start_keep_alive_once():
    if os.environ.get("ENABLE_KEEP_ALIVE", "1") == "1":
        if not any(t.name == "EhabKeepAliveThread" for t in threading.enumerate()):
            t = threading.Thread(target=_keep_alive_worker, name="EhabKeepAliveThread", daemon=True)
            t.start()


def list_servers_for_user(username: str):
    ensure_user_dirs(username)
    root = get_user_servers_root(username)
    servers = []
    if not os.path.isdir(root):
        return servers
    for folder in sorted(os.listdir(root)):
        server_dir = get_server_dir(username, folder)
        if not os.path.isdir(server_dir):
            continue
        meta = read_meta(username, folder)
        banned = bool(meta.get("banned", False))
        key = normalize_state_key(username, folder)
        st = _lookup_running_state([key, folder], banned)
        links = build_generated_server_url(username, folder, meta.get("startup_file", ""))
        servers.append({
            "title": meta.get("display_name", folder),
            "folder": folder,
            "owner": username,
            "key": key,
            "subtitle": f"Owner: {username}",
            "startup_file": meta.get("startup_file", ""),
            "generated_url": meta.get("generated_url") or links["generated_url"],
            "google_jump_url": meta.get("google_jump_url") or links["google_jump_url"],
            "status": st,
        })
    return servers


def _render_js_runner_page(owner: str, folder: str, startup_file: str = "", subpath: str = "", auto_google: bool = False):
    server_dir = get_server_dir(owner, folder)
    if not os.path.isdir(server_dir):
        return jsonify({"success": False, "message": "السيرفر غير موجود"}), 404

    meta = read_meta(owner, folder)
    bot_title = meta.get("display_name") or folder
    resolved_file = startup_file or resolve_startup_file(owner, folder, meta.get("startup_file") or "index.js")
    links = refresh_server_js_link(owner, folder, resolved_file, subpath=subpath, req=request)
    sync_active_server_for_owner(owner, folder, startup_file=resolved_file, req=request)
    google_url = links["google_target"]
    gen_url = links["generated_url"]

    state_key = normalize_state_key(owner, folder)
    cur_state = _lookup_running_state([state_key, folder], bool(meta.get("banned", False)))
    if not meta.get("banned", False) and cur_state != "Running":
        log_append(state_key, f"[JS-LINK] Auto-starting server for file: {resolved_file} | URL: {gen_url}\n")
        t = threading.Thread(target=background_start, args=(state_key, owner, folder, resolved_file, subpath), daemon=True)
        t.start()

    if auto_google:
        return redirect(google_url, code=302)

    html = f"""<!DOCTYPE html>
<html lang="ar" dir="rtl">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>تشغيل البوت - {bot_title}</title>
  <style>
    body {{
      font-family: Tahoma, Arial, sans-serif;
      background: #ffffff;
      color: #111827;
      margin: 0;
      padding: 40px 18px;
      text-align: center;
    }}
    .box {{
      max-width: 640px;
      margin: 0 auto;
      line-height: 1.9;
    }}
    .title {{
      font-size: 20px;
      font-weight: bold;
      margin-bottom: 10px;
    }}
    .meta {{
      font-size: 16px;
      font-weight: bold;
      margin: 6px 0;
    }}
    .url-box {{
      margin-top: 18px;
      padding: 12px;
      background: #f3f4f6;
      border-radius: 8px;
      word-break: break-all;
      font-size: 13px;
    }}
    a.btn {{
      display: inline-block;
      margin-top: 14px;
      background: #1a73e8;
      color: #fff;
      text-decoration: none;
      padding: 10px 20px;
      border-radius: 8px;
      font-weight: bold;
    }}
  </style>
</head>
<body>
  <div class="box">
    <div class="title">✨ تم بنجاح تشغيل الخادم والبوت ✨</div>
    <div class="meta">🤖 البوت : {bot_title}</div>
    <div class="meta">@Y_20_20 : المطور</div>
    <div class="url-box">
      <div><b>ملف التشغيل:</b> {resolved_file}</div>
      <div><b>الرابط المولّد:</b> <a href="{gen_url}">{gen_url}</a></div>
    </div>
    <a class="btn" id="goGoogleBtn" href="{google_url}">الانتقال إلى جوجل</a>
  </div>
  <script>
    setTimeout(function() {{
      window.location.href = {json.dumps(google_url)};
    }}, 800);
  </script>
</body>
</html>"""
    return Response(html, mimetype="text/html; charset=utf-8")


@app.route("/js/<owner>/<folder>", methods=["GET"])
@app.route("/js/<owner>/<folder>/<path:subpath>", methods=["GET"])
def js_server_link_route(owner, folder, subpath=""):
    safe_o = re.sub(r"[^a-zA-Z0-9_.-]", "", owner or "")
    safe_f = re.sub(r"[^a-zA-Z0-9_.-]", "", folder or "")
    if not safe_o or not safe_f:
        return jsonify({"success": False, "message": "معرّف السيرفر غير صالح"}), 400
    startup_file = (request.args.get("file") or "").strip()
    auto_google = (request.args.get("redirect_google") or "").strip() in ("1", "true", "yes")
    return _render_js_runner_page(safe_o, safe_f, startup_file=startup_file, subpath=subpath, auto_google=auto_google)


@app.route("/js/go/<owner>/<folder>", methods=["GET"])
@app.route("/js/go/<owner>/<folder>/<path:subpath>", methods=["GET"])
def js_server_google_jump_route(owner, folder, subpath=""):
    safe_o = re.sub(r"[^a-zA-Z0-9_.-]", "", owner or "")
    safe_f = re.sub(r"[^a-zA-Z0-9_.-]", "", folder or "")
    if not safe_o or not safe_f:
        return jsonify({"success": False, "message": "معرّف السيرفر غير صالح"}), 400
    startup_file = (request.args.get("file") or "").strip()
    return _render_js_runner_page(safe_o, safe_f, startup_file=startup_file, subpath=subpath, auto_google=True)


@app.route("/", methods=["GET"])
def index_page():
    return render_unified_index("home")


@app.route("/login", methods=["GET"])
def login_page():
    return render_unified_index("login")


@app.route("/create", methods=["GET"])
def create_account_page():
    return render_unified_index("create")


@app.route("/home", methods=["GET"])
def home_page():
    return render_unified_index("home")


@app.route("/admin", methods=["GET"])
def admin_page():
    return render_unified_index("admin")


@app.route("/api/auth/login", methods=["POST"])
def api_login():
    data = request.get_json(silent=True) or request.form
    username = (data.get("username") or "").strip()
    password = (data.get("password") or "").strip()

    if username == ADMIN_USERNAME and password == ADMIN_PASSWORD:
        session["user"] = {
            "username": ADMIN_USERNAME,
            "email": f"{ADMIN_USERNAME}@local.admin",
            "is_admin": True,
            "premium": True,
            "free_admin": True,
        }
        ensure_user_dirs(ADMIN_USERNAME)
        return jsonify({"success": True, "username": ADMIN_USERNAME, "is_admin": True, "premium": True, "free_admin": True, "redirect": "/"})

    db = load_users()
    u = find_user(db, username)
    if u and check_password_hash(u.get("password_hash", ""), password):
        if not u.get("active", True):
            return jsonify({"success": False, "message": "الحساب غير نشط أو معطل"}), 403
        session["user"] = {
            "username": u["username"],
            "email": u.get("email", ""),
            "is_admin": False,
            "premium": bool(u.get("premium", False)),
            "free_admin": False,
        }
        ensure_user_dirs(u["username"])
        return jsonify({"success": True, "username": u["username"], "is_admin": False, "premium": bool(u.get("premium", False)), "redirect": "/"})

    return jsonify({"success": False, "message": "اسم المستخدم أو كلمة المرور غير صحيحة"}), 401


@app.route("/api/auth/create", methods=["POST"])
def api_create():
    data = request.get_json(silent=True) or request.form
    username = (data.get("username") or "").strip()
    email = (data.get("email") or "").strip()
    password = (data.get("password") or "").strip()
    password2 = (data.get("password2") or "").strip()

    if not re.match(r"^[a-zA-Z0-9_.-]{3,32}$", username):
        return jsonify({"success": False, "message": "اسم المستخدم يجب أن يكون من 3 إلى 32 حرفاً وأرقاماً (_ أو - أو .)"})
    if not email or "@" not in email or "." not in email.split("@")[-1]:
        return jsonify({"success": False, "message": "البريد الإلكتروني غير صالح"})
    if len(password) < 6:
        return jsonify({"success": False, "message": "كلمة المرور يجب أن تكون 6 أحرف على الأقل"})
    if password2 and password != password2:
        return jsonify({"success": False, "message": "كلمتا المرور غير متطابقتين"})
    if username.lower() == ADMIN_USERNAME.lower():
        return jsonify({"success": False, "message": "هذا الاسم محجوز"})

    db = load_users()
    if find_user(db, username):
        return jsonify({"success": False, "message": "اسم المستخدم مستخدم بالفعل"})

    api_key = "MK-" + uuid.uuid4().hex.upper()
    new_user = {
        "username": username,
        "email": email,
        "password_hash": generate_password_hash(password),
        "api_key": api_key,
        "active": True,
        "premium": False,
        "created_at": datetime.utcnow().isoformat() + "Z",
    }
    db.setdefault("users", []).append(new_user)
    save_users(db)
    ensure_user_dirs(username)

    return jsonify({"success": True, "message": "تم إنشاء الحساب بنجاح", "api_key": api_key, "redirect": "/login"})


@app.route("/logout", methods=["GET", "POST"])
def logout_route():
    session.pop("user", None)
    if request.method == "POST":
        return jsonify({"success": True, "redirect": "/login"})
    return redirect("/login")


@app.route("/servers", methods=["GET"])
@api_login_required
def get_servers():
    if is_admin_session():
        return jsonify({"servers": list_all_servers_for_admin(), "is_admin": True})
    u = current_username()
    return jsonify({"servers": list_servers_for_user(u), "is_admin": False})


@app.route("/add", methods=["POST"])
@api_login_required
def add_server():
    data = request.get_json(silent=True) or {}
    raw_name = (data.get("name") or "").strip()
    server_type = (data.get("server_type") or "Python").strip()

    folder = sanitize_folder_name(raw_name)
    if not folder:
        return jsonify({"success": False, "message": "اسم السيرفر غير صالح"})

    owner = current_username() or ADMIN_USERNAME
    ensure_user_dirs(owner)

    if not is_admin_session():
        cur_count = len(list_servers_for_user(owner))
        limit = get_user_limit(owner)
        if cur_count >= limit:
            return jsonify({"success": False, "message": f"وصلت للحد الأقصى لعدد السيرفرات ({limit}). ترقية الحساب تمنحك حتى 1000 سيرفر."})

    server_dir = get_server_dir(owner, folder)
    if not is_path_safe(USERS_ROOT, server_dir):
        return jsonify({"success": False, "message": "مسار غير آمن"}), 400

    if os.path.exists(server_dir):
        return jsonify({"success": False, "message": "السيرفر موجود بالفعل"})

    os.makedirs(server_dir, exist_ok=True)
    display_title = safe_name(raw_name) or folder
    default_startup = "index.js" if ("js" in server_type.lower() or "node" in server_type.lower()) else "main.py"
    links = build_generated_server_url(owner, folder, default_startup, req=request)
    meta_data = {
        "display_name": display_title,
        "startup_file": default_startup,
        "owner": owner,
        "banned": False,
        "generated_url": links["generated_url"],
        "google_jump_url": links["google_jump_url"],
    }
    _atomic_write_json_raw(os.path.join(server_dir, "meta.json"), meta_data)

    if default_startup == "index.js":
        sample_path = os.path.join(server_dir, "index.js")
        if not os.path.exists(sample_path):
            with open(sample_path, "w", encoding="utf-8") as f:
                f.write("console.log('Server initialized successfully');\n")
    else:
        sample_path = os.path.join(server_dir, "main.py")
        if not os.path.exists(sample_path):
            with open(sample_path, "w", encoding="utf-8") as f:
                f.write("print('Server initialized successfully')\n")

    types_db = _read_json(SERVER_TYPES_DB, {"types": {}})
    types_db.setdefault("types", {})[normalize_state_key(owner, folder)] = server_type
    _atomic_write_json(SERVER_TYPES_DB, types_db)

    set_state(normalize_state_key(owner, folder), "Offline")
    sync_active_server_for_owner(owner, folder, startup_file=default_startup, req=request)
    return jsonify({
        "success": True,
        "folder": folder,
        "key": normalize_state_key(owner, folder),
        "generated_url": links["generated_url"],
        "google_jump_url": links["google_jump_url"],
    })


def background_start(state_key: str, owner: str, folder: str, startup_file: str, subpath: str = ""):
    try:
        meta = read_meta(owner, folder)
        if meta.get("banned", False):
            set_state(state_key, "Banned")
            log_append(state_key, "[SYSTEM] Server is BANNED by admin.\n")
            return

        set_state(state_key, "Installing")
        ensure_requirements_installed(owner, folder)

        set_state(state_key, "Starting")
        eff_startup = startup_file or meta.get("startup_file") or "main.py"
        links = refresh_server_js_link(owner, folder, startup_file=eff_startup, subpath=subpath)
        sync_active_server_for_owner(owner, folder, startup_file=eff_startup)
        log_append(state_key, f"[SYSTEM] Starting {eff_startup}... | Generated Link: {links['generated_url']}\n")
        proc, logf = start_with_autoinstall(owner, folder, eff_startup)

        with lock:
            running_procs[state_key] = (proc, logf)
            running_procs[folder] = (proc, logf)

        time.sleep(0.7)
        if proc.poll() is None:
            set_state(state_key, "Running")
            log_append(state_key, f"[SYSTEM] Process running (PID={proc.pid}) ✅\n")
        else:
            set_state(state_key, "Offline")
            log_append(state_key, f"[SYSTEM] Process exited with code {proc.returncode}\n")
    except Exception as e:
        set_state(state_key, "Offline")
        log_append(state_key, f"[SYSTEM] Error starting server: {e}\n")


@app.route("/server/action/<path:key>/<act>", methods=["POST"])
@api_login_required
def server_action(key, act):
    try:
        owner, folder = parse_server_key(key, allow_admin=True)
    except ValueError as e:
        return jsonify({"success": False, "message": "Forbidden" if str(e) == "forbidden" else "Invalid server key"}), 403 if str(e) == "forbidden" else 400

    server_dir = get_server_dir(owner, folder)
    if not os.path.isdir(server_dir):
        return jsonify({"success": False, "message": "السيرفر غير موجود"}), 404

    meta = read_meta(owner, folder)
    state_key = normalize_state_key(owner, folder)
    req_data = request.get_json(silent=True) or {}
    req_file = (req_data.get("file") or "").strip()
    req_subpath = (req_data.get("subpath") or "").strip()
    eff_startup = req_file or meta.get("startup_file") or "main.py"
    links = refresh_server_js_link(owner, folder, startup_file=eff_startup, subpath=req_subpath, req=request)
    sync_active_server_for_owner(owner, folder, startup_file=eff_startup, req=request)

    if meta.get("banned", False) and act in ("start", "restart"):
        set_state(state_key, "Banned")
        return jsonify({"success": False, "message": "هذا السيرفر محظور من الإدارة ولا يمكن تشغيله"})

    if act == "start":
        t = threading.Thread(target=background_start, args=(state_key, owner, folder, eff_startup, req_subpath), daemon=True)
        t.start()
        return jsonify({
            "success": True,
            "message": "جاري تشغيل السيرفر...",
            "generated_url": links["generated_url"],
            "google_jump_url": links["google_jump_url"],
        })

    if act == "stop":
        stop_proc(state_key, owner, folder)
        set_state(state_key, "Offline")
        log_append(state_key, "[SYSTEM] Server stopped by user.\n")
        return jsonify({"success": True, "message": "تم إيقاف السيرفر", "generated_url": links["generated_url"]})

    if act == "restart":
        stop_proc(state_key, owner, folder)
        set_state(state_key, "Offline")
        log_append(state_key, "[SYSTEM] Restarting server...\n")
        t = threading.Thread(target=background_start, args=(state_key, owner, folder, eff_startup, req_subpath), daemon=True)
        t.start()
        return jsonify({
            "success": True,
            "message": "جاري إعادة تشغيل السيرفر...",
            "generated_url": links["generated_url"],
            "google_jump_url": links["google_jump_url"],
        })

    if act == "delete":
        stop_proc(state_key, owner, folder)
        if is_path_safe(USERS_ROOT, server_dir):
            shutil.rmtree(server_dir, ignore_errors=True)
        with lock:
            for ck in _candidate_keys(state_key, owner, folder):
                server_states.pop(ck, None)
                running_procs.pop(ck, None)
        return jsonify({"success": True, "message": "تم حذف السيرفر"})

    return jsonify({"success": False, "message": "إجراء غير معروف"}), 400


@app.route("/server/set-startup/<path:key>", methods=["POST"])
@api_login_required
def set_startup(key):
    try:
        owner, folder = parse_server_key(key, allow_admin=True)
    except Exception:
        return jsonify({"success": False, "message": "Invalid server key"}), 400

    data = request.get_json(silent=True) or {}
    fname = (data.get("file") or "").strip().lstrip("/")
    if not fname or ".." in fname.split("/"):
        return jsonify({"success": False, "message": "اسم ملف غير صالح"})

    server_dir = get_server_dir(owner, folder)
    if not os.path.isdir(server_dir):
        return jsonify({"success": False, "message": "السيرفر غير موجود"}), 404

    meta = read_meta(owner, folder)
    meta["startup_file"] = fname
    write_meta(owner, folder, meta)
    links = refresh_server_js_link(owner, folder, startup_file=fname, req=request)
    sync_active_server_for_owner(owner, folder, startup_file=fname, req=request)
    return jsonify({
        "success": True,
        "startup_file": fname,
        "generated_url": links["generated_url"],
        "google_jump_url": links["google_jump_url"],
    })


@app.route("/server/stats/<path:key>", methods=["GET"])
@api_login_required
def server_stats(key):
    try:
        owner, folder = parse_server_key(key, allow_admin=True)
    except Exception:
        return jsonify({"success": False, "message": "Invalid server key"}), 400

    server_dir = get_server_dir(owner, folder)
    if not os.path.isdir(server_dir):
        return jsonify({"success": False, "message": "السيرفر غير موجود"}), 404

    meta = read_meta(owner, folder)
    state_key = normalize_state_key(owner, folder)
    st = _lookup_running_state([state_key, folder], bool(meta.get("banned", False)))

    logs_text = ""
    log_path = os.path.join(server_dir, "server.log")
    if os.path.exists(log_path):
        try:
            with open(log_path, "r", encoding="utf-8", errors="ignore") as f:
                logs_text = f.read()[-12000:]
        except Exception:
            logs_text = ""

    return jsonify({
        "success": True,
        "status": st,
        "cpu": 0.0,
        "ram": "0 MB",
        "uptime": "0s",
        "logs": logs_text,
    })


@app.route("/files/list/<path:key>", methods=["GET"])
@api_login_required
def files_list(key):
    rel = request.args.get("path", "")
    try:
        target = safe_join_server_path(key, rel)
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 400

    if not os.path.exists(target) or not os.path.isdir(target):
        return jsonify({"success": False, "message": "المجلد غير موجود"}), 404

    dirs = []
    files = []
    for entry in sorted(os.listdir(target)):
        if entry == "meta.json":
            continue
        full = os.path.join(target, entry)
        if os.path.isdir(full):
            dirs.append({"name": entry})
        else:
            try:
                sz = os.path.getsize(full)
            except Exception:
                sz = 0
            files.append({"name": entry, "size": sz})

    return jsonify({"success": True, "dirs": dirs, "files": files})


@app.route("/files/content/<path:key>", methods=["GET"])
@api_login_required
def file_content_route(key):
    rel = request.args.get("file", "")
    try:
        target = safe_join_server_path(key, rel)
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 400

    if not os.path.isfile(target):
        return jsonify({"success": False, "message": "الملف غير موجود"}), 404

    try:
        with open(target, "r", encoding="utf-8", errors="replace") as f:
            content = f.read()
        return jsonify({"success": True, "content": content})
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500


@app.route("/files/save/<path:key>", methods=["POST"])
@api_login_required
def file_save_route(key):
    data = request.get_json(silent=True) or {}
    rel = data.get("file", "")
    content = data.get("content", "")
    try:
        target = safe_join_server_path(key, rel)
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 400

    try:
        os.makedirs(os.path.dirname(target), exist_ok=True)
        with open(target, "w", encoding="utf-8") as f:
            f.write(content)
        return jsonify({"success": True})
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500


@app.route("/api/admin/quickstats", methods=["GET"])
@api_admin_required
def api_admin_quickstats():
    db = load_users()
    users_list = db.get("users", [])
    total_users = len(users_list)
    active_users = sum(1 for u in users_list if u.get("active", True))
    premium_users = sum(1 for u in users_list if u.get("premium", False))
    all_srvs = list_all_servers_for_admin()
    running_srvs = sum(1 for s in all_srvs if s.get("status") == "Running")
    return jsonify({
        "success": True,
        "stats": {
            "total_users": total_users,
            "active_users": active_users,
            "premium_users": premium_users,
            "total_servers": len(all_srvs),
            "running_servers": running_srvs,
        },
    })


@app.route("/api/admin/users", methods=["GET"])
@api_admin_required
def api_admin_users():
    db = load_users()
    out = []
    for u in db.get("users", []):
        uname = u.get("username", "")
        out.append({
            "username": uname,
            "email": u.get("email", ""),
            "active": bool(u.get("active", True)),
            "premium": bool(u.get("premium", False)),
            "servers": len(list_servers_for_user(uname)),
        })
    return jsonify({"success": True, "users": out})


@app.route("/api/admin/servers", methods=["GET"])
@api_admin_required
def api_admin_servers():
    return jsonify({"success": True, "servers": list_all_servers_for_admin()})


def _find_server_by_folder_or_key(folder_or_key: str, user_info: dict = None):
    raw = (folder_or_key or "").strip()
    if not raw:
        return None, None
    default_owner = (user_info or {}).get("username", "") or current_username()
    is_adm = bool((user_info or {}).get("is_admin")) or is_admin_session()

    try:
        owner, folder = parse_server_key(raw, allow_admin=True, default_owner=default_owner, force_admin=is_adm)
        if os.path.isdir(get_server_dir(owner, folder)):
            return owner, folder
    except Exception:
        pass

    if is_adm and os.path.isdir(USERS_ROOT):
        for candidate_owner in os.listdir(USERS_ROOT):
            if os.path.isdir(get_server_dir(candidate_owner, raw)):
                return candidate_owner, raw
    return None, None


@app.route("/api/bot/js-link", methods=["GET"])
def api_bot_js_link():
    api_key = (request.headers.get("X-API-Key") or request.args.get("api_key") or "").strip()
    user_info = resolve_user_for_api(api_key)
    folder_arg = (request.args.get("folder") or "").strip()
    startup_arg = (request.args.get("file") or "").strip()
    subpath_arg = (request.args.get("subpath") or "").strip()

    owner, folder = _find_server_by_folder_or_key(folder_arg, user_info)
    if not owner or not folder:
        active_db = _read_json(os.path.join(DATA_DIR, "active_servers.json"), {"by_owner": {}, "last_selected": None})
        owner_hint = (user_info or {}).get("username") or current_username()
        picked = active_db.get("by_owner", {}).get(owner_hint) or active_db.get("last_selected")
        if picked and picked.get("owner") and picked.get("folder"):
            owner, folder = picked["owner"], picked["folder"]
            if not startup_arg:
                startup_arg = picked.get("startup_file") or ""

    if not owner or not folder:
        all_srvs = list_all_servers_for_admin()
        if all_srvs:
            owner = all_srvs[0]["owner"]
            folder = all_srvs[0]["folder"]
            if not startup_arg:
                startup_arg = all_srvs[0].get("startup_file") or ""
        else:
            links = build_generated_server_url(ADMIN_USERNAME, "default-server", startup_arg or "index.js", subpath=subpath_arg, req=request)
            return jsonify({
                "success": True,
                "folder": "default-server",
                "owner": ADMIN_USERNAME,
                "generated_url": links["generated_url"],
                "google_jump_url": links["google_jump_url"],
                "google_target": links["google_target"],
            })

    meta = read_meta(owner, folder)
    eff_file = startup_arg or resolve_startup_file(owner, folder, meta.get("startup_file") or "index.js")
    links = refresh_server_js_link(owner, folder, startup_file=eff_file, subpath=subpath_arg, req=request)
    sync_active_server_for_owner(owner, folder, startup_file=eff_file, req=request)
    return jsonify({
        "success": True,
        "owner": owner,
        "folder": folder,
        "key": normalize_state_key(owner, folder),
        "startup_file": eff_file,
        "generated_url": links["generated_url"],
        "google_jump_url": links["google_jump_url"],
        "google_target": links["google_target"],
    })


@app.route("/api/bot/server/action", methods=["POST"])
def api_bot_server_action():
    data = request.get_json(silent=True) or {}
    api_key = (request.headers.get("X-API-Key") or data.get("api_key") or "").strip()
    user_info = resolve_user_for_api(api_key)

    folder_raw = (data.get("folder") or data.get("key") or "").strip()
    act = (data.get("action") or "").strip().lower()
    if act not in ("start", "stop", "restart", "delete", "status"):
        return jsonify({"success": False, "message": "إجراء غير صالح"}), 400

    owner, folder = _find_server_by_folder_or_key(folder_raw, user_info)
    if not owner or not folder:
        return jsonify({"success": False, "message": "السيرفر غير موجود"}), 404

    state_key = normalize_state_key(owner, folder)
    server_dir = get_server_dir(owner, folder)
    meta = read_meta(owner, folder)

    if act == "status":
        st = _lookup_running_state([state_key, folder], bool(meta.get("banned", False)))
        links = build_generated_server_url(owner, folder, meta.get("startup_file", ""), req=request)
        return jsonify({
            "success": True,
            "folder": folder,
            "owner": owner,
            "key": state_key,
            "status": st,
            "generated_url": meta.get("generated_url") or links["generated_url"],
            "google_jump_url": meta.get("google_jump_url") or links["google_jump_url"],
        })

    if act == "delete":
        stop_proc(state_key, owner, folder)
        if is_path_safe(USERS_ROOT, server_dir):
            shutil.rmtree(server_dir, ignore_errors=True)
        with lock:
            for ck in _candidate_keys(state_key, owner, folder):
                server_states.pop(ck, None)
                running_procs.pop(ck, None)
        return jsonify({"success": True, "message": f"تم حذف السيرفر {folder} بنجاح"})

    eff_startup = (data.get("file") or "").strip() or resolve_startup_file(owner, folder, meta.get("startup_file") or "index.js")
    req_subpath = (data.get("subpath") or "").strip()
    links = refresh_server_js_link(owner, folder, startup_file=eff_startup, subpath=req_subpath, req=request)
    sync_active_server_for_owner(owner, folder, startup_file=eff_startup, req=request)

    if act in ("start", "restart"):
        if meta.get("banned", False):
            set_state(state_key, "Banned")
            return jsonify({"success": False, "message": "السيرفر محظور من الإدارة"}), 403
        if act == "restart":
            stop_proc(state_key, owner, folder)
            set_state(state_key, "Offline")
        t = threading.Thread(target=background_start, args=(state_key, owner, folder, eff_startup, req_subpath), daemon=True)
        t.start()
        return jsonify({
            "success": True,
            "message": f"تم تنفيذ {act} للسيرفر {folder}",
            "generated_url": links["generated_url"],
            "google_jump_url": links["google_jump_url"],
        })

    stop_proc(state_key, owner, folder)
    set_state(state_key, "Offline")
    return jsonify({
        "success": True,
        "message": f"تم إيقاف السيرفر {folder}",
        "generated_url": links["generated_url"],
        "google_jump_url": links["google_jump_url"],
    })


# ==============================================================================
# ٩. بوت تيليجرام التفاعلي (python-telegram-bot v20+)
# ==============================================================================
def _is_tg_admin(user_id: int) -> bool:
    return bool(user_id in ADMIN_TELEGRAM_IDS or is_admin(user_id))


def _tg_user_key(user_id: int) -> str:
    return f"tg:{user_id}"


def _tg_is_free_admin(user_id: int) -> bool:
    return _is_tg_admin(user_id) and ADMIN_FREE_MODE


def _tg_main_keyboard(user_id: int) -> InlineKeyboardMarkup:
    bal = get_balance(_tg_user_key(user_id))
    rows = [
        [InlineKeyboardButton("🚀 استضافة سريعة / تشغيل فوري", callback_data="tg_quick_host")],
        [
            InlineKeyboardButton("🛒 الخدمات المدفوعة", callback_data="tg_services"),
            InlineKeyboardButton(f"💰 رصيدي ({bal:.2f}$)", callback_data="tg_wallet"),
        ],
        [
            InlineKeyboardButton("📦 طلباتي", callback_data="tg_orders"),
            InlineKeyboardButton("🖥 حالة الخادم", callback_data="tg_status"),
        ],
    ]
    if _is_tg_admin(user_id):
        rows.append([InlineKeyboardButton("👑 لوحة الأدمن المجانية", callback_data="tg_admin_panel")])
    rows.append([InlineKeyboardButton("👨‍💻 معلومات المطور", callback_data="tg_dev_info")])
    return InlineKeyboardMarkup(rows)


async def _ptb_error_handler(update: object, context: ContextTypes.DEFAULT_TYPE):
    err = context.error
    if "Conflict" in str(err):
        logger.warning("⚠️ تعارض getUpdates (Conflict): تأكد من عدم تشغيل نسخة أخرى بنفس التوكن.")
        await asyncio.sleep(5)
        return
    logger.warning(f"⚠️ خطأ في python-telegram-bot: {err}")


async def _run_ptb_async():
    application = Application.builder().token(TOKEN).build()
    application.add_error_handler(_ptb_error_handler)
    application.add_handler(CommandHandler("start", tg_start_cmd))
    application.add_handler(CommandHandler("cancel", tg_cancel_cmd))
    application.add_handler(CallbackQueryHandler(tg_callback_handler))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, tg_text_message_handler))

    await application.initialize()
    await application.start()
    if application.updater:
        await application.updater.start_polling(drop_pending_updates=True)

    try:
        while True:
            await asyncio.sleep(3600)
    finally:
        if application.updater and application.updater.running:
            await application.updater.stop()
        if application.running:
            await application.stop()
        await application.shutdown()


def _run_telegram_bot_thread():
    if not TOKEN or ":" not in TOKEN:
        logger.warning("⚠️ TOKEN غير مضبوط؛ تم تخطي تشغيل بوت python-telegram-bot")
        return

    allow_dup = os.environ.get("ALLOW_DUPLICATE_TOKEN", "0").strip() in ("1", "true", "yes")
    if TOKEN and TOKEN == TOKEN and not allow_dup:
        logger.warning(
            "⚠️ TOKEN مطابق لـ TOKEN المستخدم مع TeleBot؛ تم تخطي تشغيل python-telegram-bot لتجنب تعارض getUpdates."
        )
        return

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        logger.info("🤖 تشغيل بوت python-telegram-bot بنجاح...")
        loop.run_until_complete(_run_ptb_async())
    except Exception as e:
        logger.error(f"❌ خطأ في تشغيل بوت python-telegram-bot: {e}")
    finally:
        try:
            pending = asyncio.all_tasks(loop=loop)
            for task in pending:
                task.cancel()
            if pending:
                loop.run_until_complete(asyncio.gather(*pending, return_exceptions=True))
            loop.run_until_complete(loop.shutdown_asyncgens())
        except Exception:
            pass
        try:
            loop.close()
        except Exception:
            pass


def _run_telebot_polling_thread():
    if not TOKEN or ":" not in TOKEN:
        logger.warning("⚠️ TOKEN غير مضبوط؛ تم تخطي تشغيل بوت TeleBot")
        return
    logger.info("🤖 تشغيل بوت TeleBot الرئيسي بنجاح...")
    while True:
        try:
            bot.infinity_polling(none_stop=True, interval=1, timeout=30)
        except Exception as e:
            logger.warning(f"⚠️ إعادة تشغيل TeleBot polling بعد خطأ: {e}")
            time.sleep(3)


def _run_secondary_flask_port():
    if os.environ.get("RENDER") or os.environ.get("RENDER_EXTERNAL_URL"):
        return
    if PANEL_PORT_SECONDARY and PANEL_PORT_SECONDARY != PANEL_PORT_PRIMARY:
        try:
            app.run(host="0.0.0.0", port=PANEL_PORT_SECONDARY, debug=False, use_reloader=False, threaded=True)
        except Exception as e:
            logger.warning(f"⚠️ تعذر تشغيل المنفذ الثانوي {PANEL_PORT_SECONDARY}: {e}")


# ==============================================================================
# ١٠. نقطة الدخول الرئيسية (Main Entrypoint)
# ==============================================================================
def bootstrap_system():
    init_db()
    ensure_index_html_exists()
    _start_keep_alive_once()
    if not any(t.name == "EhabSecondaryFlask" for t in threading.enumerate()):
        threading.Thread(target=_run_secondary_flask_port, name="EhabSecondaryFlask", daemon=True).start()
    if not any(t.name == "EhabTeleBotThread" for t in threading.enumerate()):
        threading.Thread(target=_run_telebot_polling_thread, name="EhabTeleBotThread", daemon=True).start()
    if not any(t.name == "EhabPTBThread" for t in threading.enumerate()):
        threading.Thread(target=_run_telegram_bot_thread, name="EhabPTBThread", daemon=True).start()


bootstrap_system()

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
