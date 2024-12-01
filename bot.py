import os
import logging
import asyncio
from datetime import datetime
from typing import Dict, List, Optional
from dotenv import load_dotenv
from supabase import create_client, Client
from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type
)

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

# Initialize Supabase
supabase_url = os.getenv("SUPABASE_URL")
supabase_key = os.getenv("SUPABASE_KEY")
bot_token = os.getenv("BOT_TOKEN")

if not all([supabase_url, supabase_key, bot_token]):
    raise ValueError("Missing required environment variables")

supabase: Client = create_client(supabase_url, supabase_key)

# Achievement definitions
ACHIEVEMENTS = [
    {
        "id": "burner_fist",
        "title": "🔥 Burner Fist",
        "description": "Burn more supply",
        "requirement": 1000,
    },
    {
        "id": "firegod_fist",
        "title": "🌋 Firegod Fist",
        "description": "Burn more supply",
        "requirement": 3000,
    },
    {
        "id": "hellfire_fist",
        "title": "👹 Hellfire Fist",
        "description": "Burn a more supply",
        "requirement": 10000,
    },
    {
        "id": "clasher",
        "title": "⚔️ Clasher",
        "description": "Get 50 Booster",
        "requirement": 8000,
    },
    {
        "id": "mad_clasher",
        "title": "🗡️ Mad Clasher",
        "description": "Get 300 Booster",
        "requirement": 9000,
    }
]

@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=4, max=10),
    retry=retry_if_exception_type(Exception)
)
async def fetch_global_stats() -> Dict:
    """Fetch global statistics from Supabase."""
    try:
        response = supabase.table('global_stats').select("*").execute()
        return response.data[0] if response.data else {"total_points": 0, "total_games": 0}
    except Exception as e:
        logger.error(f"Error fetching global stats: {e}")
        raise

@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=4, max=10),
    retry=retry_if_exception_type(Exception)
)
async def fetch_leaderboard() -> List[Dict]:
    """Fetch leaderboard data from Supabase."""
    try:
        response = supabase.table('players').select("*").order('points', desc=True).limit(10).execute()
        return response.data
    except Exception as e:
        logger.error(f"Error fetching leaderboard: {e}")
        raise

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /start command."""
    welcome_message = (
        "🎮 Welcome to BurnTheDev Bot!\n\n"
        "I'm here to track your achievements and progress. Here are my commands:\n"
        "/progress - View your achievement progress\n"
        "/global - Show global game statistics\n"
        "/leaderboard - View top players\n"
        "/help - Show this help message"
    )
    await update.message.reply_text(welcome_message)

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /help command."""
    help_text = (
        "🤖 BurnTheDev Bot Commands:\n\n"
        "/progress - Check your achievement progress\n"
        "/global - View global game statistics\n"
        "/leaderboard - See top players\n"
        "/help - Show this help message"
    )
    await update.message.reply_text(help_text)

async def progress(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /progress command."""
    try:
        # Fetch user progress (implement your logic here)
        total_achievements = len(ACHIEVEMENTS)
        completed_achievements = 0  # Replace with actual count
        
        progress_message = "🏆 Achievement Progress\n\n"
        
        for achievement in ACHIEVEMENTS:
            # Replace with actual completion check
            is_completed = False
            status = "✅" if is_completed else "🔒"
            progress_message += f"{status} {achievement['title']}\n"
            progress_message += f"└ {achievement['description']} ({achievement['requirement']} points)\n\n"
        
        progress_message += f"\nTotal Progress: {completed_achievements}/{total_achievements} achievements"
        await update.message.reply_text(progress_message)
    except Exception as e:
        logger.error(f"Error in progress command: {e}")
        await update.message.reply_text("❌ Error fetching progress. Please try again later.")

async def global_stats(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /global command."""
    try:
        stats = await fetch_global_stats()
        
        message = (
            "🌍 Global Statistics\n\n"
            f"Total Points: {stats['total_points']:,} 💎\n"
            f"Games Played: {stats['total_games']:,} 🎮"
        )
        await update.message.reply_text(message)
    except Exception as e:
        logger.error(f"Error in global stats command: {e}")
        await update.message.reply_text("❌ Error fetching global stats. Please try again later.")

async def leaderboard(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /leaderboard command."""
    try:
        players = await fetch_leaderboard()
        
        message = "🏆 Top Players\n\n"
        for i, player in enumerate(players, 1):
            medal = "🥇" if i == 1 else "🥈" if i == 2 else "🥉" if i == 3 else "👑"
            message += f"{medal} {i}. {player['name']}: {player['points']:,} points\n"
        
        await update.message.reply_text(message)
    except Exception as e:
        logger.error(f"Error in leaderboard command: {e}")
        await update.message.reply_text("❌ Error fetching leaderboard. Please try again later.")

async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle errors."""
    logger.error(f"Update {update} caused error {context.error}")
    if update and update.message:
        await update.message.reply_text(
            "❌ An error occurred while processing your request. Please try again later."
        )

def main() -> None:
    """Start the bot."""
    # Create application and add handlers
    application = Application.builder().token(bot_token).build()

    # Add command handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("progress", progress))
    application.add_handler(CommandHandler("global", global_stats))
    application.add_handler(CommandHandler("leaderboard", leaderboard))

    # Add error handler
    application.add_error_handler(error_handler)

    # Start the bot
    logger.info("Starting bot...")
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()
