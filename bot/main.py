"""
Main entry point for the Telegram Expense Bot.
"""

import os
import sys
import logging
import yaml

from telegram.ext import Application
from handlers import setup_handlers, setup_pdf_handlers


def load_config() -> dict:
    """Load configuration from config.yaml."""
    search_paths = [
        os.path.expanduser("~/.config/expense-bot/config.yaml"),
        os.path.join(os.path.dirname(os.path.dirname(__file__)), "config.yaml"),
    ]
    
    for path in search_paths:
        if os.path.exists(path):
            with open(path, "r") as f:
                return yaml.safe_load(f)
    
    raise FileNotFoundError("Configuration file not found!")


def setup_logging():
    """Configure logging for the bot."""
    logging.basicConfig(
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        level=logging.INFO,
    )


async def post_init(application: Application):
    """Run after bot initialization."""
    logging.info("Expense Bot started successfully!")


def main():
    """Main function to run the bot."""
    setup_logging()
    config = load_config()
    
    token = config["bot"]["token"]
    
    if token == "YOUR_BOT_TOKEN_HERE":
        logging.error("Please configure your bot token in config.yaml!")
        sys.exit(1)
    
    application = (
        Application.builder()
        .token(token)
        .post_init(post_init)
        .build()
    )
    
    application.bot_data["config"] = config
    
    setup_handlers(application)
    setup_pdf_handlers(application)
    
    logging.info("Starting bot...")
    application.run_polling(allowed_updates=["message", "edited_message"])


if __name__ == "__main__":
    main()
