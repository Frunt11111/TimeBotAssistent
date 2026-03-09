import asyncio
import logging
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, WebAppInfo

# ================== НАСТРОЙКИ ==================
TOKEN = "8786657197:AAGcz1OLUZtEaLbPldGLsd64uL2U2Z6Ef6I"
WEBAPP_URL = "https://твой-домен.com/index.html"  # ЗАМЕНИТЬ НА РЕАЛЬНЫЙ URL

logging.basicConfig(level=logging.INFO)

bot = Bot(token=TOKEN)
dp = Dispatcher()

# ================== КОМАНДА START ==================
@dp.message(Command("start"))
async def cmd_start(message: Message):
    # Кнопка для открытия Mini App
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🚀 Открыть приложение", web_app=WebAppInfo(url=WEBAPP_URL))]
    ])
    
    await message.answer(
        f"👋 Привет, {message.from_user.first_name}!\n\n"
        "Нажми кнопку ниже, чтобы открыть Mini App 👇",
        reply_markup=keyboard
    )

# ================== ЗАПУСК ==================
async def main():
    print("🚀 Бот для Mini App запущен!")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
    