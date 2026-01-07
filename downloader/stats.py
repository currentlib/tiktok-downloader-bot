import sqlite3
import re
from collections import Counter
from datetime import datetime, timedelta
import time
import threading

class StatsManager:
    def __init__(self, db_name="chat_stats.db"):
        self.db_name = db_name
        self._init_db()

    def _init_db(self):
        """Ініціалізація БД, якщо її не існує"""
        with sqlite3.connect(self.db_name) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS messages (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    username TEXT NOT NULL,
                    message_text TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            conn.commit()

    def log_message(self, username, text):
        """Цю функцію треба викликати кожного разу, коли приходить повідомлення"""
        with sqlite3.connect(self.db_name) as conn:
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO messages (username, message_text) VALUES (?, ?)",
                (username, text)
            )
            conn.commit()

    def get_daily_stats(self):
        """Генерує звіт за останні 24 години"""
        # Визначаємо часовий проміжок (останні 24 години)
        yesterday = datetime.now() - timedelta(days=1)
        
        with sqlite3.connect(self.db_name) as conn:
            cursor = conn.cursor()
            
            # 1. Отримуємо повідомлення тільки за останню добу
            cursor.execute(
                "SELECT username, message_text FROM messages WHERE created_at > ?", 
                (yesterday,)
            )
            data = cursor.fetchall()

        if not data:
            return None # Повідомлень не було

        # Обробка даних
        users = [row[0] for row in data]
        texts = [row[1] for row in data]
        total_messages = len(data)

        # Статистика: Топ юзерів
        top_users = Counter(users).most_common(3)

        # Статистика: Хмара слів (проста версія)
        all_text = " ".join(texts).lower()
        # Прибираємо спецсимволи і лишаємо тільки слова
        words = re.findall(r'\b\w+\b', all_text)
        
        # Список стоп-слів (щоб не рахувати прийменники)
        stop_words = {'і', 'та', 'а', 'але', 'що', 'як', 'це', 'в', 'на', 'до', 'з', 'не', 'я', 'ти', 'він'}
        filtered_words = [w for w in words if w not in stop_words and len(w) > 3]
        top_words = Counter(filtered_words).most_common(5)

        return {
            "total": total_messages,
            "top_users": top_users,
            "top_words": top_words
        }

    def format_report(self, stats):
        """Перетворює словник зі статистикою у гарний текст"""
        if not stats:
            return "Сьогодні в чаті була тиша... 🦗"

        report = f"📊 **Щоденна статистика чату**\n\n"
        report += f"💬 Всього повідомлень: {stats['total']}\n\n"
        
        report += "🏆 **Найактивніші балакуни:**\n"
        for idx, (user, count) in enumerate(stats['top_users'], 1):
            report += f"{idx}. {user} — {count} повідомлень\n"
        
        report += "\n🗣 **Слова дня:**\n"
        words_str = ", ".join([f"{w} ({c})" for w, c in stats['top_words']])
        report += words_str if words_str else "Замало даних для слів."

        return report

# --- Налаштування Планувальника (Scheduler) ---

def schedule_runner(stats_manager, send_callback, target_hour=9, target_minute=0):
    """
    Фоновий процес, який перевіряє час кожну хвилину.
    send_callback — це функція вашого бота, яка відправляє повідомлення в чат.
    """
    while True:
        now = datetime.now()
        # Перевіряємо, чи настав час (наприклад, 09:00)
        if now.hour == target_hour and now.minute == target_minute:
            
            # 1. Генеруємо звіт
            stats = stats_manager.get_daily_stats()
            text_report = stats_manager.format_report(stats)
            
            # 2. Відправляємо в чат (через callback)
            send_callback(text_report)
            
            # 3. Чекаємо 61 секунду, щоб не відправити двічі за одну хвилину
            time.sleep(61)
        else:
            # Перевіряємо раз на 30 секунд
            time.sleep(30)

# --- Приклад використання (Імітація бота) ---

# 1. Ініціалізація
stats_db = StatsManager()

# 2. Функція відправки (заміни її на реальний bot.send_message)
def mock_send_to_chat(text):
    print("\n--- [BOT SENDS MESSAGE] ---")
    print(text)
    print("---------------------------\n")

# 3. Запуск планувальника в окремому потоці (щоб бот не завис)
# Встановимо час на хвилину вперед від поточного для тесту
current_time = datetime.now()
sched_thread = threading.Thread(
    target=schedule_runner, 
    args=(stats_db, mock_send_to_chat, current_time.hour, current_time.minute + 1) # +1 хвилина для тесту
)
sched_thread.daemon = True # Потік закриється разом з основною програмою
sched_thread.start()

# 4. Імітація роботи бота (прийом повідомлень)
print("Бот запущено. Пишіть повідомлення (імітація)...")

# Імітуємо активність
stats_db.log_message("@alex", "Всім привіт, як справи?")
stats_db.log_message("@maria", "Привіт! Чудово, а в тебе?")
stats_db.log_message("@alex", "Та теж нічого, працюю над ботом")
stats_db.log_message("@ivan", "О, що за бот? Розкажи детальніше")
stats_db.log_message("@alex", "Бот для статистики. Статистика це круто")
stats_db.log_message("@alex", "Статистика статистика статистика") # Накручуємо слово

# Щоб скрипт не завершився одразу (у реальному боті тут `bot.polling()`)
try:
    while True:
        time.sleep(1)
except KeyboardInterrupt:
    print("Бот зупинено.")