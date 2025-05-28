from flask import Flask
from app.config import Config
from app.db.oracle_client import OracleDBClient
from app.gitlab.client import GitLabClient
from app.utils.logging import configure_logging
import logging

def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)
    
    # Initialize dependencies
    app.oracle_client = OracleDBClient(
        user=app.config['ORACLE_USER'],
        password=app.config['ORACLE_PASSWORD'],
        dsn=app.config['ORACLE_DSN']
    )
    
    app.gitlab_client = GitLabClient(
        url=app.config['GITLAB_URL']
    )
    
    # Register blueprints
    from app.routes import api
    app.register_blueprint(api, url_prefix='/api/v1')
    
    # Configure logging
    configure_logging(app)
    
    return app