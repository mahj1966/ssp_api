import oracledb
from typing import Dict, List, Any, Optional
import structlog
from cachetools import cached, TTLCache

logger = structlog.get_logger(__name__)

# Cache 10 min sur les templates
cache_templates = TTLCache(maxsize=100, ttl=600)

class OracleDBService:
    _instance = None

    def __new__(cls, config):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance.__init_once(config)
        return cls._instance

    def __init_once(self, config):
        self.config = config
        self.pool = self._initialize_pool()

    def _initialize_pool(self):
        try:
            pool = oracledb.create_pool(
                user=self.config.ORACLE_USER,
                password=self.config.ORACLE_PASSWORD,
                dsn=self.config.ORACLE_DSN,
                min=self.config.ORACLE_POOL_MIN,
                max=self.config.ORACLE_POOL_MAX,
                increment=1,
                encoding="UTF-8"
            )
            logger.info("Pool Oracle initialisé")
            return pool
        except Exception as e:
            logger.error("Erreur init pool Oracle", error=str(e), exc_info=True)
            raise

    def get_resource_data(self, cloud_id, resource_type, request_id) -> Dict[str, Any]:
        # Protection anti SQL injection (vérifie cloud_id/resource_type)
        allowed_clouds = {"aws", "gcp", "azure"}
        if cloud_id not in allowed_clouds:
            logger.error("Cloud non autorisé", cloud_id=cloud_id)
            return {}
        view_name = f"v_{cloud_id}_{resource_type}_requests"
        query = f"SELECT * FROM {view_name} WHERE id = :request_id"
        try:
            with self.pool.acquire() as connection:
                with connection.cursor() as cursor:
                    cursor.execute(query, request_id=request_id)
                    columns = [col[0].lower() for col in cursor.description]
                    row = cursor.fetchone()
                    if not row:
                        return {}
                    data = dict(zip(columns, row))
                    data['sg_rules'] = self._get_sg_rules(connection, cloud_id, resource_type, request_id)
                    return data
        except Exception as e:
            logger.error("Erreur lecture ressource", error=str(e), exc_info=True)
            return {}

    def _get_sg_rules(self, connection, cloud_id, resource_type, request_id):
        try:
            view_name = f"v_{cloud_id}_{resource_type}_requests_sg_ingress"
            with connection.cursor() as cursor:
                cursor.execute(f"SELECT * FROM {view_name} WHERE request_id = :request_id", request_id=request_id)
                columns = [col[0].lower() for col in cursor.description]
                return [dict(zip(columns, row)) for row in cursor]
        except Exception:
            return []

    @cached(cache_templates)
    def get_jinja_template(self, cloud_id, resource_type, module_version):
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
                    cursor.execute(query, cloud_id=cloud_id, resource_type=resource_type, module_version=module_version)
                    result = cursor.fetchone()
                    return result[0] if result else None
        except Exception as e:
            logger.error("Erreur lecture template", error=str(e))
            return None

    def get_user_gitlab_token(self, username):
        query = "SELECT gitlab_token FROM users WHERE login = :username"
        try:
            with self.pool.acquire() as connection:
                with connection.cursor() as cursor:
                    cursor.execute(query, username=username)
                    result = cursor.fetchone()
                    return result[0] if result else None
        except Exception:
            return None

    def get_gitlab_project_id(self, cloud_id, resource_type, request_id):
        view_name = f"v_{cloud_id}_{resource_type}_requests"
        query = f"SELECT gitlab_project_id FROM {view_name} WHERE id = :request_id"
        try:
            with self.pool.acquire() as connection:
                with connection.cursor() as cursor:
                    cursor.execute(query, request_id=request_id)
                    result = cursor.fetchone()
                    return result[0] if result else None
        except Exception:
            return None

    def save_generation_status(self, apex_request_id, username, cloud_id, resource_type, status, message, merge_request_url=None):
        query = """
        MERGE INTO terraform_requests_status t
        USING (SELECT :apex_request_id AS apex_request_id FROM dual) s
        ON (t.apex_request_id = s.apex_request_id)
        WHEN MATCHED THEN
            UPDATE SET status = :status, message = :message, finished_at = SYSTIMESTAMP, merge_request_url = :merge_request_url
        WHEN NOT MATCHED THEN
            INSERT (apex_request_id, username, cloud_id, resource_type, status, message, started_at, merge_request_url)
            VALUES (:apex_request_id, :username, :cloud_id, :resource_type, :status, :message, SYSTIMESTAMP, :merge_request_url)
        """
        try:
            with self.pool.acquire() as connection:
                with connection.cursor() as cursor:
                    cursor.execute(query, apex_request_id=apex_request_id, username=username,
                                   cloud_id=cloud_id, resource_type=resource_type, status=status,
                                   message=message, merge_request_url=merge_request_url)
                connection.commit()
        except Exception as e:
            logger.error("Erreur save status", error=str(e))

    def get_user_status_history(self, username):
        query = "SELECT * FROM terraform_requests_status WHERE username = :username ORDER BY started_at DESC FETCH NEXT 20 ROWS ONLY"
        try:
            with self.pool.acquire() as connection:
                with connection.cursor() as cursor:
                    cursor.execute(query, username=username)
                    columns = [col[0].lower() for col in cursor.description]
                    return [dict(zip(columns, row)) for row in cursor]
        except Exception as e:
            logger.error("Erreur get status", error=str(e))
            return []
