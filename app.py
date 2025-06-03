from flask import Flask, jsonify
import structlog
from config import get_config
from app.utils.logging_utils import configure_logging
from app.routes.terraform_routes import terraform_bp
from app.services.db_service import OracleDBService
from flasgger import Swagger

def create_app(config_name='dev'):
    app = Flask(__name__)
    app.config.from_object(get_config())
    Swagger(app)
    logger = configure_logging(app.config)
    # Singleton DB Service
    app.db_service = OracleDBService(app.config)
    app.register_blueprint(terraform_bp, url_prefix='/api/terraform')

    @app.route('/health', methods=['GET'])
    def health_check():
        return jsonify({"status": "healthy", "version": "1.0.0"})

    @app.errorhandler(404)
    def not_found(e):
        return jsonify({"error": "Route non trouvée"}), 404

    @app.errorhandler(500)
    def internal_server_error(e):
        logger.error("Erreur serveur interne", error=str(e), exc_info=True)
        return jsonify({"error": "Erreur serveur interne"}), 500

    @app.errorhandler(400)
    def bad_request(e):
        return jsonify({"error": "Requête invalide", "details": str(e)}), 400

    logger.info("App Flask initialisée")
    return app

if __name__ == '__main__':
    app = create_app()
    app.run(host='0.0.0.0', port=8444)
