# scraper.py
import requests
import time

# API URLs
COINGECKO_PRICE_URL = "https://api.coingecko.com/api/v3/simple/price"
# Використовуємо інший сервіс для фіатних курсів (для стабільності EUR/USD/UAH)
EXCHANGERATE_API_URL = "https://api.exchangerate-api.com/v4/latest/USD"
COINGECKO_SEARCH_URL = "https://api.coingecko.com/api/v3/search"

# Словник ID (залишається без змін)
COIN_IDS = {
    "BTC": "bitcoin",
    "USDT": "tether",
    "SOL": "solana",
    "ETH": "ethereum",
    "ADA": "cardano",
    "TON": "the-open-network",
    "DOGE": "dogecoin",
    "PEPE": "pepe",
    "XRP": "ripple",
    "LTC": "litecoin",
    "TRX": "tron",
}

# --- МЕХАНІЗМИ СТАБІЛЬНОСТІ ---
PRICE_CACHE = {}
CACHE_TIMEOUT = 90  # 1.5 хвилини
LAST_API_CALL_TIME = 0
API_CALL_DELAY = 1.5  # 1.5 секунди між викликами


# --- Допоміжна Функція: Пошук ID за Символом ---
def find_coin_id(symbol: str) -> str | None:
    global LAST_API_CALL_TIME

    try:
        if symbol in COIN_IDS:
            return COIN_IDS[symbol]

        time_since_last_call = time.time() - LAST_API_CALL_TIME
        if time_since_last_call < API_CALL_DELAY:
            time.sleep(API_CALL_DELAY - time_since_last_call)

        params = {'query': symbol}
        response = requests.get(COINGECKO_SEARCH_URL, params=params, timeout=10)
        response.raise_for_status()

        LAST_API_CALL_TIME = time.time()

        data = response.json()
        if data and data.get('coins'):
            first_result = data['coins'][0]
            if first_result.get('symbol', '').upper() == symbol:
                COIN_IDS[symbol] = first_result['id']
                return first_result['id']
        return None
    except Exception as e:
        print(f"Помилка find_coin_id: {e}")
        return None


# --- Допоміжна Функція: Отримання Фіатних Курсів ---
def get_fiat_rates() -> dict | None:
    """Отримує фіатні курси відносно USD."""
    global LAST_API_CALL_TIME

    try:
        time_since_last_call = time.time() - LAST_API_CALL_TIME
        if time_since_last_call < API_CALL_DELAY:
            time.sleep(API_CALL_DELAY - time_since_last_call)

        response = requests.get(EXCHANGERATE_API_URL, timeout=10)
        response.raise_for_status()

        LAST_API_CALL_TIME = time.time()

        data = response.json()

        if data.get('result') == 'success' and 'rates' in data:
            return data.get('rates')
        if 'rates' in data:
            return data.get('rates')

        return None
    except Exception as e:
        print(f"Помилка get_fiat_rates: {e}")
        return None


# --- Основна Функція: Отримання Ціни ---
def get_crypto_price(crypto_symbol: str) -> tuple[str, str] | tuple[None, str]:
    global PRICE_CACHE, LAST_API_CALL_TIME

    symbol = crypto_symbol.upper()
    cache_key = symbol

    # 1. ПЕРЕВІРКА КЕШУ
    if cache_key in PRICE_CACHE and (time.time() - PRICE_CACHE[cache_key]['timestamp']) < CACHE_TIMEOUT:
        return PRICE_CACHE[cache_key]['name'], PRICE_CACHE[cache_key]['data']

    # --- 2. Обробка Фіатних Валют (EUR, USD) ---
    if symbol in ["EUR", "USD"]:
        rates = get_fiat_rates()
        if not rates or 'UAH' not in rates or 'EUR' not in rates:
            return None, "Не вдалося отримати актуальні фіатні курси (немає UAH або EUR)."

        try:
            uah_per_usd = rates.get('UAH', 0)
            eur_per_usd = rates.get('EUR', 0)

            if uah_per_usd == 0 or eur_per_usd == 0:
                return None, "Фіатні курси недійсні (значення = 0)."

            if symbol == "USD":
                usd_price = 1.0
                uah_price = uah_per_usd
                coin_name = "US Dollar"
                response_text = (
                    f"**{coin_name}** (USD)\n\n"
                    f"💵 USD: **${usd_price:,.2f}**\n"
                    f"🇺🇦 UAH: **₴{uah_price:,.2f}**\n\n"
                    f"Зміна (24г): ⚪ N/A (фіат)"
                )

            elif symbol == "EUR":
                usd_price = 1.0 / eur_per_usd
                uah_price = usd_price * uah_per_usd
                coin_name = "Євро"
                response_text = (
                    f"**{coin_name}** (EUR)\n\n"
                    f"💵 USD: **${usd_price:,.4f}**\n"
                    f"🇺🇦 UAH: **₴{uah_price:,.2f}**\n\n"
                    f"Зміна (24г): ⚪ N/A (фіат)"
                )

            # ЗБЕРЕЖЕННЯ В КЕШ
            PRICE_CACHE[cache_key] = {'name': coin_name, 'data': response_text, 'timestamp': time.time()}
            return coin_name, response_text

        except Exception as e:
            print(f"Помилка обробки фіату: {e}")
            return None, "Невідома помилка при обробці фіатних курсів."

    # --- 3. Обробка Криптовалют (CoinGecko) ---
    coin_id = find_coin_id(symbol)

    if not coin_id:
        return None, f"Криптовалюта **{symbol}** не знайдена. Перевірте символ."

    try:
        time_since_last_call = time.time() - LAST_API_CALL_TIME
        if time_since_last_call < API_CALL_DELAY:
            time.sleep(API_CALL_DELAY - time_since_last_call)

        params = {
            'ids': coin_id,
            'vs_currencies': 'usd,uah',
            'include_24hr_change': 'true'
        }

        response = requests.get(COINGECKO_PRICE_URL, params=params, timeout=10)
        response.raise_for_status()

        LAST_API_CALL_TIME = time.time()
        data = response.json()

        if not data or coin_id not in data:
            return None, f"Монета з ID **{coin_id}** не має цінових даних."

        price_data = data[coin_id]
        price_usd = price_data.get('usd')
        price_uah = price_data.get('uah')
        price_change_24h = price_data.get('usd_24h_change')

        if price_usd is None:
            if symbol in ["USDT", "USDC", "BUSD"]:
                price_usd = 1.0
                price_change_24h = 0.0
            else:
                return None, f"Не вдалося отримати ціну для **{coin_id}**."

        # Форматування
        # Використовуємо ID для "справжньої" назви
        coin_name = coin_id.replace('-', ' ').title()
        usd_price_str = f"${price_usd:,.4f}" if symbol in ["USDT", "USDC", "BUSD"] else (
            f"${price_usd:,.8f}" if price_usd < 1.0 else f"${price_usd:,.2f}")
        uah_price_str = f"₴{price_uah:,.2f}" if price_uah else "₴N/A"

        if price_change_24h is not None:
            change_str = f"{price_change_24h:+.2f}%"
            emoji = "🟢" if price_change_24h >= 0 else "🔴"
        else:
            change_str = "N/A"
            emoji = "⚪"

        response_text = (
            f"**{coin_name}** ({symbol})\n\n"
            f"💵 USD: **{usd_price_str}**\n"
            f"🇺🇦 UAH: **{uah_price_str}**\n\n"
            f"Зміна (24г): {emoji} {change_str}"
        )

        PRICE_CACHE[cache_key] = {'name': coin_name, 'data': response_text, 'timestamp': time.time()}
        return coin_name, response_text

    except requests.exceptions.RequestException as e:
        print(f"Помилка API Coingecko: {e}")
        return None, "Помилка з'єднання з API. Спробуйте пізніше."
    except Exception as e:
        print(f"Невідома помилка обробки крипти: {e}")
        return None, "Невідома помилка при отриманні даних."