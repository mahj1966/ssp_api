import jwt
from functools import wraps
from flask import request, jsonify
from loguru import logger

def validate_jwt(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        token = request.headers.get('Authorization')
        if not token:
            return jsonify({"error": "Token missing"}), 401
            
        try:
            decoded = jwt.decode(
                token.split()[1],
                current_app.config['JWT_SECRET'],
                algorithms=["HS256"]
            )
            request.user = decoded['user']
        except Exception as e:
            logger.error(f"JWT Error: {str(e)}")
            return jsonify({"error": "Invalid token"}), 401
            
        return f(*args, **kwargs)
    return decorated