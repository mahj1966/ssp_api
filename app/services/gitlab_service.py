"""Service pour l'intégration avec GitLab."""
import gitlab
import base64
import structlog
from typing import Dict, Optional

logger = structlog.get_logger(__name__)

class GitLabService:
    """Service pour les opérations GitLab."""
    
    def __init__(self, gitlab_api_url: str):
        """
        Initialise le service GitLab.
        
        Args:
            gitlab_api_url: URL de l'API GitLab
        """
        self.gitlab_api_url = gitlab_api_url
        
    def create_merge_request(self, 
                            token: str, 
                            project_id: int, 
                            terraform_files: Dict[str, str],
                            source_branch: str,
                            target_branch: str = "main",
                            title: str = "Ajout de ressources Terraform",
                            description: str = "Ressources Terraform générées automatiquement") -> Dict:
        """
        Crée une merge request dans GitLab avec les fichiers Terraform générés.
        
        Args:
            token: Jeton d'accès GitLab
            project_id: ID du projet GitLab
            terraform_files: Dictionnaire avec nom de fichier -> contenu
            source_branch: Nom de la branche source
            target_branch: Nom de la branche cible
            title: Titre de la merge request
            description: Description de la merge request
            
        Returns:
            Informations sur la merge request créée
        """
        try:
            # Initialiser le client GitLab
            gl = gitlab.Gitlab(self.gitlab_api_url, private_token=token)
            
            # Récupérer le projet
            project = gl.projects.get(project_id)
            logger.info("Projet GitLab récupéré", project_id=project_id)
            
            # Vérifier si la branche existe déjà et la supprimer si nécessaire
            try:
                branch = project.branches.get(source_branch)
                branch.delete()
                logger.info("Branche existante supprimée", branch=source_branch)
            except gitlab.exceptions.GitlabGetError:
                pass  # La branche n'existe pas encore
            
            # Créer une nouvelle branche
            project.branches.create({'branch': source_branch, 'ref': target_branch})
            logger.info("Nouvelle branche créée", branch=source_branch)
            
            # Ajouter les fichiers Terraform
            for file_path, content in terraform_files.items():
                project.files.create({
                    'file_path': file_path,
                    'branch': source_branch,
                    'content': content,
                    'commit_message': f'Ajout du fichier {file_path}'
                })
                logger.info("Fichier ajouté", file_path=file_path, branch=source_branch)
            
            # Créer la merge request
            merge_request = project.mergerequests.create({
                'source_branch': source_branch,
                'target_branch': target_branch,
                'title': title,
                'description': description
            })
            logger.info("Merge request créée", merge_request_id=merge_request.id)
            
            return {
                'merge_request_id': merge_request.id,
                'merge_request_url': merge_request.web_url,
                'source_branch': source_branch,
                'target_branch': target_branch
            }
            
        except Exception as e:
            logger.error("Erreur lors de la création de la merge request", 
                        error=str(e), 
                        project_id=project_id, 
                        source_branch=source_branch,
                        exc_info=True)
            raise
    
    def validate_terraform_files(self, token: str, terraform_content: str) -> Dict:
        """
        Valide les fichiers Terraform (syntaxe, format).
        Peut être étendu pour utiliser des services comme Terraform Cloud ou des validations personnalisées.
        
        Args:
            token: Jeton d'accès GitLab (non utilisé pour la validation simple)
            terraform_content: Contenu du fichier Terraform à valider
            
        Returns:
            Résultat de la validation
        """
        # Validation basique
        is_valid = True
        errors = []
        
        # Vérifications simples
        if '{' not in terraform_content or '}' not in terraform_content:
            is_valid = False
            errors.append("Le fichier ne semble pas contenir de blocs de configuration Terraform valides")
        
        # Autres vérifications possibles (détecter les sections requises, etc.)
        required_sections = ['resource', 'module', 'provider', 'variable', 'output']
        if not any(section in terraform_content for section in required_sections):
            is_valid = False
            errors.append("Le fichier ne contient aucune section Terraform requise (resource, module, etc.)")
        
        # Note: Pour une validation complète, il faudrait utiliser `terraform validate`,
        # ce qui nécessiterait d'exécuter Terraform dans un environnement contrôlé.
        
        logger.info("Validation des fichiers Terraform", is_valid=is_valid)
        
        return {
            'is_valid': is_valid,
            'errors': errors
        }
