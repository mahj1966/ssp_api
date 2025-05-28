import gitlab
import structlog
from typing import Dict

logger = structlog.get_logger(__name__)

class GitLabService:
    def __init__(self, gitlab_api_url: str):
        self.gitlab_api_url = gitlab_api_url

    def create_merge_request(self, 
                            token: str, 
                            project_id: int, 
                            terraform_files: Dict[str, str],
                            source_branch: str,
                            target_branch: str = "main",
                            title: str = "Ajout de ressources Terraform",
                            description: str = "Ressources Terraform générées automatiquement") -> Dict:
        try:
            gl = gitlab.Gitlab(self.gitlab_api_url, private_token=token)
            project = gl.projects.get(project_id)
            try:
                branch = project.branches.get(source_branch)
                branch.delete()
            except gitlab.exceptions.GitlabGetError:
                pass
            project.branches.create({'branch': source_branch, 'ref': target_branch})
            for file_path, content in terraform_files.items():
                project.files.create({
                    'file_path': file_path,
                    'branch': source_branch,
                    'content': content,
                    'commit_message': f'Ajout du fichier {file_path}'
                })
            merge_request = project.mergerequests.create({
                'source_branch': source_branch,
                'target_branch': target_branch,
                'title': title,
                'description': description
            })
            return {
                'merge_request_id': merge_request.id,
                'merge_request_url': merge_request.web_url,
                'source_branch': source_branch,
                'target_branch': target_branch
            }
        except Exception as e:
            logger.error("Erreur MR GitLab", error=str(e), project_id=project_id)
            raise

    def validate_terraform_files(self, token: str, terraform_content: str) -> Dict:
        is_valid = True
        errors = []
        if '{' not in terraform_content or '}' not in terraform_content:
            is_valid = False
            errors.append("Le fichier ne semble pas contenir de blocs de configuration Terraform valides")
        required_sections = ['resource', 'module', 'provider', 'variable', 'output']
        if not any(section in terraform_content for section in required_sections):
            is_valid = False
            errors.append("Le fichier ne contient aucune section Terraform requise (resource, module, etc.)")
        return {
            'is_valid': is_valid,
            'errors': errors
        }
