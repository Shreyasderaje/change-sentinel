
from uuid import uuid4

from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    Query,
)
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import current_user
from app.models import Imagery, User
from app.schemas.imagery import ImageryCreate, ImageryOut
from app.services.permissions import require_project_access


router = APIRouter(
    prefix="/projects",
    tags=["imagery"],
)


@router.post(
    "/{project_id}/imagery",
    response_model=ImageryOut,
    status_code=201,
)
def create_imagery(
    project_id: str,
    payload: ImageryCreate,
    db: Session = Depends(get_db),
    user: User = Depends(current_user),
):

    require_project_access(
        db,
        project_id,
        user,
        write=True,
    )

    imagery_id = str(uuid4())

    imagery = Imagery(
        id=imagery_id,
        project_id=project_id,
        filename=payload.filename,
        acquisition_date=payload.acquisition_date,
        storage_key=f"projects/{project_id}/imagery/{imagery_id}",
        crs=None,
        metadata_json=None,
    )

    db.add(imagery)
    db.commit()
    db.refresh(imagery)

    return imagery


@router.get(
    "/{project_id}/imagery",
    response_model=list[ImageryOut],
)
def list_imagery(
    project_id: str,
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
    user: User = Depends(current_user),
):

    require_project_access(db, project_id, user)

    query = (
        select(Imagery)
        .where(Imagery.project_id == project_id)
        .order_by(Imagery.id)
        .offset(offset)
        .limit(limit)
    )

    return db.scalars(query).all()


@router.get(
    "/{project_id}/imagery/{imagery_id}",
    response_model=ImageryOut,
)
def get_imagery(
    project_id: str,
    imagery_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(current_user),
):

    require_project_access(db, project_id, user)

    imagery = db.scalar(
        select(Imagery).where(
            Imagery.id == imagery_id,
            Imagery.project_id == project_id,
        )
    )

    if imagery is None:
        raise HTTPException(404, "Imagery not found")

    return imagery


import io
import os
from datetime import datetime
from pathlib import Path
from PIL import Image
from fastapi import File, UploadFile, Form


MAX_UPLOAD_BYTES = 20 * 1024 * 1024
MAX_IMAGE_PIXELS = 40_000_000

ALLOWED_IMAGE_FORMATS = {
    ".jpg": "JPEG",
    ".jpeg": "JPEG",
    ".png": "PNG",
    ".tif": "TIFF",
    ".tiff": "TIFF",
}


def get_storage_root():
    return Path(
        os.environ.get(
            "SENTINEL_STORAGE_ROOT",
            str(Path.home() / ".change-sentinel" / "storage"),
        )
    ).resolve()


@router.post(
    "/{project_id}/imagery/upload",
    response_model=ImageryOut,
    status_code=201,
)
def upload_imagery(
    project_id: str,
    file: UploadFile = File(...),
    acquisition_date: datetime | None = Form(None),
    db: Session = Depends(get_db),
    user: User = Depends(current_user),
):

    project = require_project_access(
        db, project_id, user, write=True
    )

    if user.role != "admin" and project.owner_id != user.id:
        raise HTTPException(403, "Write permission denied")

    filename = file.filename or ""

    if (
        not filename
        or len(filename) > 255
        or "/" in filename
        or chr(92) in filename
        or ":" in filename
        or any(ord(c) < 32 for c in filename)
    ):
        raise HTTPException(422, "Invalid filename")

    extension = Path(filename).suffix.lower()

    if extension not in ALLOWED_IMAGE_FORMATS:
        raise HTTPException(415, "Unsupported image format")

    data = file.file.read(MAX_UPLOAD_BYTES + 1)

    if not data:
        raise HTTPException(400, "Empty image")

    if len(data) > MAX_UPLOAD_BYTES:
        raise HTTPException(413, "Image exceeds 20 MB limit")

    try:
        with Image.open(io.BytesIO(data)) as image:

            image_format = image.format
            width, height = image.size

            if image_format != ALLOWED_IMAGE_FORMATS[extension]:
                raise HTTPException(
                    415, "Image content does not match file extension"
                )

            if width * height > MAX_IMAGE_PIXELS:
                raise HTTPException(
                    413, "Image dimensions exceed limit"
                )

            if getattr(image, "n_frames", 1) != 1:
                raise HTTPException(
                    415, "Multiple image frames are not supported"
                )

            image.verify()

        with Image.open(io.BytesIO(data)) as image:
            image.load()

    except HTTPException:
        raise

    except Exception:
        raise HTTPException(400, "Invalid or corrupted image")

    imagery_id = str(uuid4())

    storage_key = (
        f"projects/{project.id}/imagery/"
        f"{imagery_id}{extension}"
    )

    root = get_storage_root()
    storage_path = (root / storage_key).resolve()

    if not storage_path.is_relative_to(root):
        raise HTTPException(500, "Invalid storage location")

    imagery = Imagery(
        id=imagery_id,
        project_id=project.id,
        filename=filename,
        acquisition_date=acquisition_date,
        storage_key=storage_key,
        crs=None,
        metadata_json={
            "storage_status": "stored",
            "format": image_format,
            "width": width,
            "height": height,
            "size_bytes": len(data),
        },
    )

    created = False

    try:
        storage_path.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        with storage_path.open("xb") as destination:
            created = True
            destination.write(data)

        db.add(imagery)
        db.commit()

    except Exception:
        db.rollback()

        if created:
            storage_path.unlink(missing_ok=True)

        raise HTTPException(
            500, "Unable to store imagery"
        )

    db.refresh(imagery)

    return imagery
