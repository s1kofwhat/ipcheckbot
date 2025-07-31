# main.py
import asyncio
import requests
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
from flask import Flask
import threading
import os
from dotenv import load_dotenv

# 🔁 Загружаем .env (только для локальной разработки)
load_dotenv()

# === ТОКЕН БОТА ===
BOT_TOKEN = os.getenv("BOT_TOKEN")
if not BOT_TOKEN:
    raise ValueError("Токен бота не найден! Убедись, что добавил BOT_TOKEN в Secrets или в .env")

# 🌐 Веб-сервер для keep-alive (для Replit)
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


# 🎯 Клавиатура с кнопками
def get_keyboard():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="🌐 Отправить свой IP")],
            [KeyboardButton(text="❓ Как использовать?")]
        ],
        resize_keyboard=True,
        one_time_keyboard=False
    )


@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    await message.answer(
        "👋 Привет! Я помогу определить геолокацию по IP-адресу.\n\n"
        "Нажми кнопку ниже или отправь любой публичный IP (например, <code>8.8.8.8</code>).",
        parse_mode="HTML",
        reply_markup=get_keyboard()
    )


@dp.message()
async def handle_message(message: types.Message):
    text = message.text.strip()

    # 🌐 Обработка: "Отправить свой IP"
    if text == "🌐 Отправить свой IP":
        # Telegram передаёт IP пользователя через заголовки, но мы можем использовать сторонний сервис
        try:
            ip_response = requests.get("https://api.ipify.org", timeout=5)
            if ip_response.status_code == 200:
                user_ip = ip_response.text
                sent = await message.reply(f"🔍 Определяем местоположение вашего IP: <code>{user_ip}</code>...", parse_mode="HTML")
                result = get_ip_info(user_ip)
                await sent.edit_text(result, parse_mode="HTML", disable_web_page_preview=True)
            else:
                await message.reply("❌ Не удалось определить ваш IP.")
        except Exception as e:
            print(f"🔹 Ошибка получения IP: {e}")
            await message.reply("❌ Ошибка при определении вашего IP.")
        return

    # ❓ Обработка: "Как использовать?"
    elif text == "❓ Как использовать?":
        await message.reply(
            "📘 <b>Как пользоваться ботом:</b>\n\n"
            "1️⃣ Отправьте любой публичный IPv4-адрес, например: <code>8.8.8.8</code>\n"
            "2️⃣ Бот покажет страну, город и координаты\n"
            "3️⃣ Нажмите на ссылку с координатами — откроется Google Карты\n\n"
            "🔒 Приватные IP (вроде 192.168.0.1) не имеют геолокации.",
            parse_mode="HTML"
        )
        return

    # 📬 Обработка введённого IP
    import re
    if not re.fullmatch(r"^(?:[0-9]{1,3}\.){3}[0-9]{1,3}$", text):
        await message.reply("❌ Введите корректный IPv4-адрес.")
        return

    private_ranges = [
        text.startswith("192.168."),
        text.startswith("10."),
        text.startswith("172.") and 16 <= int(text.split(".")[1]) <= 31,
        text == "127.0.0.1"
    ]
    if any(private_ranges):
        await message.reply("🔒 Это приватный (внутренний) IP-адрес. У него нет внешней геолокации.")
        return

    sent = await message.reply("🔍 Определяем местоположение...")
    result = get_ip_info(text)

    try:
        await sent.edit_text(result, parse_mode="HTML", disable_web_page_preview=True)
    except Exception as e:
        print(f"🔹 Ошибка при отправке в Telegram: {e}")
        await sent.edit_text("❌ Не удалось отобразить результат.")


async def main():
    # Запускаем веб-сервер (для Replit)
    keep_alive()
    print("✅ Веб-сервер запущен для keep-alive")

    print("✅ Бот запущен и готов к работе.")
    await dp.start_polling(bot)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("Бот остановлен.")
