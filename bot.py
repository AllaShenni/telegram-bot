import asyncio
import os
import smtplib
from email.mime.text import MIMEText

from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.utils.keyboard import InlineKeyboardBuilder

BOT_TOKEN = os.getenv("BOT_TOKEN")
OWNER_ID = int(os.getenv("OWNER_ID"))
GMAIL_ADDRESS = os.getenv("GMAIL_ADDRESS")
GMAIL_APP_PASSWORD = os.getenv("GMAIL_APP_PASSWORD")

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(storage=MemoryStorage())

SERVICE_LABELS = {
    "curator": "Куратор студентов",
    "moderator": "Модератор вебинаров",
    "both": "Куратор студентов + Модератор вебинаров",
}

WELCOME_TEXT = (
    "Добрый день!\n\n"
    "Меня зовут Алла. Я куратор студентов и модератор обучающих вебинаров с большим опытом.\n\n"
    "Если вам нужен специалист — оставьте заявку или напишите мне напрямую."
)


class OrderForm(StatesGroup):
    waiting_for_name = State()
    waiting_for_goal = State()
    waiting_for_contact = State()


class FreeForm(StatesGroup):
    waiting_for_message = State()
    waiting_for_contact = State()


def main_keyboard():
    builder = InlineKeyboardBuilder()
    builder.button(text="1. Нужен куратор студентов", callback_data="service_curator")
    builder.button(text="2. Нужен модератор вебинаров", callback_data="service_moderator")
    builder.button(text="3. Нужны оба", callback_data="service_both")
    builder.button(text="4. Написать в ЛС", callback_data="service_free")
    builder.adjust(1)
    return builder.as_markup()


async def send_welcome(message: types.Message):
    await message.answer(WELCOME_TEXT, reply_markup=main_keyboard())


def utf16_len(text: str) -> int:
    return len(text.encode("utf-16-le")) // 2


def send_email(subject: str, body: str) -> None:
    if not GMAIL_ADDRESS or not GMAIL_APP_PASSWORD:
        print("Email не настроен: GMAIL_ADDRESS или GMAIL_APP_PASSWORD отсутствуют")
        return

    try:
        msg = MIMEText(body, "plain", "utf-8")
        msg["Subject"] = subject
        msg["From"] = GMAIL_ADDRESS
        msg["To"] = GMAIL_ADDRESS

        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
            server.login(GMAIL_ADDRESS, GMAIL_APP_PASSWORD)
            server.sendmail(GMAIL_ADDRESS, GMAIL_ADDRESS, msg.as_string())

        print("Email отправлен успешно")
    except Exception as e:
        print(f"Ошибка отправки email: {e}")


async def send_notification(text_lines: str, user: types.User, subject: str) -> None:
    prefix = text_lines + "🔗 Telegram: "

    if user.username:
        mention_str = f"@{user.username}"
        full_text = prefix + mention_str
        entity = types.MessageEntity(
            type="mention",
            offset=utf16_len(prefix),
            length=utf16_len(mention_str),
        )
    else:
        mention_str = user.full_name or str(user.id)
        full_text = prefix + mention_str
        entity = types.MessageEntity(
            type="text_mention",
            offset=utf16_len(prefix),
            length=utf16_len(mention_str),
            user=user,
        )

    try:
        await bot.send_message(chat_id=OWNER_ID, text=full_text, entities=[entity])
    except Exception as e:
        print(f"Ошибка Telegram: {e}")
        try:
            await bot.send_message(chat_id=OWNER_ID, text=full_text)
        except Exception as e2:
            print(f"Ошибка fallback Telegram: {e2}")

    email_body = full_text.replace("🔗 Telegram: ", "Telegram: ")
    loop = asyncio.get_running_loop()
    await loop.run_in_executor(None, send_email, subject, email_body)


@dp.message(CommandStart())
async def start_handler(message: types.Message, state: FSMContext):
    await state.clear()
    await send_welcome(message)


@dp.callback_query(F.data.in_({"service_curator", "service_moderator", "service_both"}))
async def service_handler(callback: types.CallbackQuery, state: FSMContext):
    service_key = callback.data.replace("service_", "")
    await state.update_data(service=SERVICE_LABELS[service_key])
    await state.set_state(OrderForm.waiting_for_name)
    await callback.message.answer("Добрый день, как к вам обращаться?")
    await callback.answer()


@dp.callback_query(F.data == "service_free")
async def free_handler(callback: types.CallbackQuery, state: FSMContext):
    await state.set_state(FreeForm.waiting_for_message)
    await callback.message.answer("Напишите ваше сообщение в свободной форме:")
    await callback.answer()


@dp.message(OrderForm.waiting_for_name)
async def name_handler(message: types.Message, state: FSMContext):
    await state.update_data(name=message.text)
    await state.set_state(OrderForm.waiting_for_goal)
    await message.answer(
        "Напишите, пожалуйста, для каких целей ищете специалиста?\n"
        "(для онлайн-школы, для курса в мессенджере, для частных созвонов/вебинаров и т.д.)"
    )


@dp.message(OrderForm.waiting_for_goal)
async def goal_handler(message: types.Message, state: FSMContext):
    await state.update_data(goal=message.text)
    await state.set_state(OrderForm.waiting_for_contact)
    await message.answer("Сообщите, пожалуйста, ваш мейл или мессенджер.")


@dp.message(OrderForm.waiting_for_contact)
async def contact_handler(message: types.Message, state: FSMContext):
    data = await state.get_data()
    await state.clear()

    text_lines = (
        f"📬 Новая заявка!\n\n"
        f"🎯 Услуга: {data.get('service', '—')}\n"
        f"👤 Имя / должность: {data.get('name', '—')}\n"
        f"📋 Цель: {data.get('goal', '—')}\n"
        f"📩 Контакт: {message.text}\n"
    )

    await send_notification(text_lines, message.from_user, subject="📬 Новая заявка от клиента")
    await message.answer("Спасибо, ваш запрос получен, я обязательно отвечу вам в ближайшее время.")


@dp.message(FreeForm.waiting_for_message)
async def free_message_handler(message: types.Message, state: FSMContext):
    await state.update_data(free_message=message.text)
    await state.set_state(FreeForm.waiting_for_contact)
    await message.answer("Укажите, пожалуйста, ваш мейл или мессенджер для связи:")


@dp.message(FreeForm.waiting_for_contact)
async def free_contact_handler(message: types.Message, state: FSMContext):
    data = await state.get_data()
    await state.clear()

    text_lines = (
        f"💬 Сообщение в ЛС!\n\n"
        f"📝 Текст: {data.get('free_message', '—')}\n"
        f"📩 Контакт: {message.text}\n"
    )

    await send_notification(text_lines, message.from_user, subject="💬 Новое сообщение от клиента")
    await message.answer("Спасибо, ваш запрос получен, я обязательно отвечу вам в ближайшее время.")


@dp.message()
async def fallback_handler(message: types.Message, state: FSMContext):
    if await state.get_state() is None:
        await send_welcome(message)


async def main():
    print("Бот запущен...")
    try:
        await bot.set_my_description("Вас приветствует бот-ассистент, нажмите Старт!")
        await dp.start_polling(bot)
    finally:
        await bot.session.close()


if __name__ == "__main__":
    asyncio.run(main())
