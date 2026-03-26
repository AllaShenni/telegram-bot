import asyncio
import logging
import os
from datetime import datetime

from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import ReplyKeyboardRemove

# === ВАЖНО: токен теперь берется из Render ===
BOT_TOKEN = os.getenv("BOT_TOKEN")

CHANNEL_ID = -1003877095294

WELCOME_TEXT = """👋 Добрый день!

Меня зовут Алла. Я куратор онлайн-школ и модератор вебинаров с опытом более 2 с половиной лет.

Выхожу в эфир только голосом, без камеры.

Чем могу помочь?"""

ASK_NAME = "Как к вам обращаться?"
ASK_PHONE = "Ваш номер телефона?"
ASK_EMAIL = "Ваш email?"
ASK_COMMENT = "Опишите задачу:"
SUCCESS_TEXT = "✅ Заявка принята! Свяжусь в течение 24 часов: {phone} или {email}."
CANCEL_TEXT = "Отменено. Напишите /start"

BTN_CURATOR = "🎓 Кураторство"
BTN_MODERATOR = "🎤 Модерация"
BTN_BOTH = "📋 Оба варианта"
BTN_CANCEL = "❌ Отмена"

logging.basicConfig(level=logging.INFO)

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(storage=MemoryStorage())


class Form(StatesGroup):
    service = State()
    name = State()
    phone = State()
    email = State()
    comment = State()


def cancel_btn():
    return types.ReplyKeyboardMarkup(
        keyboard=[[types.KeyboardButton(text=BTN_CANCEL)]],
        resize_keyboard=True
    )


@dp.message(Command("start"))
async def start(message: types.Message, state: FSMContext):
    await state.clear()

    kb = types.ReplyKeyboardMarkup(
        keyboard=[
            [types.KeyboardButton(text=BTN_CURATOR)],
            [types.KeyboardButton(text=BTN_MODERATOR)],
            [types.KeyboardButton(text=BTN_BOTH)],
            [types.KeyboardButton(text=BTN_CANCEL)]
        ],
        resize_keyboard=True
    )

    await message.answer(WELCOME_TEXT, reply_markup=kb)
    await state.set_state(Form.service)


@dp.message(F.text == BTN_CANCEL)
@dp.message(Command("cancel"))
async def cancel(message: types.Message, state: FSMContext):
    await state.clear()
    await message.answer(CANCEL_TEXT, reply_markup=ReplyKeyboardRemove())


@dp.message(Form.service)
async def get_service(message: types.Message, state: FSMContext):
    if message.text == BTN_CANCEL:
        return await cancel(message, state)

    if message.text not in [BTN_CURATOR, BTN_MODERATOR, BTN_BOTH]:
        return await message.answer("Выберите из кнопок")

    await state.update_data(service=message.text)
    await message.answer(ASK_NAME, reply_markup=cancel_btn())
    await state.set_state(Form.name)


@dp.message(Form.name)
async def get_name(message: types.Message, state: FSMContext):
    if message.text == BTN_CANCEL:
        return await cancel(message, state)

    if len(message.text) < 2:
        return await message.answer("Слишком коротко")

    await state.update_data(name=message.text)
    await message.answer(ASK_PHONE, reply_markup=cancel_btn())
    await state.set_state(Form.phone)


@dp.message(Form.phone)
async def get_phone(message: types.Message, state: FSMContext):
    if message.text == BTN_CANCEL:
        return await cancel(message, state)

    digits = ''.join(filter(str.isdigit, message.text))
    if len(digits) < 7:
        return await message.answer("Неверный номер")

    await state.update_data(phone=message.text)
    await message.answer(ASK_EMAIL, reply_markup=cancel_btn())
    await state.set_state(Form.email)


@dp.message(Form.email)
async def get_email(message: types.Message, state: FSMContext):
    if message.text == BTN_CANCEL:
        return await cancel(message, state)

    email = message.text.lower().strip()
    if "@" not in email or "." not in email.split("@")[-1]:
        return await message.answer("Неверный email")

    await state.update_data(email=email)
    await message.answer(ASK_COMMENT, reply_markup=cancel_btn())
    await state.set_state(Form.comment)


@dp.message(Form.comment)
async def finish(message: types.Message, state: FSMContext):
    if message.text == BTN_CANCEL:
        return await cancel(message, state)

    data = await state.get_data()

    text = f"""📬 ЗАЯВКА

👤 {data['name']}
📱 {data['phone']}
📧 {data['email']}
💼 {data['service']}
📝 {message.text}
⏰ {datetime.now().strftime('%d.%m.%Y %H:%M')}
🔗 @{message.from_user.username or 'нет'}"""

    try:
        await bot.send_message(chat_id=CHANNEL_ID, text=text)
        logging.info("✅ Отправлено в канал")
    except Exception as e:
        logging.error(f"❌ Ошибка отправки в канал: {e}")
        await message.answer("⚠️ Не удалось отправить заявку. Напишите @AllaShenni")
        return

    await message.answer(
        SUCCESS_TEXT.format(phone=data['phone'], email=data['email']),
        reply_markup=ReplyKeyboardRemove()
    )

    await state.clear()


async def main():
    print("🚀 Бот запущен!")
    print(f"Заявки будут в канал: {CHANNEL_ID}")

    # защита от падений
    while True:
        try:
            await dp.start_polling(bot)
        except Exception as e:
            logging.error(f"Падение бота: {e}")
            await asyncio.sleep(5)


if __name__ == "__main__":
    asyncio.run(main())