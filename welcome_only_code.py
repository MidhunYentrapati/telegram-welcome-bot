from flask import Flask
from threading import Thread
import os
import random
from telegram import Update, ChatMember
from telegram.ext import ApplicationBuilder, ChatMemberHandler, MessageHandler, filters, ContextTypes

# Flask app to keep bot alive (useful on Replit/Railway)
flask_app = Flask(__name__)

@flask_app.route('/')
def home():
    return "🤖 Welcome Bot is running!"

def run_flask():
    flask_app.run(host="0.0.0.0", port=8080)

Thread(target=run_flask).start()

# Welcome messages list
WELCOME_MESSAGES = [
    "👋 Welcome {name} to Maker's Vault! Let's build magic together.",
    "🎉 Hey {name}, you’ve just joined a community of storytellers and creators!",
    "🔥 Big welcome {name}! Let's grow together in Maker's Vault.",
    "🚀 {name} just landed in Maker's Vault. Time to collaborate!",
    "✨ Welcome aboard {name}! Let’s create greatness together.",
]

# Get your bot token from environment variable or hardcode (not recommended)
TOKEN = os.getenv("BOT_TOKEN")
if not TOKEN:
    print("❌ BOT_TOKEN not found. Please set it in your environment variables.")
    exit()

# Triggered when user joins the group (standard update)
async def handle_new_chat_members(update: Update, context: ContextTypes.DEFAULT_TYPE):
    for user in update.message.new_chat_members:
        if not user.is_bot:
            name = f"@{user.username}" if user.username else user.full_name
            welcome_text = random.choice(WELCOME_MESSAGES).format(name=name)
            await context.bot.send_message(chat_id=update.effective_chat.id, text=welcome_text)
            print(f"✅ Sent welcome message to {name}")

# Triggered when member status changes (more reliable sometimes)
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

# Run the bot
if __name__ == "__main__":
    print("🚀 Starting Welcome Bot...")

    app = ApplicationBuilder().token(TOKEN).build()

    # Handlers
    app.add_handler(MessageHandler(filters.StatusUpdate.NEW_CHAT_MEMBERS, handle_new_chat_members))
    app.add_handler(ChatMemberHandler(handle_chat_member_update, ChatMemberHandler.CHAT_MEMBER))

    print("📡 Bot is polling for updates...")
    app.run_polling()
