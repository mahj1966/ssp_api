from flask import Blueprint, request, jsonify, current_app
from app.validators.schemas import GenerateRequestSchema
from app.utils.security import validate_jwt
from loguru import logger

api = Blueprint('api', __name__)

@api.route('/generate', methods=['POST'])
@validate_jwt
def generate_terraform_config():
    schema = GenerateRequestSchema()
    errors = schema.validate(request.json)
    if errors:
        return jsonify({"errors": errors}), 400
    
    try:
        data = schema.load(request.json)
        
        # Récupération des données
        oracle_client = current_app.oracle_client
        gitlab_token = oracle_client.fetch_gitlab_token(data['user_name'])
        
        # Génération Terraform
        generator = current_app.terraform_generator
        config_files = generator.generate_config(...)
        
        # Création MR GitLab
        gitlab_data = {
            'branch_name': f"terraform-{data['request_id']}",
            'files': config_files,
            'base_branch': 'main',
            'title': f"Deployment {data['resource_type']}",
            'description': "Auto-generated Terraform configuration"
        }
        
        mr_url = current_app.gitlab_client.create_merge_request(
            project_id=...,
            token=gitlab_token,
            data=gitlab_data
        )
        
        return jsonify({"mr_url": mr_url}), 200
        
    except Exception as e:
        logger.error(f"API Error: {str(e)}")
        return jsonify({"error": str(e)}), 500