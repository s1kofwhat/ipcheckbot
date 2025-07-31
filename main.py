import asyncio
import requests
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command

# === ТОКЕН БОТА ===
BOT_TOKEN = "***"

# ✅  API — РАБОТАЕТ БЕЗ ТОКЕНА
GEO_API_URL = "http://ip-api.com/json/"

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()


def get_ip_info(ip: str) -> str:
    try:
        # Запрос к ip-api.com
        response = requests.get(
            GEO_API_URL + ip,
            params={"lang": "ru", "fields": "status,message,country,city,regionName,lat,lon"},
            timeout=10
        )

        # Логируем ответ
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

        # Ссылка на карту
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
        # 🔐 ВАЖНО: НЕ отправляй сырые ошибки в Telegram!
        # Чтобы избежать "can't parse entities", экранируем
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

    # Проверка формата IPv4
    import re
    if not re.fullmatch(r"^(?:[0-9]{1,3}\.){3}[0-9]{1,3}$", ip):
        await message.reply("❌ Введите корректный IPv4-адрес.")
        return

    # Приватные IP (не имеют геолокации)
    private_ranges = [
        ip.startswith("192.168."),
        ip.startswith("10."),
        ip.startswith("172.") and 16 <= int(ip.split(".")[1]) <= 31,
        ip == "127.0.0.1"
    ]
    if any(private_ranges):
        await message.reply("🔒 Это приватный (внутренний) IP-адрес. У него нет внешней геолокации.")
        return

    # Показываем "поиск..."
    sent = await message.reply("🔍 Определяем местоположение...")

    # Получаем данные
    result = get_ip_info(ip)

    # Редактируем сообщение
    try:
        await sent.edit_text(result, parse_mode="HTML", disable_web_page_preview=True)
    except Exception as e:
        print(f"🔹 Ошибка при отправке в Telegram: {e}")
        await sent.edit_text("❌ Не удалось отобразить результат.")

async def main():
    print("✅ Бот запущен и готов к работе.")
    await dp.start_polling(bot)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("Бот остановлен.")
