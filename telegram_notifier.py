import os

from dotenv import load_dotenv
from telegram import Bot

load_dotenv()


def format_analysis_message(scenario_id: str, analysis: str) -> str:
    return f"🌦️ [{scenario_id}] 침수 예방 분석\n\n{analysis}"


async def send_analysis_message(scenario_id: str, analysis: str) -> None:
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    chat_id = os.getenv("TELEGRAM_CHAT_ID")

    if not token or not chat_id:
        raise ValueError(
            "TELEGRAM_BOT_TOKEN 또는 TELEGRAM_CHAT_ID가 .env에 설정되지 않았습니다."
        )

    bot = Bot(token=token)
    await bot.send_message(
        chat_id=chat_id,
        text=format_analysis_message(scenario_id, analysis),
    )


async def discover_chat_id() -> str | None:
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    if not token:
        raise ValueError("TELEGRAM_BOT_TOKEN이 .env에 설정되지 않았습니다.")

    bot = Bot(token=token)
    updates = await bot.get_updates()

    if not updates:
        return None

    return str(updates[-1].message.chat.id)
