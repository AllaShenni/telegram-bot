import asyncio
from aiogram import Bot, Dispatcher, types

import os

# Вставьте сюда ваш токен
BOT_TOKEN = os.getenv("BOT_TOKEN")

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# Пример команды /start
@dp.message(commands=["start"])
async def start_handler(message: types.Message):
    await message.answer("Привет! Я ваш бот 🤖")

# Пример команды /help
@dp.message(commands=["help"])
async def help_handler(message: types.Message):
    await message.answer("Напиши мне что-нибудь, и я отвечу!")

# Обработка любых текстовых сообщений
@dp.message()
async def echo(message: types.Message):
    await message.answer(f"Вы написали: {message.text}")

# Запуск бота
async def main():
    try:
        print("Бот запущен...")
        await dp.start_polling(bot)
    finally:
        await bot.session.close()

if __name__ == "__main__":
    asyncio.run(main())

if __name__ == "__main__":
    asyncio.run(main())
