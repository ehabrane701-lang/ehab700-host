#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
𝙼𝙴𝚁𝙾 𝙷𝙾𝚂𝚃 - النظام الموحد للاستضافة والتحكم وإدارة البوتات والخدمات (app.py)
طُوِّر بواسطة: 𝗘𝗛𝗔𝗕𝗔𝗜𝗛𝗔𝗪𝗕𝗔𝗡𝗜 | @Y_20_20
"""

# ==============================================================================
# ١. الاستيرادات والتهيئة الأولية (Imports & Initialization)
# ==============================================================================
import os
import sys
import json
import re
import shutil
import socket
import hashlib
import subprocess
import threading
import time
import uuid
import logging
import asyncio
from functools import wraps
from datetime import datetime

import psutil
import requests
from flask import Flask, request, jsonify, session, Response
from werkzeug.security import generate_password_hash, check_password_hash

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
logger = logging.getLogger("MERO_HOST_APP")


# ==============================================================================
# ٢. الإعدادات والثوابت والخدمات (Configuration, Constants & Services)
# ==============================================================================
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
SECURE_ROOT = os.path.abspath(BASE_DIR)

USERS_ROOT = os.path.join(SECURE_ROOT, "USERS")
DATA_DIR = os.path.join(SECURE_ROOT, "DATA")
SERVICES_STORAGE_DIR = os.path.join(DATA_DIR, "services_storage")
USERS_DB = os.path.join(DATA_DIR, "users.json")
PENDING_DB = os.path.join(DATA_DIR, "pending_requests.json")
BALANCES_DB = os.path.join(DATA_DIR, "balances.json")
ORDERS_DB = os.path.join(DATA_DIR, "orders.json")
SERVER_TYPES_DB = os.path.join(DATA_DIR, "server_types.json")
INDEX_HTML_PATH = os.path.join(BASE_DIR, "index.html")

os.makedirs(USERS_ROOT, exist_ok=True)
os.makedirs(DATA_DIR, exist_ok=True)
os.makedirs(SERVICES_STORAGE_DIR, exist_ok=True)

# إعدادات لوحة الويب والأدمن
PANEL_PORT_PRIMARY = int(os.environ.get("PORT", os.environ.get("SERVER_PORT", 8008)))
PANEL_PORT_SECONDARY = int(os.environ.get("SECONDARY_SERVER_PORT", 3004))

ADMIN_USERNAME = os.environ.get("ADMIN_USER", "Y_20_20")
ADMIN_PASSWORD = os.environ.get("ADMIN_PASS", "1002670694")

# إعدادات بوت تيليجرام والمطور
BOT_TOKEN = os.environ.get("BOT_TOKEN", "9294301891:AAG4oWwRlxxnyCIe3yIutxr_NSELsgBic68")
API_BASE_URL = os.environ.get("API_BASE_URL", f"http://127.0.0.1:{PANEL_PORT_PRIMARY}")
PUBLIC_API_URL = os.environ.get("PUBLIC_API_URL", "https://ehab700-host.onrender.com")
ADMIN_TELEGRAM_IDS = [1002670694]
LOG_CHANNEL_ID = os.environ.get("LOG_CHANNEL_ID", "")

DEVELOPER_INFO = (
    "<b><blockquote>🛠 طُوِّر بواسطة: 𝗘𝗛𝗔𝗕𝗔𝗜𝗛𝗔𝗪𝗕𝗔𝗡𝗜</blockquote></b>\n"
    "<b>📬 تواصل:</b> <code>@Y_20_20</code>\n"
    "<tg-spoiler>نسخة مدفوعة ومحمية بالكامل - جميع الحقوق محفوظة</tg-spoiler>"
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

app = Flask(__name__)
app.secret_key = os.environ.get("PANEL_SECRET_KEY", "MERO_HOST_SECURE_" + os.urandom(16).hex())

running_procs = {}   # key -> (Popen, log_file_handle)
server_states = {}   # key -> Offline/Installing/Starting/Running/Banned
lock = threading.Lock()
finance_lock = threading.Lock()


# ==============================================================================
# ٣. أدوات الأمان والمسارات والحماية (Security, Paths & Protection)
# ==============================================================================
def is_path_safe(base_dir: str, target_path: str) -> bool:
    try:
        real_target = os.path.realpath(target_path)
        real_base = os.path.realpath(base_dir)
        common = os.path.commonpath([real_target, real_base])
        return common == real_base
    except (ValueError, OSError):
        return False


def secure_join(base_dir: str, *paths) -> str:
    base_dir = os.path.realpath(base_dir)
    current_path = base_dir
    for path in paths:
        parts = str(path).split("/")
        for part in parts:
            if part == "..":
                raise ValueError("Path traversal attempt detected")
            if part in (".", ""):
                continue
            current_path = os.path.join(current_path, part)
            current_path = os.path.realpath(current_path)
            if not current_path.startswith(base_dir + os.sep) and current_path != base_dir:
                raise ValueError("Security violation: Attempted to access outside secure root")
    return current_path


def get_ip():
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("10.255.255.255", 1))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return "127.0.0.1"


def sanitize_folder_name(name: str) -> str:
    name = (name or "").strip()
    name = re.sub(r"\s+", "-", name)
    name = re.sub(r"[^A-Za-z0-9\-_\.]", "", name)
    return name[:200]


def safe_name(name: str) -> str:
    name = (name or "").strip()
    name = re.sub(r"[\\/]+", "", name)
    name = re.sub(r"[^A-Za-z0-9\-_\. ]", "", name)
    return name[:200].strip()


def set_state(key: str, state: str):
    with lock:
        server_states[key] = state


def get_state(key: str) -> str:
    with lock:
        return server_states.get(key, "Offline")


def get_user_servers_root(username: str) -> str:
    safe_username = re.sub(r"[^a-zA-Z0-9_.-]", "", username or "")
    return os.path.join(USERS_ROOT, safe_username, "servers")


def get_server_dir(owner: str, folder: str) -> str:
    safe_owner = re.sub(r"[^a-zA-Z0-9_.-]", "", owner or "")
    safe_folder = re.sub(r"[^a-zA-Z0-9_.-]", "", folder or "")
    base = get_user_servers_root(safe_owner)
    return os.path.join(base, safe_folder)


def ensure_user_dirs(username: str):
    try:
        path = get_user_servers_root(username)
        os.makedirs(path, exist_ok=True)
    except Exception as e:
        logger.warning(f"Security Alert: {e}")


def is_admin_session():
    u = session.get("user") or {}
    return bool(u.get("is_admin"))


def current_username():
    u = session.get("user") or {}
    return (u.get("username") or "").strip()


def parse_server_key(key: str, allow_admin: bool):
    key = (key or "").strip()
    if ".." in key or key.startswith("/") or key.startswith("\\"):
        raise ValueError("Invalid key format")

    if "::" in key:
        if not allow_admin or not is_admin_session():
            raise ValueError("forbidden")
        owner, folder = key.split("::", 1)
        owner = owner.strip()
        folder = folder.strip()
        if not re.match(r"^[a-zA-Z0-9_.-]+$", owner) or not re.match(r"^[a-zA-Z0-9_.-]+$", folder):
            raise ValueError("Invalid characters in owner or folder")
        return owner, folder

    user = current_username()
    if not is_admin_session():
        if not user or not re.match(r"^[a-zA-Z0-9_.-]+$", user) or not re.match(r"^[a-zA-Z0-9_.-]+$", key):
            raise ValueError("Invalid characters")
        return user, key
    return (user or ADMIN_USERNAME), key


def can_access_key(key: str) -> bool:
    try:
        owner, _folder = parse_server_key(key, allow_admin=True)
    except Exception:
        return False
    if is_admin_session():
        return True
    return owner == current_username()


def safe_join_server_path(key: str, rel_path: str = "") -> str:
    owner, folder = parse_server_key(key, allow_admin=True)
    server_root = os.path.abspath(get_server_dir(owner, folder))

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
        owner, folder = parse_server_key(key, allow_admin=True)
        server_dir = get_server_dir(owner, folder)
        os.makedirs(server_dir, exist_ok=True)
        log_path = os.path.join(server_dir, "server.log")
        with open(log_path, "a", encoding="utf-8", errors="ignore") as f:
            f.write(text)
    except Exception:
        pass


# ==============================================================================
# ٤. قاعدة البيانات والأرصدة والخدمات والطلبات (DB, Balances, Services & Orders)
# ==============================================================================
def _atomic_write_json(path: str, payload: dict):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2, ensure_ascii=False)
    os.replace(tmp, path)


def _read_json(path: str, default: dict) -> dict:
    if not os.path.exists(path):
        return dict(default)
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
            return data if isinstance(data, dict) else dict(default)
    except Exception:
        return dict(default)


def load_users():
    return _read_json(USERS_DB, {"users": []})


def save_users(db):
    _atomic_write_json(USERS_DB, db)


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
    if key == ADMIN_USERNAME or key == f"ADMIN_{ADMIN_USERNAME}":
        return {"username": ADMIN_USERNAME, "is_admin": True, "active": True, "premium": True}
    db = load_users()
    for u in db.get("users", []):
        if u.get("api_key") == key:
            return {**u, "is_admin": False}
    return None


def get_user_limit(username: str) -> int:
    if is_admin_session():
        return 999999
    db = load_users()
    u = find_user(db, username)
    if not u:
        return 1
    return 1000 if u.get("premium", False) else 1


def get_balance(user_key: str) -> float:
    with finance_lock:
        db = _read_json(BALANCES_DB, {"balances": {}})
        return float(db["balances"].get(str(user_key), 0.0))


def add_balance(user_key: str, amount: float) -> float:
    with finance_lock:
        db = _read_json(BALANCES_DB, {"balances": {}})
        cur = float(db["balances"].get(str(user_key), 0.0))
        new_bal = round(cur + float(amount), 4)
        if new_bal < 0:
            raise ValueError("Balance cannot be negative")
        db["balances"][str(user_key)] = new_bal
        _atomic_write_json(BALANCES_DB, db)
        return new_bal


def deduct_balance_safe(user_key: str, amount: float) -> tuple[bool, float]:
    with finance_lock:
        amt = float(amount)
        if amt <= 0:
            return False, get_balance(user_key)
        db = _read_json(BALANCES_DB, {"balances": {}})
        cur = float(db["balances"].get(str(user_key), 0.0))
        if cur < amt:
            return False, cur
        new_bal = round(cur - amt, 4)
        db["balances"][str(user_key)] = new_bal
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
            "created_at": datetime.utcnow().isoformat(),
        }
        db["orders"].append(entry)
        _atomic_write_json(ORDERS_DB, db)

        svc_meta = SERVICES_CATALOG.get(service_id)
        if svc_meta:
            svc_data = _read_json(svc_meta["file"], {"service_id": service_id, "records": []})
            svc_data["records"].append(entry)
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
                item["updated_at"] = datetime.utcnow().isoformat()
                break
        _atomic_write_json(ORDERS_DB, db)


def execute_paid_service_order(user_key: str, service_id: str, details: str) -> dict:
    svc = SERVICES_CATALOG.get(service_id)
    if not svc:
        return {"success": False, "message": "الخدمة غير موجودة"}

    price = float(svc["price"])
    ok, balance_after_deduct = deduct_balance_safe(user_key, price)
    if not ok:
        return {
            "success": False,
            "message": f"رصيدك الحالي ({balance_after_deduct:.2f} {svc['currency']}) غير كافٍ لإتمام الدفع ({price:.2f} {svc['currency']}).",
        }

    order_id = record_order(user_key, service_id, price, details, "paid_pending", "تم حجز المبلغ وجاري التنفيذ")

    try:
        if not details or len(details.strip()) < 2:
            raise ValueError("البيانات المدخلة للطلب غير مكتملة")

        web_dir = os.path.join(DATA_DIR, "web_requests", order_id)
        os.makedirs(web_dir, exist_ok=True)
        request_file = os.path.join(web_dir, "request_info.json")
        _atomic_write_json(request_file, {
            "order_id": order_id,
            "user_key": str(user_key),
            "service": svc["name"],
            "details": details.strip(),
            "route": f"/web/{order_id}",
            "created_at": datetime.utcnow().isoformat(),
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
        refunded_bal = add_balance(user_key, price)
        update_order_status(order_id, "refunded", f"تم الاسترجاع تلقائياً بسبب: {e}")
        return {
            "success": False,
            "order_id": order_id,
            "balance": refunded_bal,
            "message": f"تعذر إتمام التسليم وتم إرجاع المبلغ ({price:.2f}) إلى رصيدك تلقائياً. السبب: {e}",
        }


# ==============================================================================
# ٥. إدارة الميتا وتثبيت المكتبات وتشغيل السيرفرات (Meta, Auto-Install & Runner)
# ==============================================================================
def ensure_meta(owner: str, folder: str):
    server_dir = get_server_dir(owner, folder)
    os.makedirs(server_dir, exist_ok=True)
    meta_path = os.path.join(server_dir, "meta.json")
    base = {"display_name": folder, "startup_file": "", "owner": owner, "banned": False}
    if not os.path.exists(meta_path):
        _atomic_write_json(meta_path, base)
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
            _atomic_write_json(meta_path, m)
    return meta_path


def read_meta(owner: str, folder: str):
    ensure_meta(owner, folder)
    meta_path = os.path.join(get_server_dir(owner, folder), "meta.json")
    return _read_json(meta_path, {"display_name": folder, "startup_file": "", "owner": owner, "banned": False})


def write_meta(owner: str, folder: str, meta):
    ensure_meta(owner, folder)
    meta_path = os.path.join(get_server_dir(owner, folder), "meta.json")
    _atomic_write_json(meta_path, meta)


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


def ensure_requirements_installed(owner: str, folder: str):
    server_dir = get_server_dir(owner, folder)
    req_path = os.path.join(server_dir, "requirements.txt")
    if not os.path.exists(req_path):
        return False

    req_sha = sha256_file(req_path)
    cur = read_installed(owner, folder)
    if cur["req_sha"] == req_sha:
        return False

    log_append(f"{owner}::{folder}", "[SYSTEM] Installing requirements.txt...\n")
    try:
        subprocess.check_call([sys.executable, "-m", "pip", "install", "-r", "requirements.txt"], cwd=server_dir)
        write_installed(owner, folder, req_sha=req_sha)
        log_append(f"{owner}::{folder}", "[SYSTEM] requirements installed ✅\n")
        return True
    except subprocess.CalledProcessError as e:
        log_append(f"{owner}::{folder}", f"[SYSTEM] requirements install failed: {e}\n")
        return False


def start_with_autoinstall(owner: str, folder: str, startup_file: str):
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
        return n
    s = str(e)
    m = re.search(r"No module named '([^']+)'", s)
    if m:
        return m.group(1)
    return None

while True:
    try:
        runpy.run_path(script, run_name="__main__")
        break
    except ModuleNotFoundError as e:
        pkg = parse_missing_name(e)
        if not pkg:
            traceback.print_exc()
            break
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
    server_dir = get_server_dir(owner, folder)
    log_path = os.path.join(server_dir, "server.log")
    log_file = open(log_path, "a", encoding="utf-8", errors="ignore")

    proc = subprocess.Popen(
        [sys.executable, "-u", "-c", wrapper_code, startup_file],
        cwd=server_dir,
        stdout=log_file,
        stderr=log_file,
    )
    return proc, log_file


def stop_proc(key: str):
    with lock:
        proc_tuple = running_procs.pop(key, None)
    if proc_tuple:
        proc, logf = proc_tuple
        try:
            p = psutil.Process(proc.pid)
            for child in p.children(recursive=True):
                child.kill()
            p.kill()
        except Exception:
            pass
        try:
            logf.close()
        except Exception:
            pass


# ==============================================================================
# ٦. تجميع الصفحات في index.html وإصلاح المسارات والـ API (Unified index.html)
# ==============================================================================
DEFAULT_UNIFIED_INDEX_HTML = """<!DOCTYPE html>
<html lang="ar" dir="rtl">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>𝙼𝙴𝚁𝙾 𝙷𝙾𝚂𝚃 - اللوحة الموحدة</title>
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
  </style>
</head>
<body>
  <div class="container">
    <h2>🚀 𝙼𝙴𝚁𝙾 𝙷𝙾𝚂𝚃 — اللوحة الموحدة (دخول • إنشاء حساب • سيرفرات • أدمن)</h2>
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
      <button class="success" onclick="addServer()">➕ إنشاء سيرفر</button>
      <button onclick="loadServers()">🔄 تحديث القائمة</button>
      <hr />
      <h3>السيرفرات الخاصة بك</h3>
      <div id="serversList"></div>
      <div id="fileManagerBox" class="card hidden">
        <h4>إدارة ملفات السيرفر: <span id="activeServerKey"></span></h4>
        <input id="startupFileInput" placeholder="ملف التشغيل الرئيسي (مثال: main.py)" />
        <button onclick="saveStartup()">💾 حفظ ملف التشغيل</button>
        <button class="success" onclick="serverAct('start')">▶️ تشغيل</button>
        <button class="danger" onclick="serverAct('stop')">⏹ إيقاف</button>
        <button onclick="serverAct('restart')">🔄 إعادة تشغيل</button>
        <h5>الملفات والمجلدات:</h5>
        <div id="filesList"></div>
        <input id="editFilePath" placeholder="مسار الملف للتعديل أو الحفظ (مثال: main.py)" />
        <textarea id="editFileContent" rows="8" placeholder="محتوى الملف..."></textarea>
        <button onclick="loadFileContent()">📂 فتح الملف</button>
        <button class="success" onclick="saveFileContent()">💾 حفظ الملف</button>
        <h5>الكونسول والسجل:</h5>
        <pre id="serverLogs"></pre>
      </div>
    </div>

    <div id="tab-admin" class="hidden">
      <h3>👑 لوحة إدارة الأدمن</h3>
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
        div.innerHTML = `<b>${s.title}</b> (${s.status}) - ${s.subtitle}<br/><button onclick="openServer('${s.key}', '${s.startup_file || ""}')">⚙️ إدارة</button>`;
        box.appendChild(div);
      }
    }
    async function addServer() {
      const name = document.getElementById("newServerName").value;
      const res = await fetch("/add", {
        method: "POST",
        headers: {"Content-Type": "application/json"},
        body: JSON.stringify({name})
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
    async function saveStartup() {
      const f = document.getElementById("startupFileInput").value;
      await fetch("/server/set-startup/" + encodeURIComponent(currentKey), {
        method: "POST",
        headers: {"Content-Type": "application/json"},
        body: JSON.stringify({file: f})
      });
      showMsg("تم حفظ ملف التشغيل");
    }
    async function serverAct(act) {
      const res = await fetch("/server/action/" + encodeURIComponent(currentKey) + "/" + act, {method: "POST"});
      const d = await res.json();
      showMsg(d.success ? ("تم تنفيذ " + act) : ("خطأ: " + d.message));
      refreshServerDetails();
    }
    async function refreshServerDetails() {
      if (!currentKey) return;
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
            key = f"{owner}::{folder}"
            st = "Banned" if banned else get_state(key)
            servers.append({
                "title": meta.get("display_name", folder),
                "folder": folder,
                "owner": owner,
                "key": key,
                "subtitle": f"Owner: {owner}",
                "startup_file": meta.get("startup_file", ""),
                "status": st,
            })
    return servers


@app.route("/api/ping", methods=["GET"])
def api_ping():
    return jsonify({
        "success": True,
        "status": "alive",
        "timestamp": datetime.utcnow().isoformat(),
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
                        "User-Agent": "MERO-HOST-KEEP-ALIVE/1.0",
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
        if not any(t.name == "MeroKeepAliveThread" for t in threading.enumerate()):
            t = threading.Thread(target=_keep_alive_worker, name="MeroKeepAliveThread", daemon=True)
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
        key = folder
        st = "Banned" if banned else get_state(key)
        servers.append({
            "title": meta.get("display_name", folder),
            "folder": folder,
            "owner": username,
            "key": key,
            "subtitle": f"Owner: {username}",
            "startup_file": meta.get("startup_file", ""),
            "status": st,
        })
    return servers


@app.route("/")
def home():
    return render_unified_index("home")


@app.route("/login")
def login_page():
    return render_unified_index("login")


@app.route("/create")
def create_page():
    return render_unified_index("create")


@app.route("/admin")
def admin_page():
    return render_unified_index("admin")


@app.route("/logout")
def logout():
    session.pop("user", None)
    return jsonify({"success": True, "redirect": "/login"})


@app.route("/web/<order_id>")
def web_order_route(order_id):
    safe_oid = re.sub(r"[^A-Za-z0-9\-]", "", order_id or "")
    req_file = os.path.join(DATA_DIR, "web_requests", safe_oid, "request_info.json")
    if not os.path.exists(req_file):
        return jsonify({"success": False, "message": "Web route not found"}), 404
    return jsonify({"success": True, "data": _read_json(req_file, {})})


@app.route("/api/auth/login", methods=["POST"])
def api_login():
    data = request.get_json(silent=True) or {}
    username = (data.get("username") or "").strip()
    password = data.get("password") or ""

    if username == ADMIN_USERNAME and password == ADMIN_PASSWORD:
        session["user"] = {"username": ADMIN_USERNAME, "is_admin": True}
        return jsonify({"success": True, "is_admin": True, "username": ADMIN_USERNAME})

    db = load_users()
    u = find_user(db, username)
    if not u:
        return jsonify({"success": False, "message": "Invalid username or password"}), 401
    if not u.get("active", True):
        return jsonify({"success": False, "message": "Account is banned / inactive"}), 403
    if not check_password_hash(u.get("password_hash", ""), password):
        return jsonify({"success": False, "message": "Invalid username or password"}), 401

    session["user"] = {"username": u.get("username"), "is_admin": False}
    ensure_user_dirs(u.get("username"))
    return jsonify({"success": True, "is_admin": False, "username": u.get("username")})


@app.route("/api/auth/create", methods=["POST"])
def api_create():
    data = request.get_json(silent=True) or {}
    username = (data.get("username") or "").strip()
    email = (data.get("email") or "").strip()
    password = data.get("password") or ""
    password2 = data.get("password2") or ""

    if not username or len(username) < 3:
        return jsonify({"success": False, "message": "Username must be at least 3 chars"}), 400
    if not re.fullmatch(r"[A-Za-z0-9_\.]+", username):
        return jsonify({"success": False, "message": "Username allowed: letters, numbers, _ and ."}), 400
    if username.upper() == ADMIN_USERNAME.upper():
        return jsonify({"success": False, "message": "This username is reserved"}), 400
    if not email or "@" not in email:
        return jsonify({"success": False, "message": "Enter a valid email"}), 400
    if len(password) < 6:
        return jsonify({"success": False, "message": "Password must be at least 6 chars"}), 400
    if password != password2:
        return jsonify({"success": False, "message": "Passwords do not match"}), 400

    db = load_users()
    if find_user(db, username):
        return jsonify({"success": False, "message": "Username already exists"}), 409

    generated_api_key = f"MERO_{hashlib.sha256((username + os.urandom(12).hex()).encode()).hexdigest()[:24].upper()}"
    db["users"].append({
        "username": username,
        "email": email,
        "password_hash": generate_password_hash(password),
        "api_key": generated_api_key,
        "active": True,
        "approved": False,
        "premium": False,
    })
    save_users(db)
    ensure_user_dirs(username)

    pending = _read_json(PENDING_DB, {"requests": []})
    pending["requests"].append({
        "username": username,
        "email": email,
        "api_key": generated_api_key,
        "created_at": datetime.utcnow().isoformat(),
    })
    _atomic_write_json(PENDING_DB, pending)
    return jsonify({"success": True, "api_key": generated_api_key})


@app.route("/servers")
@api_login_required
def servers():
    if is_admin_session():
        return jsonify({"success": True, "servers": list_all_servers_for_admin()})
    return jsonify({"success": True, "servers": list_servers_for_user(current_username())})


@app.route("/add", methods=["POST"])
@api_login_required
def add_server():
    data = request.get_json(silent=True) or {}
    name = (data.get("name") or "").strip()
    folder = sanitize_folder_name(name)
    if not folder:
        return jsonify({"success": False, "message": "Invalid server name"}), 400

    owner = current_username()
    ensure_user_dirs(owner)

    if not is_admin_session():
        limit = get_user_limit(owner)
        user_root = get_user_servers_root(owner)
        existing_count = len([d for d in os.listdir(user_root) if os.path.isdir(os.path.join(user_root, d))])
        if existing_count >= limit:
            return jsonify({"success": False, "message": f"Server limit reached ({limit}). Ask admin for premium."}), 403

    target = get_server_dir(owner, folder)
    if os.path.exists(target):
        return jsonify({"success": False, "message": "Server already exists"}), 409

    os.makedirs(target, exist_ok=True)
    open(os.path.join(target, "server.log"), "w", encoding="utf-8").close()
    write_meta(owner, folder, {
        "display_name": name or folder,
        "startup_file": "",
        "owner": owner,
        "banned": False,
    })
    set_state(folder if not is_admin_session() else f"{owner}::{folder}", "Offline")

    if is_admin_session():
        return jsonify({"success": True, "servers": list_all_servers_for_admin()})
    return jsonify({"success": True, "servers": list_servers_for_user(owner)})


@app.route("/server/stats/<path:key>")
@api_login_required
def server_stats(key):
    if not can_access_key(key):
        return jsonify({"success": False, "message": "Forbidden"}), 403

    owner, folder = parse_server_key(key, allow_admin=True)
    server_dir = get_server_dir(owner, folder)
    if not os.path.isdir(server_dir):
        return jsonify({"status": "Offline", "cpu": "0%", "mem": "0 MB", "logs": "", "ip": get_ip()}), 404

    meta = read_meta(owner, folder)
    if meta.get("banned", False):
        set_state(key, "Banned")

    with lock:
        proc_tuple = running_procs.get(key)

    running = False
    cpu, mem = "0%", "0 MB"

    if proc_tuple:
        proc, _logf = proc_tuple
        if psutil.pid_exists(proc.pid):
            try:
                p = psutil.Process(proc.pid)
                if p.is_running() and p.status() != psutil.STATUS_ZOMBIE:
                    running = True
                    cpu = f"{p.cpu_percent(interval=None)}%"
                    mem = f"{p.memory_info().rss / 1024 / 1024:.1f} MB"
            except Exception:
                pass

    log_path = os.path.join(server_dir, "server.log")
    try:
        logs = open(log_path, "r", encoding="utf-8", errors="ignore").read() if os.path.exists(log_path) else ""
    except Exception:
        logs = ""

    state = get_state(key)
    if meta.get("banned", False):
        state = "Banned"
    elif running:
        state = "Running"
        set_state(key, "Running")
    elif state not in ("Installing", "Starting"):
        state = "Offline"
        set_state(key, "Offline")

    return jsonify({"status": state, "cpu": cpu, "mem": mem, "logs": logs, "ip": get_ip()})


def background_start(key: str, owner: str, folder: str, startup_file: str):
    try:
        set_state(key, "Installing")
        log_append(key, "[SYSTEM] Preparing...\n")
        ensure_requirements_installed(owner, folder)

        set_state(key, "Starting")
        log_append(key, "[SYSTEM] Starting...\n")
        proc, logf = start_with_autoinstall(owner, folder, startup_file)
        with lock:
            running_procs[key] = (proc, logf)

        time.sleep(1.0)
        if proc.poll() is None:
            set_state(key, "Running")
        else:
            set_state(key, "Offline")
    except Exception as e:
        log_append(key, f"[SYSTEM] Start failed: {e}\n")
        set_state(key, "Offline")


@app.route("/server/action/<path:key>/<act>", methods=["POST"])
@api_login_required
def server_action(key, act):
    if not can_access_key(key):
        return jsonify({"success": False, "message": "Forbidden"}), 403

    owner, folder = parse_server_key(key, allow_admin=True)
    server_dir = get_server_dir(owner, folder)
    if not os.path.isdir(server_dir):
        return jsonify({"success": False, "message": "Server not found"}), 404

    meta = read_meta(owner, folder)
    if meta.get("banned", False):
        set_state(key, "Banned")
        return jsonify({"success": False, "message": "Server is banned by admin"}), 403

    if act in ("stop", "restart"):
        stop_proc(key)
        set_state(key, "Offline")

    if act == "stop":
        return jsonify({"success": True})

    startup = meta.get("startup_file") or ""
    if not startup:
        return jsonify({"success": False, "message": "No main file set"}), 400

    open(os.path.join(server_dir, "server.log"), "w", encoding="utf-8").close()
    t = threading.Thread(target=background_start, args=(key, owner, folder, startup), daemon=True)
    t.start()
    return jsonify({"success": True})


@app.route("/server/set-startup/<path:key>", methods=["POST"])
@api_login_required
def set_startup(key):
    if not can_access_key(key):
        return jsonify({"success": False, "message": "Forbidden"}), 403

    owner, folder = parse_server_key(key, allow_admin=True)
    server_dir = get_server_dir(owner, folder)
    if not os.path.isdir(server_dir):
        return jsonify({"success": False, "message": "Server not found"}), 404

    data = request.get_json(silent=True) or {}
    f = (data.get("file") or "").strip()
    meta = read_meta(owner, folder)
    meta["startup_file"] = f
    write_meta(owner, folder, meta)
    return jsonify({"success": True})


@app.route("/files/list/<path:key>")
@api_login_required
def files_list(key):
    if not can_access_key(key):
        return jsonify({"success": False, "message": "Forbidden", "path": ""}), 403

    rel = request.args.get("path", "") or ""
    try:
        base = safe_join_server_path(key, rel)
    except Exception:
        return jsonify({"success": False, "message": "Invalid path", "path": ""}), 400

    dirs, files = [], []
    if os.path.isdir(base):
        for name in sorted(os.listdir(base), key=lambda x: (not os.path.isdir(os.path.join(base, x)), x.lower())):
            if rel == "" and name in ("meta.json", "server.log"):
                continue
            full = os.path.join(base, name)
            if os.path.isdir(full):
                dirs.append({"name": name})
            elif os.path.isfile(full):
                try:
                    size_kb = os.path.getsize(full) / 1024
                    size = f"{size_kb:.1f} KB"
                except Exception:
                    size = ""
                files.append({"name": name, "size": size})

    return jsonify({"success": True, "path": rel, "dirs": dirs, "files": files})


@app.route("/files/content/<path:key>")
@api_login_required
def file_content(key):
    if not can_access_key(key):
        return jsonify({"content": ""}), 403
    file_rel = request.args.get("file", "") or ""
    try:
        full = safe_join_server_path(key, file_rel)
    except Exception:
        return jsonify({"content": ""}), 400
    if os.path.isdir(full):
        return jsonify({"content": ""}), 400
    try:
        with open(full, "r", encoding="utf-8", errors="ignore") as f:
            return jsonify({"content": f.read()})
    except Exception:
        return jsonify({"content": ""})


@app.route("/files/save/<path:key>", methods=["POST"])
@api_login_required
def file_save(key):
    if not can_access_key(key):
        return jsonify({"success": False, "message": "Forbidden"}), 403
    data = request.get_json(silent=True) or {}
    file_rel = data.get("file", "") or ""
    content = data.get("content", "")
    try:
        full = safe_join_server_path(key, file_rel)
    except Exception:
        return jsonify({"success": False, "message": "Invalid path"}), 400
    os.makedirs(os.path.dirname(full), exist_ok=True)
    try:
        with open(full, "w", encoding="utf-8") as f:
            f.write(content)
        return jsonify({"success": True})
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500


@app.route("/files/mkdir/<path:key>", methods=["POST"])
@api_login_required
def file_mkdir(key):
    if not can_access_key(key):
        return jsonify({"success": False, "message": "Forbidden"}), 403
    data = request.get_json(silent=True) or {}
    rel = data.get("path", "") or ""
    name = safe_name(data.get("name", ""))
    if not name:
        return jsonify({"success": False, "message": "Bad name"}), 400
    try:
        target = safe_join_server_path(key, os.path.join(rel, name))
        os.makedirs(target, exist_ok=False)
        return jsonify({"success": True})
    except FileExistsError:
        return jsonify({"success": False, "message": "Already exists"}), 409
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500


@app.route("/files/rename/<path:key>", methods=["POST"])
@api_login_required
def file_rename(key):
    if not can_access_key(key):
        return jsonify({"success": False, "message": "Forbidden"}), 403
    data = request.get_json(silent=True) or {}
    rel = data.get("path", "") or ""
    old = safe_name(data.get("old", ""))
    new = safe_name(data.get("new", ""))
    if not old or not new:
        return jsonify({"success": False, "message": "Bad name"}), 400
    try:
        src = safe_join_server_path(key, os.path.join(rel, old))
        dst = safe_join_server_path(key, os.path.join(rel, new))
        os.rename(src, dst)
        return jsonify({"success": True})
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500


@app.route("/files/delete/<path:key>", methods=["POST"])
@api_login_required
def file_delete(key):
    if not can_access_key(key):
        return jsonify({"success": False, "message": "Forbidden"}), 403
    data = request.get_json(silent=True) or {}
    rel = data.get("path", "") or ""
    name = safe_name(data.get("name", ""))
    kind = (data.get("kind") or "file").lower()
    if not name:
        return jsonify({"success": False, "message": "Bad name"}), 400
    try:
        target = safe_join_server_path(key, os.path.join(rel, name))
        if kind == "dir":
            shutil.rmtree(target)
        else:
            os.remove(target)
        return jsonify({"success": True})
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500


@app.route("/files/upload/<path:key>", methods=["POST"])
@api_login_required
def file_upload(key):
    if not can_access_key(key):
        return jsonify({"success": False, "message": "Forbidden"}), 403

    rel = request.args.get("path", "") or ""
    try:
        base_dir = safe_join_server_path(key, rel)
    except Exception:
        return jsonify({"success": False, "message": "Invalid path"}), 400
    os.makedirs(base_dir, exist_ok=True)

    files = request.files.getlist("files") or []
    if not files:
        one = request.files.get("file")
        if one:
            files = [one]
    if not files:
        return jsonify({"success": False, "message": "No file"}), 400

    relpaths = request.form.getlist("relpaths")
    saved = 0
    for i, f in enumerate(files):
        if not f or not f.filename:
            continue
        filename = os.path.basename(f.filename)
        rp = (relpaths[i] or "").replace("\\", "/").lstrip("/") if (relpaths and i < len(relpaths)) else ""
        try:
            target_dir = safe_join_server_path(key, os.path.join(rel, os.path.dirname(rp))) if rp else base_dir
        except Exception:
            continue
        os.makedirs(target_dir, exist_ok=True)
        f.save(os.path.join(target_dir, filename))
        saved += 1

    return jsonify({"success": True, "saved": saved})


@app.route("/api/bot/verify", methods=["POST"])
def api_bot_verify():
    data = request.get_json(silent=True) or {}
    api_key = (data.get("api_key") or "").strip()
    user_info = find_user_by_api_key(api_key)
    if not user_info:
        return jsonify({"success": False, "message": "Invalid API Key"}), 401
    if not user_info.get("active", True):
        return jsonify({"success": False, "message": "Account banned"}), 403
    return jsonify({
        "success": True,
        "username": user_info.get("username"),
        "is_admin": bool(user_info.get("is_admin", False)),
    })


@app.route("/api/bot/servers", methods=["GET"])
def api_bot_servers():
    api_key = (request.args.get("api_key") or "").strip()
    user_info = find_user_by_api_key(api_key)
    if not user_info:
        return jsonify({"success": False, "message": "Invalid API Key"}), 401

    types_db = _read_json(SERVER_TYPES_DB, {"types": {}})
    if user_info.get("is_admin"):
        raw = list_all_servers_for_admin()
    else:
        raw = list_servers_for_user(user_info.get("username"))

    formatted = []
    for s in raw:
        key = s["key"]
        srv_type = types_db["types"].get(key, "python")
        formatted.append({
            "id": key,
            "folder": s["folder"],
            "name": s["title"],
            "title": s["title"],
            "type": srv_type,
            "status": s["status"],
            "port": f"{get_ip()}:{PANEL_PORT_PRIMARY}",
        })
    return jsonify({"success": True, "servers": formatted})


@app.route("/api/bot/create_server", methods=["POST"])
def api_bot_create_server():
    data = request.get_json(silent=True) or {}
    api_key = (data.get("api_key") or "").strip()
    user_info = find_user_by_api_key(api_key)
    if not user_info:
        return jsonify({"success": False, "message": "Invalid API Key"}), 401

    name = (data.get("name") or "").strip()
    srv_type = (data.get("server_type") or "Python").strip()
    folder = sanitize_folder_name(name)
    if not folder:
        return jsonify({"success": False, "message": "اسم السيرفر غير صالح"}), 400

    owner = user_info.get("username")
    ensure_user_dirs(owner)
    target = get_server_dir(owner, folder)
    if os.path.exists(target):
        return jsonify({"success": False, "message": "السيرفر موجود مسبقاً"}), 409

    os.makedirs(target, exist_ok=True)
    open(os.path.join(target, "server.log"), "w", encoding="utf-8").close()

    default_startup = {
        "HTML": "index.html",
        "Node.js/JS": "index.js",
        "PHP": "index.php",
        "Python": "main.py",
    }.get(srv_type, "main.py")

    write_meta(owner, folder, {
        "display_name": name or folder,
        "startup_file": default_startup,
        "owner": owner,
        "banned": False,
    })

    types_db = _read_json(SERVER_TYPES_DB, {"types": {}})
    key = f"{owner}::{folder}" if user_info.get("is_admin") else folder
    types_db["types"][key] = srv_type
    _atomic_write_json(SERVER_TYPES_DB, types_db)
    set_state(key, "Offline")

    return jsonify({"success": True, "folder": key, "type": srv_type})


@app.route("/api/bot/server/action", methods=["POST"])
def api_bot_server_action():
    data = request.get_json(silent=True) or {}
    api_key = (data.get("api_key") or "").strip()
    user_info = find_user_by_api_key(api_key)
    if not user_info:
        return jsonify({"success": False, "message": "Invalid API Key"}), 401

    folder_or_key = (data.get("folder") or "").strip()
    action = (data.get("action") or "").strip()

    if "::" in folder_or_key:
        owner, folder = folder_or_key.split("::", 1)
    else:
        owner, folder = user_info.get("username"), folder_or_key

    if not user_info.get("is_admin") and owner != user_info.get("username"):
        return jsonify({"success": False, "message": "Forbidden"}), 403

    server_dir = get_server_dir(owner, folder)
    if not os.path.isdir(server_dir):
        return jsonify({"success": False, "message": "السيرفر غير موجود"}), 404

    state_key = f"{owner}::{folder}" if user_info.get("is_admin") else folder
    meta = read_meta(owner, folder)

    if action == "delete":
        stop_proc(state_key)
        shutil.rmtree(server_dir, ignore_errors=True)
        return jsonify({"success": True, "message": "تم حذف السيرفر بنجاح"})

    if meta.get("banned"):
        return jsonify({"success": False, "message": "السيرفر محظور من الإدارة"}), 403

    if action in ("stop", "restart"):
        stop_proc(state_key)
        set_state(state_key, "Offline")
        if action == "stop":
            return jsonify({"success": True, "message": "تم إيقاف السيرفر"})

    startup = meta.get("startup_file") or "main.py"
    sample_path = os.path.join(server_dir, startup)
    if not os.path.exists(sample_path):
        with open(sample_path, "w", encoding="utf-8") as f:
            f.write('import time\nprint("𝙼𝙴𝚁𝙾 𝙷𝙾𝚂𝚃 Server Running...")\ntime.sleep(2)\n')

    t = threading.Thread(target=background_start, args=(state_key, owner, folder, startup), daemon=True)
    t.start()
    return jsonify({"success": True, "message": "تم إرسال أمر التشغيل بنجاح"})


@app.route("/api/bot/console", methods=["GET"])
def api_bot_console():
    api_key = (request.args.get("api_key") or "").strip()
    user_info = find_user_by_api_key(api_key)
    if not user_info:
        return jsonify({"success": False, "message": "Invalid API Key"}), 401
    folder_or_key = (request.args.get("folder") or "").strip()
    owner, folder = folder_or_key.split("::", 1) if "::" in folder_or_key else (user_info.get("username"), folder_or_key)
    log_path = os.path.join(get_server_dir(owner, folder), "server.log")
    logs = open(log_path, "r", encoding="utf-8", errors="ignore").read() if os.path.exists(log_path) else "لا توجد سجلات"
    return jsonify({"success": True, "logs": logs})


@app.route("/api/bot/errors", methods=["GET"])
def api_bot_errors():
    api_key = (request.args.get("api_key") or "").strip()
    user_info = find_user_by_api_key(api_key)
    if not user_info:
        return jsonify({"success": False, "message": "Invalid API Key"}), 401
    folder_or_key = (request.args.get("folder") or "").strip()
    owner, folder = folder_or_key.split("::", 1) if "::" in folder_or_key else (user_info.get("username"), folder_or_key)
    log_path = os.path.join(get_server_dir(owner, folder), "server.log")
    content = open(log_path, "r", encoding="utf-8", errors="ignore").read() if os.path.exists(log_path) else ""
    err_lines = [ln for ln in content.splitlines() if any(w in ln.lower() for w in ("error", "traceback", "exception", "failed", "خطأ"))]
    return jsonify({"success": True, "errors": "\n".join(err_lines) if err_lines else "✅ لا توجد أخطاء مسجلة"})


@app.route("/api/bot/install", methods=["POST"])
def api_bot_install():
    data = request.get_json(silent=True) or {}
    api_key = (data.get("api_key") or "").strip()
    user_info = find_user_by_api_key(api_key)
    if not user_info:
        return jsonify({"success": False, "message": "Invalid API Key"}), 401
    folder_or_key = (data.get("folder") or "").strip()
    owner, folder = folder_or_key.split("::", 1) if "::" in folder_or_key else (user_info.get("username"), folder_or_key)
    ok = ensure_requirements_installed(owner, folder)
    return jsonify({"success": True, "message": "تم فحص/تثبيت requirements.txt" if ok else "لا يوجد ملف requirements.txt جديد أو تم التثبيت مسبقاً"})


@app.route("/api/system/metrics", methods=["GET"])
def api_system_metrics():
    return jsonify({
        "success": True,
        "cpu": psutil.cpu_percent(interval=0.2),
        "memory": psutil.virtual_memory().percent,
        "disk": psutil.disk_usage(SECURE_ROOT).percent,
    })


@app.route("/api/admin/servers")
@api_admin_required
def admin_servers():
    return jsonify({"success": True, "servers": list_all_servers_for_admin()})


@app.route("/api/admin/server/ban", methods=["POST"])
@api_admin_required
def admin_server_ban():
    data = request.get_json(silent=True) or {}
    key = (data.get("key") or "").strip()
    banned = bool(data.get("banned", True))
    owner, folder = parse_server_key(key, allow_admin=True)
    server_dir = get_server_dir(owner, folder)
    if not os.path.isdir(server_dir):
        return jsonify({"success": False, "message": "Server not found"}), 404
    meta = read_meta(owner, folder)
    meta["banned"] = banned
    write_meta(owner, folder, meta)
    if banned:
        stop_proc(key)
        set_state(key, "Banned")
        log_append(key, "[ADMIN] Server banned.\n")
    else:
        set_state(key, "Offline")
        log_append(key, "[ADMIN] Server unbanned.\n")
    return jsonify({"success": True})


@app.route("/api/admin/users")
def admin_users():
    api_key = (request.args.get("api_key") or "").strip()
    user_info = find_user_by_api_key(api_key)
    if not (is_admin_session() or (user_info and user_info.get("is_admin"))):
        return jsonify({"success": False, "message": "Admin only"}), 403

    db = load_users()
    counts = {}
    if os.path.isdir(USERS_ROOT):
        for owner in os.listdir(USERS_ROOT):
            root = get_user_servers_root(owner)
            if os.path.isdir(root):
                counts[owner] = len([d for d in os.listdir(root) if os.path.isdir(os.path.join(root, d))])

    users = [{
        "username": u.get("username"),
        "email": u.get("email"),
        "active": bool(u.get("active", True)),
        "premium": bool(u.get("premium", False)),
        "servers": counts.get(u.get("username") or "", 0),
    } for u in db.get("users", [])]
    return jsonify({"success": True, "users": users})


@app.route("/api/admin/pending")
def admin_pending():
    api_key = (request.args.get("api_key") or "").strip()
    user_info = find_user_by_api_key(api_key)
    if not (is_admin_session() or (user_info and user_info.get("is_admin"))):
        return jsonify({"success": False, "message": "Admin only"}), 403
    pending = _read_json(PENDING_DB, {"requests": []})
    return jsonify({"success": True, "requests": pending.get("requests", [])})


@app.route("/api/admin/approve", methods=["POST"])
def admin_approve():
    data = request.get_json(silent=True) or {}
    api_key = (data.get("api_key") or "").strip()
    user_info = find_user_by_api_key(api_key)
    if not (is_admin_session() or (user_info and user_info.get("is_admin"))):
        return jsonify({"success": False, "message": "Admin only"}), 403

    target_user = (data.get("username") or "").strip()
    db = load_users()
    u = find_user(db, target_user)
    if u:
        u["active"] = True
        u["approved"] = True
        save_users(db)

    pending = _read_json(PENDING_DB, {"requests": []})
    pending["requests"] = [r for r in pending.get("requests", []) if r.get("username") != target_user]
    _atomic_write_json(PENDING_DB, pending)
    return jsonify({"success": True})


@app.route("/api/admin/reject", methods=["POST"])
def admin_reject():
    data = request.get_json(silent=True) or {}
    api_key = (data.get("api_key") or "").strip()
    user_info = find_user_by_api_key(api_key)
    if not (is_admin_session() or (user_info and user_info.get("is_admin"))):
        return jsonify({"success": False, "message": "Admin only"}), 403

    target_user = (data.get("username") or "").strip()
    pending = _read_json(PENDING_DB, {"requests": []})
    pending["requests"] = [r for r in pending.get("requests", []) if r.get("username") != target_user]
    _atomic_write_json(PENDING_DB, pending)
    return jsonify({"success": True})


@app.route("/api/admin/delete-user", methods=["POST"])
def admin_delete_user():
    data = request.get_json(silent=True) or {}
    api_key = (data.get("api_key") or "").strip()
    user_info = find_user_by_api_key(api_key)
    if not (is_admin_session() or (user_info and user_info.get("is_admin"))):
        return jsonify({"success": False, "message": "Admin only"}), 403

    target_user = (data.get("username") or "").strip()
    if not target_user or target_user == ADMIN_USERNAME:
        return jsonify({"success": False, "message": "لا يمكن حذف حساب الأدمن"}), 400

    db = load_users()
    db["users"] = [u for u in db.get("users", []) if u.get("username") != target_user]
    save_users(db)

    safe_u = re.sub(r"[^a-zA-Z0-9_.-]", "", target_user)
    shutil.rmtree(os.path.join(USERS_ROOT, safe_u), ignore_errors=True)
    return jsonify({"success": True})


@app.route("/api/admin/user/update", methods=["POST"])
@api_admin_required
def admin_user_update():
    data = request.get_json(silent=True) or {}
    username = (data.get("username") or "").strip()
    if not username:
        return jsonify({"success": False, "message": "Username required"}), 400
    db = load_users()
    u = find_user(db, username)
    if not u:
        return jsonify({"success": False, "message": "User not found"}), 404
    if "active" in data:
        u["active"] = bool(data["active"])
    if "premium" in data:
        u["premium"] = bool(data["premium"])
    save_users(db)
    return jsonify({"success": True})


@app.route("/api/admin/quickstats")
@api_admin_required
def admin_quickstats():
    total_servers = running = installing = banned = 0
    for s in list_all_servers_for_admin():
        total_servers += 1
        if s.get("status") == "Banned":
            banned += 1
        elif s.get("status") == "Running":
            running += 1
        elif s.get("status") in ("Installing", "Starting"):
            installing += 1

    db = load_users()
    total_users = len(db.get("users", []))
    active_users = sum(1 for u in db.get("users", []) if u.get("active", True))
    premium_users = sum(1 for u in db.get("users", []) if u.get("premium", False))

    return jsonify({"success": True, "stats": {
        "servers_total": total_servers,
        "servers_running": running,
        "servers_installing": installing,
        "servers_banned": banned,
        "users_total": total_users,
        "users_active": active_users,
        "users_premium": premium_users,
    }})


# ==============================================================================
# ٧. مسارات التنقل والرجوع خطوة للوراء وبوت 𝙼𝙴𝚁𝙾 𝙷𝙾𝚂𝚃 (Bot Navigation & UI)
# ==============================================================================
def api_request(endpoint, method="GET", data=None, params=None, api_key=None):
    url = f"{API_BASE_URL}{endpoint}"
    try:
        if method == "GET":
            p = dict(params or {})
            if api_key:
                p["api_key"] = api_key
            resp = requests.get(url, params=p, timeout=30)
        else:
            d = dict(data or {})
            if api_key and "api_key" not in d:
                d["api_key"] = api_key
            resp = requests.post(url, json=d, timeout=30)
        return resp.json() if resp.ok else {"success": False, "message": f"HTTP {resp.status_code}"}
    except Exception as e:
        return {"success": False, "message": str(e)}


def is_admin_tg(update: Update) -> bool:
    user_id = update.effective_user.id if update.effective_user else (update.effective_chat.id if update.effective_chat else 0)
    return user_id in ADMIN_TELEGRAM_IDS


def push_nav_state(context: ContextTypes.DEFAULT_TYPE, screen_name: str):
    stack = context.user_data.setdefault("nav_stack", ["main_menu"])
    if not stack or stack[-1] != screen_name:
        stack.append(screen_name)


def pop_nav_state(context: ContextTypes.DEFAULT_TYPE) -> str:
    stack = context.user_data.setdefault("nav_stack", ["main_menu"])
    if len(stack) > 1:
        stack.pop()
    return stack[-1] if stack else "main_menu"


async def show_main_menu(update: Update, context: ContextTypes.DEFAULT_TYPE, edit=False):
    context.user_data["nav_stack"] = ["main_menu"]
    api_key = context.user_data.get("api_key")
    username = context.user_data.get("username", "")
    uid = update.effective_user.id if update.effective_user else 0
    bal = get_balance(uid)
    is_adm = is_admin_tg(update)

    keyboard = []
    if api_key:
        keyboard.append([
            InlineKeyboardButton("📁 ملفاتي وسيرفراتي", callback_data="my_servers"),
            InlineKeyboardButton("➕ رفع / إنشاء سيرفر", callback_data="create_server"),
        ])
        keyboard.append([
            InlineKeyboardButton("🛒 الخدمات وطلب موقع", callback_data="services_menu"),
            InlineKeyboardButton(f"💰 رصيدي: {bal:.2f}$", callback_data="wallet_menu"),
        ])
        keyboard.append([
            InlineKeyboardButton("🔑 تغيير API Key", callback_data="change_api"),
            InlineKeyboardButton("🚪 تسجيل خروج", callback_data="logout"),
        ])
    else:
        keyboard.append([InlineKeyboardButton("🔑 ربط API Key", callback_data="enter_api")])
        keyboard.append([
            InlineKeyboardButton("🛒 الخدمات وطلب موقع", callback_data="services_menu"),
            InlineKeyboardButton(f"💰 رصيدي: {bal:.2f}$", callback_data="wallet_menu"),
        ])

    if is_adm:
        pending_count = 0
        result = api_request("/api/admin/pending", api_key=api_key or f"ADMIN_{ADMIN_USERNAME}")
        if result and result.get("success"):
            pending_count = len(result.get("requests", []))
        bell = f"🔔 إشعارات الحسابات ({pending_count})" if pending_count > 0 else "🔕 لا إشعارات"
        keyboard.append([
            InlineKeyboardButton("👑 لوحة الإدارة الخارقة", callback_data="admin_panel"),
            InlineKeyboardButton(bell, callback_data="admin_notifications"),
        ])

    keyboard.append([InlineKeyboardButton("💬 تواصل مع المطور @Y_20_20", url="https://t.me/Y_20_20")])

    text = (
        "<b>━━━━━━━━━━━━━━━━━━━━</b>\n"
        "      <b>𝙼𝙴𝚁𝙾 𝙷𝙾𝚂𝚃 🚀</b>\n"
        "<b>━━━━━━━━━━━━━━━━━━━━</b>\n"
    )
    if username:
        text += f"<b>👤 أهلاً بك:</b> <code>{username}</code>\n"
    text += f"<b>💰 الرصيد الحالي:</b> <code>{bal:.2f} USD</code>\n"
    text += ("<b>✅ متصل بسيرفر المنصة بنجاح</b>\n" if api_key else "<b>⚠️ ربط API Key اختياري أو للتحكم الكامل بالسيرفرات</b>\n")
    text += f"\n{DEVELOPER_INFO}"

    markup = InlineKeyboardMarkup(keyboard)
    try:
        if edit and update.callback_query:
            await update.callback_query.edit_message_text(text, parse_mode=ParseMode.HTML, reply_markup=markup)
        elif update.message:
            await update.message.reply_text(text, parse_mode=ParseMode.HTML, reply_markup=markup)
        elif update.callback_query and update.callback_query.message:
            await update.callback_query.message.edit_text(text, parse_mode=ParseMode.HTML, reply_markup=markup)
    except Exception as e:
        logger.debug(f"show_main_menu edit error: {e}")


async def show_services_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    push_nav_state(context, "services_menu")
    query = update.callback_query
    if query:
        await query.answer()

    rows = []
    lines = [
        "<b>━━━━━━━━━━━━━━━━━━━━</b>",
        "   <b>🛒 الخدمات وطلبات المواقع</b>",
        "<b>━━━━━━━━━━━━━━━━━━━━</b>",
        "<i>يتم حجز المبلغ ولا يُثبّت التسليم إلا بعد اكتمال الطلب، وإلا يُعاد الرصيد تلقائياً.</i>\n",
    ]
    for svc_id, svc in SERVICES_CATALOG.items():
        lines.append(
            f"<b>• {svc['name']}</b> — <code>{svc['price']:.2f} {svc['currency']}</code>\n"
            f"  <i>{svc['desc']}</i>"
        )
        rows.append([InlineKeyboardButton(f"💳 طلب: {svc['name']} ({svc['price']:.0f}$)", callback_data=f"buy_svc|{svc_id}")])

    rows.append([InlineKeyboardButton("🔙 رجوع خطوة للخلف", callback_data="go_back")])
    rows.append([InlineKeyboardButton("🏠 القائمة الرئيسية", callback_data="main_menu")])

    text = "\n".join(lines)
    if query:
        await query.edit_message_text(text, parse_mode=ParseMode.HTML, reply_markup=InlineKeyboardMarkup(rows))


async def show_wallet_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    push_nav_state(context, "wallet_menu")
    query = update.callback_query
    if query:
        await query.answer()

    uid = update.effective_user.id if update.effective_user else 0
    bal = get_balance(uid)
    orders_db = _read_json(ORDERS_DB, {"orders": []})
    user_orders = [o for o in orders_db.get("orders", []) if str(o.get("user_key")) == str(uid)][-5:]

    orders_txt = ""
    if user_orders:
        orders_txt = "\n<b>🧾 آخر الطلبات:</b>\n" + "\n".join(
            f"• <code>{o['order_id']}</code> | <b>{o['status']}</b> | {o['amount']:.2f}$"
            for o in user_orders
        )

    text = (
        "<b>━━━━━━━━━━━━━━━━━━━━</b>\n"
        "        <b>💰 المحفظة والرصيد</b>\n"
        "<b>━━━━━━━━━━━━━━━━━━━━</b>\n"
        f"<b>الرصيد المتاح:</b> <code>{bal:.2f} USD</code>\n"
        "<b>قاعدة الأمان:</b> لا يتم خصم رصيدك نهائياً إلا عند إتمام الدفع والاستلام.\n"
        f"{orders_txt}"
    )
    keyboard = [
        [InlineKeyboardButton("➕ طلب شحن رصيد", callback_data="topup_request")],
        [InlineKeyboardButton("🔙 رجوع خطوة للخلف", callback_data="go_back")],
        [InlineKeyboardButton("🏠 القائمة الرئيسية", callback_data="main_menu")],
    ]
    if query:
        await query.edit_message_text(text, parse_mode=ParseMode.HTML, reply_markup=InlineKeyboardMarkup(keyboard))


async def show_servers_list(update: Update, context: ContextTypes.DEFAULT_TYPE):
    push_nav_state(context, "my_servers")
    query = update.callback_query
    if query:
        await query.answer()

    api_key = context.user_data.get("api_key")
    if not api_key:
        if query:
            await query.edit_message_text(
                "<b>❌ يجب ربط API Key أولاً.</b>",
                parse_mode=ParseMode.HTML,
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("🔑 ربط API Key", callback_data="enter_api")],
                    [InlineKeyboardButton("🔙 رجوع", callback_data="go_back")],
                ]),
            )
        return

    result = api_request("/api/bot/servers", api_key=api_key)
    if not result or not result.get("success"):
        if query:
            await query.edit_message_text(
                "<b>━━━━━━━━━━━━━━━━━━━━</b>\n"
                "<b>❌ فشل جلب السيرفرات والملفات</b>\n"
                "<b>━━━━━━━━━━━━━━━━━━━━</b>\n"
                "<i>تحقق من صحة الـ API Key أو حالة الاتصال.</i>",
                parse_mode=ParseMode.HTML,
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 رجوع", callback_data="go_back")]]),
            )
        return

    servers = result.get("servers", [])
    if not servers:
        if query:
            await query.edit_message_text(
                "<b>━━━━━━━━━━━━━━━━━━━━</b>\n"
                "<b>📭 لا توجد ملفات أو سيرفرات مرفوعة</b>\n"
                "<b>━━━━━━━━━━━━━━━━━━━━</b>\n"
                "<i>قم برفع ملفك الأول عبر الزر أدناه!</i>",
                parse_mode=ParseMode.HTML,
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("➕ رفع ملف / إنشاء سيرفر", callback_data="create_server")],
                    [InlineKeyboardButton("🔙 رجوع", callback_data="go_back")],
                ]),
            )
        return

    if query:
        await query.edit_message_text(f"<b>📋 لديك <code>{len(servers)}</code> عناصر مستضافة:</b>", parse_mode=ParseMode.HTML)

    for srv in servers:
        status_emoji = "🟢" if srv.get("status", "Running") == "Running" else "⚫"
        srv_type = str(srv.get("type", "html")).upper()
        type_icon = "🌐"
        if "JS" in srv_type:
            type_icon = "🟨"
        elif "PHP" in srv_type:
            type_icon = "🐘"
        elif "PY" in srv_type:
            type_icon = "🐍"

        text = (
            "<b>━━━━━━━━━━━━━━━━━━━━</b>\n"
            f"{status_emoji} <b>{srv.get('name', srv.get('title', 'ملف'))}</b>\n"
            "<b>━━━━━━━━━━━━━━━━━━━━</b>\n"
            f"{type_icon} <b>نوع البيئة:</b> <code>{srv_type}</code>\n"
            f"<b>📊 الحالة:</b> <code>{srv.get('status', 'نشط')}</code>\n"
            f"<b>🔌 المنفذ/الرابط:</b> <code>{srv.get('port', 'متصل')}</code>"
        )
        folder = srv.get("id", srv.get("folder", ""))
        keyboard = [
            [
                InlineKeyboardButton("▶️ تشغيل", callback_data=f"srv_start|{folder}"),
                InlineKeyboardButton("⏹ إيقاف", callback_data=f"srv_stop|{folder}"),
                InlineKeyboardButton("🔄 إعادة تشغيل", callback_data=f"srv_restart|{folder}"),
            ],
            [
                InlineKeyboardButton("🖥 كونسول السيرفر", callback_data=f"console|{folder}"),
                InlineKeyboardButton("⚠️ الأخطاء", callback_data=f"errors|{folder}"),
                InlineKeyboardButton("🗑 حذف", callback_data=f"srv_delete|{folder}"),
            ],
            [InlineKeyboardButton("📦 تثبيت الحزم والمكتبات", callback_data=f"install|{folder}")],
        ]
        if query and query.message:
            await query.message.reply_text(text, parse_mode=ParseMode.HTML, reply_markup=InlineKeyboardMarkup(keyboard))

    if query and query.message:
        await query.message.reply_text(
            "<b>━━━━━━━━━━━━━━━━━━━━</b>",
            parse_mode=ParseMode.HTML,
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🔙 رجوع خطوة للخلف", callback_data="go_back")],
                [InlineKeyboardButton("🏠 القائمة الرئيسية", callback_data="main_menu")],
            ]),
        )


async def show_admin_panel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    push_nav_state(context, "admin_panel")
    query = update.callback_query
    if query:
        await query.answer()

    if not is_admin_tg(update):
        if query:
            await query.edit_message_text("<b>❌ غير مصرح لك بالدخول إلى لوحة الإدارة.</b>", parse_mode=ParseMode.HTML)
        return

    api_key = context.user_data.get("api_key") or f"ADMIN_{ADMIN_USERNAME}"
    result = api_request("/api/admin/users", api_key=api_key)
    users = result.get("users", []) if result and result.get("success") else []

    pending_result = api_request("/api/admin/pending", api_key=api_key)
    pending_count = len(pending_result.get("requests", [])) if pending_result and pending_result.get("success") else 0

    text = (
        "<b>━━━━━━━━━━━━━━━━━━━━</b>\n"
        "  <b>👑 لوحة إدارة 𝙼𝙴𝚁𝙾 𝙷𝙾𝚂𝚃</b>\n"
        "<b>━━━━━━━━━━━━━━━━━━━━</b>\n"
        f"<b>👥 إجمالي المستخدمين:</b> <code>{len(users)}</code>\n"
        f"<b>🔔 طلبات الحسابات المعلقة:</b> <code>{pending_count}</code>\n"
        "<b>━━━━━━━━━━━━━━━━━━━━</b>\n"
    )
    for u in users[:10]:
        text += f"• <code>{u.get('username')}</code> | الحالة: <b>{'نشط' if u.get('active') else 'موقوف'}</b>\n"
    if len(users) > 10:
        text += f"<i>... و {len(users) - 10} مستخدمين آخرين</i>\n"

    bell = f"🔔 الطلبات ({pending_count})" if pending_count > 0 else "🔕 لا طلبات"
    keyboard = [
        [
            InlineKeyboardButton(bell, callback_data="admin_notifications"),
            InlineKeyboardButton("📊 إحصائيات النظام", callback_data="admin_stats"),
        ],
        [InlineKeyboardButton("🗑 حذف مستخدم من المنصة", callback_data="admin_delete_user")],
        [InlineKeyboardButton("🔙 رجوع خطوة للخلف", callback_data="go_back")],
        [InlineKeyboardButton("🏠 القائمة الرئيسية", callback_data="main_menu")],
    ]
    if query:
        await query.edit_message_text(text, parse_mode=ParseMode.HTML, reply_markup=InlineKeyboardMarkup(keyboard))


async def show_admin_notifications(update: Update, context: ContextTypes.DEFAULT_TYPE):
    push_nav_state(context, "admin_notifications")
    query = update.callback_query
    if query:
        await query.answer()

    if not is_admin_tg(update):
        if query:
            await query.edit_message_text("<b>❌ غير مصرح.</b>", parse_mode=ParseMode.HTML)
        return

    api_key = context.user_data.get("api_key") or f"ADMIN_{ADMIN_USERNAME}"
    result = api_request("/api/admin/pending", api_key=api_key)
    if not result or not result.get("success"):
        if query:
            await query.edit_message_text("<b>❌ فشل جلب الإشعارات من السيرفر.</b>", parse_mode=ParseMode.HTML)
        return

    requests_list = result.get("requests", [])
    if not requests_list:
        if query:
            await query.edit_message_text(
                "<b>━━━━━━━━━━━━━━━━━━━━</b>\n"
                "<b>🔕 لا توجد طلبات حسابات معلقة</b>\n"
                "<b>━━━━━━━━━━━━━━━━━━━━</b>",
                parse_mode=ParseMode.HTML,
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 رجوع", callback_data="go_back")]]),
            )
        return

    if query:
        await query.edit_message_text(
            f"<b>━━━━━━━━━━━━━━━━━━━━</b>\n"
            f"<b>🔔 طلبات الحسابات الجديدة ({len(requests_list)})</b>\n"
            f"<b>━━━━━━━━━━━━━━━━━━━━</b>",
            parse_mode=ParseMode.HTML,
        )

    for req in requests_list:
        text = (
            f"<b>👤 اسم المستخدم:</b> <code>{req.get('username')}</code>\n"
            f"<b>📅 التاريخ:</b> <code>{str(req.get('created_at', ''))[:19]}</code>"
        )
        keyboard = [[
            InlineKeyboardButton("✅ قبول الحساب", callback_data=f"approve|{req.get('username')}"),
            InlineKeyboardButton("❌ رفض الحساب", callback_data=f"reject|{req.get('username')}"),
        ]]
        if query and query.message:
            await query.message.reply_text(text, parse_mode=ParseMode.HTML, reply_markup=InlineKeyboardMarkup(keyboard))

    if query and query.message:
        await query.message.reply_text(
            "<b>━━━━━━━━━━━━━━━━━━━━</b>",
            parse_mode=ParseMode.HTML,
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 رجوع", callback_data="go_back")]]),
        )


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["nav_stack"] = ["main_menu"]
    api_key = context.user_data.get("api_key")
    if api_key:
        result = api_request("/api/bot/verify", method="POST", data={"api_key": api_key})
        if result and result.get("success"):
            context.user_data["username"] = result.get("username")
            await show_main_menu(update, context)
            return ConversationHandler.END
        context.user_data.clear()

    keyboard = [
        [InlineKeyboardButton("🔑 إدخال API Key للربط", callback_data="enter_api")],
        [InlineKeyboardButton("🛒 الخدمات وطلب موقع", callback_data="services_menu")],
        [InlineKeyboardButton("💬 تواصل مع المطور @Y_20_20", url="https://t.me/Y_20_20")],
    ]
    await update.message.reply_text(
        "<b>━━━━━━━━━━━━━━━━━━━━</b>\n"
        "      <b>𝙼𝙴𝚁𝙾 𝙷𝙾𝚂𝚃 🚀</b>\n"
        "<b>━━━━━━━━━━━━━━━━━━━━</b>\n"
        "<b>منصة استضافة الملفات والخدمات الشاملة</b> (HTML, JS, PHP, Python)\n\n"
        "<b>للحصول على حساب مفعل:</b>\n"
        "<b>📬 تواصل مع المطور:</b> <code>@Y_20_20</code>\n\n"
        f"{DEVELOPER_INFO}",
        parse_mode=ParseMode.HTML,
        reply_markup=InlineKeyboardMarkup(keyboard),
    )
    return ConversationHandler.END


async def handle_api_key(update: Update, context: ContextTypes.DEFAULT_TYPE):
    api_key = update.message.text.strip()
    result = api_request("/api/bot/verify", method="POST", data={"api_key": api_key})
    if not result or not result.get("success"):
        keyboard = [
            [InlineKeyboardButton("💬 تواصل مع المطور", url="https://t.me/Y_20_20")],
            [InlineKeyboardButton("🔙 رجوع", callback_data="go_back")],
        ]
        await update.message.reply_text(
            "<b>❌ مفتاح API غير صالح أو خاطئ!</b>\n\n"
            "<i>تأكد من نسخه بدقة أو تواصل مع المطور:</i> <code>@Y_20_20</code>",
            parse_mode=ParseMode.HTML,
            reply_markup=InlineKeyboardMarkup(keyboard),
        )
        return WAITING_FOR_API_KEY

    context.user_data["api_key"] = api_key
    context.user_data["username"] = result.get("username")
    context.user_data["is_admin"] = result.get("is_admin", False)

    await update.message.reply_text(
        f"<b>✅ تم ربط الحساب بنجاح!</b>\n"
        f"<b>👤 أهلاً بك يا:</b> <code>{result.get('username')}</code>",
        parse_mode=ParseMode.HTML,
    )
    await show_main_menu(update, context)
    return ConversationHandler.END


async def receive_server_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    name = update.message.text.strip()
    context.user_data["pending_server_name"] = name
    keyboard = [
        [
            InlineKeyboardButton("🌐 HTML / HTM", callback_data="server_type_html"),
            InlineKeyboardButton("🟨 JavaScript", callback_data="server_type_js"),
        ],
        [
            InlineKeyboardButton("🐘 PHP Server", callback_data="server_type_php"),
            InlineKeyboardButton("🐍 Python / Bot", callback_data="server_type_python"),
        ],
        [InlineKeyboardButton("🔙 رجوع", callback_data="go_back")],
    ]
    await update.message.reply_text(
        f"<b>📦 اختر نوع بيئة التشغيل المستهدفة:</b>\n\n<b>اسم الملف/السيرفر:</b> <code>{name}</code>",
        parse_mode=ParseMode.HTML,
        reply_markup=InlineKeyboardMarkup(keyboard),
    )
    return WAITING_FOR_SERVER_TYPE


async def receive_server_type(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    type_mapping = {
        "server_type_html": "HTML",
        "server_type_js": "Node.js/JS",
        "server_type_php": "PHP",
        "server_type_python": "Python",
    }
    srv_type = type_mapping.get(query.data, "Python")
    name = context.user_data.get("pending_server_name", "Project")

    result = api_request("/api/bot/create_server", method="POST", data={
        "api_key": context.user_data.get("api_key"),
        "name": name,
        "server_type": srv_type,
        "plan": "free",
        "storage": 500,
        "ram": 512,
        "cpu": 1.0,
    })

    if result and result.get("success"):
        await query.edit_message_text(
            f"<b>✅ تم تجهيز السيرفر والبيئة بنجاح!</b>\n\n"
            f"<b>📛 الاسم:</b> <code>{name}</code>\n"
            f"<b>⚙️ النوع:</b> <code>{srv_type}</code>",
            parse_mode=ParseMode.HTML,
        )
    else:
        await query.edit_message_text(
            f"<b>❌ فشل إعداد السيرفر!</b>\n<i>{result.get('message', 'خطأ غير معروف') if result else 'خطأ'}</i>",
            parse_mode=ParseMode.HTML,
        )

    await show_main_menu(update, context, edit=False)
    return ConversationHandler.END


async def receive_service_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id if update.effective_user else 0
    svc_id = context.user_data.get("pending_service_id", "")
    details = (update.message.text or "").strip()

    res = execute_paid_service_order(uid, svc_id, details)
    if res.get("success"):
        await update.message.reply_text(
            f"<b>✅ تم تأكيد الدفع وإتمام التسليم بنجاح!</b>\n"
            f"<b>رقم الطلب:</b> <code>{res.get('order_id')}</code>\n"
            f"<b>الرصيد المتبقي:</b> <code>{res.get('balance', 0.0):.2f} USD</code>\n"
            f"<b>التفاصيل:</b> <code>{res.get('message')}</code>",
            parse_mode=ParseMode.HTML,
        )
    else:
        await update.message.reply_text(
            f"<b>⚠️ لم يكتمل الطلب:</b>\n<i>{res.get('message')}</i>\n"
            f"<b>الرصيد الحالي:</b> <code>{res.get('balance', get_balance(uid)):.2f} USD</code>",
            parse_mode=ParseMode.HTML,
        )
    await show_main_menu(update, context)
    return ConversationHandler.END


async def receive_topup_info(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id if update.effective_user else 0
    info_txt = (update.message.text or "").strip()
    topup_file = os.path.join(SERVICES_STORAGE_DIR, "topup_requests.json")
    db = _read_json(topup_file, {"requests": []})
    db["requests"].append({
        "user_id": uid,
        "info": info_txt,
        "status": "pending_payment_confirmation",
        "created_at": datetime.utcnow().isoformat(),
    })
    _atomic_write_json(topup_file, db)

    await update.message.reply_text(
        "<b>📩 تم تسجيل طلب شحن الرصيد بنجاح!</b>\n"
        "<i>لن يتم خصم أو إضافة أي رصيد نهائي قبل التحقق وتأكيد الدفع من الإدارة.</i>",
        parse_mode=ParseMode.HTML,
    )
    await show_main_menu(update, context)
    return ConversationHandler.END


async def show_console(update: Update, context: ContextTypes.DEFAULT_TYPE, folder: str):
    push_nav_state(context, "my_servers")
    query = update.callback_query
    result = api_request("/api/bot/console", params={"folder": folder}, api_key=context.user_data.get("api_key"))
    if result and result.get("success"):
        logs = result.get("logs", "لا توجد سجلات تشغيل حالية")
        if len(logs) > 3500:
            logs = "...\n" + logs[-3500:]
        keyboard = [[
            InlineKeyboardButton("🔄 تحديث السجلات", callback_data=f"console|{folder}"),
            InlineKeyboardButton("🔙 رجوع", callback_data="go_back"),
        ]]
        await query.edit_message_text(
            f"<b>🖥 كونسول السيرفر والبيئة</b>\n<pre>{logs}</pre>",
            parse_mode=ParseMode.HTML,
            reply_markup=InlineKeyboardMarkup(keyboard),
        )
    else:
        await query.edit_message_text("<b>❌ فشل جلب مخرجات الكونسول.</b>", parse_mode=ParseMode.HTML)


async def show_errors(update: Update, context: ContextTypes.DEFAULT_TYPE, folder: str):
    push_nav_state(context, "my_servers")
    query = update.callback_query
    result = api_request("/api/bot/errors", params={"folder": folder}, api_key=context.user_data.get("api_key"))
    if result and result.get("success"):
        errors = result.get("errors", "✅ ممتاز: لا توجد أي أخطاء مسجلة")
        if len(errors) > 3500:
            errors = "...\n" + errors[-3500:]
        keyboard = [[InlineKeyboardButton("🔙 رجوع", callback_data="go_back")]]
        await query.edit_message_text(
            f"<b>⚠️ سجل الأخطاء والتنبيهات</b>\n<pre>{errors}</pre>",
            parse_mode=ParseMode.HTML,
            reply_markup=InlineKeyboardMarkup(keyboard),
        )
    else:
        await query.edit_message_text("<b>❌ فشل جلب سجل الأخطاء.</b>", parse_mode=ParseMode.HTML)


async def admin_delete_user_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    push_nav_state(context, "admin_panel")
    query = update.callback_query
    await query.answer()
    if not is_admin_tg(update):
        await query.edit_message_text("<b>❌ غير مصرح لك بذلك.</b>", parse_mode=ParseMode.HTML)
        return ConversationHandler.END
    await query.edit_message_text(
        "<b>📝 أرسل الآن اسم المستخدم (Username) المراد حذفه نهائياً من المنصة:</b>",
        parse_mode=ParseMode.HTML,
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 رجوع", callback_data="go_back")]]),
    )
    return WAITING_FOR_DELETE_USERNAME


async def admin_delete_user_confirm(update: Update, context: ContextTypes.DEFAULT_TYPE):
    username = update.message.text.strip()
    api_key = context.user_data.get("api_key") or f"ADMIN_{ADMIN_USERNAME}"
    result = api_request("/api/admin/delete-user", method="POST", data={
        "api_key": api_key,
        "username": username,
    })
    if result and result.get("success"):
        await update.message.reply_text(f"<b>✅ تم حذف المستخدم</b> <code>{username}</code> <b>وجميع ملفاته بنجاح</b>", parse_mode=ParseMode.HTML)
    else:
        await update.message.reply_text(f"<b>❌ فشل الحذف:</b> <i>{result.get('message', 'خطأ غير متوقع') if result else 'خطأ'}</i>", parse_mode=ParseMode.HTML)
    await show_main_menu(update, context)
    return ConversationHandler.END


async def admin_stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    push_nav_state(context, "admin_panel")
    query = update.callback_query
    await query.answer()
    metrics = api_request("/api/system/metrics")
    cpu = metrics.get("cpu", "0") if metrics else "0"
    ram = metrics.get("memory", "0") if metrics else "0"
    disk = metrics.get("disk", "0") if metrics else "0"
    await query.edit_message_text(
        "<b>━━━━━━━━━━━━━━━━━━━━</b>\n"
        "  <b>📊 إحصائيات استهلاك النظام</b>\n"
        "<b>━━━━━━━━━━━━━━━━━━━━</b>\n"
        f"<b>🖥 استهلاك المعالج CPU:</b>  <code>{cpu}%</code>\n"
        f"<b>💾 استهلاك الذاكرة RAM:</b>  <code>{ram}%</code>\n"
        f"<b>💿 المساحة المستخدمة Disk:</b> <code>{disk}%</code>",
        parse_mode=ParseMode.HTML,
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 رجوع", callback_data="go_back")]]),
    )


async def _navigate_to_screen(update: Update, context: ContextTypes.DEFAULT_TYPE, screen: str):
    if screen == "main_menu":
        await show_main_menu(update, context, edit=True)
    elif screen == "my_servers":
        await show_servers_list(update, context)
    elif screen == "services_menu":
        await show_services_menu(update, context)
    elif screen == "wallet_menu":
        await show_wallet_menu(update, context)
    elif screen == "admin_panel":
        await show_admin_panel(update, context)
    elif screen == "admin_notifications":
        await show_admin_notifications(update, context)
    else:
        await show_main_menu(update, context, edit=True)


async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    data = query.data or ""

    if data == "go_back":
        prev_screen = pop_nav_state(context)
        await _navigate_to_screen(update, context, prev_screen)
        return ConversationHandler.END

    if data == "main_menu":
        await show_main_menu(update, context, edit=True)
        return ConversationHandler.END

    if data == "my_servers":
        await show_servers_list(update, context)
        return ConversationHandler.END

    if data == "services_menu":
        await show_services_menu(update, context)
        return ConversationHandler.END

    if data == "wallet_menu":
        await show_wallet_menu(update, context)
        return ConversationHandler.END

    if data == "topup_request":
        push_nav_state(context, "wallet_menu")
        await query.edit_message_text(
            "<b>💳 طلب شحن رصيد</b>\n\n"
            "<i>أرسل المبلغ المطلوب وتفاصيل الدفع (لن يُحتسب أو يُخصم أي رصيد إلا بعد التحقق والتأكيد):</i>",
            parse_mode=ParseMode.HTML,
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 رجوع", callback_data="go_back")]]),
        )
        return WAITING_FOR_TOPUP_INFO

    if data in ("enter_api", "change_api"):
        push_nav_state(context, "main_menu")
        context.user_data.pop("api_key", None)
        await query.edit_message_text(
            "<b>🔑 أدخل مفتاح الـ API الخاص بك أدناه:</b>\n\n"
            "<i>يمكنك استخراجه مباشرة من لوحة حسابك أو من المطور</i> <code>@Y_20_20</code>",
            parse_mode=ParseMode.HTML,
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 رجوع", callback_data="go_back")]]),
        )
        return WAITING_FOR_API_KEY

    if data == "logout":
        context.user_data.clear()
        await query.edit_message_text(
            "<b>🚪 تم تسجيل الخروج من جلستك بنجاح.</b>\n<i>استخدم الأمر</i> <code>/start</code> <i>لإعادة الدخول.</i>",
            parse_mode=ParseMode.HTML,
        )
        return ConversationHandler.END

    if data == "create_server":
        push_nav_state(context, "main_menu")
        await query.edit_message_text(
            "<b>➕ إنشاء سيرفر جديد أو رفع ملف استضافة</b>\n\n<b>📝 أرسل اسم السيرفر أو الملف:</b>",
            parse_mode=ParseMode.HTML,
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 رجوع", callback_data="go_back")]]),
        )
        return WAITING_FOR_NEW_SERVER_NAME

    if data == "admin_panel":
        await show_admin_panel(update, context)
        return ConversationHandler.END

    if data == "admin_notifications":
        await show_admin_notifications(update, context)
        return ConversationHandler.END

    if data == "admin_delete_user":
        return await admin_delete_user_start(update, context)

    if data == "admin_stats":
        await admin_stats(update, context)
        return ConversationHandler.END

    if "|" in data:
        cmd, value = data.split("|", 1)
        api_key = context.user_data.get("api_key") or f"ADMIN_{ADMIN_USERNAME}"

        if cmd == "buy_svc":
            svc = SERVICES_CATALOG.get(value)
            if not svc:
                await query.answer("الخدمة غير متاحة", show_alert=True)
                return ConversationHandler.END
            push_nav_state(context, "services_menu")
            context.user_data["pending_service_id"] = value
            await query.edit_message_text(
                f"<b>🛒 طلب خدمة: {svc['name']}</b>\n"
                f"<b>💵 السعر:</b> <code>{svc['price']:.2f} {svc['currency']}</code>\n\n"
                "<i>أرسل الآن تفاصيل الطلب أو رابط/اسم الموقع الإلكتروني المطلوب:</i>",
                parse_mode=ParseMode.HTML,
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 رجوع", callback_data="go_back")]]),
            )
            return WAITING_FOR_SERVICE_INPUT

        if cmd in ("srv_start", "srv_stop", "srv_restart", "srv_delete"):
            action = cmd.replace("srv_", "")
            result = api_request("/api/bot/server/action", method="POST", data={
                "api_key": api_key,
                "folder": value,
                "action": action,
            })
            if result and result.get("success"):
                await query.answer(result.get("message", "✅ تمت العملية بنجاح")[:200], show_alert=True)
            else:
                await query.answer(f"❌ {result.get('message', 'فشل التنفيذ') if result else 'خطأ'}"[:200], show_alert=True)
            await show_servers_list(update, context)

        elif cmd == "console":
            await show_console(update, context, value)

        elif cmd == "errors":
            await show_errors(update, context, value)

        elif cmd == "install":
            result = api_request("/api/bot/install", method="POST", data={
                "api_key": api_key,
                "folder": value,
            })
            msg = result.get("message", "✅ جاري تثبيت الحزم المطلوبة") if result and result.get("success") else f"❌ {result.get('message', 'فشل التثبيت') if result else 'خطأ'}"
            await query.edit_message_text(
                f"<b>📦 إدارة الحزم والمكتبات</b>\n\n<i>{msg}</i>",
                parse_mode=ParseMode.HTML,
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("🖥 فتح الكونسول", callback_data=f"console|{value}")],
                    [InlineKeyboardButton("🔙 رجوع", callback_data="go_back")],
                ]),
            )

        elif cmd == "approve":
            result = api_request("/api/admin/approve", method="POST", data={
                "api_key": api_key,
                "username": value,
            })
            msg = f"✅ تم قبول حساب المستخدم {value}" if result and result.get("success") else "❌ فشل قبول الحساب"
            await query.answer(msg, show_alert=True)
            await show_admin_notifications(update, context)

        elif cmd == "reject":
            result = api_request("/api/admin/reject", method="POST", data={
                "api_key": api_key,
                "username": value,
            })
            msg = f"🚫 تم رفض طلب الحساب {value}" if result and result.get("success") else "❌ فشل الرفض"
            await query.answer(msg, show_alert=True)
            await show_admin_notifications(update, context)

    return ConversationHandler.END


# ==============================================================================
# ٨. مشغّل البوتات الفرعية المدمج (Embedded Telegram Bot Runner)
# ==============================================================================
async def runner_start_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(
        "<b>👋 مرحباً! أنا بوت يعمل على 𝙼𝙴𝚁𝙾 𝙷𝙾𝚂𝚃</b>\n\n"
        "<b>الأوامر المتاحة:</b>\n"
        "• <code>/start</code> - عرض هذه الرسالة\n"
        "• <code>/help</code> - الحصول على المساعدة\n"
        "• <code>/info</code> - معلومات البوت\n\n"
        f"{DEVELOPER_INFO}",
        parse_mode=ParseMode.HTML,
    )


async def runner_help_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(
        "<b>📚 المساعدة:</b>\n\n"
        "<i>هذا البوت يعمل بشكل مستمر على خادم 𝙼𝙴𝚁𝙾 𝙷𝙾𝚂𝚃</i>\n"
        "<b>للاشتراك أو الاستفسار:</b> <code>@Y_20_20</code>",
        parse_mode=ParseMode.HTML,
    )


async def runner_info_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(
        "<b>ℹ️ معلومات البوت:</b>\n\n"
        "<b>🤖 الخدمة:</b> <code>𝙼𝙴𝚁𝙾 𝙷𝙾𝚂𝚃</code>\n"
        "<b>✅ الحالة:</b> <b>نشط ومستمر</b>\n"
        "<b>🛠 المطور:</b> <code>@Y_20_20</code>",
        parse_mode=ParseMode.HTML,
    )


async def runner_handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_message = update.message.text or ""
    await update.message.reply_text(
        f"<b>📨 تم استقبال رسالتك:</b>\n\n<blockquote>{user_message}</blockquote>\n"
        "<i>شكراً لاستخدامك 𝙼𝙴𝚁𝙾 𝙷𝙾𝚂𝚃!</i>\n"
        "<b>🛠</b> <code>@Y_20_20</code>",
        parse_mode=ParseMode.HTML,
    )


async def runner_error_handler(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    logger.error("Exception while handling runner update: %s", context.error)


def run_runner_bot(token: str, bot_name: str) -> None:
    try:
        logger.info("🤖 𝙼𝙴𝚁𝙾 𝙷𝙾𝚂𝚃 - تشغيل البوت الفرعي: %s", bot_name)
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        application = Application.builder().token(token).build()
        application.add_handler(CommandHandler("start", runner_start_cmd))
        application.add_handler(CommandHandler("help", runner_help_cmd))
        application.add_handler(CommandHandler("info", runner_info_cmd))
        application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, runner_handle_message))
        application.add_error_handler(runner_error_handler)
        application.run_polling(drop_pending_updates=True, stop_signals=None)
    except Exception as e:
        logger.error("❌ خطأ في تشغيل البوت %s: %s", bot_name, str(e))


# ==============================================================================
# ٩. التشغيل والاستمرارية (Startup, Flask Server & Telegram Bot Loop)
# ==============================================================================
def run_flask_server(port: int):
    ensure_index_html_exists()
    app.run(host="0.0.0.0", port=port, debug=False, use_reloader=False)


def build_and_run_main_bot():
    if not BOT_TOKEN:
        logger.warning("⚠️ BOT_TOKEN غير مضبوط — تم تخطي تشغيل بوت تيليجرام الرئيسي.")
        return

    while True:
        try:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            application = Application.builder().token(BOT_TOKEN).build()

            conv = ConversationHandler(
                entry_points=[
                    CommandHandler("start", start),
                    CallbackQueryHandler(button_callback, pattern="^(topup_request|enter_api|change_api|create_server|admin_delete_user|buy_svc\\|.*)$"),
                ],
                states={
                    WAITING_FOR_API_KEY: [
                        MessageHandler(filters.TEXT & ~filters.COMMAND, handle_api_key)
                    ],
                    WAITING_FOR_NEW_SERVER_NAME: [
                        MessageHandler(filters.TEXT & ~filters.COMMAND, receive_server_name)
                    ],
                    WAITING_FOR_SERVER_TYPE: [
                        CallbackQueryHandler(receive_server_type, pattern="^server_type_")
                    ],
                    WAITING_FOR_DELETE_USERNAME: [
                        MessageHandler(filters.TEXT & ~filters.COMMAND, admin_delete_user_confirm)
                    ],
                    WAITING_FOR_TOPUP_INFO: [
                        MessageHandler(filters.TEXT & ~filters.COMMAND, receive_topup_info)
                    ],
                    WAITING_FOR_SERVICE_INPUT: [
                        MessageHandler(filters.TEXT & ~filters.COMMAND, receive_service_input)
                    ],
                },
                fallbacks=[
                    CommandHandler("start", start),
                    CallbackQueryHandler(button_callback, pattern="^(go_back|main_menu)$"),
                ],
            )

            application.add_handler(conv)
            application.add_handler(CallbackQueryHandler(button_callback))
            logger.info("🚀 𝙼𝙴𝚁𝙾 𝙷𝙾𝚂𝚃 Bot يعمل بكفاءة تامة 24/7...")
            application.run_polling(drop_pending_updates=True, stop_signals=None)
        except Exception as e:
            logger.error("انقطاع مؤقت في البوت الرئيسي، إعادة الاتصال خلال 5 ثوانٍ: %s", e)
            time.sleep(5)


def _start_bot_background_once():
    if os.environ.get("RUN_BOT_ON_RENDER", "1") == "1" and os.environ.get("START_BOT_THREAD", "1") == "1":
        if not any(t.name == "MeroHostBotThread" for t in threading.enumerate()):
            bot_thread = threading.Thread(target=build_and_run_main_bot, name="MeroHostBotThread", daemon=True)
            bot_thread.start()
            logger.info("🤖 تم إطلاق خيط بوت 𝙼𝙴𝚁𝙾 𝙷𝙾𝚂𝚃 تلقائياً مع app.py")


ensure_index_html_exists()
_start_bot_background_once()
_start_keep_alive_once()


def main():
    ensure_index_html_exists()

    if len(sys.argv) >= 2 and sys.argv[1] not in ("--panel-only", "--bot-only", "--all"):
        token = sys.argv[1]
        bot_name = sys.argv[2] if len(sys.argv) > 2 else "mero_host_bot"
        run_runner_bot(token, bot_name)
        return

    mode = sys.argv[1] if len(sys.argv) >= 2 else "--all"

    if mode in ("--panel-only", "--all"):
        flask_thread = threading.Thread(target=run_flask_server, args=(PANEL_PORT_PRIMARY,), daemon=True)
        flask_thread.start()
        logger.info("🌐 خادم لوحة التحكم يعمل على المنفذ %s عبر index.html الموحد", PANEL_PORT_PRIMARY)

    if mode in ("--bot-only", "--all"):
        if not any(t.name == "MeroHostBotThread" for t in threading.enumerate()):
            build_and_run_main_bot()
        while True:
            time.sleep(60)
    else:
        while True:
            time.sleep(60)


if __name__ == "__main__":
    main()
