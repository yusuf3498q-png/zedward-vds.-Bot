import telebot
import os
import json
import subprocess
import time
import signal
from threading import Lock
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton

API_KEY = '9280190146:AAEAVwMGyTy5nqMpHNOIHN1Ra-W8pi8mogQ' #botfather tokeni girin
ADMIN_ID = 8940836716  #telegram idinizi girin
SCRIPT_FOLDER = 'user_scripts'
DATA_FILE = 'user_data.json'

bot = telebot.TeleBot(API_KEY)
os.makedirs(SCRIPT_FOLDER, exist_ok=True)

user_data = {}
cooldowns = {}
lock = Lock()

if os.path.exists(DATA_FILE):
    with open(DATA_FILE, 'r') as f:
        user_data = json.load(f)

def save_data():
    with open(DATA_FILE, 'w') as f:
        json.dump(user_data, f)

def stop_script(user_id):
    info = user_data.get(str(user_id))
    if info and "pid" in info:
        try:
            os.kill(info["pid"], signal.SIGTERM)
        except Exception:
            pass
        file_path = info.get("file")
        if file_path and os.path.exists(file_path):
            os.remove(file_path)
        del user_data[str(user_id)]
        save_data()

def create_main_menu():
    markup = InlineKeyboardMarkup()
    markup.add(
        InlineKeyboardButton("Dosya Ekle", callback_data="add_file"),
        InlineKeyboardButton("Dosya Sil", callback_data="delete_file")
    )
    markup.add(
        InlineKeyboardButton("Mevcut Dosya", callback_data="show_file")
    )
    markup.add(
        InlineKeyboardButton("ADMİN", url="http://t.me/ketoxhuporj")  #ketoxhup
    )
    return markup

@bot.message_handler(commands=['start'])
def handle_start(message):
    user_id = message.from_user.id
    bot.send_message(user_id, "Bot sadece Telegram botlarını çalıştırmak için kullanılabilir. Lütfen yalnızca .py dosyası gönderin.")
    time.sleep(2)
    bot.send_message(user_id, "Hoş geldin! Aşağıdaki menüden seçim yapabilirsin:", reply_markup=create_main_menu())

@bot.message_handler(commands=['sil'])
def handle_delete(message):
    user_id = message.from_user.id
    stop_script(user_id)
    bot.reply_to(message, "Dosyan silindi ve çalışan script durduruldu.")

@bot.message_handler(content_types=['document'])
def handle_document(message):
    user_id = message.from_user.id
    chat_id = message.chat.id
    now = time.time()

    if user_id in cooldowns and now - cooldowns[user_id] < 5:
        bot.reply_to(message, "Lütfen 5 saniye bekleyin...")
        return
    cooldowns[user_id] = now

    doc = message.document
    if not doc.file_name.endswith('.py'):
        bot.reply_to(message, "Sadece .py uzantılı dosyaları kabul ediyorum.")
        return

    with lock:
        stop_script(user_id)
        file_info = bot.get_file(doc.file_id)
        downloaded = bot.download_file(file_info.file_path)

        local_path = os.path.join(SCRIPT_FOLDER, f"{user_id}_{doc.file_name}")
        with open(local_path, 'wb') as f:
            f.write(downloaded)

        try:
            proc = subprocess.Popen(['python', local_path])
            user_data[str(user_id)] = {
                "file": local_path,
                "pid": proc.pid,
                "time": int(time.time())
            }
            save_data()
            bot.reply_to(message, f"Dosya yüklendi ve çalıştırıldı.\nPID: {proc.pid}")
        except Exception as e:
            bot.reply_to(message, f"Hata oluştu: {e}")
            if os.path.exists(local_path):
                os.remove(local_path)

@bot.callback_query_handler(func=lambda call: True)
def handle_callback(call):
    user_id = call.from_user.id
    data = call.data

    if data == "add_file":
        bot.send_message(user_id, "Bir .py dosyası gönderin.")
    elif data == "delete_file":
        stop_script(user_id)
        bot.send_message(user_id, "Dosyan silindi ve çalışan script durduruldu.")  #ketoxhuporj
    elif data == "show_file":
        info = user_data.get(str(user_id))
        if info:
            bot.send_message(user_id, f"Yüklü dosyan: {os.path.basename(info['file'])}")
        else:
            bot.send_message(user_id, "Yüklü dosyan yok.")

@bot.message_handler(commands=['ms'])
def admin_message_all(message):
    if message.from_user.id == ADMIN_ID:
        try:
            text = message.text.split(' ', 1)[1]
            for uid in user_data:
                try:
                    bot.send_message(int(uid), f"[Admin Mesajı]\n{text}")
                except Exception as e:
                    print(f"Mesaj gönderilirken hata oluştu: {e}")
            bot.reply_to(message, "Mesaj gönderildi.")
        except IndexError:
            bot.reply_to(message, "Mesajı eksiksiz yaz.")
    else:
        bot.reply_to(message, "Yetkin yok.")

@bot.message_handler(commands=['k'])
def admin_list_users(message):
    if message.from_user.id == ADMIN_ID:
        users = "\n".join(user_data.keys()) or "Kayıtlı kullanıcı yok."
        bot.reply_to(message, f"Kayıtlı kullanıcılar:\n{users}")
    else:
        bot.reply_to(message, "Yetkin yok.")

import atexit
atexit.register(lambda: [stop_script(int(uid)) for uid in list(user_data.keys())])  #ketoxhuporj

print("Bot aktif.")
bot.polling(none_stop=True)