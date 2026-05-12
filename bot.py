import asyncio
import os
from dotenv import load_dotenv
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
MODE = os.getenv("MODE", "semi")
RISK_PER_TRADE = float(os.getenv("RISK_PER_TRADE_USDC", 4.0))

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

USER_CHAT_ID = None

@dp.message(Command("start"))
async def start(message: types.Message):
    global USER_CHAT_ID
    USER_CHAT_ID = message.chat.id
    await message.answer(
        "✅ Бот успешно запущен на Railway!\n"
        f"Режим: <b>{MODE.upper()}</b>\n"
        f"Риск на сделку: ${RISK_PER_TRADE}\n\n"
        "Команды:\n/mode semi\n/mode auto\n/status",
        parse_mode="HTML"
    )

@dp.message(Command("mode"))
async def change_mode(message: types.Message):
    global MODE
    args = message.text.split()
    if len(args) > 1 and args[1] in ["semi", "auto"]:
        MODE = args[1]
        await message.answer(f"✅ Режим изменён на <b>{MODE.upper()}</b>")
    else:
        await message.answer("Использование: /mode semi или /mode auto")

@dp.message(Command("status"))
async def status(message: types.Message):
    await message.answer(f"Текущий режим: <b>{MODE.upper()}</b>")

async def whale_monitor():
    global USER_CHAT_ID
    while True:
        if USER_CHAT_ID is None:
            await asyncio.sleep(10)
            continue
        
        text = "🐳 ТЕСТОВЫЙ АЛЕРТ\nКИТ ШОРТИТ на Polymarket\n(бот работает на Railway)"
        
        keyboard = None
        if MODE == "semi":
            keyboard = InlineKeyboardMarkup(inline_keyboard=[[
                InlineKeyboardButton(text="✅ ШОРТИТЬ $4", callback_data="short_test"),
                InlineKeyboardButton(text="❌ Пропустить", callback_data="skip")
            ]])
        
        await bot.send_message(USER_CHAT_ID, text, reply_markup=keyboard, parse_mode="HTML")
        await asyncio.sleep(180)

@dp.callback_query()
async def callback_handler(callback: types.CallbackQuery):
    if callback.data == "short_test":
        await callback.message.edit_text("✅ Тестовый ордер на шорт $4 отправлен")
    elif callback.data == "skip":
        await callback.message.edit_text("❌ Пропущено")
    await callback.answer()

async def main():
    print("🚀 Полимаркет Шорт-бот запущен на Railway!")
    asyncio.create_task(whale_monitor())
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
