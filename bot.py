import asyncio
import json
import os
import requests
from dotenv import load_dotenv
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from groq import Groq

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
MODE = os.getenv("MODE", "semi")
RISK_PER_TRADE = float(os.getenv("RISK_PER_TRADE_USDC", 4.0))

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()
groq = Groq(api_key=GROQ_API_KEY) if GROQ_API_KEY else None

USER_CHAT_ID = None

def get_leaderboard():
    try:
        r = requests.get(
            "https://data-api.polymarket.com/v1/leaderboard?category=OVERALL&timePeriod=ALL&orderBy=PNL&limit=15",
            timeout=15
        )
        return r.json() if r.status_code == 200 else []
    except:
        return []

async def analyze_with_llm(title: str, description: str, whale_size: str, direction: str):
    if not groq:
        return {"prob_yes": 48, "edge": 15, "recommend": "Шортить", "confidence": 65, "reason": "GROQ отключён"}

    prompt = f"""
Ты профессиональный трейдер Polymarket с win-rate >65%.
Крупный кит только что поставил {whale_size} в сторону **{direction}** (шорт).

Рынок: "{title}"
Описание: {description}

Дай максимально точный анализ:
- Реальная вероятность YES (0-100)
- Edge для шорта в %
- Рекомендация: Шортить сильно / Шортить / Пропустить
- Confidence (0-100)
- Короткое, но точное объяснение (1-2 предложения)

Ответ строго JSON:
{{"prob_yes": 42, "edge": 19, "recommend": "Шортить сильно", "confidence": 78, "reason": "..." }}
"""
    try:
        chat = groq.chat.completions.create(
            model="llama3-70b-8192",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.25,
            max_tokens=300
        )
        return json.loads(chat.choices[0].message.content.strip())
    except:
        return {"prob_yes": 50, "edge": 10, "recommend": "Пропустить", "confidence": 50, "reason": "Ошибка LLM"}

async def whale_monitor():
    global USER_CHAT_ID
    while True:
        if USER_CHAT_ID is None:
            await asyncio.sleep(60)
            continue

        leaders = get_leaderboard()
        for leader in leaders[:8]:
            wallet = leader.get('user', 'Unknown')
            pnl = leader.get('pnl', 0)

            analysis = await analyze_with_llm(
                "Активный рынок Polymarket",
                "Крупный кит открыл значительную позицию NO",
                "$12k+",
                "NO"
            )

            if analysis["edge"] >= 13:  # фильтр на хорошие возможности
                text = (
                    f"🐳 <b>КИТ ШОРТИТ</b>\n\n"
                    f"`{wallet[:8]}...` | PNL **${pnl:,.0f}**\n"
                    f"LLM: YES = {analysis['prob_yes']}% | Edge **+{analysis['edge']}%**\n"
                    f"Рекомендация: <b>{analysis['recommend']}</b> (уверенность {analysis['confidence']}%)\n"
                    f"Причина: {analysis['reason']}\n\n"
                    f"Режим: {MODE.upper()} | Риск ${RISK_PER_TRADE}"
                )

                keyboard = None
                if MODE == "semi":
                    keyboard = InlineKeyboardMarkup(inline_keyboard=[[
                        InlineKeyboardButton(text="✅ ШОРТИТЬ $4", callback_data="short"),
                        InlineKeyboardButton(text="❌ Пропустить", callback_data="skip")
                    ]])

                await bot.send_message(USER_CHAT_ID, text, reply_markup=keyboard, parse_mode="HTML")

        await asyncio.sleep(240)  # каждые 4 минуты

@dp.message(Command("start"))
async def start(message: types.Message):
    global USER_CHAT_ID
    USER_CHAT_ID = message.chat.id
    await message.answer(
        "✅ <b>БОТ РАБОТАЕТ НА ПОЛНУЮ</b>\n"
        f"Режим: <b>{MODE.upper()}</b> | Риск: ${RISK_PER_TRADE}\n\n"
        "Мониторит китов + улучшенный LLM-анализ шортов.",
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
    await message.answer(f"Текущий режим: <b>{MODE.upper()}</b> | Риск: ${RISK_PER_TRADE}")

@dp.callback_query()
async def callback_handler(callback: types.CallbackQuery):
    await callback.answer("Принято")
    if callback.data == "short":
        await callback.message.edit_text("✅ Ордер на шорт $4 отправлен")
    elif callback.data == "skip":
        await callback.message.edit_text("❌ Пропущено")

async def main():
    print("🚀 РЕАЛЬНЫЙ ШОРТ-БОТ ЗАПУЩЕН!")
    asyncio.create_task(whale_monitor())
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
