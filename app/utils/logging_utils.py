"""Configuration de la journalisation."""
import os
import yaml
import logging
import structlog
from structlog.stdlib import LoggerFactory

def configure_logging(config):
    """Configure la journalisation avec différents niveaux et sorties."""
    log_level = getattr(logging, config.LOG_LEVEL)
    
    # Configuration de structlog pour une journalisation structurée
    structlog.configure(
        processors=[
            structlog.stdlib.filter_by_level,
            structlog.stdlib.add_logger_name,
            structlog.stdlib.add_log_level,
            structlog.processors.TimeStamper(fmt="%Y-%m-%d %H:%M:%S"),
            structlog.contextvars.merge_contextvars,
            structlog.processors.format_exc_info,
            structlog.processors.UnicodeDecoder(),
            structlog.stdlib.ProcessorFormatter.wrap_for_formatter,
        ],
        logger_factory=LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )

    # Configuration avec logging standard
    logging.basicConfig(
        level=log_level,
        format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S',
    )

    # Ajout d'un handler pour enregistrer dans un fichier
    if not os.path.exists('logs'):
        os.makedirs('logs')
    
    file_handler = logging.FileHandler('logs/terraform_generator.log')
    file_handler.setLevel(log_level)
    file_handler.setFormatter(logging.Formatter(
        '%(asctime)s [%(levelname)s] %(name)s: %(message)s'
    ))
    
    # Récupération du logger racine et ajout du handler de fichier
    root_logger = logging.getLogger()
    root_logger.addHandler(file_handler)
    
    return structlog.get_logger()
