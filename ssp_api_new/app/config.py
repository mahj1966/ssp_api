import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    ORACLE_USER = os.getenv('ORACLE_USER')
    ORACLE_PASSWORD = os.getenv('ORACLE_PASSWORD')
    ORACLE_DSN = os.getenv('ORACLE_DSN')
    GITLAB_URL = os.getenv('GITLAB_URL')
    JWT_SECRET = os.getenv('JWT_SECRET')
    FLASK_ENV = os.getenv('FLASK_ENV', 'production')