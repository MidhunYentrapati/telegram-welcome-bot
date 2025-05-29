from flask import Flask
from threading import Thread
import os
import random
import base64
import logging
from telegram import Update
from telegram.ext import (
    ApplicationBuilder, ChatMemberHandler,
    MessageHandler, ContextTypes, filters
)
from google.cloud import dialogflow_v2 as dialogflow
from google.api_core.exceptions import GoogleAPICallError

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# ========== HANDLER FUNCTIONS ==========
async def handle_new_chat_members(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle new members joining the group"""
    for user in update.message.new_chat_members:
        if not user.is_bot:
            name = f"@{user.username}" if user.username else user.full_name
            welcome_text = random.choice(WELCOME_MESSAGES).format(name=name)
            await context.bot.send_message(chat_id=update.effective_chat.id, text=welcome_text)
            logger.info(f"✅ Sent welcome message to {name}")

async def handle_chat_member_update(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle when a user rejoins the group"""
    old = update.chat_member.old_chat_member
    new = update.chat_member.new_chat_member
    if old.status in ["left", "kicked"] and new.status == "member":
        user = new.user
        if not user.is_bot:
            name = f"@{user.username}" if user.username else user.full_name
            welcome_text = random.choice(WELCOME_MESSAGES).format(name=name)
            await context.bot.send_message(chat_id=update.chat_member.chat.id, text=welcome_text)
            logger.info(f"✅ Sent welcome message to {name}")

async def handle_direct_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle private messages using Dialogflow"""
    if update.message.chat.type == "private":
        user_text = update.message.text
        dialogflow_response = await detect_intent_texts(
            DIALOGFLOW_PROJECT_ID, SESSION_ID, user_text, DIALOGFLOW_LANGUAGE_CODE
        )
        if dialogflow_response:
            await context.bot.send_message(chat_id=update.effective_chat.id, text=dialogflow_response)
            logger.info(f"💬 Replied with: {dialogflow_response}")
        else:
            await context.bot.send_message(chat_id=update.effective_chat.id, text="Sorry, I didn't get that.")

# ========== DIALOGFLOW FUNCTION ==========
async def detect_intent_texts(project_id, session_id, text, language_code):
    """Send user message to Dialogflow and get intent response."""
    try:
        session_client = dialogflow.SessionsClient()
        session = session_client.session_path(project_id, session_id)
        text_input = dialogflow.TextInput(text=text, language_code=language_code)
        query_input = dialogflow.QueryInput(text=text_input)

        response = session_client.detect_intent(
            request={"session": session, "query_input": query_input}
        )
        return response.query_result.fulfillment_text
    except GoogleAPICallError as e:
        logger.error(f"Dialogflow API error: {e}")
        return None
    except Exception as e:
        logger.error(f"Unexpected error in detect_intent_texts: {e}")
        return None

# ========== FLASK SETUP ==========
flask_app = Flask(__name__)

@flask_app.route('/')
def home():
    return "🤖 Maker's Vault Bot is active!"

def run_flask():
    flask_app.run(host="0.0.0.0", port=8080)

# ========== MAIN APPLICATION ==========
if __name__ == "__main__":
    # Validate environment variables
    REQUIRED_ENV = ["BOT_TOKEN", "DIALOGFLOW_CREDS_BASE64", "DIALOGFLOW_PROJECT_ID"]
    missing = [var for var in REQUIRED_ENV if not os.getenv(var)]
    if missing:
        logger.error(f"❌ Missing required environment variables: {', '.join(missing)}")
        exit(1)

    # Setup Dialogflow credentials
    try:
        encoded_creds = os.getenv("DIALOGFLOW_CREDS_BASE64")
        creds_path = "/tmp/dialogflow_creds.json"
        with open(creds_path, "wb") as f:
            f.write(base64.b64decode(encoded_creds))
        os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = creds_path
        logger.info("✅ Dialogflow credentials set up successfully")
    except Exception as e:
        logger.error(f"❌ Failed to set up Dialogflow credentials: {e}")

    # Configuration
    WELCOME_MESSAGES = [
        "👋 Welcome {name} to Maker's Vault! Let's build magic together.",
        # ... (rest of your messages)
    ]

    # Start Flask in a separate thread
    Thread(target=run_flask).start()

    # Start the Telegram bot
    try:
        logger.info("🚀 Starting Maker's Vault Bot...")
        app = ApplicationBuilder().token(os.getenv("BOT_TOKEN")).build()

        # Register handlers
        app.add_handler(MessageHandler(filters.StatusUpdate.NEW_CHAT_MEMBERS, handle_new_chat_members))
        app.add_handler(ChatMemberHandler(handle_chat_member_update, ChatMemberHandler.CHAT_MEMBER))
        app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_direct_message))

        logger.info("📡 Bot is polling...")
        app.run_polling()
    except Exception as e:
        logger.error(f"Bot crashed with error: {e}")
