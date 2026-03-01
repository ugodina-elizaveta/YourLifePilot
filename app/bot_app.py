
import logging
import sys
from datetime import datetime

from telegram.ext import Application

from app.config import BOT_TOKEN

# Настройка логирования
logging.basicConfig(
    level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', stream=sys.stdout
)
logger = logging.getLogger(__name__)

# Проверка токена
if not BOT_TOKEN:
    logger.error("❌ BOT_TOKEN not configured!")
    sys.exit(1)

# Создаем экземпляр бота
bot_app = Application.builder().token(BOT_TOKEN).build()
logger.info("✅ Bot application created")

# Для отслеживания активности
last_activity = datetime.now()
