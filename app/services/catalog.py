"""
Car Catalog Service
--------------------
Downloads the community-maintained GT7 car list from ddm999's public CSV
and upserts it into the local database.
"""

import csv
import io
import logging

import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.db.models import Car

logger = logging.getLogger(__name__)


async def sync_catalog(db: AsyncSession) -> dict:
    cfg = get_settings()
    logger.info("Syncing GT7 car catalog from %s", cfg.gt7_cars_csv_url)

    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.get(cfg.gt7_cars_csv_url)
        resp.raise_for_status()

    reader = csv.DictReader(io.StringIO(resp.text))
    created = updated = skipped = 0

    for row in reader:
        # ddm999 CSV columns: ID, ShortName, Maker (case-insensitive lookup)
        row_lower = {k.lower(): v for k, v in row.items()}
        car_id = (
            row_lower.get("id")
            or row_lower.get("carid")
            or row_lower.get("car_id")
            or ""
        ).strip()
        if not car_id:
            skipped += 1
            continue

        name = row_lower.get("shortname") or row_lower.get("name") or ""
        name = name.strip()
        manufacturer = (row_lower.get("maker") or row_lower.get("manufacturer") or "").strip()

        result = await db.execute(select(Car).where(Car.car_id == car_id))
        existing = result.scalar_one_or_none()

        if existing:
            existing.name = name
            existing.manufacturer = manufacturer
            updated += 1
        else:
            db.add(Car(car_id=car_id, name=name, manufacturer=manufacturer))
            created += 1

    await db.commit()
    result = {"created": created, "updated": updated, "skipped": skipped}
    logger.info("Catalog sync complete: %s", result)
    return result
