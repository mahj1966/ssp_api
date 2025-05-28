from jinja2 import Environment, StrictUndefined
from loguru import logger

class TemplateService:
    def __init__(self):
        self.env = Environment(
            loader=MemoryLoader(),
            undefined=StrictUndefined,
            trim_blocks=True,
            lstrip_blocks=True
        )
    
    @logger.catch
    def render_template(self, template_content: str, context: Dict) -> str:
        try:
            template = self.env.from_string(template_content)
            return template.render(context)
        except Exception as e:
            logger.error(f"Template Error: {str(e)}")
            raise