import oracledb
from typing import Dict, List
from loguru import logger

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
    def fetch_gitlab_token(self, username: str) -> str:
        query = "SELECT gitlab_token FROM users WHERE login = :username"
        with self.get_connection() as conn:
            return conn.cursor().execute(query, [username]).fetchone()[0]
    
    # Other methods from previous example...