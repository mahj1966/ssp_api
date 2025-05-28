from marshmallow import Schema, fields, validate

class GenerateRequestSchema(Schema):
    user_name = fields.Str(required=True)
    cloud_id = fields.Str(
        required=True,
        validate=validate.OneOf(['aws', 'gcp', 'alicloud'])
    )
    resource_type = fields.Str(required=True)
    request_id = fields.Int(required=True)