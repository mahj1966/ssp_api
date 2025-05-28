import pytest
from app.services.jinja_service import JinjaService

def test_render_simple_template():
    service = JinjaService()
    template = 'resource "aws_s3_bucket" "{{ name }}" {}'
    data = {'name': 'my-bucket'}
    rendered = service.render_terraform_code(template, data)
    assert 'my-bucket' in rendered
