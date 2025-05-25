"""Service pour la gestion des connexions à la base de données Oracle."""
import oracledb
from typing import Dict, List, Any, Optional, Tuple
import structlog

logger = structlog.get_logger(__name__)

class OracleDBService:
    """Classe de service pour les opérations de base de données Oracle."""

    def __init__(self, config):
        """Initialise le service avec la configuration fournie."""
        self.config = config
        self.pool = None
        self._initialize_pool()

    def _initialize_pool(self):
        """Initialise le pool de connexions Oracle."""
        try:
            self.pool = oracledb.create_pool(
                user=self.config.ORACLE_USER,
                password=self.config.ORACLE_PASSWORD,
                dsn=self.config.ORACLE_DSN,
                min=self.config.ORACLE_POOL_MIN,
                max=self.config.ORACLE_POOL_MAX,
                increment=1,
                encoding="UTF-8"
            )
            logger.info("Pool de connexions Oracle initialisé avec succès")
        except Exception as e:
            logger.error("Erreur lors de l'initialisation du pool Oracle", error=str(e), exc_info=True)
            raise

    def get_resource_data(self, cloud_id: str, resource_type: str, request_id: int) -> Dict[str, Any]:
        """
        Récupère les données d'une ressource spécifique.
        
        Args:
            cloud_id: Identifiant du cloud (aws, gcp, etc.)
            resource_type: Type de ressource (rds, ec2, etc.)
            request_id: ID de la demande
            
        Returns:
            Dictionnaire contenant les données de la ressource
        """
        view_name = f"v_{cloud_id}_{resource_type}_requests"
        query = f"SELECT * FROM {view_name} WHERE id = :request_id"
        
        try:
            with self.pool.acquire() as connection:
                with connection.cursor() as cursor:
                    cursor.execute(query, request_id=request_id)
                    columns = [col[0].lower() for col in cursor.description]
                    row = cursor.fetchone()
                    
                    if not row:
                        logger.warning("Aucune ressource trouvée", 
                                      cloud_id=cloud_id, 
                                      resource_type=resource_type, 
                                      request_id=request_id)
                        return {}
                    
                    resource_data = dict(zip(columns, row))
                    
                    # Récupération des règles de sécurité associées
                    sg_data = self._get_sg_rules(connection, cloud_id, resource_type, request_id)
                    if sg_data:
                        resource_data['sg_rules'] = sg_data
                    
                    logger.info("Données de ressource récupérées", 
                               cloud_id=cloud_id, 
                               resource_type=resource_type, 
                               request_id=request_id)
                    return resource_data
                    
        except Exception as e:
            logger.error("Erreur lors de la récupération des données de ressource", 
                        cloud_id=cloud_id, 
                        resource_type=resource_type, 
                        request_id=request_id,
                        error=str(e), 
                        exc_info=True)
            raise

    def _get_sg_rules(self, connection, cloud_id: str, resource_type: str, request_id: int) -> List[Dict[str, Any]]:
        """Récupère les règles de groupe de sécurité associées à une ressource."""
        sg_view_name = f"v_{cloud_id}_{resource_type}_requests_sg_ingress"
        try:
            with connection.cursor() as cursor:
                cursor.execute(
                    f"SELECT * FROM {sg_view_name} WHERE request_id = :request_id",
                    request_id=request_id
                )
                columns = [col[0].lower() for col in cursor.description]
                sg_rules = []
                for row in cursor:
                    sg_rules.append(dict(zip(columns, row)))
                return sg_rules
        except Exception as e:
            logger.warning(f"Pas de règles SG trouvées ou erreur: {str(e)}")
            return []

    def get_jinja_template(self, cloud_id: str, resource_type: str, module_version: str) -> Optional[str]:
        """
        Récupère le template Jinja pour une ressource spécifique.
        
        Args:
            cloud_id: Identifiant du cloud
            resource_type: Type de ressource
            module_version: Version du module Terraform
            
        Returns:
            Le template Jinja ou None si non trouvé
        """
        query = """
        SELECT jinja_template 
        FROM tf_template 
        WHERE cloud_id = :cloud_id 
        AND resource_type = :resource_type 
        AND module_version = :module_version
        """
        
        try:
            with self.pool.acquire() as connection:
                with connection.cursor() as cursor:
                    cursor.execute(
                        query, 
                        cloud_id=cloud_id, 
                        resource_type=resource_type, 
                        module_version=module_version
                    )
                    result = cursor.fetchone()
                    
                    if not result:
                        logger.warning("Template Jinja non trouvé", 
                                      cloud_id=cloud_id, 
                                      resource_type=resource_type, 
                                      module_version=module_version)
                        return None
                    
                    logger.info("Template Jinja récupéré", 
                               cloud_id=cloud_id, 
                               resource_type=resource_type, 
                               module_version=module_version)
                    return result[0]
                    
        except Exception as e:
            logger.error("Erreur lors de la récupération du template Jinja", 
                        cloud_id=cloud_id, 
                        resource_type=resource_type, 
                        module_version=module_version,
                        error=str(e), 
                        exc_info=True)
            raise

    def get_user_gitlab_token(self, username: str) -> Optional[str]:
        """
        Récupère le jeton GitLab d'un utilisateur.
        
        Args:
            username: Nom d'utilisateur
            
        Returns:
            Le jeton GitLab ou None si non trouvé
        """
        query = "SELECT gitlab_token FROM users WHERE login = :username"
        
        try:
            with self.pool.acquire() as connection:
                with connection.cursor() as cursor:
                    cursor.execute(query, username=username)
                    result = cursor.fetchone()
                    
                    if not result:
                        logger.warning("Jeton GitLab non trouvé", username=username)
                        return None
                    
                    logger.info("Jeton GitLab récupéré", username=username)
                    return result[0]
                    
        except Exception as e:
            logger.error("Erreur lors de la récupération du jeton GitLab", 
                        username=username,
                        error=str(e), 
                        exc_info=True)
            raise

    def get_gitlab_project_id(self, cloud_id: str, resource_type: str, request_id: int) -> Optional[int]:
        """
        Récupère l'ID du projet GitLab pour une ressource spécifique.
        
        Args:
            cloud_id: Identifiant du cloud
            resource_type: Type de ressource
            request_id: ID de la demande
            
        Returns:
            L'ID du projet GitLab ou None si non trouvé
        """
        view_name = f"v_{cloud_id}_{resource_type}_requests"
        query = f"SELECT gitlab_project_id FROM {view_name} WHERE id = :request_id"
        
        try:
            with self.pool.acquire() as connection:
                with connection.cursor() as cursor:
                    cursor.execute(query, request_id=request_id)
                    result = cursor.fetchone()
                    
                    if not result:
                        logger.warning("ID de projet GitLab non trouvé", 
                                     cloud_id=cloud_id, 
                                     resource_type=resource_type, 
                                     request_id=request_id)
                        return None
                    
                    logger.info("ID de projet GitLab récupéré", 
                               cloud_id=cloud_id, 
                               resource_type=resource_type, 
                               request_id=request_id,
                               project_id=result[0])
                    return result[0]
                    
        except Exception as e:
            logger.error("Erreur lors de la récupération de l'ID de projet GitLab", 
                        cloud_id=cloud_id, 
                        resource_type=resource_type, 
                        request_id=request_id,
                        error=str(e), 
                        exc_info=True)
            raise
