import asyncio
import logging
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

from database import Database
from ton_client import SimpleTONClient

# Конфигурация
BOT_TOKEN = "YOUR_BOT_TOKEN"
TONCENTER_API_KEY = "YOUR_TONCENTER_API_KEY"
BOT_WALLET_ADDRESS = "YOUR_BOT_WALLET_ADDRESS"  # Адрес, на который пользователи будут отправлять TON

logging.basicConfig(level=logging.INFO)
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

db = Database()
ton_client = SimpleTONClient(TONCENTER_API_KEY)

# States для FSM (Finite State Machine) для обработки вывода
class WithdrawState(StatesGroup):
    waiting_for_address = State()
    waiting_for_amount = State()

# Команда /start
@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    kb = [
        [KeyboardButton(text="💰 Баланс")],
        [KeyboardButton(text="📥 Депозит"), KeyboardButton(text="📤 Вывод")]
    ]
    keyboard = ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True)
    await message.answer("Добро пожаловать! Используйте кнопки ниже для управления балансом.", reply_markup=keyboard)

# Обработка кнопки "Баланс"
@dp.message(F.text == "💰 Баланс")
async def show_balance(message: types.Message):
    user_id = message.from_user.id
    balance = db.get_user_balance(user_id)
    await message.answer(f"Ваш текущий баланс: {balance:.2f} TON")

# Обработка кнопки "Депозит"
@dp.message(F.text == "📥 Депозит")
async def deposit(message: types.Message):
    user_id = message.from_user.id
    # Генерируем адрес для депозита. В данном случае используем один адрес бота.
    # В идеале нужно генерировать уникальный адрес или использовать комментарий (payload) с user_id.
    deposit_address = BOT_WALLET_ADDRESS

    text = (
        "Для пополнения баланса, отправьте TON на следующий адрес:\n\n"
        f"`{deposit_address}`\n\n"
        "*Минимальная сумма депозита: 0.1 TON*\n"
        "После отправки транзакции, баланс обновится автоматически после 1-го подтверждения сети."
    )
    # Можно также сгенерировать QR-код для удобства
    await message.answer(text, parse_mode="Markdown")

# Обработка кнопки "Вывод"
@dp.message(F.text == "📤 Вывод")
async def withdraw_start(message: types.Message, state: FSMContext):
    user_id = message.from_user.id
    balance = db.get_user_balance(user_id)
    if balance <= 0:
        await message.answer("На вашем балансе недостаточно средств для вывода.")
        return

    await message.answer(f"Ваш баланс: {balance:.2f} TON.\nВведите сумму для вывода:")
    await state.set_state(WithdrawState.waiting_for_amount)

# Получение суммы для вывода
@dp.message(WithdrawState.waiting_for_amount)
async def withdraw_get_amount(message: types.Message, state: FSMContext):
    user_id = message.from_user.id
    balance = db.get_user_balance(user_id)

    try:
        amount = float(message.text)
    except ValueError:
        await message.answer("Пожалуйста, введите корректную сумму (число).")
        return

    if amount <= 0:
        await message.answer("Сумма должна быть положительной.")
        return
    if amount > balance:
        await message.answer("Недостаточно средств на балансе.")
        return

    await state.update_data(amount=amount)
    await message.answer("Теперь введите адрес вашего TON кошелька:")
    await state.set_state(WithdrawState.waiting_for_address)

# Получение адреса и выполнение вывода
@dp.message(WithdrawState.waiting_for_address)
async def withdraw_get_address(message: types.Message, state: FSMContext):
    user_id = message.from_user.id
    wallet_address = message.text.strip()

    # Простая валидация адреса TON
    if not wallet_address.startswith(("EQ", "UQ")) or len(wallet_address) != 48:
        await message.answer("Пожалуйста, введите корректный TON адрес (начинается с EQ или UQ, 48 символов).")
        return

    data = await state.get_data()
    amount = data['amount']

    # Списание средств с баланса пользователя
    db.update_user_balance(user_id, -amount)

    # Здесь должна быть реальная логика отправки TON с кошелька бота на wallet_address
    # await ton_client.send_ton(BOT_WALLET_SEED, wallet_address, amount, comment=f"Withdraw for user {user_id}")
    # Это опасная операция! Убедитесь в безопасности кошелька бота.

    # Временно имитируем успешный вывод
    logging.info(f"Вывод {amount} TON на адрес {wallet_address} для пользователя {user_id}")

    await message.answer(f"✅ Запрос на вывод {amount:.2f} TON на адрес `{wallet_address}` принят в обработку.", parse_mode="Markdown")
    await state.clear()

#### Шаг 4: Фоновая задача для проверки депозитов

async def check_deposits_periodically():
    """
    Фоновая задача, которая периодически проверяет новые транзакции на адресе бота
    и зачисляет средства на баланс пользователей.
    """
    while True:
        try:
            transactions = await ton_client.get_transactions(BOT_WALLET_ADDRESS, limit=10)
            for tx in transactions:
                tx_hash = tx['transaction_id']['hash']
                # Проверяем, не обрабатывали ли мы уже эту транзакцию
                if db.is_transaction_processed(tx_hash):
                    continue

                # Ищем входящие сообщения (депозиты)
                in_msg = tx.get('in_msg')
                if in_msg and in_msg['source'] != "" and in_msg['value'] > 0: # Источник не пустой (не системное сообщение) и есть значение
                    sender_address = in_msg['source']
                    amount = int(in_msg['value']) / 10**9  # Конвертируем наноТОН в TON

                    # ВАЖНО: Здесь сложная часть - сопоставить транзакцию с пользователем.
                    # Если вы используете один адрес для всех, то можно использовать комментарий (msg_body).
                    # Если генерируете уникальные адреса - то сопоставлять по адресу.
                    # Для примера, предположим, что user_id передается в комментарии как plain text.

                    # user_id = extract_user_id_from_comment(in_msg.get('msg_body')) 
                    # Это нужно реализовать в зависимости от вашей логики.

                    # Временно: зачисляем на тестового пользователя (ЗАМЕНИТЕ НА РЕАЛЬНУЮ ЛОГИКУ!)
                    user_id = 123456789 # Пример user_id

                    if amount >= 0.1:  # Минимальная сумма депозита
                        db.add_transaction(tx_hash, user_id, amount, "confirmed")
                        db.update_user_balance(user_id, amount)
                        # Уведомляем пользователя
                        try:
                            await bot.send_message(user_id, f"✅ На ваш баланс зачислено {amount:.2f} TON.")
                        except:
                            logging.warning(f"Не удалось уведомить пользователя {user_id} о депозите.")
                    else:
                        db.add_transaction(tx_hash, user_id, amount, "amount_too_small")

        except Exception as e:
            logging.error(f"Ошибка при проверке депозитов: {e}")

        await asyncio.sleep(30)  # Проверяем каждые 30 секунд

# Запуск фоновой задачи при старте бота
async def on_startup(bot: Bot):
    asyncio.create_task(check_deposits_periodically())

dp.startup.register(on_startup)

if __name__ == "__main__":
    async def main():
        await dp.start_polling(bot)
    asyncio.run(main())
