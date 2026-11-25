import aioboto3
from app.config import settings
session = aioboto3.Session(aws_access_key_id=settings.aws_access_key_id,
    aws_secret_access_key=settings.aws_secret_access_key, region_name=settings.aws_region)
def kwargs():
    return {"endpoint_url": settings.s3_endpoint_url} if settings.s3_endpoint_url else {}
