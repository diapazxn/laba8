# config.py
import os
from dotenv import load_dotenv

# Завантажуємо змінні оточення з .env
load_dotenv()

# ТОКЕН БЕРЕМО З ЗМІННИХ ОТОЧЕННЯ. Тепер BOT_TOKEN буде коректно визначений.
BOT_TOKEN = os.getenv("BOT_TOKEN")

# Об'єднаний список валют, які бот відстежуватиме за замовчуванням
DEFAULT_TRACKED_SYMBOLS = ["BTC", "USDT", "SOL", "EUR", "USD"]