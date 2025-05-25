"""Service pour la génération de code Terraform à partir de templates Jinja."""
from jinja2 import Template, Environment, BaseLoader
import structlog
from typing import Dict, Any

logger = structlog.get_logger(__name__)

class JinjaService:
    """Service pour le traitement des templates Jinja."""
    
    def __init__(self):
        """Initialise l'environnement Jinja avec des configurations personnalisées."""
        self.env = Environment(
            loader=BaseLoader(),
            trim_blocks=True,
            lstrip_blocks=True,
            keep_trailing_newline=True
        )
        
        # Ajout de filtres personnalisés pour Jinja
        self.env.filters['to_terraform_string'] = self._to_terraform_string
        self.env.filters['to_terraform_list'] = self._to_terraform_list
        
    def _to_terraform_string(self, value):
        """Convertit une valeur en chaîne Terraform valide."""
        if value is None:
            return 'null'
        return f'"{value}"'
    
    def _to_terraform_list(self, value):
        """Convertit une liste en liste Terraform valide."""
        if not value:
            return '[]'
        if isinstance(value, str) and value.startswith('[') and value.endswith(']'):
            # Déjà au format liste
            items = value[1:-1].split(',')
            items = [item.strip() for item in items]
        elif isinstance(value, list):
            items = value
        else:
            items = [value]
        
        formatted_items = [f'"{item}"' for item in items if item]
        return f'[{", ".join(formatted_items)}]'
    
    def render_terraform_code(self, template_str: str, data: Dict[str, Any]) -> str:
        """
        Génère le code Terraform en appliquant les données au template.
        
        Args:
            template_str: Chaîne de caractères contenant le template Jinja
            data: Dictionnaire de données à injecter dans le template
            
        Returns:
            Code Terraform généré
        """
        try:
            template = self.env.from_string(template_str)
            rendered_code = template.render(**data)
            logger.info("Code Terraform généré avec succès")
            return rendered_code
        except Exception as e:
            logger.error("Erreur lors de la génération du code Terraform", 
                        error=str(e), 
                        exc_info=True)
            raise ValueError(f"Erreur lors de la génération du code Terraform: {str(e)}")
