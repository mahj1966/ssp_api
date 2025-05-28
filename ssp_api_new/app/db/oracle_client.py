import oracledb
from typing import Dict, List, Any
from app.utils.logging import logger

class OracleDBClient:
    def __init__(self, user: str, password: str, dsn: str):
        self.pool = oracledb.create_pool(
            user=user,
            password=password,
            dsn=dsn,
            min=2,
            max=5,
            increment=1
        )
    
    def get_connection(self):
        return self.pool.acquire()

    @logger.catch
    def fetch_template(self, cloud_id: str, resource_type: str, module_version: str) -> str:
        query = """
            SELECT jinja_template 
            FROM tf_template 
            WHERE cloud_id = :cloud_id 
            AND resource_type = :resource_type 
            AND module_version = :module_version
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query, [cloud_id, resource_type, module_version])
            return cursor.fetchone()[0]

    @logger.catch
    def fetch_request_data(self, cloud_id: str, resource_type: str, request_id: int) -> Dict:
        # Validation des entrées
        valid_clouds = {'aws', 'alicloud', 'gcp'}
        if cloud_id not in valid_clouds:
            raise ValueError("Cloud provider non valide")
        
        # Construction dynamique des noms de vue
        main_view = f"v_{cloud_id}_{resource_type}_requests"
        sg_view = f"v_{cloud_id}_{resource_type}_requests_sg_ingress"
        
        # Récupération des données
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            # Données principales
            cursor.execute(f"""
                SELECT * 
                FROM {main_view} 
                WHERE id = :request_id
            """, [request_id])
            main_data = cursor.fetchone()
            
            # Règles de sécurité
            cursor.execute(f"""
                SELECT * 
                FROM {sg_view} 
                WHERE request_id = :request_id
            """, [request_id])
            sg_rules = cursor.fetchall()
            
        return {
            "main": dict(zip([d[0] for d in cursor.description], main_data)),
            "sg_rules": [dict(zip([d[0] for d in cursor.description], rule)) for rule in sg_rules]
        }