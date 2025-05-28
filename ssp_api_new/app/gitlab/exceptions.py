class GitLabIntegrationError(Exception):
    """Exception base pour les erreurs GitLab"""
    
class MergeRequestError(GitLabIntegrationError):
    """Erreur lors de la création de la merge request"""