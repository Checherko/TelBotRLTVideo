import os
import logging
from aiogram import Bot, Dispatcher, types
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters import Command
from aiogram.types import ParseMode
from dotenv import load_dotenv

from app.database import get_db
from app.services.nlp_service import NLPService, QueryBuilder
from sqlalchemy.orm import Session
from sqlalchemy import text

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

# Initialize bot and dispatcher
bot = Bot(token=os.getenv('TELEGRAM_BOT_TOKEN'))
storage = MemoryStorage()
dp = Dispatcher(bot, storage=storage)

# Initialize NLP service
try:
    nlp_service = NLPService(openai_api_key=os.getenv('OPENAI_API_KEY'))
except Exception as e:
    logger.error(f"Failed to initialize NLP service: {e}")
    raise

@dp.message_handler(Command('start'))
async def send_welcome(message: types.Message):
    """Send a welcome message when the command /start is issued."""
    welcome_text = (
        "👋 Привет! Я бот для аналитики по видео.\n\n"
        "Вы можете задавать мне вопросы на естественном языке, например:\n"
        "• Сколько всего видео есть в системе?\n"
        "• Сколько видео у креатора с id 123 вышло с 1 ноября 2025 по 5 ноября 2025?\n"
        "• Сколько видео набрало больше 100 000 просмотров за всё время?\n"
        "• На сколько просмотров в сумме выросли все видео 28 ноября 2025?\n"
        "• Сколько разных видео получали новые просмотры 27 ноября 2025?\n\n"
        "Задайте мне вопрос, и я постараюсь на него ответить!"
    )
    await message.reply(welcome_text)

@dp.message_handler(Command('help'))
async def send_help(message: types.Message):
    """Send a help message when the command /help is issued."""
    help_text = (
        "ℹ️ *Помощь по боту*\n\n"
        "Я умею отвечать на вопросы о видео и их статистике. Вот примеры запросов:\n\n"
        "*Подсчет видео*\n"
        "• Сколько всего видео в системе?\n"
        "• Сколько видео вышло за последнюю неделю?\n"
        "• Сколько видео у креатора с id 123?\n\n"
        "*Статистика просмотров*\n"
        "• Сколько просмотров у видео с id 456?\n"
        "• Сколько просмотров набрали видео за вчера?\n"
        "• Какие видео набрали больше 1000 просмотров?\n\n"
        "*Анализ активности*\n"
        "• Какие видео получали новые просмотры вчера?\n"
        "• Сколько лайков в среднем получают видео?\n\n"
        "Просто задайте вопрос, и я постараюсь на него ответить!"
    )
    await message.reply(help_text, parse_mode=ParseMode.MARKDOWN)

@dp.message_handler()
async def handle_message(message: types.Message):
    """Handle all other messages with the NLP service."""
    try:
        # Show typing indicator
        await types.ChatActions.typing()
        
        # Parse the user's question
        intent = nlp_service.parse_query(message.text)
        logger.info(f"Parsed intent: {intent}")
        
        # Build and execute the query
        query, params = QueryBuilder.build_query(intent)
        logger.info(f"Generated query: {query}")
        logger.info(f"Query params: {params}")
        
        # Execute the query
        db: Session = next(get_db())
        result = db.execute(text(query), params).scalar()
        
        # Format the response
        response = f"📊 Результат: {result}"
        
    except Exception as e:
        logger.error(f"Error processing message: {e}", exc_info=True)
        response = "❌ Произошла ошибка при обработке вашего запроса. Пожалуйста, попробуйте сформулировать его иначе."
    
    await message.reply(response)

def start_bot():
    """Start the bot."""
    from aiogram import executor
    
    # Start the bot
    logger.info("Starting bot...")
    executor.start_polling(dp, skip_updates=True)
