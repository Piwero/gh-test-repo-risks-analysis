import uuid
from pathlib import Path

from fastapi import UploadFile

from app.config import get_settings

CHUNK_SIZE = 64 * 1024


class UploadTooLargeError(Exception):
    pass


def upload_root() -> Path:
    root = get_settings().upload_dir.resolve()
    root.mkdir(parents=True, exist_ok=True)
    return root


def save_upload(file: UploadFile) -> tuple[str, int]:
    """Persist an upload under a server-generated name. Returns (stored_name, size)."""
    max_bytes = get_settings().max_upload_bytes
    stored_name = uuid.uuid4().hex
    destination = upload_root() / stored_name

    size = 0
    try:
        with destination.open("wb") as out:
            while chunk := file.file.read(CHUNK_SIZE):
                size += len(chunk)
                if size > max_bytes:
                    raise UploadTooLargeError
                out.write(chunk)
    except UploadTooLargeError:
        destination.unlink(missing_ok=True)
        raise
    return stored_name, size


def stored_path(stored_name: str) -> Path:
    return upload_root() / stored_name


def delete_stored(stored_name: str) -> None:
    stored_path(stored_name).unlink(missing_ok=True)
