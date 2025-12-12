import os
import logging
from dotenv import load_dotenv
from app.database import init_db
from app.bot import start_bot

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def main():
    # Load environment variables
    load_dotenv()
    
    # Check required environment variables
    required_vars = [
        'TELEGRAM_BOT_TOKEN',
        'OPENAI_API_KEY',
        'POSTGRES_USER',
        'POSTGRES_PASSWORD',
        'POSTGRES_DB',
        'POSTGRES_HOST',
        'POSTGRES_PORT'
    ]
    
    missing_vars = [var for var in required_vars if not os.getenv(var)]
    if missing_vars:
        logger.error(f"Missing required environment variables: {', '.join(missing_vars)}")
        logger.info("Please copy .env.example to .env and fill in the required values.")
        return
    
    try:
        # Initialize database
        logger.info("Initializing database...")
        init_db()
        
        # Start the bot
        logger.info("Starting Telegram bot...")
        start_bot()
        
    except Exception as e:
        logger.error(f"An error occurred: {e}", exc_info=True)
    finally:
        logger.info("Bot has been stopped.")

if __name__ == "__main__":
    main()
