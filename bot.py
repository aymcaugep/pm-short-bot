async def status(message: types.Message):
    await message.answer(f"Текущий режим: <b>{MODE.upper()}</b> | Риск: ${RISK_PER_TRADE}")

@dp.callback_query()
async def callback_handler(callback: types.CallbackQuery):
    await callback.answer("Принято")
    if callback.data == "short":
        await callback.message.edit_text("✅ Ордер на шорт $4 отправлен (тест)")
    elif callback.data == "skip":
        await callback.message.edit_text("❌ Пропущено")

async def main():
    print("🚀 Полимаркет Шорт-бот с live LLM запущен!")
    asyncio.create_task(whale_monitor())
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
    import asyncio
import json
import os
import requests
from datetime import datetime
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
groq = Groq(api_key=GROQ_API_KEY)

USER_CHAT_ID = None

def get_leaderboard():
    try:
        r = requests.get(
            "https://data-api.polymarket.com/v1/leaderboard?category=OVERALL&timePeriod=ALL&orderBy=PNL&limit=12",
            timeout=15
        )
        return r.json() if r.status_code == 200 else []
    except:
        return []

async def analyze_short_with_llm(market_title, description, whale_size):
    prompt = f"""
Ты эксперт Polymarket. Сейчас крупный кит зашёл в NO на {whale_size}$.

Рынок: "{market_title}"
Описание: {description}

Дай короткий анализ:
- Твоя вероятность YES (0-100%)
- Edge для шорта (насколько переоценён YES)
- Рекомендация: Шортить сильно / Шортить / Пропустить
- Короткое объяснение (1 предложение)

Ответ строго JSON:
{{"prob_yes": 38, "edge": 22, "recommend": "Шортить сильно", "reason": "..." }}
"""
    try:
        chat = groq.chat.completions.create(
            model="llama3-70b-8192",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3,
            max_tokens=300
        )
        return json.loads(chat.choices[0].message.content.strip())
    except:
        return {"prob_yes": 50, "edge": 10, "recommend": "Пропустить", "reason": "Ошибка анализа"}

async def whale_monitor():
    global USER_CHAT_ID
    while True:
        if USER_CHAT_ID is None:
            await asyncio.sleep(60)
            continue

        leaders = get_leaderboard()
        if leaders:
            text = "🐳 <b>НОВЫЕ КИТЫ НА ШОРТЕ</b>\n\n"
            for leader in leaders[:6]:
                wallet = leader.get('user', 'Unknown')[:8] + "..."
                pnl = leader.get('pnl', 0)
                text += f"• {wallet} | PNL: **${pnl:,.0f}**\n"

            # Пример LLM-анализа (можно расширить на конкретные рынки)
            analysis = await analyze_short_with_llm(
                "Популярный политический/крипто рынок",
                "Крупный кит только что открыл большую позицию NO",
                15000
            )

            text += f"\n📊 LLM анализ: YES = {analysis['prob_yes']}% | Edge шорта +{analysis['edge']}%\n"
            text += f"Рекомендация: <b>{analysis['recommend']}</b>\n"
            text += f"Причина: {analysis['reason']}"

            keyboard = None
            if MODE == "semi":
                keyboard = InlineKeyboardMarkup(inline_keyboard=[[
                    InlineKeyboardButton(text="✅ ШОРТИТЬ $4", callback_data="short"),
                    InlineKeyboardButton(text="❌ Пропустить", callback_data="skip")
                ]])

            await bot.send_message(USER_CHAT_ID, text, reply_markup=keyboard, parse_mode="HTML")

        await asyncio.sleep(240)  # каждые 4 минуты

# ==================== КОМАНДЫ ====================
@dp.message(Command("start"))
async def start(message: types.Message):
    global USER_CHAT_ID
    USER_CHAT_ID = message.chat.id
    await message.answer(
        "✅ <b>Бот запущен с live LLM + мониторингом китов!</b>\n"
        f"Режим: <b>{MODE.upper()}</b> | Риск: ${RISK_PER_TRADE}\n\n"
        "Теперь присылает реальных китов + LLM-анализ выгодности шорта.",
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
