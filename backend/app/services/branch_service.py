"""Customer-safe branch discovery and order routing helpers."""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any
from zoneinfo import ZoneInfo

from app.config import get_settings
from app.database import get_supabase
from app.schemas.branch import PublicBranchSchema

logger = logging.getLogger(__name__)

ASHESI_BRANCH_ID = "a5010000-0000-4000-8000-000000000001"
ABELEMKPE_BRANCH_ID = "abe10000-0000-4000-8000-000000000002"

LAUNCH_BRANCH_CODES = ("ASHESI", "ABELEMKPE")

STATIC_BRANCHES: list[dict[str, Any]] = [
    {
        "id": ASHESI_BRANCH_ID,
        "name": "Ashesi University",
        "code": "ASHESI",
        "slug": "ashesi-university",
        "phone": None,
        "address": "Ashesi University campus",
        "city": "Berekuso",
        "latitude": None,
        "longitude": None,
        "is_default": True,
        "is_active": True,
        "order_enabled": True,
        "opening_hours_json": {},
        "hours_label": "Daily 10:00–22:00 (provisional)",
        "service_area_label": "Ashesi campus and nearby Berekuso",
        "delivery_fee": 5,
        "minimum_order": 25,
        "eta_min_minutes": 35,
        "eta_max_minutes": 60,
    },
    {
        "id": ABELEMKPE_BRANCH_ID,
        "name": "Abelemkpe",
        "code": "ABELEMKPE",
        "slug": "abelemkpe",
        "phone": None,
        "address": "Abelemkpe, Accra",
        "city": "Accra",
        "latitude": None,
        "longitude": None,
        "is_default": False,
        "is_active": True,
        "order_enabled": True,
        "opening_hours_json": {},
        "hours_label": "Daily 10:00–22:00 (provisional)",
        "service_area_label": "Abelemkpe and nearby Accra areas",
        "delivery_fee": 8,
        "minimum_order": 25,
        "eta_min_minutes": 35,
        "eta_max_minutes": 60,
    },
]


def _hours_label(row: dict[str, Any]) -> str | None:
    configured = row.get("hours_label")
    if configured:
        return str(configured)

    opening_hours = row.get("opening_hours_json") or {}
    if isinstance(opening_hours, dict):
        label = opening_hours.get("label")
        if label:
            return str(label)
    return None


def _is_open_now(row: dict[str, Any]) -> bool:
    if not get_settings().enforce_business_hours:
        return True
    schedule = row.get("opening_hours_json") or {}
    daily = schedule.get("daily") if isinstance(schedule, dict) else None
    if not isinstance(daily, dict):
        return True
    try:
        now = datetime.now(ZoneInfo("Africa/Accra")).time()
        open_time = datetime.strptime(str(daily["open"]), "%H:%M").time()
        close_time = datetime.strptime(str(daily["close"]), "%H:%M").time()
        return open_time <= now < close_time
    except (KeyError, TypeError, ValueError):
        return True


def _to_public_branch(row: dict[str, Any]) -> PublicBranchSchema:
    code = str(row.get("code") or "").upper()
    default_slug = (
        "ashesi-university"
        if code == "ASHESI"
        else str(row.get("name") or code).strip().lower().replace(" ", "-")
    )
    is_open_now = _is_open_now(row)
    return PublicBranchSchema(
        id=str(row["id"]),
        name=str(row["name"]),
        code=code,
        slug=str(row.get("slug") or default_slug),
        phone=row.get("phone"),
        address=row.get("address"),
        city=row.get("city"),
        latitude=float(row["latitude"]) if row.get("latitude") is not None else None,
        longitude=float(row["longitude"]) if row.get("longitude") is not None else None,
        is_default=bool(row.get("is_default", False)),
        accepting_orders=bool(
            row.get("is_active", True) and row.get("order_enabled", True)
            and is_open_now
        ),
        is_open_now=is_open_now,
        hours_label=_hours_label(row),
        service_area_label=row.get("service_area_label"),
        delivery_fee=float(row.get("delivery_fee") or 0),
        minimum_order=float(row.get("minimum_order") or 0),
        eta_min_minutes=(
            int(row["eta_min_minutes"])
            if row.get("eta_min_minutes") is not None
            else None
        ),
        eta_max_minutes=(
            int(row["eta_max_minutes"])
            if row.get("eta_max_minutes") is not None
            else None
        ),
    )


async def fetch_public_branches() -> list[PublicBranchSchema]:
    """Return the two launch branches, falling back only for local/demo use."""
    try:
        result = (
            get_supabase()
            .table("branches")
            .select("*")
            .eq("is_active", True)
            .execute()
        )
        rows = [
            row
            for row in (result.data or [])
            if str(row.get("code") or "").upper() in LAUNCH_BRANCH_CODES
        ]
        if rows:
            branches = [_to_public_branch(dict(row)) for row in rows]
            return sorted(
                branches,
                key=lambda branch: (
                    not branch.is_default,
                    LAUNCH_BRANCH_CODES.index(branch.code),
                ),
            )
    except Exception as exc:
        logger.warning("Branch fetch failed, using local launch fallback: %s", exc)

    return [_to_public_branch(dict(row)) for row in STATIC_BRANCHES]


async def get_public_branch(branch_reference: str) -> PublicBranchSchema | None:
    reference = branch_reference.strip().lower()
    for branch in await fetch_public_branches():
        if reference in {
            branch.id.lower(),
            branch.code.lower(),
            branch.slug.lower(),
        }:
            return branch
    return None


async def update_branch_ordering(
    branch_id: str,
    *,
    accepting_orders: bool,
) -> PublicBranchSchema | None:
    result = (
        get_supabase()
        .table("branches")
        .update({"order_enabled": accepting_orders})
        .eq("id", branch_id)
        .execute()
    )
    if result.data:
        return _to_public_branch(dict(result.data[0]))
    return None
