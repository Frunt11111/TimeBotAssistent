import asyncio
import logging
import sqlite3
from datetime import datetime, timedelta
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.types import Message, ReplyKeyboardMarkup, KeyboardButton, WebAppInfo, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from apscheduler.schedulers.asyncio import AsyncIOScheduler
import json

# ================== НАСТРОЙКИ ==================
TOKEN = "8786657197:AAGcz1OLUZtEaLbPldGLsd64uL2U2Z6Ef6I"
WEBAPP_URL = "https://frunt11111.github.io/TimeBotAssistent/"
DND_START = 22  # 22:00
DND_END = 8     # 08:00

logging.basicConfig(level=logging.INFO)

# ================== БАЗА ДАННЫХ ==================
def init_db():
    conn = sqlite3.connect('tasks.db')
    cur = conn.cursor()
    # Таблица задач
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
    # Таблица привычек
    cur.execute('''
        CREATE TABLE IF NOT EXISTS habits (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            habit_name TEXT,
            current_streak INTEGER DEFAULT 0,
            best_streak INTEGER DEFAULT 0,
            last_check TEXT,
            created_at TEXT
        )
    ''')
    # Таблица помидорок
    cur.execute('''
        CREATE TABLE IF NOT EXISTS pomodoro (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            sessions INTEGER DEFAULT 0,
            date TEXT
        )
    ''')
    conn.commit()
    conn.close()
    print("✅ База данных готова (с новыми таблицами)")

# ================== ИНИЦИАЛИЗАЦИЯ ==================
storage = MemoryStorage()
bot = Bot(token=TOKEN)
dp = Dispatcher(storage=storage)
scheduler = AsyncIOScheduler()

# ================== КОМАНДА START ==================
@dp.message(Command("start"))
async def cmd_start(message: Message):
    keyboard = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="🚀 Открыть приложение", web_app=WebAppInfo(url=WEBAPP_URL))],
            [KeyboardButton(text="📋 Сегодня"), KeyboardButton(text="📅 Неделя")],
            [KeyboardButton(text="📋 Все задачи"), KeyboardButton(text="✅ Выполненные")],
            [KeyboardButton(text="🔥 Привычки"), KeyboardButton(text="🍅 Помидор"), KeyboardButton(text="📊 Статистика")],
            [KeyboardButton(text="❓ Помощь")]
        ],
        resize_keyboard=True
    )
    await message.answer(
        f"👋 Привет, {message.from_user.first_name}!\n\n"
        "Я TimeBot Assistant – помогу не забывать о делах и следить за привычками.\n"
        "Нажимай кнопки ниже или открой приложение.",
        reply_markup=keyboard
    )

# ================== ПОЛУЧЕНИЕ ДАННЫХ ИЗ MINI APP ==================
@dp.message(F.web_app_data)
async def handle_webapp_data(message: Message):
    print("📩 Получены данные из Mini App")
    try:
        data = json.loads(message.web_app_data.data)
        user_id = message.from_user.id
        print(f"👤 Пользователь: {user_id}, Данные: {data}")

        if data['action'] == 'add':
            task = data['task']
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
        elif data['action'] == 'delete':
            task_id = data['taskId']
            conn = sqlite3.connect('tasks.db')
            cur = conn.cursor()
            cur.execute("DELETE FROM tasks WHERE user_id = ? AND task_id = ?", (user_id, str(task_id)))
            conn.commit()
            conn.close()
            await message.answer("🗑️ Задача удалена из напоминаний")
    except Exception as e:
        print(f"❌ Ошибка: {e}")
        await message.answer("❌ Ошибка при обработке данных")

# ================== ПРИВЫЧКИ ==================
class HabitStates(StatesGroup):
    waiting_for_name = State()

@dp.message(lambda msg: msg.text == "🔥 Привычки")
@dp.message(Command("habits"))
async def habits_menu(message: Message):
    user_id = message.from_user.id
    conn = sqlite3.connect('tasks.db')
    cur = conn.cursor()
    cur.execute("SELECT id, habit_name, current_streak, best_streak FROM habits WHERE user_id = ?", (user_id,))
    habits = cur.fetchall()
    conn.close()
    if not habits:
        await message.answer("У вас пока нет привычек. Создайте командой /addhabit")
        return
    text = "📋 **Ваши привычки:**\n\n"
    for h in habits:
        text += f"• {h[1]} – 🔥 {h[2]} дней (рекорд: {h[3]})\n   ✅ /check_{h[0]}  |  ❌ /del_habit_{h[0]}\n"
    await message.answer(text, parse_mode="Markdown")

@dp.message(Command("addhabit"))
async def add_habit_start(message: Message, state: FSMContext):
    await state.set_state(HabitStates.waiting_for_name)
    await message.answer("Введите название привычки (например: «Зарядка»):")

@dp.message(HabitStates.waiting_for_name)
async def add_habit_finish(message: Message, state: FSMContext):
    habit_name = message.text.strip()
    user_id = message.from_user.id
    conn = sqlite3.connect('tasks.db')
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO habits (user_id, habit_name, created_at) VALUES (?, ?, ?)",
        (user_id, habit_name, datetime.now().isoformat())
    )
    conn.commit()
    conn.close()
    await state.clear()
    await message.answer(f"✅ Привычка «{habit_name}» добавлена! Отмечайте её выполнение командой /check_номер")

@dp.message(lambda msg: msg.text and msg.text.startswith('/check_'))
async def check_habit(message: Message):
    try:
        habit_id = int(message.text.replace('/check_', ''))
        user_id = message.from_user.id
        conn = sqlite3.connect('tasks.db')
        cur = conn.cursor()
        # Получаем текущие данные привычки
        cur.execute("SELECT last_check, current_streak, best_streak FROM habits WHERE id = ? AND user_id = ?", (habit_id, user_id))
        row = cur.fetchone()
        if not row:
            await message.answer("❌ Привычка не найдена")
            conn.close()
            return
        last_check_str, current_streak, best_streak = row
        today = datetime.now().date()
        if last_check_str:
            last_check = datetime.fromisoformat(last_check_str).date()
            if last_check == today:
                await message.answer("Вы уже отмечали эту привычку сегодня!")
                conn.close()
                return
            elif last_check == today - timedelta(days=1):
                # подряд
                current_streak += 1
            else:
                # пропуск
                current_streak = 1
        else:
            current_streak = 1
        # обновляем лучший streak
        if current_streak > best_streak:
            best_streak = current_streak
        cur.execute(
            "UPDATE habits SET last_check = ?, current_streak = ?, best_streak = ? WHERE id = ?",
            (today.isoformat(), current_streak, best_streak, habit_id)
        )
        conn.commit()
        conn.close()
        await message.answer(f"✅ Отлично! Текущая серия: {current_streak} дней")
    except Exception as e:
        await message.answer("❌ Ошибка")

@dp.message(lambda msg: msg.text and msg.text.startswith('/del_habit_'))
async def delete_habit(message: Message):
    try:
        habit_id = int(message.text.replace('/del_habit_', ''))
        user_id = message.from_user.id
        conn = sqlite3.connect('tasks.db')
        cur = conn.cursor()
        cur.execute("DELETE FROM habits WHERE id = ? AND user_id = ?", (habit_id, user_id))
        conn.commit()
        conn.close()
        await message.answer("🗑️ Привычка удалена")
    except:
        await message.answer("❌ Ошибка")

# ================== ПОМИДОРНЫЙ ТАЙМЕР ==================
pomodoro_tasks = {}  # user_id -> (chat_id, task_name)

@dp.message(lambda msg: msg.text == "🍅 Помидор")
@dp.message(Command("pomodoro"))
async def pomodoro_start(message: Message):
    await message.answer(
        "🍅 Помидорный таймер\n"
        "Напишите название задачи, над которой будете работать (или просто нажмите /pomodorogo):"
    )

@dp.message(Command("pomodorogo"))
async def pomodoro_go(message: Message):
    await start_pomodoro(message.from_user.id, message.chat.id, "Без названия")

async def start_pomodoro(user_id, chat_id, task_name):
    if user_id in pomodoro_tasks:
        await bot.send_message(chat_id, "У вас уже запущен помидор! Сначала завершите его.")
        return
    pomodoro_tasks[user_id] = (chat_id, task_name)
    await bot.send_message(chat_id, f"🍅 Таймер на 25 минут запущен! Задача: {task_name}\nРаботайте без отвлечений.")
    scheduler.add_job(
        finish_pomodoro,
        'date',
        run_date=datetime.now() + timedelta(minutes=25),
        args=[user_id]
    )

async def finish_pomodoro(user_id):
    if user_id not in pomodoro_tasks:
        return
    chat_id, task_name = pomodoro_tasks.pop(user_id)
    # Проверка режима не беспокоить
    if not can_send_notification():
        # отложим отправку на утро
        scheduler.add_job(
            lambda: bot.send_message(chat_id, f"⏰ Помидор завершён! Задача: {task_name}. Время отдохнуть."),
            'date',
            run_date=datetime.now().replace(hour=9, minute=0, second=0) + timedelta(days=1)
        )
    else:
        await bot.send_message(chat_id, f"⏰ Помидор завершён! Задача: {task_name}. Время отдохнуть.")
    # Сохраняем статистику
    conn = sqlite3.connect('tasks.db')
    cur = conn.cursor()
    today = datetime.now().date().isoformat()
    cur.execute(
        "INSERT INTO pomodoro (user_id, sessions, date) VALUES (?, 1, ?)",
        (user_id, today)
    )
    conn.commit()
    conn.close()

# ================== СТАТИСТИКА ==================
@dp.message(lambda msg: msg.text == "📊 Статистика")
@dp.message(Command("stats"))
async def show_stats(message: Message):
    user_id = message.from_user.id
    today = datetime.now().date()
    week_ago = (today - timedelta(days=7)).isoformat()
    conn = sqlite3.connect('tasks.db')
    cur = conn.cursor()
    # Задачи выполненные за неделю
    cur.execute(
        "SELECT COUNT(*) FROM tasks WHERE user_id = ? AND completed = 1 AND task_date >= ?",
        (user_id, week_ago)
    )
    tasks_done = cur.fetchone()[0]
    # Просроченные активные задачи
    cur.execute(
        "SELECT COUNT(*) FROM tasks WHERE user_id = ? AND completed = 0 AND task_date < ?",
        (user_id, today.isoformat())
    )
    overdue = cur.fetchone()[0]
    # Помидорки за неделю
    cur.execute(
        "SELECT SUM(sessions) FROM pomodoro WHERE user_id = ? AND date >= ?",
        (user_id, week_ago)
    )
    pomos = cur.fetchone()[0] or 0
    # Привычки
    cur.execute("SELECT COUNT(*) FROM habits WHERE user_id = ?", (user_id,))
    habits_count = cur.fetchone()[0]
    cur.execute("SELECT current_streak FROM habits WHERE user_id = ? ORDER BY current_streak DESC LIMIT 1")
    best_streak_row = cur.fetchone()
    best_streak = best_streak_row[0] if best_streak_row else 0
    conn.close()
    text = (
        f"📊 **Ваша статистика за неделю**\n\n"
        f"✅ Выполнено задач: {tasks_done}\n"
        f"⚠️ Просрочено задач: {overdue}\n"
        f"🍅 Помидорок: {pomos}\n"
        f"🔥 Привычек: {habits_count}, лучшая серия: {best_streak} дн.\n\n"
        "Так держать!"
    )
    await message.answer(text, parse_mode="Markdown")

# ================== ПРОСМОТР ЗАДАЧ (оставляем как есть, но можно добавить inline-кнопки для отметки) ==================
@dp.message(lambda msg: msg.text == "📋 Сегодня")
@dp.message(Command("today"))
async def show_today(message: Message):
    user_id = message.from_user.id
    today = datetime.now().date().isoformat()
    conn = sqlite3.connect('tasks.db')
    cur = conn.cursor()
    cur.execute(
        "SELECT id, task_name, task_time, priority FROM tasks WHERE user_id = ? AND task_date = ? AND completed = 0 ORDER BY task_time",
        (user_id, today)
    )
    tasks = cur.fetchall()
    conn.close()
    if not tasks:
        await message.answer("🎉 На сегодня задач нет!")
        return
    text = "📋 **Задачи на сегодня:**\n\n"
    for t in tasks:
        prio = {"high": "🔥", "medium": "⭐", "low": "✅"}.get(t[3], "⭐")
        text += f"{prio} {t[1]} – {t[2]}\n   ✅ /done_{t[0]}  |  ❌ /del_{t[0]}\n"
    await message.answer(text, parse_mode="Markdown")

@dp.message(lambda msg: msg.text == "📅 Неделя")
@dp.message(Command("week"))
async def show_week(message: Message):
    user_id = message.from_user.id
    today = datetime.now().date()
    week_later = today + timedelta(days=7)
    conn = sqlite3.connect('tasks.db')
    cur = conn.cursor()
    cur.execute(
        "SELECT task_name, task_date, task_time, priority FROM tasks WHERE user_id = ? AND completed = 0 ORDER BY task_date, task_time",
        (user_id,)
    )
    all_tasks = cur.fetchall()
    conn.close()
    week_tasks = [t for t in all_tasks if today <= datetime.strptime(t[1], "%Y-%m-%d").date() <= week_later]
    if not week_tasks:
        await message.answer("📅 На неделю задач нет.")
        return
    text = "📅 **Задачи на неделю:**\n\n"
    for t in week_tasks:
        date_obj = datetime.strptime(t[1], "%Y-%m-%d")
        date_str = date_obj.strftime("%d.%m")
        prio = {"high": "🔥", "medium": "⭐", "low": "✅"}.get(t[3], "⭐")
        text += f"{prio} {t[0]} – {date_str} {t[2]}\n"
    await message.answer(text, parse_mode="Markdown")

@dp.message(lambda msg: msg.text == "📋 Все задачи")
@dp.message(Command("all"))
async def show_all(message: Message):
    user_id = message.from_user.id
    conn = sqlite3.connect('tasks.db')
    cur = conn.cursor()
    cur.execute(
        "SELECT id, task_name, task_date, task_time, priority FROM tasks WHERE user_id = ? AND completed = 0 ORDER BY task_date, task_time",
        (user_id,)
    )
    tasks = cur.fetchall()
    conn.close()
    if not tasks:
        await message.answer("📋 Нет активных задач.")
        return
    text = "📋 **Все задачи:**\n\n"
    for t in tasks:
        prio = {"high": "🔥", "medium": "⭐", "low": "✅"}.get(t[4], "⭐")
        date_obj = datetime.strptime(t[2], "%Y-%m-%d")
        date_str = date_obj.strftime("%d.%m")
        text += f"🆔 {t[0]} {prio} {t[1]} – {date_str} {t[3]}\n   ✅ /done_{t[0]}  |  ❌ /del_{t[0]}\n"
    await message.answer(text, parse_mode="Markdown")

@dp.message(lambda msg: msg.text and msg.text.startswith('/done_'))
async def done_task(message: Message):
    try:
        task_id = int(message.text.replace('/done_', ''))
        user_id = message.from_user.id
        conn = sqlite3.connect('tasks.db')
        cur = conn.cursor()
        cur.execute("UPDATE tasks SET completed = 1 WHERE id = ? AND user_id = ?", (task_id, user_id))
        conn.commit()
        conn.close()
        await message.answer("✅ Задача выполнена!")
    except:
        await message.answer("❌ Ошибка")

@dp.message(lambda msg: msg.text and msg.text.startswith('/del_'))
async def delete_task(message: Message):
    try:
        task_id = int(message.text.replace('/del_', ''))
        user_id = message.from_user.id
        conn = sqlite3.connect('tasks.db')
        cur = conn.cursor()
        cur.execute("DELETE FROM tasks WHERE id = ? AND user_id = ?", (task_id, user_id))
        conn.commit()
        conn.close()
        await message.answer("🗑️ Задача удалена")
    except:
        await message.answer("❌ Ошибка")

# ================== ПОМОЩЬ ==================
@dp.message(lambda msg: msg.text == "❓ Помощь")
@dp.message(Command("help"))
async def help_message(message: Message):
    text = (
        "📌 **Команды бота:**\n"
        "/start – главное меню\n"
        "➕ Добавить задачу – через кнопку ниже\n"
        "/today – задачи на сегодня\n"
        "/week – задачи на неделю\n"
        "/all – все задачи\n"
        "/habits – управление привычками\n"
        "/addhabit – создать привычку\n"
        "/pomodoro – запустить таймер\n"
        "/stats – статистика\n\n"
        "Также можно использовать кнопки внизу экрана."
    )
    await message.answer(text, parse_mode="Markdown")

# ================== НАПОМИНАНИЯ С УЧЁТОМ DND ==================
def can_send_notification(now=None):
    if now is None:
        now = datetime.now().hour
    if DND_START <= now or now < DND_END:
        return False
    return True

async def check_reminders():
    print("⏰ Запуск проверки напоминаний...")
    try:
        conn = sqlite3.connect('tasks.db')
        cur = conn.cursor()
        now = datetime.now()
        today = now.date().isoformat()
        cur.execute(
            "SELECT id, user_id, task_name, task_time FROM tasks WHERE task_date = ? AND completed = 0 AND reminded = 0",
            (today,)
        )
        tasks = cur.fetchall()
        for task in tasks:
            task_id, user_id, task_name, task_time = task
            task_dt = datetime.strptime(f"{today} {task_time}", "%Y-%m-%d %H:%M")
            minutes_left = (task_dt - now).total_seconds() / 60
            if 29.5 < minutes_left <= 30.5:  # примерно 30 минут
                if not can_send_notification():
                    # откладываем на утро
                    scheduler.add_job(
                        lambda uid=user_id, name=task_name, tt=task_time: bot.send_message(
                            uid, f"⏰ Доброе утро! Напоминаю: сегодня в {tt} – {name}"
                        ),
                        'date',
                        run_date=datetime.now().replace(hour=9, minute=0, second=0) + timedelta(days=1)
                    )
                else:
                    await bot.send_message(
                        user_id,
                        f"⏰ **Напоминание!** Через 30 минут: {task_name} в {task_time}"
                    )
                cur.execute("UPDATE tasks SET reminded = 1 WHERE id = ?", (task_id,))
                conn.commit()
        conn.close()
    except Exception as e:
        print(f"Ошибка в напоминаниях: {e}")

# ================== ЗАПУСК ==================
async def main():
    init_db()
    scheduler.add_job(check_reminders, 'interval', minutes=1)
    scheduler.start()
    print("🚀 Бот с полным функционалом запущен!")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())