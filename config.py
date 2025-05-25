"""Configuration de l'application Flask."""
import os
from dotenv import load_dotenv

load_dotenv()  # Charger les variables d'environnement depuis .env

class Config:
    """Configuration de base."""
    SECRET_KEY = os.environ.get('SECRET_KEY', 'dev-key-change-in-production')
    ORACLE_USER = os.environ.get('ORACLE_USER', '')
    ORACLE_PASSWORD = os.environ.get('ORACLE_PASSWORD', '')
    ORACLE_DSN = os.environ.get('ORACLE_DSN', '')
    ORACLE_POOL_MIN = int(os.environ.get('ORACLE_POOL_MIN', 2))
    ORACLE_POOL_MAX = int(os.environ.get('ORACLE_POOL_MAX', 10))
    LOG_LEVEL = os.environ.get('LOG_LEVEL', 'INFO')
    GITLAB_API_URL = os.environ.get('GITLAB_API_URL', 'https://gitlab.com/api/v4')

class DevelopmentConfig(Config):
    """Configuration de développement."""
    DEBUG = True
    TESTING = False

class ProductionConfig(Config):
    """Configuration de production."""
    DEBUG = False
    TESTING = False

class TestingConfig(Config):
    """Configuration de test."""
    DEBUG = True
    TESTING = True

config_by_name = {
    'dev': DevelopmentConfig,
    'prod': ProductionConfig,
    'test': TestingConfig
}

def get_config():
    """Récupérer la configuration en fonction de l'environnement."""
    env = os.environ.get('FLASK_ENV', 'dev')
    return config_by_name[env]
