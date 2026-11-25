from datetime import datetime
from pydantic import BaseModel, ConfigDict
class IngestResult(BaseModel):
    created: int
    updated: int
    deleted: int
    unchanged: int
    reprocessed_pages: list[str]
class FileOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    s3_key: str
    etag: str | None
    version_id: str | None
    last_modified: datetime | None
    size: int
    operation: str
    is_present: bool
    content_hash: str | None
class PageOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    page_path: str
    title: str
    content: str
    extracted_at: datetime
    content_hash: str
