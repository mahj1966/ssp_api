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
                user=self.config["ORACLE_USER"],
                password=self.config["ORACLE_PASSWORD"],
                dsn=self.config["ORACLE_DSN"],
                min=self.config.get("ORACLE_POOL_MIN", 2),
                max=self.config.get("ORACLE_POOL_MAX", 10),
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


    def extract_substring(text, keyword):
        last_index = text.rfind(keyword)  # Find the last occurrence of the keyword
        if last_index != -1:
            return text[last_index + len(keyword):]  # Extract the substring after the keyword
        else:
            return ""

    def get_last_element(text, separator):
        elements = text.split(separator)
        if elements:  # Check if the list is not empty
            return elements[-1]  # Return the last element
        else:
            return text

    def extract_key_value_pairs(obj, path=""):
        items = []
        if isinstance(obj, dict):
            for key, value in obj.items():
                current_path = f"{path}.{key}" if path else key  # Build the path
                items.append((current_path, value))  # Append the key-value pair with path
                items.extend(extract_key_value_pairs(value, current_path))  # Recurse
        elif isinstance(obj, list):
            for i, item in enumerate(obj):
                current_path = f"{path}[{i}]"  # Add index for list items
                items.extend(extract_key_value_pairs(item, current_path))
        return items

    def get_value_by_key_path(data, key_path):
        keys = key_path.split(".")
        current = data
        try:
            for key in keys:
                if "[" in key and "]" in key:  # Handle list indices
                    key_name, index = key.split("[")
                    index = int(index[:-1])  # Remove the closing bracket and convert to integer
                    current = current[key_name][index]
                else:
                    current = current[key]
            return current
        except (KeyError, TypeError, IndexError):
            return None

    def upload_to_cloud_request( data: dict, add_sg,add_pg,add_og ):
        cursor = conn.cursor()
        ci_data = json.dumps(data)
        assert type(ci_data) == str
        try:
            query= """
                INSERT INTO port_request (ci_data, initiatedby, run_id, action_identifier, action_blueprint, trigger_at, resourcetype, engine, created_on)
                VALUES (:ci_data, :initiatedby, :run_id, :action_identifier, :action_blueprint, :trigger_at, :resourcetype, :engine, SYSDATE)
                """
            cursor.execute(query, {
                    "ci_data": str(ci_data),
                    "initiatedby": get_value_by_key_path(data, "payload.trigger.by.user.email"),
                    "run_id": get_value_by_key_path(data, "payload.run.id"),
                    "action_identifier": get_value_by_key_path(data, "payload.action.identifier"),
                    "action_blueprint": get_value_by_key_path(data, "payload.action.blueprint"),
                    "trigger_at": get_value_by_key_path(data, "payload.trigger.at"),
                    "resourcetype": "rds",
                    "engine": get_last_element(get_value_by_key_path(data, "payload.action.identifier"), '-') },)
            conn.commit()
            query = """
                    INSERT INTO aws_rds_request (incident_id, maximum_storage_size, region, account, module,
                                                git_project_id, cloud, short_name, module_version, identifier,
                                                environment, description, maison, service_mapping, project_id,
                                                application, powerpolicy, confidential_data, engine, engine_version,
                                                instance_class, initial_storage_size)
                    SELECT run_id  AS incident_id, (initial_storage_size * 3) AS maximum_storage_size,
                    'eu-central-1 (Frankfurt)' AS region, aws_account AS account, 'global' AS module,
                    '4375' AS git_project_id, 'AWS' AS cloud, identifier AS short_name,
                    '2.3.0' AS module_version,  identifier||decode(lower(environment),
                    'prd','','-'||lower(environment)) identifier, upper(environment) environment, description,
                    'xxxx' maison,'123456' service_mapping,'123456' project_id, 'APP0001' application,
                    powerpolicy,  lower(confidential_data) confidential_data, engine, engine_version,
                    instance_class,initial_storage_size
                    FROM port_request s, JSON_TABLE (s.ci_data, '$' COLUMNS (
                            identifier VARCHAR2(255) PATH '$.instance_name',
                            description VARCHAR2(255) PATH '$.description',
                            environment VARCHAR2(255) PATH '$.environment',
                            powerpolicy VARCHAR2(255) PATH '$.power_policy',
                            confidential_data VARCHAR2(255) PATH '$.confidential_data',
                            engine_version VARCHAR2(255) PATH '$.version',
                            instance_class VARCHAR2(255) PATH '$.instance_class',
                            initial_storage_size VARCHAR2(255) PATH '$.initial_storage_size' ,
                            aws_account VARCHAR2(255) PATH '$.aws_account.identifier'
                        )
                    ) json WHERE run_id = :run_id
                    """
            cursor.execute(query , {"run_id": run_id,},)
            conn.commit()
            logger.info("insert into aws_rds_request")
            request_id = fetch_data(conn, "SELECT * FROM aws_rds_request WHERE incident_id = :id", [run_id])

            query = """
            SELECT s.ci_data,allowed_cidr_blocks,allowed_security_group,parameters
            FROM port_request s,
            JSON_TABLE (s.ci_data, '$' COLUMNS (
            allowed_cidr_blocks  VARCHAR2(4000) FORMAT JSON PATH '$.allowed_cidr_blocks',
            allowed_security_group  VARCHAR2(4000)  FORMAT JSON PATH '$.allowed_security_group',
            parameters  VARCHAR2(4000) FORMAT JSON PATH '$.parameters') ) json
            WHERE s.run_id = :run_id
            """
            advanced_data = fetch_data(conn, query, [run_id], )

            if advanced_data["allowed_cidr_blocks"] and add_sg = true :
                query="""
                INSERT INTO aws_rds_request_sg (ID_REQUEST, SECURITY_GROUP_SOURCE,SECURITY_GROUP_TYPE) values (:id,:sgs,:sgt)
                """
                cursor.execute(query,{"id": request_id["id"], "sgs": str(json.loads(advanced_data["allowed_cidr_blocks"])[0]), "sgt": "CIDR_GROUP"},)
                conn.commit()

            if advanced_data["allowed_security_group"] and add_sg = true:
                query="""
                INSERT INTO aws_rds_request_sg (ID_REQUEST,  SECURITY_GROUP_SOURCE,SECURITY_GROUP_TYPE) values (:id,:sgs,:sgt)
                """
                    cursor.execute(query,{"id": request_id["id"], "sgs": str(json.loads(advanced_data["allowed_security_group"])[0]), "sgt": "APP_GROUP"},)
                    conn.commit()

            if advanced_data["parameters"] and add_pg = true:
                    for x, y in json.loads(advanced_data["parameters"]).items():
                        query="""
                        INSERT INTO AWS_RDS_REQUEST_PARAMETERS (ID_REQUEST,PARAMETER_NAME,PARAMETER_VALUE) values (:id,:name,:value)
                        """
                        cursor.execute(query,{"id": request_id["id"], "name": x, "value": y},)
                        conn.commit()

            logger.info("Cloud request uploaded successfully.")

        except oracledb.DatabaseError as e:
            logger.error(f"Database error during Upload Port Request: {e}")


    def calculate_combined_data(message, add_sg, add_pg, add_og) -> dict:
        payload_timestamp = ""

        upload_to_cloud_request(message,add_sg, add_pg, add_og )

        request_data = fetch_data(conn, "SELECT * FROM v_aws_rds_request WHERE incident_id = :id", [message.metadata.source_system_event_id])
        cidr_data = fetchall_data(
            conn,
                "SELECT SECURITY_GROUP_SOURCE allowed_cidr_blocks FROM AWS_RDS_REQUEST_SG WHERE id_request = :id AND security_group_type = 'CIDR_GROUP'",
                [request_data["id"]],
            )
        app_group_data = fetchall_data(
                conn,
                "SELECT SECURITY_GROUP_SOURCE as allowed_security_group_ids FROM AWS_RDS_REQUEST_SG WHERE id_request = :id AND security_group_type = 'APP_GROUP'",
                [request_data["id"]],
            )
        parameters_data = fetchall_data(
                conn, "SELECT PARAMETER_NAME name, PARAMETER_VALUE value FROM AWS_RDS_REQUEST_parameters WHERE id_request = :id", [request_data["id"]]
            )

        combined_data = {
                **request_data,
                "allowed_cidr_blocks": [item["allowed_cidr_blocks"] for item in cidr_data],
                "allowed_security_group_ids": [item["allowed_security_group_ids"] for item in app_group_data],
                "parameters": parameters_data,
            }
        return combined_data
