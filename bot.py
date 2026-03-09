import asyncio
import logging
import sqlite3
from datetime import datetime, timedelta
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, WebAppInfo
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

# ================== КОМАНДА START ==================
@dp.message(Command("start"))
async def cmd_start(message: Message):
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🚀 Открыть приложение", web_app=WebAppInfo(url=WEBAPP_URL))]
    ])
    
    await message.answer(
        f"👋 Привет, {message.from_user.first_name}!\n\n"
        "Я буду присылать напоминания о задачах, которые ты добавишь в приложении.",
        reply_markup=keyboard
    )

# ================== ПОЛУЧЕНИЕ ДАННЫХ ИЗ MINI APP ==================
@dp.message()
async def handle_webapp_data(message: Message):
    """Получает данные из Mini App"""
    print("📩 Получено сообщение")
    
    # Проверяем, есть ли web_app_data
    if message.web_app_data:
        print(f"📦 Данные из Mini App: {message.web_app_data.data}")
        
        try:
            data = json.loads(message.web_app_data.data)
            user_id = message.from_user.id
            print(f"👤 Пользователь: {user_id}")
            print(f"📊 Данные: {data}")
            
            if data['action'] == 'add':
                task = data['task']
                print(f"➕ Добавление задачи: {task}")
                
                # Сохраняем в базу
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
                print(f"🗑️ Удаление задачи: {task_id}")
                
                conn = sqlite3.connect('tasks.db')
                cur = conn.cursor()
                cur.execute(
                    "DELETE FROM tasks WHERE user_id = ? AND task_id = ?",
                    (user_id, str(task_id))
                )
                conn.commit()
                conn.close()
                
                await message.answer("🗑️ Задача удалена из напоминаний")
                print("✅ Задача удалена из БД")
                
        except Exception as e:
            print(f"❌ Ошибка: {e}")
            await message.answer("❌ Ошибка при сохранении задачи")
    
    # Если это обычное сообщение
    else:
        print(f"💬 Обычное сообщение: {message.text}")
        
# ================== НАПОМИНАНИЯ ==================
async def check_reminders():
    """Проверяет задачи и отправляет напоминания"""
    print("⏰ Запуск проверки напоминаний...")
    try:
        conn = sqlite3.connect('tasks.db')
        cur = conn.cursor()
        
        now = datetime.now()
        today = now.date().isoformat()
        current_time = now.strftime("%H:%M")
        
        print(f"📅 Сегодня: {today}, Сейчас: {current_time}")
        
        # Ищем все задачи на сегодня
        cur.execute(
            """SELECT user_id, task_name, task_time, id 
               FROM tasks 
               WHERE task_date = ? AND completed = 0""",
            (today,)
        )
        tasks = cur.fetchall()
        
        print(f"📋 Найдено задач на сегодня: {len(tasks)}")
        
        for task in tasks:
            user_id, task_name, task_time, task_id = task
            print(f"  ➡️ Задача: {task_name}, Время: {task_time}")
            
            # Сравниваем время
            try:
                task_dt = datetime.strptime(f"{today} {task_time}", "%Y-%m-%d %H:%M")
                minutes_left = (task_dt - now).total_seconds() / 60
                
                print(f"     ⏱️ До задачи: {minutes_left:.1f} минут")
                
                # Если до задачи осталось от 1 до 30 минут
                if 0 < minutes_left <= 30:
                    print(f"     ✅ НУЖНО ОТПРАВИТЬ НАПОМИНАНИЕ!")
                    
                    # Проверяем, отправляли ли уже
                    cur.execute(
                        "SELECT reminded FROM tasks WHERE id = ?",
                        (task_id,)
                    )
                    reminded = cur.fetchone()[0]
                    
                    if reminded == 0:
                        # Отправляем сообщение
                        await bot.send_message(
                            user_id,
                            f"⏰ **Напоминание!**\n"
                            f"Через {int(minutes_left)} минут: {task_name}\n"
                            f"⏱️ {task_time}"
                        )
                        print(f"     ✅ Сообщение отправлено пользователю {user_id}")
                        
                        # Отмечаем, что напомнили
                        cur.execute(
                            "UPDATE tasks SET reminded = 1 WHERE id = ?",
                            (task_id,)
                        )
                        conn.commit()
                    else:
                        print(f"     ⏭️ Уже напоминали")
                else:
                    print(f"     ⏭️ Еще рано (или уже поздно)")
                    
            except Exception as e:
                print(f"     ❌ Ошибка обработки задачи: {e}")
        
        conn.close()
        print("✅ Проверка завершена")
        
    except Exception as e:
        print(f"❌ Ошибка в check_reminders: {e}")

# ================== ЗАПУСК ==================
async def main():
    init_db()
    scheduler.add_job(check_reminders, 'interval', minutes=1)
    scheduler.start()
    print("🚀 Бот для Mini App с напоминаниями запущен!")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())