"""
Simple AI Telegram Bot with memory.
Talks like an AI, remembers facts about you, can be extended to check email.
"""

import os
import json
import logging
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, ContextTypes, filters
import anthropic

logging.basicConfig(level=logging.INFO)

TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN", "")
ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")

MEMORY_FILE = "memory.json"
client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)


def load_memory():
    if os.path.exists(MEMORY_FILE):
        with open(MEMORY_FILE, "r") as f:
            return json.load(f)
    return {"facts": [], "chat_history": []}


def save_memory(mem):
    with open(MEMORY_FILE, "w") as f:
        json.dump(mem, f, indent=2)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Hi! I'm your AI bot. I remember things about you and I can chat.\n\n"
        "Try:\n"
        "/remember <fact> — save something about you\n"
        "/facts — see what I remember\n"
        "Or just message me anything to chat."
    )


async def remember(update: Update, context: ContextTypes.DEFAULT_TYPE):
    fact = " ".join(context.args)
    if not fact:
        await update.message.reply_text("Tell me what to remember. Example: /remember I like coffee")
        return
    mem = load_memory()
    mem["facts"].append(fact)
    save_memory(mem)
    await update.message.reply_text(f"Got it, I'll remember: {fact}")


async def facts(update: Update, context: ContextTypes.DEFAULT_TYPE):
    mem = load_memory()
    if not mem["facts"]:
        await update.message.reply_text("I don't know anything about you yet.")
        return
    text = "Here's what I remember:\n" + "\n".join(f"- {f}" for f in mem["facts"])
    await update.message.reply_text(text)


async def chat(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_msg = update.message.text
    mem = load_memory()

    facts_text = "\n".join(mem["facts"]) if mem["facts"] else "Nothing yet."
    system_prompt = (
        "You are a helpful, friendly assistant chatting with the user on Telegram. "
        "Keep answers short and simple, easy words, no jargon.\n\n"
        f"Known facts about the user:\n{facts_text}"
    )

    history = mem["chat_history"][-10:]  # last 10 messages for context
    history.append({"role": "user", "content": user_msg})

    response = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=500,
        system=system_prompt,
        messages=history,
    )
    reply = response.content[0].text

    history.append({"role": "assistant", "content": reply})
    mem["chat_history"] = history[-20:]
    save_memory(mem)

    await update.message.reply_text(reply)


def main():
    if not TELEGRAM_TOKEN or not ANTHROPIC_API_KEY:
        print("ERROR: Set TELEGRAM_TOKEN and ANTHROPIC_API_KEY environment variables first.")
        return

    app = Application.builder().token(TELEGRAM_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("remember", remember))
    app.add_handler(CommandHandler("facts", facts))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, chat))

    print("Bot is running...")
    app.run_polling()


if __name__ == "__main__":
    main()
