# external/storage.py
from minio import Minio


def get_minio_client():
    config = get_config()["resource"]
    return Minio(
        config["minio_endpoint"],
        access_key=config["minio_access_key"],
        secret_key=config["minio_secret_key"],
        secure=False  # 根据需要设为 True
    )