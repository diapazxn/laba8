# main.py
import asyncio
import json
import logging
import os
import sys

from aiogram import Bot, Dispatcher, Router, F, types
from aiogram.enums import ParseMode
from aiogram.filters import Command, CommandObject
from aiogram.types import Message, CallbackQuery
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.client.default import DefaultBotProperties  # <-- ВИПРАВЛЕННЯ 1: НОВИЙ ІМПОРТ

# Імпортуємо налаштування з config.py та функції з scraper.py
from config import BOT_TOKEN, DEFAULT_TRACKED_SYMBOLS
from scraper import get_crypto_price

# Файл для збереження користувацьких валют
TRACKED_COINS_FILE = 'tracked_coins.json'


# --- 💾 Збереження/Завантаження Даних ---

def load_tracked_coins():
    """Завантажує відстежувані монети з файлу або повертає дефолтний список."""
    if os.path.exists(TRACKED_COINS_FILE):
        try:
            with open(TRACKED_COINS_FILE, 'r') as f:
                return json.load(f)
        except json.JSONDecodeError:
            print("Попередження: файл tracked_coins.json порожній або пошкоджений.")
            pass
    return {"general_list": DEFAULT_TRACKED_SYMBOLS}


def save_tracked_coins(coins_data):
    """Зберігає відстежувані монети у файл."""
    with open(TRACKED_COINS_FILE, 'w') as f:
        json.dump(coins_data, f, indent=4)


# --- 🎯 Ініціалізація Списку та Роутера ---

tracked_coins = load_tracked_coins()
if "general_list" not in tracked_coins:
    tracked_coins["general_list"] = DEFAULT_TRACKED_SYMBOLS

router = Router()


# --- 🔑 Допоміжна функція для Клавіатури ---

def get_catalog_keyboard():
    """Створює Inline-клавіатуру з відстежуваними монетами (версія aiogram)."""
    symbols = tracked_coins.get("general_list", DEFAULT_TRACKED_SYMBOLS)
    builder = InlineKeyboardBuilder()

    for symbol in symbols:
        builder.button(text=symbol, callback_data=f'check_{symbol}')

    builder.adjust(3)
    return builder.as_markup()


# --- 🚀 Обробники Команд (aiogram) ---

@router.message(Command("start"))
async def start_command(message: Message):
    """Обробник команди /start. Відображає гайд."""
    intro_message = (
        "👋 **Вітаю в Крипто-Чекері!**\n\n"
        "Я бот, який перевіряє ціни криптовалют.\n\n"
        "**📚 Як користуватися:**\n"
        "1. **Каталог (Кнопки)**: Натисніть команду /catalog, щоб побачити список монет. Натискання на кнопку покаже ціну.\n"
        "2. **Командою**: Напишіть `/price [СИМВОЛ]`, наприклад, `/price BTC` або `/price EUR`.\n"
        "3. **Додати Монету**: Напишіть `/add [СИМВОЛ]`.\n"
        "4. **Видалити Монету**: Напишіть `/remove [СИМВОЛ]`.\n\n"
        "Спробуйте /catalog, щоб почати!"
    )
    # Ми встановлюємо parse_mode за замовчуванням, тому тут його можна не вказувати
    await message.answer(intro_message)


@router.message(Command("catalog"))
async def catalog_command(message: Message):
    """Обробник команди /catalog. Надсилає кнопки."""
    reply_markup = get_catalog_keyboard()
    await message.answer(
        "⬇️ **Каталог Валют** (Натисніть на монету, щоб перевірити ціну):",
        reply_markup=reply_markup
    )


@router.message(Command("price"))
async def price_command(message: Message, command: CommandObject):
    """Обробник команди /price [СИМВОЛ]."""
    if not command.args:
        await message.answer(
            "Будь ласка, вкажіть символ монети. Формат: `/price [СИМВОЛ]`"
        )
        return

    symbol = command.args.upper()
    await message.answer(f"⏳ Перевіряю ціну для **{symbol}**...")

    coin_name, price_info = get_crypto_price(symbol)

    if coin_name:
        response_text = price_info
    else:
        response_text = f"❌ Не вдалося отримати ціну для **{symbol}**.\nПомилка: {price_info}"

    await message.answer(response_text)


@router.message(Command("add"))
async def add_coin_command(message: Message, command: CommandObject):
    """Обробник команди /add [СИМВОЛ]."""
    if not command.args:
        await message.answer(
            "Будь ласка, вкажіть символ монети для додавання. Формат: `/add [СИМВОЛ]`"
        )
        return

    symbol = command.args.upper()
    current_list = tracked_coins.get("general_list", DEFAULT_TRACKED_SYMBOLS)

    if symbol in current_list:
        await message.answer(f"✅ Монета **{symbol}** вже є у каталозі!")
        return

    current_list.append(symbol)
    tracked_coins["general_list"] = current_list
    save_tracked_coins(tracked_coins)

    await message.answer(
        f"🎉 Монета **{symbol}** успішно додана до каталогу! Тепер її можна перевірити через /catalog."
    )


@router.message(Command("remove"))
async def remove_coin_command(message: Message, command: CommandObject):
    """Обробник команди /remove [СИМВОЛ]."""
    if not command.args:
        await message.answer(
            "Будь ласка, вкажіть символ монети для видалення. Формат: `/remove [СИМВОЛ]`"
        )
        return

    symbol = command.args.upper()
    current_list = tracked_coins.get("general_list", DEFAULT_TRACKED_SYMBOLS)

    if symbol not in current_list:
        await message.answer(f"❌ Монети **{symbol}** немає у каталозі. Нічого видаляти.")
        return

    current_list.remove(symbol)
    tracked_coins["general_list"] = current_list
    save_tracked_coins(tracked_coins)

    await message.answer(
        f"🗑️ Монета **{symbol}** успішно видалена з каталогу."
    )


# --- 👆 Обробники Кнопок (Callback) ---

@router.callback_query(F.data.startswith('check_'))
async def button_callback(query: CallbackQuery):
    """Обробник натискання Inline-кнопок."""
    symbol = query.data.split('_')[1]
    await query.answer(f"Перевіряю {symbol}...")

    await query.message.edit_text(
        f"⏳ Перевіряю ціну для **{symbol}**..."
    )

    coin_name, price_info = get_crypto_price(symbol)

    if coin_name:
        response_text = price_info
    else:
        response_text = f"❌ Не вдалося отримати ціну для **{symbol}**.\nПомилка: {price_info}"

    await query.message.edit_text(
        response_text,
        reply_markup=get_catalog_keyboard()
    )


# --- 🚫 Обробники Невідомих Команд ---

@router.message(F.text.startswith('/'))
async def unknown_command(message: Message):
    """Відповідь на невідомі команди."""
    await message.answer(
        "Невідома команда. Спробуйте `/start` для гайду або `/catalog` для перевірки цін."
    )


@router.message()
async def unknown_text(message: Message):
    """Відповідь на будь-який текст, що не є командою."""
    await message.answer(
        "Я розумію лише команди. Будь ласка, почніть з /start або /catalog."
    )


# --- ⚙️ Точка Входу (main) ---

async def main():
    """Точка входу та ініціалізація бота."""
    if not BOT_TOKEN:
        print("❌ ПОМИЛКА: Токен бота не знайдено. Переконайтеся, що файл .env існує і містить BOT_TOKEN.")
        return


    bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.MARKDOWN))

    dp = Dispatcher()
    dp.include_router(router)

    print("🚀 Бот запущено! Очікую на команди...")
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)


if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO, stream=sys.stdout)
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("Бот зупинено.")