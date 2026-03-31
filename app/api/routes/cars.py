from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Car
from app.db.session import get_db
from app.schemas.schemas import CarOut, TuningProfileIn, TuningScreenshotResponse
from app.services.catalog import sync_catalog
from app.services.ocr import get_ocr_provider

router = APIRouter(prefix="/cars", tags=["cars"])


@router.get("/", response_model=list[CarOut])
async def list_cars(
    manufacturer_id: str | None = None,
    name: str | None = None,
    db: AsyncSession = Depends(get_db),
):
    q = select(Car).order_by(Car.manufacturer, Car.name)
    if manufacturer_id:
        q = q.where(Car.manufacturer.ilike(f"%{manufacturer_id}%"))
    if name:
        q = q.where(Car.name.ilike(f"%{name}%"))
    result = await db.execute(q)
    return result.scalars().all()


@router.get("/{car_id}", response_model=CarOut)
async def get_car(car_id: int, db: AsyncSession = Depends(get_db)):
    car = await db.get(Car, car_id)
    if not car:
        raise HTTPException(404, "Car not found")
    return car


@router.put("/{car_id}/tuning-profile", response_model=CarOut)
async def set_tuning_profile(
    car_id: int,
    body: TuningProfileIn,
    db: AsyncSession = Depends(get_db),
):
    """
    Define which parameters are tunable and their valid ranges.

    Example body:
    {
      "suspension": {
        "ranges": {
          "spring_rate_front": [3.0, 15.0],
          "ride_height_front": [50, 150],
          "camber_front": [-3.0, 0.0]
        },
        "current": {
          "spring_rate_front": 7.5,
          "ride_height_front": 65
        }
      },
      "aerodynamics": {
        "ranges": { "downforce_front": [0, 50], "downforce_rear": [0, 50] }
      }
    }
    """
    car = await db.get(Car, car_id)
    if not car:
        raise HTTPException(404, "Car not found")
    car.tuning_profile = body.model_dump(exclude_none=True)
    await db.flush()
    await db.refresh(car)
    return car


@router.post("/sync-catalog", status_code=202)
async def trigger_catalog_sync(db: AsyncSession = Depends(get_db)):
    """Pull the latest GT7 car list from ddm999 and upsert locally."""
    summary = await sync_catalog(db)
    return {"message": "Sync complete", **summary}


@router.post("/parse-tuning-screenshot", response_model=TuningScreenshotResponse)
async def parse_tuning_screenshot(
    screenshot: UploadFile = File(...),
    ocr=Depends(get_ocr_provider),
):
    """
    Extract tuning parameters from a GT7 configuration sheet screenshot.

    Accepts an image file (JPEG, PNG, WEBP) and uses the configured OCR provider
    to extract all visible tuning parameters. Returns the extracted profile for
    preview before saving.
    """
    if not screenshot.content_type or not screenshot.content_type.startswith("image/"):
        raise HTTPException(400, "File must be an image (JPEG, PNG, or WEBP)")

    contents = await screenshot.read()
    if len(contents) > 10 * 1024 * 1024:
        raise HTTPException(413, "Image too large (max 10MB)")

    try:
        result = await ocr.extract(
            image_bytes=contents,
            media_type=screenshot.content_type,
        )
    except NotImplementedError as e:
        raise HTTPException(400, str(e))
    except ValueError as e:
        raise HTTPException(400, f"Failed to parse image: {str(e)}")

    return TuningScreenshotResponse(
        extracted_profile=result.extracted_profile,
        provider=result.provider,
        model=result.model,
        sections_found=result.sections_found,
        warnings=result.warnings,
        car_name=result.car_name,
    )
