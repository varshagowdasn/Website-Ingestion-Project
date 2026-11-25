from datetime import datetime, timezone
from sqlalchemy import String, DateTime, Integer, Text, ForeignKey, Boolean, UniqueConstraint
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
def now(): return datetime.now(timezone.utc)
class Base(DeclarativeBase): pass
class IngestedFile(Base):
    __tablename__ = "ingested_files"
    id: Mapped[int] = mapped_column(primary_key=True)
    s3_key: Mapped[str] = mapped_column(String(1024), unique=True, index=True)
    etag: Mapped[str | None] = mapped_column(String(255), nullable=True)
    version_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    last_modified: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    size: Mapped[int] = mapped_column(Integer, default=0)
    operation: Mapped[str] = mapped_column(String(20), default="created")
    is_present: Mapped[bool] = mapped_column(Boolean, default=True)
    content_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now, onupdate=now)
class ExtractedPage(Base):
    __tablename__ = "extracted_pages"
    id: Mapped[int] = mapped_column(primary_key=True)
    page_path: Mapped[str] = mapped_column(String(1024), unique=True, index=True)
    title: Mapped[str] = mapped_column(String(500), default="")
    content: Mapped[str] = mapped_column(Text, default="")
    extracted_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    content_hash: Mapped[str] = mapped_column(String(64), default="")
class PageDependency(Base):
    __tablename__ = "page_dependencies"
    __table_args__ = (UniqueConstraint("page_id", "s3_key"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    page_id: Mapped[int] = mapped_column(ForeignKey("extracted_pages.id", ondelete="CASCADE"), index=True)
    s3_key: Mapped[str] = mapped_column(String(1024), index=True)
