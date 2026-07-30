from pydantic import BaseModel


class PublicBranchSchema(BaseModel):
    id: str
    name: str
    code: str
    slug: str
    phone: str | None = None
    address: str | None = None
    city: str | None = None
    latitude: float | None = None
    longitude: float | None = None
    is_default: bool = False
    accepting_orders: bool = True
    is_open_now: bool = True
    hours_label: str | None = None
    service_area_label: str | None = None
    delivery_fee: float = 0
    minimum_order: float = 0
    eta_min_minutes: int | None = None
    eta_max_minutes: int | None = None


class PublicBranchListSchema(BaseModel):
    items: list[PublicBranchSchema]
