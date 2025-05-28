from flask import Blueprint, request, jsonify, current_app
import structlog
import uuid
from marshmallow import Schema, fields, ValidationError
from ..services.db_service import OracleDBService
from ..services.jinja_service import JinjaService
from ..services.gitlab_service import GitLabService
from flasgger.utils import swag_from

logger = structlog.get_logger(__name__)
terraform_bp = Blueprint('terraform', __name__)

class TerraformRequestSchema(Schema):
    username = fields.String(required=True)
    cloud_id = fields.String(required=True)
    resource_type = fields.String(required=True)
    request_id = fields.Integer(required=True)

def check_api_key():
    api_key = request.headers.get("X-API-KEY")
    expected = current_app.config.get("API_KEY")
    if not api_key or api_key != expected:
        return jsonify({"error": "API key manquante ou invalide"}), 401

@terraform_bp.route('/generate', methods=['POST'])
@swag_from({
    'tags': ['terraform'],
    'parameters': [{
        'name': 'body',
        'in': 'body',
        'schema': {
            'type': 'object',
            'properties': {
                'username': {'type': 'string'},
                'cloud_id': {'type': 'string'},
                'resource_type': {'type': 'string'},
                'request_id': {'type': 'integer'}
            },
            'required': ['username', 'cloud_id', 'resource_type', 'request_id']
        }
    }],
    'responses': {
        200: {'description': 'Succès'},
        400: {'description': 'Erreur de validation'},
        401: {'description': 'API key manquante ou invalide'},
        500: {'description': 'Erreur serveur'}
    }
})
def generate_terraform():
    key_check = check_api_key()
    if key_check: return key_check

    logger_req = logger.bind(request_id=str(uuid.uuid4())[:8])
    try:
        schema = TerraformRequestSchema()
        data = schema.load(request.json)
    except ValidationError as err:
        return jsonify({"error": "Données invalides", "details": err.messages}), 400

    username, cloud_id, resource_type, request_id = data.values()
    db_service = current_app.db_service
    jinja_service = JinjaService()
    gitlab_service = GitLabService(current_app.config.get('GITLAB_API_URL'))
    # --- Suivi d’état en DB (début)
    db_service.save_generation_status(request_id, username, cloud_id, resource_type, "STARTED", "Génération démarrée")
    try:
        resource_data = db_service.get_resource_data(cloud_id, resource_type, request_id)
        if not resource_data:
            db_service.save_generation_status(request_id, username, cloud_id, resource_type, "FAILED", "Ressource non trouvée")
            return jsonify({"error": "Ressource non trouvée"}), 404
        module_version = resource_data.get('module_version')
        if not module_version:
            db_service.save_generation_status(request_id, username, cloud_id, resource_type, "FAILED", "Module version manquante")
            return jsonify({"error": "Module version manquante"}), 400
        template = db_service.get_jinja_template(cloud_id, resource_type, module_version)
        if not template:
            db_service.save_generation_status(request_id, username, cloud_id, resource_type, "FAILED", "Template manquant")
            return jsonify({"error": "Template manquant"}), 404
        terraform_code = jinja_service.render_terraform_code(template, resource_data)
        validation = gitlab_service.validate_terraform_files(None, terraform_code)
        if not validation['is_valid']:
            db_service.save_generation_status(request_id, username, cloud_id, resource_type, "FAILED", str(validation['errors']))
            return jsonify({"error": "Validation échouée", "details": validation['errors']}), 400
        gitlab_token = db_service.get_user_gitlab_token(username)
        if not gitlab_token:
            db_service.save_generation_status(request_id, username, cloud_id, resource_type, "FAILED", "GitLab token manquant")
            return jsonify({"error": "GitLab token manquant"}), 404
        project_id = db_service.get_gitlab_project_id(cloud_id, resource_type, request_id)
        if not project_id:
            db_service.save_generation_status(request_id, username, cloud_id, resource_type, "FAILED", "Project ID manquant")
            return jsonify({"error": "Project ID manquant"}), 404
        resource_name = resource_data.get('name', f"resource-{request_id}")
        source_branch = f"feature/{cloud_id}-{resource_type}-{resource_name}"
        file_path = f"{cloud_id}/{resource_type}/{resource_name}.tf"
        terraform_files = {file_path: terraform_code}
        merge_request = gitlab_service.create_merge_request(
            token=gitlab_token,
            project_id=project_id,
            terraform_files=terraform_files,
            source_branch=source_branch,
            title=f"Ajout {cloud_id} {resource_type}: {resource_name}",
            description=f"Auto-Terraform - Req {request_id}"
        )
        db_service.save_generation_status(request_id, username, cloud_id, resource_type, "SUCCESS", "MR créée", merge_request['merge_request_url'])
        return jsonify({
            "success": True,
            "merge_request": merge_request
        })
    except Exception as e:
        db_service.save_generation_status(request_id, username, cloud_id, resource_type, "FAILED", str(e))
        return jsonify({"error": "Erreur génération", "details": str(e)}), 500

@terraform_bp.route('/status/<username>', methods=['GET'])
@swag_from({
    'tags': ['terraform'],
    'parameters': [{'name': 'username', 'in': 'path', 'type': 'string', 'required': True}],
    'responses': {200: {'description': 'Historique'}}
})
def get_status_history(username):
    key_check = check_api_key()
    if key_check: return key_check
    db_service = current_app.db_service
    try:
        status_rows = db_service.get_user_status_history(username)
        return jsonify(status_rows)
    except Exception as e:
        return jsonify({"error": str(e)}), 500
