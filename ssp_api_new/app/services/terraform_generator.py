from app.services.template_service import TemplateService
from loguru import logger

class TerraformGenerator:
    def __init__(self):
        self.template_service = TemplateService()
    
    @logger.catch
    def generate_config(self, template: str, data: Dict) -> Dict:
        try:
            return {
                'main.tf': self.template_service.render_template(template, data)
            }
        except Exception as e:
            logger.error(f"Generation Error: {str(e)}")
            raise