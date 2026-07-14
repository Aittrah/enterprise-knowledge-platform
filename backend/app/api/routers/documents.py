import re
from pathlib import Path

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, UploadFile

from app.api.deps import get_current_user, get_state
from app.api.state import AppState
from app.ingestion.extractors import SUPPORTED_EXTENSIONS

router = APIRouter(
    prefix="/documents", tags=["documents"], dependencies=[Depends(get_current_user)]
)

_SAFE_NAME = re.compile(r"[^\w.\- ]")


@router.post("/upload", status_code=202)
async def upload(
    file: UploadFile,
    background: BackgroundTasks,
    state: AppState = Depends(get_state),
) -> dict:
    filename = _SAFE_NAME.sub("_", Path(file.filename or "upload").name)
    extension = Path(filename).suffix.lower()
    if extension not in SUPPORTED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type '{extension}'. "
            f"Supported: {', '.join(SUPPORTED_EXTENSIONS)}",
        )

    content = await file.read()
    limit = state.settings.max_upload_mb * 1024 * 1024
    if len(content) > limit:
        raise HTTPException(
            status_code=413,
            detail=f"File exceeds the {state.settings.max_upload_mb} MB limit",
        )

    path = state.upload_dir / filename
    path.write_bytes(content)

    job_id = state.create_job(filename)
    background.add_task(state.run_ingestion, job_id, path, filename)
    return {"job_id": job_id, "filename": filename, "status": "queued"}


@router.get("")
def list_documents(state: AppState = Depends(get_state)) -> list[dict]:
    return sorted(
        state.documents.values(), key=lambda d: d["indexed_at"], reverse=True
    )


@router.get("/jobs/{job_id}")
def job_status(job_id: str, state: AppState = Depends(get_state)) -> dict:
    job = state.jobs.get(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail=f"No ingestion job '{job_id}'")
    return job
