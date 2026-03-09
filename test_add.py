import sqlite3
from datetime import datetime, timedelta  # ВОТ ТУТ ДОБАВИЛ timedelta

# Подключаемся к базе
conn = sqlite3.connect('tasks.db')
cur = conn.cursor()

# Твой user_id в Telegram (узнай у @userinfobot)
user_id = 5032770220  # ← ЗАМЕНИ НА СВОЙ!

# Добавляем тестовую задачу
now = datetime.now()
task_time = (now + timedelta(minutes=2)).strftime("%H:%M")
task_date = now.date().isoformat()

cur.execute(
    """INSERT INTO tasks 
       (user_id, task_id, task_name, task_date, task_time, priority, created_at) 
       VALUES (?, ?, ?, ?, ?, ?, ?)""",
    (user_id, "test_123", "ТЕСТОВАЯ ЗАДАЧА", task_date, 
     task_time, "high", now.isoformat())
)
conn.commit()

# Проверяем, что добавилось
cur.execute("SELECT * FROM tasks")
tasks = cur.fetchall()
print(f"📋 Всего задач в БД: {len(tasks)}")
for task in tasks:
    print(task)

conn.close()
print("✅ Тестовая задача добавлена!")