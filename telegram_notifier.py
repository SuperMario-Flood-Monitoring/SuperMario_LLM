import os

from dotenv import load_dotenv
from telegram import Bot

load_dotenv()


def format_analysis_message(scenario_id: str, analysis: str) -> str:
    return f"🌦️ [{scenario_id}] 침수 예방 분석\n\n{analysis}"


async def send_analysis_message(
    scenario_id: str,
    analysis: str,
    *,
    bot_token: str,
    chat_ids: list[str],
) -> list[str]:
    if not bot_token:
        raise ValueError("TELEGRAM_BOT_TOKEN이 필요합니다.")
    if not chat_ids:
        raise ValueError("TELEGRAM_CHAT_ID가 비어 있습니다.")

    unique_chat_ids: list[str] = []
    seen: set[str] = set()
    for chat_id in chat_ids:
        normalized = str(chat_id).strip()
        if not normalized or normalized in seen:
            continue
        seen.add(normalized)
        unique_chat_ids.append(normalized)

    if not unique_chat_ids:
        raise ValueError("유효한 TELEGRAM_CHAT_ID가 없습니다.")

    bot = Bot(token=bot_token)
    message = format_analysis_message(scenario_id, analysis)
    sent_to: list[str] = []
    errors: list[str] = []

    for chat_id in unique_chat_ids:
        try:
            await bot.send_message(chat_id=chat_id, text=message)
            sent_to.append(chat_id)
        except Exception as exc:
            errors.append(f"{chat_id}: {exc}")

    if errors:
        raise RuntimeError(
            "텔레그램 메시지 전송 실패: " + "; ".join(errors)
        )

    return sent_to


async def discover_chat_id() -> str | None:
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    if not token:
        raise ValueError("TELEGRAM_BOT_TOKEN이 .env에 설정되지 않았습니다.")

    bot = Bot(token=token)
    updates = await bot.get_updates()

    if not updates:
        return None

    return str(updates[-1].message.chat.id)
