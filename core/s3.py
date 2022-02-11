import boto3
from botocore.config import Config
from django.conf import settings


class S3:
    def __init__(self):
        self.client = boto3.client('s3',
                                   settings.AWS_S3_REGION_NAME,
                                   # endpoint_url='https://flamescloud.s3.us-east-2.amazonaws.com/',
                                   # wrong it's for custom host for custom url
                                   aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
                                   aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
                                   config=Config(signature_version=settings.AWS_S3_SIGNATURE_VERSION)
                                   )
        self.bucket = settings.AWS_STORAGE_BUCKET_NAME

    def get_presigned_url(self, key, time=3600):
        return self.client.generate_presigned_url(ClientMethod='put_object', ExpiresIn=time,
                                                  Params={'Bucket': self.bucket, 'Key': key})

    def get_presigned_post(self, key, time=3600):
        return self.client.generate_presigned_post(Bucket=self.bucket, Key=key, ExpiresIn=time)

    def get_file(self, key, time=3600):
        return self.client.generate_presigned_url(ClientMethod='get_object', ExpiresIn=time,
                                                  Params={'Bucket': self.bucket, 'Key': key})

    def delete_file(self, key):
        return self.client.delete_object(Bucket=settings.AWS_STORAGE_BUCKET_NAME, Key=key)
