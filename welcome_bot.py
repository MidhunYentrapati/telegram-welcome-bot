# Here's a full Python script that:
# 1. Welcomes new users using Telegram bot (same as before).
# 2. Uses Dialogflow to respond to direct messages sent to the bot.

from flask import Flask, request
from threading import Thread
import os
import random
import asyncio
import json
from telegram import Update, ChatMember
from telegram.ext import (
    ApplicationBuilder, ChatMemberHandler,
    MessageHandler, ContextTypes, filters
)
from google.cloud import dialogflow_v2 as dialogflow

# Setup Flask to keep the Railway app alive
flask_app = Flask(__name__)

@flask_app.route('/')
def home():
    return "🤖 Maker's Vault Bot is active!"

def run_flask():
    flask_app.run(host="0.0.0.0", port=8080)

Thread(target=run_flask).start()

# Welcome messages
WELCOME_MESSAGES = [
    "👋 Welcome {name} to Maker's Vault! Let's build magic together.",
    "🎉 Hey {name}, you’ve just joined a community of storytellers and creators!",
    "🔥 Big welcome {name}! Let's grow together in Maker's Vault.",
    "🚀 {name} just landed in Maker's Vault. Time to collaborate!",
    "✨ Welcome aboard {name}! Let’s create greatness together.",
]

# Telegram Bot Token
TOKEN = os.getenv("BOT_TOKEN")
if not TOKEN:
    print("❌ BOT_TOKEN not found. Please set it in your environment variables.")
    exit()

# Dialogflow setup
DIALOGFLOW_PROJECT_ID = os.getenv("DIALOGFLOW_PROJECT_ID")
DIALOGFLOW_LANGUAGE_CODE = "en"
SESSION_ID = "maker-vault-session"

def detect_intent_texts(project_id, session_id, text, language_code):
    """Send user message to Dialogflow and get intent response."""
    session_client = dialogflow.SessionsClient()
    session = session_client.session_path(project_id, session_id)
    text_input = dialogflow.TextInput(text=text, language_code=language_code)
    query_input = dialogflow.QueryInput(text=text_input)

    response = session_client.detect_intent(
        request={"session": session, "query_input": query_input}
    )
    return response.query_result.fulfillment_text

# Handle new member join
async def handle_new_chat_members(update: Update, context: ContextTypes.DEFAULT_TYPE):
    for user in update.message.new_chat_members:
        if not user.is_bot:
            name = f"@{user.username}" if user.username else user.full_name
            welcome_text = random.choice(WELCOME_MESSAGES).format(name=name)
            await context.bot.send_message(chat_id=update.effective_chat.id, text=welcome_text)
            print(f"✅ Sent welcome message to {name}")

# Handle status change (e.g. left ➜ joined)
async def handle_chat_member_update(update: Update, context: ContextTypes.DEFAULT_TYPE):
    old = update.chat_member.old_chat_member
    new = update.chat_member.new_chat_member
    if old.status in ["left", "kicked"] and new.status == "member":
        user = new.user
        if not user.is_bot:
            name = f"@{user.username}" if user.username else user.full_name
            welcome_text = random.choice(WELCOME_MESSAGES).format(name=name)
            await context.bot.send_message(chat_id=update.chat_member.chat.id, text=welcome_text)
            print(f"✅ Sent welcome message to {name}")

# Handle direct messages using Dialogflow
async def handle_direct_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.chat.type == "private":
        user_text = update.message.text
        dialogflow_response = detect_intent_texts(
            DIALOGFLOW_PROJECT_ID, SESSION_ID, user_text, DIALOGFLOW_LANGUAGE_CODE
        )
        if dialogflow_response:
            await context.bot.send_message(chat_id=update.effective_chat.id, text=dialogflow_response)
            print(f"💬 Replied with: {dialogflow_response}")
        else:
            await context.bot.send_message(chat_id=update.effective_chat.id, text="Sorry, I didn’t get that.")

# Run the bot
if __name__ == "__main__":
    print("🚀 Starting Maker’s Vault Bot...")

    app = ApplicationBuilder().token(TOKEN).build()

    # Register handlers
    app.add_handler(MessageHandler(filters.StatusUpdate.NEW_CHAT_MEMBERS, handle_new_chat_members))
    app.add_handler(ChatMemberHandler(handle_chat_member_update, ChatMemberHandler.CHAT_MEMBER))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_direct_message))

    print("📡 Bot is polling...")
    app.run_polling()
