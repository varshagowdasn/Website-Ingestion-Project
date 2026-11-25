import logging
from contextlib import asynccontextmanager
from pathlib import Path
from fastapi import FastAPI, Depends, HTTPException
from fastapi.staticfiles import StaticFiles
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.config import settings
from app.database import init_db,get_db
from app.models import IngestedFile,ExtractedPage
from app.schemas import IngestResult,FileOut,PageOut
from app.logic import run_ingestion,extract,local
logging.basicConfig(level=logging.INFO)
@asynccontextmanager
async def lifespan(app):
    Path(settings.site_root).mkdir(parents=True,exist_ok=True)
    await init_db()
    yield
app=FastAPI(title="Website Ingestion & Content Extraction API",version="1.0.0",lifespan=lifespan)
app.mount("/site",StaticFiles(directory=settings.site_root,html=True),name="site")
@app.get("/health")
async def health(): return {"status":"ok"}
@app.post("/ingestion/run",response_model=IngestResult)
async def ingestion(db:AsyncSession=Depends(get_db)):
    try: return await run_ingestion(db)
    except Exception as e:
        logging.exception("S3 ingestion failed")
        raise HTTPException(500,detail=f"Ingestion failed: {e}")
@app.get("/files",response_model=list[FileOut])
async def files(db:AsyncSession=Depends(get_db)):
    return list((await db.scalars(select(IngestedFile).order_by(IngestedFile.s3_key))).all())
@app.get("/pages",response_model=list[PageOut])
async def pages(db:AsyncSession=Depends(get_db)):
    return list((await db.scalars(select(ExtractedPage).order_by(ExtractedPage.page_path))).all())
@app.get("/pages/{page_id}",response_model=PageOut)
async def page_detail(page_id:int,db:AsyncSession=Depends(get_db)):
    page=await db.get(ExtractedPage,page_id)
    if not page: raise HTTPException(404,"Page not found")
    return page
@app.post("/pages/{page_id}/reprocess",response_model=PageOut)
async def reprocess(page_id:int,db:AsyncSession=Depends(get_db)):
    page=await db.get(ExtractedPage,page_id)
    if not page: raise HTTPException(404,"Page not found")
    if not local(page.page_path).exists(): raise HTTPException(404,"Source file missing")
    await extract(db,page); await db.commit(); await db.refresh(page)
    return page
