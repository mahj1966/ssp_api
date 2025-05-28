from loguru import logger
import sys

def configure_logging(app):
    logger.remove()
    logger.add(
        sys.stderr,
        format="{time:YYYY-MM-DD HH:mm:ss} | {level} | {message}",
        level="DEBUG" if app.config['FLASK_ENV'] == 'development' else "INFO"
    )
    logger.add(
        "logs/app.log",
        rotation="500 MB",
        retention="30 days",
        compression="zip"
    )