"""
Main entry point for the Telegram Expense Bot.

Usage:
    python3 -m bot.main
"""

import os
import sys
import logging
import yaml

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from telegram.ext import Application
from handlers import setup_handlers, setup_pdf_handlers


def load_config() -> dict:
    """Load configuration from config.yaml."""
    # 搜索配置文件路径（优先级从高到低）
    search_paths = [
        os.path.expanduser("~/.config/expense-bot/config.yaml"),
        os.path.join(os.path.dirname(os.path.dirname(__file__)), "config.yaml"),
    ]
    
    config_path = None
    for path in search_paths:
        if os.path.exists(path):
            config_path = path
            break
    
    if not config_path:
        raise FileNotFoundError(
            f"Configuration file not found!\n"
            "Please create ~/.config/expense-bot/config.yaml from config.yaml.example"
        )
    
    with open(config_path, "r") as f:
        return yaml.safe_load(f)


def setup_logging():
    """Configure logging for the bot."""
    logging.basicConfig(
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        level=logging.INFO,
    )


async def post_init(application: Application):
    """Run after bot initialization."""
    logging.info("Expense Bot started successfully!")


class UserAuthMixin:
    """Mixin to add user authentication."""
    
    @staticmethod
    async def auth_check(update, context):
        """Check if user is allowed to use the bot."""
        config = context.application.bot_data.get("config", {})
        allowed_users = config.get("security", {}).get("allowed_users", [])
        
        # If no whitelist configured, allow all
        if not allowed_users:
            return
        
        user_id = update.effective_user.id
        if user_id not in allowed_users:
            await update.message.reply_text("⛔ 您没有权限使用此机器人。")
            return False
        return True


def main():
    """Main function to run the bot."""
    setup_logging()
    config = load_config()
    
    token = config["bot"]["token"]
    
    if token == "YOUR_BOT_TOKEN_HERE":
        logging.error("Please configure your bot token in config.yaml!")
        sys.exit(1)
    
    # 先删除 webhook，确保没有冲突
    import telegram
    bot = telegram.Bot(token=token)
    try:
        bot.delete_webhook()
        logging.info("Webhook deleted successfully")
    except Exception as e:
        logging.warning(f"Could not delete webhook: {e}")
    
    # Build application
    application = (
        Application.builder()
        .token(token)
        .post_init(post_init)
        .build()
    )
    
    # Store config for auth check
    application.bot_data["config"] = config
    
    # Set up handlers
    setup_handlers(application)
    setup_pdf_handlers(application)
    
    # Start polling
    logging.info("Starting bot...")
    application.run_polling(allowed_updates=["message", "edited_message"])


def run():
    """Alias for main()."""
    main()


if __name__ == "__main__":
    main()
