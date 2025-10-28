# main.py
import json
import os
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes

# Імпортуємо налаштування з config.py та функції з scraper.py
from config import BOT_TOKEN, DEFAULT_TRACKED_SYMBOLS
from scraper import get_crypto_price

# Файл для збереження користувацьких валют
TRACKED_COINS_FILE = 'tracked_coins.json'


# --- 💾 Збереження/Завантаження Даних (ВИЗНАЧЕНІ ПЕРШИМИ) ---

def load_tracked_coins():
    """Завантажує відстежувані монети з файлу або повертає дефолтний список."""
    if os.path.exists(TRACKED_COINS_FILE):
        try:
            with open(TRACKED_COINS_FILE, 'r') as f:
                return json.load(f)
        except json.JSONDecodeError:
            print("Попередження: файл tracked_coins.json порожній або пошкоджений.")
            pass
    # Якщо файл не знайдено або помилка, повертаємо початкові дані
    return {"general_list": DEFAULT_TRACKED_SYMBOLS}


def save_tracked_coins(coins_data):
    """Зберігає відстежувані монети у файл."""
    with open(TRACKED_COINS_FILE, 'w') as f:
        json.dump(coins_data, f, indent=4)


# --- 🎯 Ініціалізація Списку ---

# Виклик функції після її визначення
tracked_coins = load_tracked_coins()
if "general_list" not in tracked_coins:
    tracked_coins["general_list"] = DEFAULT_TRACKED_SYMBOLS


# --- 🚀 Обробники Команд ---

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обробник команди /start. Відображає гайд."""
    intro_message = (
        "👋 **Вітаю в Крипто-Чекері!**\n\n"
        "Я бот, який перевіряє ціни криптовалют, використовуючи CoinCap API для стабільності.\n\n"
        "**📚 Як користуватися:**\n"
        "1. **Каталог (Кнопки)**: Натисніть команду /catalog, щоб побачити список монет. Натискання на кнопку покаже ціну.\n"
        "2. **Командою**: Напишіть `/price [СИМВОЛ]`, наприклад, `/price BTC` або `/price EUR`.\n"
        "3. **Додати Монету**: Напишіть `/add [СИМВОЛ]`. (Символ має бути на CoinCap)\n"
        "4. **Видалити Монету**: Напишіть `/remove [СИМВОЛ]`.\n\n"
        "Спробуйте /catalog, щоб почати!"
    )
    await update.message.reply_text(intro_message, parse_mode='Markdown')


def get_catalog_keyboard():
    """Створює Inline-клавіатуру з відстежуваними монетами."""
    symbols = tracked_coins.get("general_list", DEFAULT_TRACKED_SYMBOLS)

    keyboard = []
    for i in range(0, len(symbols), 3):
        row = []
        for symbol in symbols[i:i + 3]:
            row.append(InlineKeyboardButton(symbol, callback_data=f'check_{symbol}'))
        keyboard.append(row)

    return InlineKeyboardMarkup(keyboard)


async def catalog_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обробник команди /catalog. Надсилає кнопки."""
    reply_markup = get_catalog_keyboard()

    await update.message.reply_text(
        "⬇️ **Каталог Валют** (Натисніть на монету, щоб перевірити ціну):",
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )


async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обробник натискання Inline-кнопок."""
    query = update.callback_query
    await query.answer()

    if query.data.startswith('check_'):
        symbol = query.data.split('_')[1]

        await query.edit_message_text(f"⏳ Перевіряю ціну для **{symbol}**...", parse_mode='Markdown')

        # Отримуємо ціну (використовує API)
        coin_name, price_info = get_crypto_price(symbol)

        if coin_name:
            response_text = price_info  # price_info вже містить повне форматування
        else:
            response_text = f"❌ Не вдалося отримати ціну для **{symbol}**.\nПомилка: {price_info}"

        # Надсилаємо оновлений текст повідомлення з ціною і повертаємо кнопки
        await query.edit_message_text(
            response_text,
            reply_markup=get_catalog_keyboard(),
            parse_mode='Markdown'
        )


async def price_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обробник команди /price [СИМВОЛ]."""
    if not context.args:
        await update.message.reply_text("Будь ласка, вкажіть символ монети. Формат: `/price [СИМВОЛ]`",
                                        parse_mode='Markdown')
        return

    symbol = context.args[0].upper()

    await update.message.reply_text(f"⏳ Перевіряю ціну для **{symbol}**...", parse_mode='Markdown')

    coin_name, price_info = get_crypto_price(symbol)

    if coin_name:
        response_text = price_info
    else:
        response_text = f"❌ Не вдалося отримати ціну для **{symbol}**.\nПомилка: {price_info}"

    await update.message.reply_text(response_text, parse_mode='Markdown')


async def add_coin_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обробник команди /add [СИМВОЛ]."""
    if not context.args:
        await update.message.reply_text("Будь ласка, вкажіть символ монети для додавання. Формат: `/add [СИМВОЛ]`",
                                        parse_mode='Markdown')
        return

    symbol = context.args[0].upper()
    current_list = tracked_coins.get("general_list", DEFAULT_TRACKED_SYMBOLS)

    if symbol in current_list:
        await update.message.reply_text(f"✅ Монета **{symbol}** вже є у каталозі!", parse_mode='Markdown')
        return

    # Додаємо монету
    current_list.append(symbol)
    tracked_coins["general_list"] = current_list
    save_tracked_coins(tracked_coins)

    await update.message.reply_text(
        f"🎉 Монета **{symbol}** успішно додана до каталогу! Тепер її можна перевірити через /catalog.",
        parse_mode='Markdown'
    )


async def remove_coin_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обробник команди /remove [СИМВОЛ]."""
    if not context.args:
        await update.message.reply_text("Будь ласка, вкажіть символ монети для видалення. Формат: `/remove [СИМВОЛ]`",
                                        parse_mode='Markdown')
        return

    symbol = context.args[0].upper()
    current_list = tracked_coins.get("general_list", DEFAULT_TRACKED_SYMBOLS)

    if symbol not in current_list:
        await update.message.reply_text(f"❌ Монети **{symbol}** немає у каталозі. Нічого видаляти.",
                                        parse_mode='Markdown')
        return

    # Видаляємо монету
    current_list.remove(symbol)
    tracked_coins["general_list"] = current_list
    save_tracked_coins(tracked_coins)

    await update.message.reply_text(
        f"🗑️ Монета **{symbol}** успішно видалена з каталогу.",
        parse_mode='Markdown'
    )


async def unknown_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Відповідь на невідомі команди."""
    await update.message.reply_text(
        "Невідома команда. Спробуйте `/start` для гайду або `/catalog` для перевірки цін.",
        parse_mode='Markdown'
    )


# --- ⚙️ Точка Входу (main) ---

def main():
    """Точка входу та ініціалізація бота."""

    if not BOT_TOKEN:
        print("❌ ПОМИЛКА: Токен бота не знайдено. Переконайтеся, що файл .env існує і містить BOT_TOKEN.")
        return

    # 1. Створюємо Application та передаємо токен
    application = Application.builder().token(BOT_TOKEN).build()

    # 2. Обробники Команд
    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CommandHandler("catalog", catalog_command))
    application.add_handler(CommandHandler("price", price_command))
    application.add_handler(CommandHandler("add", add_coin_command))
    application.add_handler(CommandHandler("remove", remove_coin_command))

    # 3. Обробник Inline-кнопок
    application.add_handler(CallbackQueryHandler(button_callback))

    # 4. Обробник невідомих команд (має бути останнім)
    application.add_handler(MessageHandler(filters.COMMAND, unknown_command))

    # 5. Запускаємо бота
    print("🚀 Бот запущено! Очікую на команди...")
    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == '__main__':
    main()