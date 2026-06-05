"""Telegram-бот онбордера CodeAcademy Pro на Telethon.

Запуск: python bot.py

Нужны три переменные в .env:
  TELEGRAM_API_ID    — с https://my.telegram.org
  TELEGRAM_API_HASH  — с https://my.telegram.org
  TELEGRAM_BOT_TOKEN — от @BotFather
"""

import asyncio
import logging
import os
from concurrent.futures import ThreadPoolExecutor

from dotenv import load_dotenv
from telethon import TelegramClient, events

from agent import run_agent_turn
from storage import clear_history, init_db, load_history, save_history

load_dotenv()

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger(__name__)

API_ID = os.getenv("TELEGRAM_API_ID")
API_HASH = os.getenv("TELEGRAM_API_HASH")
BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")

if not all([API_ID, API_HASH, BOT_TOKEN]):
    raise RuntimeError(
        "Не заданы переменные Telegram.\n"
        "Добавь в .env:\n"
        "  TELEGRAM_API_ID    — с https://my.telegram.org\n"
        "  TELEGRAM_API_HASH  — с https://my.telegram.org\n"
        "  TELEGRAM_BOT_TOKEN — от @BotFather"
    )

client = TelegramClient("onboarder_bot", int(API_ID), API_HASH)
_executor = ThreadPoolExecutor(max_workers=4)


# ── Команды ───────────────────────────────────────────────────────────────────

@client.on(events.NewMessage(pattern=r"^/start"))
async def cmd_start(event: events.NewMessage.Event) -> None:
    clear_history(event.sender_id)
    sender = await event.get_sender()
    name = getattr(sender, "first_name", None) or "друг"
    await event.respond(
        f"Привет, {name}! 👋\n\n"
        "Я — ИИ онбордер CodeAcademy Pro. Помогу разобраться с компанией, "
        "процессами, командой и планом адаптации.\n\n"
        "Просто задавай вопросы! Для сброса диалога — /reset"
    )
    raise events.StopPropagation


@client.on(events.NewMessage(pattern=r"^/reset"))
async def cmd_reset(event: events.NewMessage.Event) -> None:
    clear_history(event.sender_id)
    await event.respond("Диалог сброшен. Начнём с чистого листа!")
    raise events.StopPropagation


@client.on(events.NewMessage(pattern=r"^/help"))
async def cmd_help(event: events.NewMessage.Event) -> None:
    await event.respond(
        "Доступные команды:\n"
        "/start — начать заново\n"
        "/reset — сбросить историю диалога\n"
        "/help — эта справка\n\n"
        "Спрашивай всё о компании, команде, процессах и адаптации!"
    )
    raise events.StopPropagation


# ── Основной обработчик сообщений ─────────────────────────────────────────────

@client.on(events.NewMessage)
async def handle_message(event: events.NewMessage.Event) -> None:
    if event.out:  # пропускаем исходящие сообщения от самого бота
        return

    text = event.message.text or ""
    if not text.strip():
        return

    user_id = event.sender_id
    messages = load_history(user_id)
    messages.append({"role": "user", "content": text})

    try:
        async with client.action(event.chat_id, "typing"):
            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(
                _executor,
                lambda: run_agent_turn(messages),
            )
        save_history(user_id, messages)
        await event.respond(response)
    except Exception as e:
        log.error("Ошибка агента для user_id=%s: %s", user_id, e, exc_info=True)
        messages.pop()
        await event.respond(
            "Что-то пошло не так, попробуй ещё раз. "
            "Если ошибка повторяется — напиши /reset"
        )


# ── Запуск ────────────────────────────────────────────────────────────────────

async def main() -> None:
    init_db()
    await client.start(bot_token=BOT_TOKEN)
    me = await client.get_me()
    log.info("Бот @%s запущен. Провайдер: %s", me.username, os.getenv("AI_PROVIDER", "openrouter"))
    await client.run_until_disconnected()


if __name__ == "__main__":
    asyncio.run(main())
