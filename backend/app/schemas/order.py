from pydantic import BaseModel
from typing import Optional
from datetime import datetime
from enum import Enum


class OrderStatus(str, Enum):
    pending = "pending"
    confirmed = "confirmed"
    preparing = "preparing"
    ready = "ready"
    delivered = "delivered"
    cancelled = "cancelled"


class OrderItemSchema(BaseModel):
    item_id: str
    name: str
    quantity: int
    unit_price: float
    total_price: float


class CreateOrderSchema(BaseModel):
    customer_phone: str          # WhatsApp number customer ordered from
    customer_name: Optional[str] = None
    delivery_address: str
    items: list[OrderItemSchema]
    total_amount: float
    payment_method: str = "momo"  # momo | cash
    notes: Optional[str] = None


class OrderResponseSchema(BaseModel):
    id: str
    customer_phone: str
    customer_name: Optional[str]
    delivery_address: str
    items: list[OrderItemSchema]
    total_amount: float
    payment_method: str
    status: OrderStatus
    notes: Optional[str]
    created_at: datetime

    class Config:
        from_attributes = True


# WhatsApp webhook payload schemas
class WhatsAppContact(BaseModel):
    profile: dict
    wa_id: str


class WhatsAppMessage(BaseModel):
    from_: str
    id: str
    timestamp: str
    text: Optional[dict] = None
    type: str

    class Config:
        populate_by_name = True
        fields = {"from_": "from"}


class WhatsAppWebhookEntry(BaseModel):
    id: str
    changes: list[dict]


class WhatsAppWebhookPayload(BaseModel):
    object: str
    entry: list[WhatsAppWebhookEntry]


# Order confirmation message builder
class OrderSummary(BaseModel):
    order_id: str
    customer_phone: str
    customer_name: Optional[str]
    delivery_address: str
    items: list[OrderItemSchema]
    total_amount: float
    payment_method: str
