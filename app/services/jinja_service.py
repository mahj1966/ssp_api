from jinja2 import Environment, BaseLoader
import structlog
from typing import Dict, Any

logger = structlog.get_logger(__name__)

class JinjaService:
    def __init__(self):
        self.env = Environment(
            loader=BaseLoader(),
            trim_blocks=True,
            lstrip_blocks=True,
            keep_trailing_newline=True
        )
        self.env.filters['to_terraform_string'] = self._to_terraform_string
        self.env.filters['to_terraform_list'] = self._to_terraform_list

    def _to_terraform_string(self, value):
        if value is None:
            return 'null'
        return f'"{value}"'

    def _to_terraform_list(self, value):
        if not value:
            return '[]'
        if isinstance(value, str) and value.startswith('[') and value.endswith(']'):
            items = value[1:-1].split(',')
            items = [item.strip() for item in items]
        elif isinstance(value, list):
            items = value
        else:
            items = [value]
        formatted_items = [f'"{item}"' for item in items if item]
        return f'[{", ".join(formatted_items)}]'

    def render_terraform_code(self, template_str: str, data: Dict[str, Any]) -> str:
        try:
            template = self.env.from_string(template_str)
            return template.render(**data)
        except Exception as e:
            logger.error("Erreur Jinja", error=str(e))
            raise
