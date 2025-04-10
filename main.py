#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import json
import re
import logging
from datetime import datetime
from dotenv import load_dotenv
from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters,
)

# Загрузка переменных окружения из .env файла
load_dotenv()

# Настройка логирования
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
    handlers=[
        logging.FileHandler("log.txt", encoding="utf-8"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Получение токена и ID админа из .env файла
BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = os.getenv("ADMIN_ID")

if not BOT_TOKEN:
    logger.error("❌ Ошибка: BOT_TOKEN не найден в .env файле")
    exit(1)

# Логгируем значение ADMIN_ID для отладки
logger.info(f"Загружен ADMIN_ID: {ADMIN_ID}")

# Паттерны для поиска ключевых слов
PATTERNS = [
    r"\bаху[йеё]\b",
    r"\bвахуй\b",  # Добавлено "вахуй"
    r"\bафиг\b",
    r"\bафіг\b",  # С украинской "і"
    r"\bв\s*аф[иі]ге\b",
    r"\bв\s*афігі\b",  # С украинской "і"
    r"\bох[уе]е[втлн]\b",
    r"\bобал?де[втлн]\b",
    r"\bв\s*шоке\b",
    r"\bшок\b",
    r"\bне\s*мог[уе]?\s*поверить\b",
    r"\bwtf\b"  # Добавлено англоязычное выражение
]

# Компиляция регулярных выражений для повышения производительности
COMPILED_PATTERNS = [re.compile(pattern, re.IGNORECASE) for pattern in PATTERNS]

# Путь к файлу со статистикой
COUNTER_FILE = "counter.json"

# Функции для работы со статистикой
def load_counter():
    """Загрузка статистики из файла"""
    try:
        if os.path.exists(COUNTER_FILE):
            with open(COUNTER_FILE, "r", encoding="utf-8") as file:
                return json.load(file)
    except Exception as e:
        logger.error(f"Ошибка при загрузке счетчика: {e}")
    return {}

def save_counter(counter):
    """Сохранение статистики в файл"""
    try:
        with open(COUNTER_FILE, "w", encoding="utf-8") as file:
            json.dump(counter, file, ensure_ascii=False, indent=2)
    except Exception as e:
        logger.error(f"Ошибка при сохранении счетчика: {e}")

def increment_counter(user_id, username, first_name, chat_id):
    """Увеличение счетчика пользователя"""
    counter = load_counter()
    
    # Преобразуем ID в строки для совместимости с JSON
    chat_id_str = str(chat_id)
    user_id_str = str(user_id)
    
    # Инициализация счетчика для чата, если его нет
    if chat_id_str not in counter:
        counter[chat_id_str] = {}
    
    # Инициализация счетчика для пользователя, если его нет
    if user_id_str not in counter[chat_id_str]:
        counter[chat_id_str][user_id_str] = {
            "count": 0,
            "username": username or None,
            "firstName": first_name or None,
            "lastUpdate": None
        }
    
    # Увеличение счетчика и обновление данных
    counter[chat_id_str][user_id_str]["count"] += 1
    counter[chat_id_str][user_id_str]["lastUpdate"] = datetime.now().isoformat()
    
    # Обновление имени пользователя, если оно изменилось
    if username and counter[chat_id_str][user_id_str]["username"] != username:
        counter[chat_id_str][user_id_str]["username"] = username
    
    if first_name and counter[chat_id_str][user_id_str]["firstName"] != first_name:
        counter[chat_id_str][user_id_str]["firstName"] = first_name
    
    save_counter(counter)
    return counter[chat_id_str][user_id_str]["count"]

def format_stats(chat_stats):
    """Форматирование статистики для вывода"""
    if not chat_stats:
        return "Никто еще не ахуел! Будьте первым 😉"
    
    # Преобразование данных в список для сортировки
    users = [
        {
            "user_id": user_id,
            "count": data["count"],
            "username": data.get("username"),
            "firstName": data.get("firstName")
        }
        for user_id, data in chat_stats.items()
    ]
    
    # Сортировка по убыванию счетчика
    users.sort(key=lambda x: x["count"], reverse=True)
    
    result = "🏆 Рейтинг ахуевших:\n\n"
    
    for index, user in enumerate(users):
        # Определение медали для первых трех мест
        if index == 0:
            medal = "🥇"
        elif index == 1:
            medal = "🥈"
        elif index == 2:
            medal = "🥉"
        else:
            medal = f"{index + 1}."
        
        # Определение имени пользователя для отображения с HTML-ссылкой
        if user["username"]:
            name = f'<a href="https://t.me/{user["username"]}">{user["username"]}</a>'
        elif user["firstName"]:
            name = user["firstName"]
        else:
            name = "Безымянный"
        
        result += f"{medal} {name}: {user['count']} раз(а)\n"
    
    return result

def reset_counter(chat_id=None):
    """Сбросить счетчик для всего чата или для всех чатов, если chat_id=None"""
    counter = load_counter()
    
    if chat_id:
        # Сброс счетчика для конкретного чата
        chat_id_str = str(chat_id)
        if chat_id_str in counter:
            # Обнуляем счетчики для всех пользователей в чате
            for user_id in counter[chat_id_str]:
                counter[chat_id_str][user_id]["count"] = 0
                counter[chat_id_str][user_id]["lastUpdate"] = datetime.now().isoformat()
            
            save_counter(counter)
            return f"Счетчики для чата {chat_id_str} сброшены"
        else:
            return f"Чат {chat_id_str} не найден в статистике"
    else:
        # Сброс всех счетчиков во всех чатах
        for chat_id_str in counter:
            for user_id in counter[chat_id_str]:
                counter[chat_id_str][user_id]["count"] = 0
                counter[chat_id_str][user_id]["lastUpdate"] = datetime.now().isoformat()
        
        save_counter(counter)
        return "Счетчики для всех чатов сброшены"

# Обработчики команд
async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик команды /start"""
    message = (
        "Привет! Я бот, который следит за выражениями удивления в чате.\n\n"
        "Я подсчитываю, кто сколько раз \"ахуел\" и веду статистику.\n\n"
        "Используйте /help чтобы узнать больше."
    )
    
    await update.message.reply_text(message)
    logger.info(f"Пользователь {update.effective_user.id} ({update.effective_user.username or update.effective_user.first_name}) запустил бота")

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик команды /help"""
    message = (
        "• 🔍 Бот автоматически отслеживает выражения удивления в сообщениях\n"
        "• 🏆 Показывает топ ахуевших в чате /ahuy"
    )
    
    await update.message.reply_text(message)
    logger.info(f"Пользователь {update.effective_user.id} ({update.effective_user.username or update.effective_user.first_name}) запросил помощь")

async def stats_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик команды для показа статистики"""
    chat_id = str(update.effective_chat.id)
    counter = load_counter()
    
    if chat_id not in counter or not counter[chat_id]:
        await update.message.reply_text("Никто еще не ахуел! Будьте первым 😉")
        return
    
    stats = format_stats(counter[chat_id])
    # Использовать HTML для кликабельных ссылок и отключить превью веб-страницы
    await update.message.reply_html(stats, disable_web_page_preview=True)
    
    logger.info(f"Пользователь {update.effective_user.id} ({update.effective_user.username or update.effective_user.first_name}) запросил статистику в чате {chat_id}")

async def reset_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик команды /rsahuy для сброса счетчиков (только для админа)"""
    user_id = str(update.effective_user.id)
    
    # Для отладки выводим ID пользователя и ID админа из конфига
    logger.info(f"Попытка сброса: user_id={user_id}, ADMIN_ID={ADMIN_ID}")
    
    # Проверка прав администратора
    if not ADMIN_ID or user_id != str(ADMIN_ID):
        # Не отвечаем в чате, просто логируем попытку
        logger.warning(f"Пользователь {user_id} попытался выполнить команду сброса без прав доступа")
        return
    
    chat_id = update.effective_chat.id
    result = reset_counter(chat_id)
    
    await update.message.reply_text(result)
    logger.info(f"Админ {user_id} сбросил счетчики в чате {chat_id}")

async def process_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик текстовых сообщений"""
    if not update.message or not update.message.text:
        return
    
    text = update.message.text
    user = update.effective_user
    chat_id = update.effective_chat.id
    
    # Проверка на ключевые слова
    matched = any(pattern.search(text) for pattern in COMPILED_PATTERNS)
    
    if matched:
        new_count = increment_counter(
            user.id, 
            user.username, 
            user.first_name, 
            chat_id
        )
        
        logger.info(f"Пользователь {user.id} ({user.username or user.first_name}) ахуел {new_count} раз(а) в чате {chat_id}")
        
        # Убираем автоматические ответы на сообщения
        # Счетчик продолжает работать, но бот не пишет в чат

def main():
    """Запуск бота"""
    # Создание приложения и передача токена
    application = Application.builder().token(BOT_TOKEN).build()
    
    # Добавление обработчиков команд
    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CommandHandler("help", help_command))
    
    # Обработчики для команд показа статистики
    # Команды должны быть только на латинице, кириллица не поддерживается в CommandHandler
    for command in ["ahuy", "top"]:
        application.add_handler(CommandHandler(command, stats_command))
    
    # Добавление обработчика для команды сброса счетчиков
    # Регистрируем обе возможные команды для сброса
    application.add_handler(CommandHandler("rsahuy", reset_command))
    application.add_handler(CommandHandler("rssahuy", reset_command))  # Добавлена альтернативная команда
    
    # Обработчик текстовых сообщений
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, process_message))
    
    # Запуск бота
    logger.info("🚀 Бот успешно запущен")
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()