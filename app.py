"""Point d'entrée de l'application Flask pour la génération de code Terraform."""
from flask import Flask, jsonify
import structlog
from config import get_config
from app.utils.logging_utils import configure_logging
from app.routes.terraform_routes import terraform_bp

def create_app(config_name='dev'):
    """
    Crée et configure l'application Flask.
    
    Args:
        config_name: Nom de la configuration à utiliser
    
    Returns:
        Application Flask configurée
    """
    app = Flask(__name__)
    app.config.from_object(get_config())
    
    # Configuration du logging
    logger = configure_logging(app.config)
    
    # Enregistrement des blueprints
    app.register_blueprint(terraform_bp, url_prefix='/api/terraform')
    
    # Route pour la vérification de l'état de santé de l'API
    @app.route('/health', methods=['GET'])
    def health_check():
        return jsonify({"status": "healthy", "version": "1.0.0"})
    
    # Gestionnaire d'erreurs pour les erreurs 404
    @app.errorhandler(404)
    def not_found(e):
        return jsonify({"error": "Route non trouvée"}), 404
    
    # Gestionnaire d'erreurs pour les erreurs 500
    @app.errorhandler(500)
    def internal_server_error(e):
        logger.error("Erreur serveur interne", error=str(e), exc_info=True)
        return jsonify({"error": "Erreur serveur interne"}), 500
    
    # Gestionnaire d'erreurs pour les erreurs de validation JSON
    @app.errorhandler(400)
    def bad_request(e):
        return jsonify({"error": "Requête invalide", "details": str(e)}), 400
    
    logger.info("Application Flask initialisée avec succès", config=config_name)
    return app

if __name__ == '__main__':
    app = create_app()
    app.run(host='0.0.0.0', port=5000)
