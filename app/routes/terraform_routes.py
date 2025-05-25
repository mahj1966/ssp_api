"""Routes de l'API pour la génération de code Terraform."""
from flask import Blueprint, request, jsonify, current_app
import structlog
import uuid
from marshmallow import Schema, fields, ValidationError
from ..services.db_service import OracleDBService
from ..services.jinja_service import JinjaService
from ..services.gitlab_service import GitLabService

logger = structlog.get_logger(__name__)
terraform_bp = Blueprint('terraform', __name__)

class TerraformRequestSchema(Schema):
    """Schéma de validation pour les requêtes de génération Terraform."""
    username = fields.String(required=True)
    cloud_id = fields.String(required=True)
    resource_type = fields.String(required=True)
    request_id = fields.Integer(required=True)

@terraform_bp.route('/generate', methods=['POST'])
def generate_terraform():
    """
    Génère des fichiers Terraform à partir des données en base et des templates Jinja.
    
    Paramètres attendus dans le corps de la requête JSON:
    - username: Nom d'utilisateur
    - cloud_id: Identifiant du cloud (aws, gcp, etc.)
    - resource_type: Type de ressource (rds, ec2, etc.)
    - request_id: ID de la demande
    
    Returns:
        Réponse JSON avec les détails de la requête de fusion créée
    """
    logger_req = logger.bind(request_id=str(uuid.uuid4())[:8])
    logger_req.info("Requête de génération Terraform reçue")
    
    # Validation des données d'entrée
    try:
        schema = TerraformRequestSchema()
        data = schema.load(request.json)
    except ValidationError as err:
        logger_req.error("Erreur de validation des données d'entrée", errors=err.messages)
        return jsonify({"error": "Données d'entrée invalides", "details": err.messages}), 400
    
    username = data['username']
    cloud_id = data['cloud_id']
    resource_type = data['resource_type']
    request_id = data['request_id']
    
    logger_req = logger_req.bind(
        username=username,
        cloud_id=cloud_id,
        resource_type=resource_type,
        request_id=request_id
    )
    
    try:
        # Initialiser les services
        db_service = OracleDBService(current_app.config)
        jinja_service = JinjaService()
        gitlab_service = GitLabService(current_app.config.get('GITLAB_API_URL'))
        
        # Récupérer les données de ressource
        resource_data = db_service.get_resource_data(cloud_id, resource_type, request_id)
        if not resource_data:
            logger_req.error("Données de ressource non trouvées")
            return jsonify({"error": f"Ressource non trouvée pour {cloud_id}/{resource_type}/{request_id}"}), 404
        
        # Récupérer le template Jinja
        module_version = resource_data.get('module_version')
        if not module_version:
            logger_req.error("Version du module non spécifiée dans les données de ressource")
            return jsonify({"error": "Version du module non spécifiée"}), 400
        
        template = db_service.get_jinja_template(cloud_id, resource_type, module_version)
        if not template:
            logger_req.error("Template Jinja non trouvé")
            return jsonify({
                "error": f"Template non trouvé pour {cloud_id}/{resource_type}/{module_version}"
            }), 404
        
        # Générer le code Terraform
        terraform_code = jinja_service.render_terraform_code(template, resource_data)
        
        # Valider le code Terraform généré
        validation = gitlab_service.validate_terraform_files(None, terraform_code)
        if not validation['is_valid']:
            logger_req.error("Validation du code Terraform échouée", errors=validation['errors'])
            return jsonify({
                "error": "Validation du code Terraform échouée",
                "details": validation['errors'],
                "terraform_code": terraform_code
            }), 400
        
        # Récupérer le jeton GitLab de l'utilisateur
        gitlab_token = db_service.get_user_gitlab_token(username)
        if not gitlab_token:
            logger_req.error("Jeton GitLab non trouvé pour l'utilisateur")
            return jsonify({"error": f"Jeton GitLab non trouvé pour l'utilisateur {username}"}), 404
        
        # Récupérer l'ID du projet GitLab
        project_id = db_service.get_gitlab_project_id(cloud_id, resource_type, request_id)
        if not project_id:
            logger_req.error("ID de projet GitLab non trouvé")
            return jsonify({"error": "ID de projet GitLab non trouvé"}), 404
        
        # Générer un nom pour la branche source
        resource_name = resource_data.get('name', f"resource-{request_id}")
        source_branch = f"feature/{cloud_id}-{resource_type}-{resource_name}"
        
        # Créer le fichier Terraform
        file_path = f"{cloud_id}/{resource_type}/{resource_name}.tf"
        terraform_files = {file_path: terraform_code}
        
        # Créer une merge request dans GitLab
        merge_request = gitlab_service.create_merge_request(
            token=gitlab_token,
            project_id=project_id,
            terraform_files=terraform_files,
            source_branch=source_branch,
            title=f"Ajout de {cloud_id} {resource_type}: {resource_name}",
            description=f"""
            Ressource Terraform générée automatiquement
            
            Cloud: {cloud_id}
            Type: {resource_type}
            Module version: {module_version}
            ID de la demande: {request_id}
            """
        )
        
        logger_req.info("Terraform généré et merge request créée avec succès", 
                      merge_request_id=merge_request['merge_request_id'],
                      merge_request_url=merge_request['merge_request_url'])
        
        return jsonify({
            "success": True,
            "message": "Code Terraform généré et merge request créée avec succès",
            "merge_request": merge_request
        })
        
    except Exception as e:
        logger_req.error("Erreur lors de la génération Terraform", error=str(e), exc_info=True)
        return jsonify({
            "error": "Erreur lors de la génération Terraform",
            "details": str(e)
        }), 500
