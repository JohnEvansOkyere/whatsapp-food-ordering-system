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
    delayed = "delayed"
    delivered = "delivered"
    cancel_requested = "cancel_requested"
    cancelled = "cancelled"
    rejected = "rejected"


class OrderListScope(str, Enum):
    all = "all"
    live = "live"
    attention = "attention"
    closed = "closed"


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


class OrderItemSelectionSchema(BaseModel):
    group_id: str
    option_id: str
    name: Optional[str] = None
    price: Optional[float] = None


class OrderItemInputSchema(BaseModel):
    item_id: str
    name: Optional[str] = None
    quantity: int = Field(..., ge=1, le=99)
    unit_price: Optional[float] = None
    total_price: Optional[float] = None
    selections: list[OrderItemSelectionSchema] = Field(default_factory=list)


class OrderItemSchema(BaseModel):
    item_id: str
    name: str
    quantity: int
    unit_price: float
    total_price: float
    selections: list[OrderItemSelectionSchema] = Field(default_factory=list)


class CreateOrderSchema(BaseModel):
    customer_phone: str = Field(..., min_length=9, max_length=20)
    customer_name: Optional[str] = Field(default=None, max_length=100)
    delivery_address: str = Field(..., min_length=3, max_length=500)
    # Present when the customer picked the address on the map. Riders navigate
    # to these when set; a typed-only address leaves them null.
    delivery_latitude: Optional[float] = Field(default=None, ge=-90, le=90)
    delivery_longitude: Optional[float] = Field(default=None, ge=-180, le=180)
    delivery_place_id: Optional[str] = Field(default=None, max_length=200)
    items: list[OrderItemInputSchema] = Field(..., min_length=1)
    total_amount: Optional[float] = None
    payment_method: PaymentMethod = PaymentMethod.momo
    notes: Optional[str] = Field(default=None, max_length=500)
    branch_id: Optional[str] = Field(default=None, max_length=100)
    idempotency_key: Optional[str] = Field(default=None, min_length=16, max_length=100)
    # Placing an order is the consent for the messages about that order: the
    # receipt, the tracking link, and status updates all go to the verified
    # number automatically. Nothing marketing is sent on this flag.
    whatsapp_consent: bool = True
    channel: str = Field(default="web", max_length=30)
    fulfillment_type: FulfillmentType = FulfillmentType.delivery


class OrderResponseSchema(BaseModel):
    id: str
    order_number: Optional[str] = None
    tracking_code: Optional[str] = None
    tracking_url: Optional[str] = None
    whatsapp_receipt_sent: Optional[bool] = None
    branch_id: Optional[str] = None
    branch_name: Optional[str] = None
    customer_phone: str
    customer_name: Optional[str]
    delivery_address: str
    delivery_latitude: Optional[float] = None
    delivery_longitude: Optional[float] = None
    items: list[OrderItemSchema]
    subtotal_amount: float
    delivery_fee: float = 0
    total_amount: float
    payment_method: PaymentMethod
    payment_status: PaymentStatus
    status: OrderStatus
    channel: str
    fulfillment_type: FulfillmentType
    notes: Optional[str]
    accepted_eta_minutes: Optional[int] = None
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
    offset: int = 0
    limit: int = 50


class AdminOrderDetailSchema(OrderResponseSchema):
    tenant_id: Optional[str] = None
    customer_id: Optional[str] = None
    allowed_next_statuses: list[OrderStatus] = Field(default_factory=list)
    events: list[OrderEventSchema] = Field(default_factory=list)


class UpdateOrderStatusSchema(BaseModel):
    status: OrderStatus
    actor_label: Optional[str] = None
    reason_code: Optional[str] = None
    reason_note: Optional[str] = None
    eta_minutes: Optional[int] = Field(default=None, ge=10, le=240)


class UpdatePaymentSchema(BaseModel):
    status: PaymentStatus
    provider: str = Field(default="manual", max_length=50)
    provider_reference: Optional[str] = Field(default=None, max_length=150)


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
    branch_name: Optional[str] = None
    branch_slug: Optional[str] = None
    branch_phone: Optional[str] = None
    eta_min_minutes: Optional[int] = None
    eta_max_minutes: Optional[int] = None
    accepted_eta_minutes: Optional[int] = None
    items: list[OrderItemSchema] = Field(default_factory=list)
    subtotal_amount: float = 0
    delivery_fee: float = 0
    total_amount: float = 0
    payment_status: PaymentStatus = PaymentStatus.unpaid
    timeline: list[OrderTrackingEventSchema]


class OrderFeedbackSchema(BaseModel):
    rating: int = Field(..., ge=1, le=5)
    comment: Optional[str] = Field(default=None, max_length=500)


class OrderFeedbackResponseSchema(BaseModel):
    accepted: bool = True


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
