import os
import sys
import sqlite3
import json
import logging
from threading import Thread
from telebot import types, TeleBot

# Настройка логирования
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

with open("./config.json", "r") as file:
    config = json.load(file)

our_chat = "-1002205702962"

bot = TeleBot(config["7644663038:AAELmKLt_KswdXon_19OWYOZIBBpjjJLns0"])
commands = [
    types.BotCommand("new", "Новое голосование"),
    types.BotCommand("db", "Просмотреть базу данных"),
    types.BotCommand("del", "Удалить по UID из бд"),
    types.BotCommand("results", "Показать результаты последнего голосования")
]

bot.set_my_commands(commands)

class db:
    @staticmethod
    def init(name):
        with sqlite3.connect(name) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS surveys(
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    reg_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    title TEXT NOT NULL,
                    options TEXT NOT NULL,
                    answers TEXT DEFAULT NULL,
                    chat INTEGER NOT NULL
                )
            """)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS patterns(
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    title TEXT NOT NULL,
                    options TEXT NOT NULL
                )
            """)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS users(
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL UNIQUE
                )
            """)
            conn.commit()

    @staticmethod
    def select(path, table, conditions=None):
        try:
            with sqlite3.connect(path) as conn:
                cursor = conn.cursor()
                query = f"SELECT * FROM {table}"
                params = []
                if conditions:
                    query += " WHERE " + " AND ".join([f"{key} = ?" for key in conditions.keys()])
                    params = list(conditions.values())
                cursor.execute(query, params)
                return cursor.fetchall()
        except Exception as e:
            logging.error(f"Ошибка при выборке из БД: {e}")
            return None

    @staticmethod
    def update(path, table, update, conditions):
        try:
            with sqlite3.connect(path) as conn:
                cursor = conn.cursor()
                set_clause = ", ".join([f"{key} = ?" for key in update.keys()])
                where_clause = " AND ".join([f"{key} = ?" for key in conditions.keys()])
                query = f"UPDATE {table} SET {set_clause} WHERE {where_clause}"
                params = list(update.values()) + list(conditions.values())
                cursor.execute(query, params)
                conn.commit()
                return db.select(path, table, conditions)
        except Exception as e:
            logging.error(f"Ошибка при обновлении БД: {e}")
            return None

    @staticmethod
    def insert(path, table, data):
        try:
            with sqlite3.connect(path) as conn:
                cursor = conn.cursor()
                columns = ", ".join(data.keys())
                placeholders = ", ".join(["?"] * len(data))
                query = f"INSERT INTO {table} ({columns}) VALUES ({placeholders})"
                cursor.execute(query, list(data.values()))
                conn.commit()
                return db.select(path, table)
        except Exception as e:
            logging.error(f"Ошибка при вставке в БД: {e}")
            return None

    @staticmethod
    def delete(path, table, conditions=None):
        try:
            with sqlite3.connect(path) as conn:
                cursor = conn.cursor()
                query = f"DELETE FROM {table}"
                params = []
                if conditions:
                    query += " WHERE " + " AND ".join([f"{key} = ?" for key in conditions.keys()])
                    params = list(conditions.values())
                cursor.execute(query, params)
                conn.commit()
                return True
        except Exception as e:
            logging.error(f"Ошибка при удалении из БД: {e}")
            return False

@bot.message_handler(commands=['results'], func=lambda message: message.chat.type == 'private' and message.from_user.id in config["ADMINS"])
def info_survey(message):
    surveys = db.select("survey.db", "surveys")
    if not surveys:
        bot.send_message(message.chat.id, "Нет доступных опросов.")
        return
    
    surv = surveys[-1]  # Последний опрос
    surv_id = surv[0]
    
    try:
        questions = json.loads(surv[4] or "{}")
        answers = json.loads(surv[3] or "{}")
    except json.JSONDecodeError:
        bot.send_message(message.chat.id, "Ошибка обработки JSON данных.")
        return

    ans = f"Дата начала: {surv[1]}\n\n"
    for k, v in questions.items():
        ans += f"{k}: {v} - {answers.get(k, 0)} голосов\n"
    
    bot.send_message(message.chat.id, ans)

if __name__ == "__main__":
    db.init("survey.db")
    bot.infinity_polling()
