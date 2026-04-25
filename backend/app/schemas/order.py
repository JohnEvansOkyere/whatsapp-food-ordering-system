from datetime import datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


class OrderStatus(str, Enum):
    pending = "pending"  # legacy compatibility
    new = "new"
    confirmed = "confirmed"
    preparing = "preparing"
    ready = "ready"
    out_for_delivery = "out_for_delivery"
    delivered = "delivered"
    cancel_requested = "cancel_requested"
    cancelled = "cancelled"
    rejected = "rejected"


class PaymentMethod(str, Enum):
    momo = "momo"
    cash = "cash"


class PaymentStatus(str, Enum):
    unpaid = "unpaid"
    pending = "pending"
    paid = "paid"
    failed = "failed"
    refunded = "refunded"


class FulfillmentType(str, Enum):
    delivery = "delivery"
    pickup = "pickup"
    dine_in = "dine_in"


class OrderItemInputSchema(BaseModel):
    item_id: str
    name: Optional[str] = None
    quantity: int = Field(..., ge=1, le=99)
    unit_price: Optional[float] = None
    total_price: Optional[float] = None


class OrderItemSchema(BaseModel):
    item_id: str
    name: str
    quantity: int
    unit_price: float
    total_price: float


class CreateOrderSchema(BaseModel):
    customer_phone: str
    customer_name: Optional[str] = None
    delivery_address: str
    items: list[OrderItemInputSchema] = Field(..., min_length=1)
    total_amount: Optional[float] = None
    payment_method: PaymentMethod = PaymentMethod.momo
    notes: Optional[str] = None
    branch_id: Optional[str] = None
    channel: str = "web"
    fulfillment_type: FulfillmentType = FulfillmentType.delivery


class OrderResponseSchema(BaseModel):
    id: str
    order_number: Optional[str] = None
    tracking_code: Optional[str] = None
    customer_phone: str
    customer_name: Optional[str]
    delivery_address: str
    items: list[OrderItemSchema]
    subtotal_amount: float
    total_amount: float
    payment_method: PaymentMethod
    payment_status: PaymentStatus
    status: OrderStatus
    channel: str
    fulfillment_type: FulfillmentType
    notes: Optional[str]
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class OrderEventSchema(BaseModel):
    id: str
    event_type: str
    from_status: Optional[OrderStatus] = None
    to_status: Optional[OrderStatus] = None
    actor_type: str
    actor_label: Optional[str] = None
    reason_code: Optional[str] = None
    reason_note: Optional[str] = None
    created_at: datetime


class AdminOrderListItemSchema(BaseModel):
    id: str
    order_number: Optional[str] = None
    tracking_code: Optional[str] = None
    customer_name: Optional[str] = None
    customer_phone: str
    branch_id: Optional[str] = None
    status: OrderStatus
    payment_status: PaymentStatus
    total_amount: float
    channel: str
    created_at: datetime


class AdminOrderListResponseSchema(BaseModel):
    items: list[AdminOrderListItemSchema]
    total: int


class AdminOrderDetailSchema(OrderResponseSchema):
    branch_id: Optional[str] = None
    tenant_id: Optional[str] = None
    customer_id: Optional[str] = None
    allowed_next_statuses: list[OrderStatus] = Field(default_factory=list)
    events: list[OrderEventSchema] = Field(default_factory=list)


class UpdateOrderStatusSchema(BaseModel):
    status: OrderStatus
    actor_label: Optional[str] = None
    reason_code: Optional[str] = None
    reason_note: Optional[str] = None


class CancelOrderSchema(BaseModel):
    reason_code: str
    reason_note: Optional[str] = None
    actor_label: Optional[str] = None


class OrderTrackingEventSchema(BaseModel):
    event_type: str
    status: Optional[OrderStatus] = None
    status_label: str
    created_at: datetime


class OrderTrackingResponseSchema(BaseModel):
    tracking_code: str
    order_number: Optional[str] = None
    status: OrderStatus
    status_label: str
    placed_at: datetime
    customer_name: Optional[str] = None
    timeline: list[OrderTrackingEventSchema]


class WhatsAppContact(BaseModel):
    profile: dict
    wa_id: str


class WhatsAppMessage(BaseModel):
    from_: str
    id: str
    timestamp: str
    text: Optional[dict] = None
    type: str

    model_config = ConfigDict(
        populate_by_name=True,
        json_schema_extra={"fields": {"from_": "from"}},
    )


class WhatsAppWebhookEntry(BaseModel):
    id: str
    changes: list[dict]


class WhatsAppWebhookPayload(BaseModel):
    object: str
    entry: list[WhatsAppWebhookEntry]


class OrderSummary(BaseModel):
    order_id: str
    customer_phone: str
    customer_name: Optional[str]
    delivery_address: str
    items: list[OrderItemSchema]
    total_amount: float
    payment_method: str
