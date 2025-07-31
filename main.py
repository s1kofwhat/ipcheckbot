# main.py
import asyncio
import requests
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from flask import Flask
import threading
import os
from dotenv import load_dotenv  # 🔁 Загрузка .env

# 🔋 Загружаем .env (работает только локально, на Render — игнорируется)
load_dotenv()

# === ТОКЕН БОТА ===
BOT_TOKEN = os.getenv("BOT_TOKEN")
if not BOT_TOKEN:
    raise ValueError("Токен бота не найден! Убедись, что добавил BOT_TOKEN в Secrets или в .env")

# 🌐 Веб-сервер для keep-alive (чтобы Replit не засыпал)
app = Flask('')

@app.route('/')
def home():
    return "<h1>IP Geolocation Bot is running!</h1>"

def run_flask():
    app.run(host='0.0.0.0', port=8080)

def keep_alive():
    t = threading.Thread(target=run_flask)
    t.daemon = True
    t.start()

# === API для геолокации ===
GEO_API_URL = "http://ip-api.com/json/"

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

def get_ip_info(ip: str) -> str:
    try:
        response = requests.get(
            GEO_API_URL + ip,
            params={"lang": "ru", "fields": "status,message,country,city,regionName,lat,lon"},
            timeout=10
        )

        print(f"🔹 API Response [{ip}]: {response.status_code} — {response.text}")

        if response.status_code != 200:
            return "❌ Ошибка соединения с сервисом определения геолокации."

        data = response.json()

        if data.get("status") == "fail":
            return f"❌ Не удалось определить местоположение: {data.get('message', 'Неизвестная ошибка')}"

        country = data.get("country", "Не указано")
        city = data.get("city", "Не указано")
        region = data.get("regionName", "Не указано")
        lat = data.get("lat")
        lon = data.get("lon")

        if lat is not None and lon is not None:
            coords = f"<a href='https://maps.google.com/?q={lat},{lon}'>{lat}, {lon}</a>"
        else:
            coords = "Нет данных"

        return (
            f"📍 Информация по IP: <b>{ip}</b>\n\n"
            f"🌍 Страна: {country}\n"
            f"🏙 Город: {city}\n"
            f"📍 Регион: {region}\n"
            f"🗺 Координаты: {coords}"
        )

    except Exception as e:
        print(f"🔹 Ошибка при запросе: {e}")
        return "❌ Произошла ошибка при обработке запроса."

@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    await message.answer(
        "👋 Привет! Отправь мне IP-адрес (например, <code>8.8.8.8</code>), "
        "и я определю его геопозицию."
    )

@dp.message()
async def handle_ip(message: types.Message):
    ip = message.text.strip()

    import re
    if not re.fullmatch(r"^(?:[0-9]{1,3}\.){3}[0-9]{1,3}$", ip):
        await message.reply("❌ Введите корректный IPv4-адрес.")
        return

    private_ranges = [
        ip.startswith("192.168."),
        ip.startswith("10."),
        ip.startswith("172.") and 16 <= int(ip.split(".")[1]) <= 31,
        ip == "127.0.0.1"
    ]
    if any(private_ranges):
        await message.reply("🔒 Это приватный (внутренний) IP-адрес. У него нет внешней геолокации.")
        return

    sent = await message.reply("🔍 Определяем местоположение...")
    result = get_ip_info(ip)

    try:
        await sent.edit_text(result, parse_mode="HTML", disable_web_page_preview=True)
    except Exception as e:
        print(f"🔹 Ошибка при отправке в Telegram: {e}")
        await sent.edit_text("❌ Не удалось отобразить результат.")

async def main():
    # 🔹 Запускаем веб-сервер (для Replit)
    keep_alive()
    print("✅ Веб-сервер запущен для keep-alive")

    print("✅ Бот запущен и готов к работе.")
    await dp.start_polling(bot)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("Бот остановлен.")
