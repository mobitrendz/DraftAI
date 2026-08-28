import structlog
from botocore.client import Config
from botocore.exceptions import ClientError

import boto3

from app.core.config import settings

logger = structlog.get_logger(__name__)


class StorageService:
    def __init__(self) -> None:
        self._client = None
        self._public_client = None

    def _build_client(self, endpoint_url: str):
        return boto3.client(
            "s3",
            endpoint_url=endpoint_url,
            aws_access_key_id=settings.S3_ACCESS_KEY,
            aws_secret_access_key=settings.S3_SECRET_KEY,
            config=Config(signature_version="s3v4"),
            region_name=settings.S3_REGION,
        )

    @property
    def client(self):
        if self._client is None:
            self._client = self._build_client(settings.S3_ENDPOINT_URL)
        return self._client

    @property
    def public_client(self):
        if self._public_client is None:
            endpoint = settings.S3_PUBLIC_ENDPOINT_URL or settings.S3_ENDPOINT_URL
            self._public_client = self._build_client(endpoint)
        return self._public_client

    def ensure_bucket(self) -> None:
        try:
            self.client.head_bucket(Bucket=settings.S3_BUCKET_NAME)
        except ClientError:
            self.client.create_bucket(Bucket=settings.S3_BUCKET_NAME)
            logger.info("Created storage bucket", bucket=settings.S3_BUCKET_NAME)

    def upload_bytes(self, *, key: str, data: bytes, content_type: str) -> str:
        self.ensure_bucket()
        self.client.put_object(
            Bucket=settings.S3_BUCKET_NAME,
            Key=key,
            Body=data,
            ContentType=content_type,
        )
        return key

    def get_object_bytes(self, *, key: str) -> tuple[bytes, str]:
        self.ensure_bucket()
        response = self.client.get_object(Bucket=settings.S3_BUCKET_NAME, Key=key)
        body = response["Body"].read()
        content_type = response.get("ContentType") or "application/octet-stream"
        return body, content_type

    def get_presigned_url(self, key: str) -> str | None:
        if not key:
            return None
        return self.public_client.generate_presigned_url(
            "get_object",
            Params={"Bucket": settings.S3_BUCKET_NAME, "Key": key},
            ExpiresIn=settings.S3_PRESIGNED_URL_EXPIRE_SECONDS,
        )

    def delete_object(self, *, key: str) -> None:
        if not key:
            return
        try:
            self.client.delete_object(Bucket=settings.S3_BUCKET_NAME, Key=key)
        except ClientError as exc:
            logger.warning("Storage delete failed", key=key, error=str(exc))


storage = StorageService()
