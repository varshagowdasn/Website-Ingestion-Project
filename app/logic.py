import hashlib, re, logging
from datetime import datetime, timedelta, timezone
from pathlib import Path
from urllib.parse import urlparse, unquote, quote
from bs4 import BeautifulSoup
from sqlalchemy import select, delete
from app.config import settings
from app.models import IngestedFile, ExtractedPage, PageDependency, now
from app.s3 import session as s3session, kwargs as s3kwargs
from app.render import render
log = logging.getLogger(__name__)
def local(key):
    prefix=settings.s3_prefix.strip("/")
    rel=key[len(prefix)+1:] if prefix and key.startswith(prefix+"/") else key
    return Path(settings.site_root)/rel
def page_url(key):
    prefix=settings.s3_prefix.strip("/")
    rel=key[len(prefix)+1:] if prefix and key.startswith(prefix+"/") else key
    return settings.base_url.rstrip("/")+"/site/"+quote(rel)
def resolve(url, parent):
    if not url or url.startswith(("http:","https:","//","data:","javascript:","#","mailto:")): return None
    raw=unquote(urlparse(url).path).split("?")[0]
    parts=[]
    for p in (Path(parent).parent / raw).as_posix().split("/"):
        if p=="..":
            if parts: parts.pop()
        elif p not in ("","."): parts.append(p)
    key="/".join(parts)
    prefix=settings.s3_prefix.strip("/")
    return key if not prefix or key.startswith(prefix+"/") else prefix+"/"+key
def dependencies(html,key):
    soup=BeautifulSoup(html,"html.parser"); result=set()
    for tag in soup.find_all(True):
        for attr in ("src","href","poster"):
            k=resolve(tag.get(attr),key)
            if k: result.add(k)
        for u in re.findall(r"url\(['\"]?([^'\")]+)",tag.get("style","")):
            k=resolve(u,key)
            if k: result.add(k)
    for k in list(result):
        if k.endswith(".css"):
            f=local(k)
            if f.exists():
                css=f.read_text(errors="ignore")
                for u in re.findall(r"url\(['\"]?([^'\")]+)",css)+re.findall(r"@import\s+['\"]([^'\"]+)",css):
                    child=resolve(u,k)
                    if child: result.add(child)
    return result
async def extract(session,page):
    title,content,digest=await render(page_url(page.page_path))
    page.title=title; page.content=content; page.content_hash=digest; page.extracted_at=now()
    html=local(page.page_path).read_text(errors="replace")
    await session.execute(delete(PageDependency).where(PageDependency.page_id==page.id))
    session.add_all([PageDependency(page_id=page.id,s3_key=k) for k in dependencies(html,page.page_path)])
async def run_ingestion(db):
    Path(settings.site_root).mkdir(parents=True,exist_ok=True)
    seen=set(); changed=set(); created=updated=deleted=unchanged=0
    cutoff=datetime.now(timezone.utc)-timedelta(hours=settings.ingestion_lookback_hours)
    async with s3session.client("s3",**s3kwargs()) as s3:
        pager=s3.get_paginator("list_objects_v2")
        async for batch in pager.paginate(Bucket=settings.s3_bucket,Prefix=settings.s3_prefix):
            for obj in batch.get("Contents",[]):
                key=obj["Key"]
                if key.endswith("/"): continue
                seen.add(key); etag=obj.get("ETag","").strip('"')
                old=await db.scalar(select(IngestedFile).where(IngestedFile.s3_key==key))
                if old and old.is_present and old.etag==etag:
                    unchanged+=1; continue
                lm=obj.get("LastModified")
                if old and old.is_present and lm and lm<cutoff:
                    unchanged+=1; continue
                op="created" if old is None or not old.is_present else "updated"
                response=await s3.get_object(Bucket=settings.s3_bucket,Key=key)
                data=await response["Body"].read()
                f=local(key); f.parent.mkdir(parents=True,exist_ok=True); f.write_bytes(data)
                if old is None: old=IngestedFile(s3_key=key); db.add(old)
                old.etag=etag; old.version_id=obj.get("VersionId"); old.last_modified=lm
                old.size=obj.get("Size",len(data)); old.operation=op; old.is_present=True
                old.content_hash=hashlib.sha256(data).hexdigest(); changed.add(key)
                if op=="created": created+=1
                else: updated+=1
        # Deletion detection by comparing a complete paginated S3 listing to persisted inventory.
        inventory=(await db.scalars(select(IngestedFile).where(IngestedFile.is_present.is_(True)))).all()
        for row in inventory:
            if row.s3_key not in seen:
                row.is_present=False; row.operation="deleted"; row.updated_at=now()
                changed.add(row.s3_key); deleted+=1
                if local(row.s3_key).exists(): local(row.s3_key).unlink()
    await db.flush()
    affected=set()
    if changed:
        deps=(await db.scalars(select(PageDependency).where(PageDependency.s3_key.in_(changed)))).all()
        affected.update(d.page_id for d in deps)
    for key in changed:
        if key.lower().endswith((".html",".htm")):
            page=await db.scalar(select(ExtractedPage).where(ExtractedPage.page_path==key))
            if page is None: page=ExtractedPage(page_path=key); db.add(page); await db.flush()
            affected.add(page.id)
    names=[]
    for pid in sorted(affected):
        page=await db.get(ExtractedPage,pid)
        if page and local(page.page_path).exists():
            await extract(db,page); names.append(page.page_path)
    await db.commit()
    log.info("ingestion finished created=%s updated=%s deleted=%s unchanged=%s",created,updated,deleted,unchanged)
    return dict(created=created,updated=updated,deleted=deleted,unchanged=unchanged,reprocessed_pages=names)
