import asyncio
import logging
import sqlite3
from datetime import datetime, timedelta
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.types import Message, ReplyKeyboardMarkup, KeyboardButton, WebAppInfo
from apscheduler.schedulers.asyncio import AsyncIOScheduler
import json

# ================== НАСТРОЙКИ ==================
TOKEN = "8786657197:AAGcz1OLUZtEaLbPldGLsd64uL2U2Z6Ef6I"
WEBAPP_URL = "https://frunt11111.github.io/TimeBotAssistent/"

logging.basicConfig(level=logging.INFO)

# ================== БАЗА ДАННЫХ ==================
def init_db():
    conn = sqlite3.connect('tasks.db')
    cur = conn.cursor()
    cur.execute('''
        CREATE TABLE IF NOT EXISTS tasks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            task_id TEXT,
            task_name TEXT,
            task_date TEXT,
            task_time TEXT,
            priority TEXT,
            completed INTEGER DEFAULT 0,
            reminded INTEGER DEFAULT 0,
            created_at TEXT
        )
    ''')
    conn.commit()
    conn.close()
    print("✅ База данных готова")

# ================== ИНИЦИАЛИЗАЦИЯ ==================
bot = Bot(token=TOKEN)
dp = Dispatcher()
scheduler = AsyncIOScheduler()

# ================== КОМАНДА START (ReplyKeyboardMarkup) ==================
@dp.message(Command("start"))
async def cmd_start(message: Message):
    # Кнопка в нижнем меню – единственный способ заставить работать sendData()
    keyboard = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="🚀 Открыть приложение", web_app=WebAppInfo(url=WEBAPP_URL))]
        ],
        resize_keyboard=True
    )
    await message.answer(
        f"👋 Привет, {message.from_user.first_name}!\n\n"
        "Нажми кнопку ниже, чтобы открыть приложение 👇",
        reply_markup=keyboard
    )

# ================== ПОЛУЧЕНИЕ ДАННЫХ ИЗ MINI APP (ТОЧНЫЙ ФИЛЬТР) ==================
@dp.message(F.web_app_data)
async def handle_webapp_data(message: Message):
    print("📩 Получены данные из Mini App")
    try:
        data = json.loads(message.web_app_data.data)
        user_id = message.from_user.id
        print(f"👤 Пользователь: {user_id}")
        print(f"📊 Данные: {data}")

        if data['action'] == 'add':
            task = data['task']
            print(f"➕ Добавление задачи: {task}")

            conn = sqlite3.connect('tasks.db')
            cur = conn.cursor()
            cur.execute(
                """INSERT INTO tasks 
                   (user_id, task_id, task_name, task_date, task_time, priority, created_at) 
                   VALUES (?, ?, ?, ?, ?, ?, ?)""",
                (user_id, str(task['id']), task['name'], task['date'], task['time'],
                 task['priority'], datetime.now().isoformat())
            )
            conn.commit()
            conn.close()

            await message.answer(f"✅ Задача '{task['name']}' добавлена! Напомню за 30 минут.")
            print("✅ Задача сохранена в БД")

        elif data['action'] == 'delete':
            task_id = data['taskId']
            conn = sqlite3.connect('tasks.db')
            cur = conn.cursor()
            cur.execute("DELETE FROM tasks WHERE user_id = ? AND task_id = ?", (user_id, str(task_id)))
            conn.commit()
            conn.close()
            await message.answer("🗑️ Задача удалена из напоминаний")
            print("✅ Задача удалена из БД")

    except Exception as e:
        print(f"❌ Ошибка обработки: {e}")
        await message.answer("❌ Ошибка при получении данных")

# ================== НАПОМИНАНИЯ ==================
async def check_reminders():
    print("⏰ Запуск проверки напоминаний...")
    try:
        conn = sqlite3.connect('tasks.db')
        cur = conn.cursor()
        now = datetime.now()
        today = now.date().isoformat()

        cur.execute(
            "SELECT user_id, task_name, task_time, id FROM tasks WHERE task_date = ? AND completed = 0",
            (today,)
        )
        tasks = cur.fetchall()
        print(f"📋 Найдено задач на сегодня: {len(tasks)}")

        for user_id, task_name, task_time, task_id in tasks:
            try:
                task_dt = datetime.strptime(f"{today} {task_time}", "%Y-%m-%d %H:%M")
                minutes_left = (task_dt - now).total_seconds() / 60
                if 0 < minutes_left <= 30:
                    # Проверяем, отправляли ли уже
                    cur.execute("SELECT reminded FROM tasks WHERE id = ?", (task_id,))
                    reminded = cur.fetchone()[0]
                    if reminded == 0:
                        await bot.send_message(
                            user_id,
                            f"⏰ **Напоминание!**\nЧерез {int(minutes_left)} минут: {task_name}\n⏱️ {task_time}"
                        )
                        cur.execute("UPDATE tasks SET reminded = 1 WHERE id = ?", (task_id,))
                        conn.commit()
                        print(f"✅ Напоминание отправлено пользователю {user_id}")
                    else:
                        print("⏭️ Уже напоминали")
                else:
                    print("⏭️ Ещё рано / уже поздно")
            except Exception as e:
                print(f"Ошибка обработки задачи {task_id}: {e}")
        conn.close()
    except Exception as e:
        print(f"Ошибка в check_reminders: {e}")

# ================== ЗАПУСК ==================
async def main():
    init_db()
    scheduler.add_job(check_reminders, 'interval', minutes=1)
    scheduler.start()
    print("🚀 Бот для Mini App с напоминаниями запущен!")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())