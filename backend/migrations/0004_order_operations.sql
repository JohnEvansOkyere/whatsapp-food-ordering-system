-- ============================================================
-- 0004_order_operations.sql
-- Normalize order lines, add tracking metadata, and create audit trail
-- Keeps legacy `orders.items` for compatibility with the current app
-- ============================================================

CREATE EXTENSION IF NOT EXISTS pgcrypto;

ALTER TABLE public.orders ADD COLUMN IF NOT EXISTS customer_id UUID;
ALTER TABLE public.orders ADD COLUMN IF NOT EXISTS order_number TEXT;
ALTER TABLE public.orders ADD COLUMN IF NOT EXISTS tracking_code TEXT;
ALTER TABLE public.orders ADD COLUMN IF NOT EXISTS channel TEXT NOT NULL DEFAULT 'web';
ALTER TABLE public.orders ADD COLUMN IF NOT EXISTS payment_status TEXT NOT NULL DEFAULT 'unpaid';
ALTER TABLE public.orders ADD COLUMN IF NOT EXISTS fulfillment_type TEXT NOT NULL DEFAULT 'delivery';
ALTER TABLE public.orders ADD COLUMN IF NOT EXISTS subtotal_amount NUMERIC(10, 2) NOT NULL DEFAULT 0;
ALTER TABLE public.orders ADD COLUMN IF NOT EXISTS delivery_fee NUMERIC(10, 2) NOT NULL DEFAULT 0;
ALTER TABLE public.orders ADD COLUMN IF NOT EXISTS discount_amount NUMERIC(10, 2) NOT NULL DEFAULT 0;
ALTER TABLE public.orders ADD COLUMN IF NOT EXISTS currency TEXT NOT NULL DEFAULT 'GHS';
ALTER TABLE public.orders ADD COLUMN IF NOT EXISTS customer_name_snapshot TEXT;
ALTER TABLE public.orders ADD COLUMN IF NOT EXISTS customer_phone_snapshot TEXT;
ALTER TABLE public.orders ADD COLUMN IF NOT EXISTS delivery_address_snapshot TEXT;
ALTER TABLE public.orders ADD COLUMN IF NOT EXISTS placed_at TIMESTAMPTZ;
ALTER TABLE public.orders ADD COLUMN IF NOT EXISTS confirmed_at TIMESTAMPTZ;
ALTER TABLE public.orders ADD COLUMN IF NOT EXISTS delivered_at TIMESTAMPTZ;
ALTER TABLE public.orders ADD COLUMN IF NOT EXISTS cancelled_at TIMESTAMPTZ;

ALTER TABLE public.orders DROP CONSTRAINT IF EXISTS orders_status_check;
ALTER TABLE public.orders ADD CONSTRAINT orders_status_check
    CHECK (status IN (
        'pending',
        'new',
        'confirmed',
        'preparing',
        'ready',
        'out_for_delivery',
        'delivered',
        'cancel_requested',
        'cancelled',
        'rejected'
    ));

ALTER TABLE public.orders DROP CONSTRAINT IF EXISTS orders_payment_method_check;
ALTER TABLE public.orders ADD CONSTRAINT orders_payment_method_check
    CHECK (payment_method IN ('momo', 'cash'));

ALTER TABLE public.orders DROP CONSTRAINT IF EXISTS orders_payment_status_check;
ALTER TABLE public.orders ADD CONSTRAINT orders_payment_status_check
    CHECK (payment_status IN ('unpaid', 'pending', 'paid', 'failed', 'refunded'));

ALTER TABLE public.orders DROP CONSTRAINT IF EXISTS orders_fulfillment_type_check;
ALTER TABLE public.orders ADD CONSTRAINT orders_fulfillment_type_check
    CHECK (fulfillment_type IN ('delivery', 'pickup', 'dine_in'));

CREATE OR REPLACE FUNCTION public.generate_order_number()
RETURNS TEXT
LANGUAGE sql
VOLATILE
AS $$
    SELECT 'ORD-' || upper(substr(replace(gen_random_uuid()::text, '-', ''), 1, 8))
$$;

CREATE OR REPLACE FUNCTION public.generate_tracking_code()
RETURNS TEXT
LANGUAGE sql
VOLATILE
AS $$
    SELECT 'TRK-' || upper(substr(replace(gen_random_uuid()::text, '-', ''), 1, 10))
$$;

ALTER TABLE public.orders ALTER COLUMN order_number SET DEFAULT public.generate_order_number();
ALTER TABLE public.orders ALTER COLUMN tracking_code SET DEFAULT public.generate_tracking_code();
ALTER TABLE public.orders ALTER COLUMN placed_at SET DEFAULT now();

UPDATE public.orders
SET
    order_number = COALESCE(order_number, 'ORD-' || upper(substr(replace(id::text, '-', ''), 1, 8))),
    tracking_code = COALESCE(tracking_code, 'TRK-' || upper(substr(replace(id::text, '-', ''), 1, 10))),
    subtotal_amount = COALESCE(subtotal_amount, total_amount, 0),
    customer_name_snapshot = COALESCE(customer_name_snapshot, customer_name),
    customer_phone_snapshot = COALESCE(customer_phone_snapshot, customer_phone),
    delivery_address_snapshot = COALESCE(delivery_address_snapshot, delivery_address),
    placed_at = COALESCE(placed_at, created_at),
    confirmed_at = CASE
        WHEN confirmed_at IS NOT NULL THEN confirmed_at
        WHEN status = 'confirmed' THEN created_at
        ELSE confirmed_at
    END,
    delivered_at = CASE
        WHEN delivered_at IS NOT NULL THEN delivered_at
        WHEN status = 'delivered' THEN created_at
        ELSE delivered_at
    END,
    cancelled_at = CASE
        WHEN cancelled_at IS NOT NULL THEN cancelled_at
        WHEN status = 'cancelled' THEN created_at
        ELSE cancelled_at
    END,
    payment_status = CASE
        WHEN payment_status IS NOT NULL AND payment_status <> '' THEN payment_status
        WHEN payment_method = 'cash' THEN 'pending'
        ELSE 'unpaid'
    END
WHERE
    order_number IS NULL
    OR tracking_code IS NULL
    OR customer_name_snapshot IS NULL
    OR customer_phone_snapshot IS NULL
    OR delivery_address_snapshot IS NULL
    OR placed_at IS NULL
    OR subtotal_amount = 0;

CREATE TABLE IF NOT EXISTS public.order_items (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID REFERENCES public.tenants(id) ON DELETE SET NULL,
    branch_id UUID REFERENCES public.branches(id) ON DELETE SET NULL,
    order_id UUID NOT NULL REFERENCES public.orders(id) ON DELETE CASCADE,
    menu_item_id TEXT,
    item_name_snapshot TEXT NOT NULL,
    unit_price NUMERIC(10, 2) NOT NULL DEFAULT 0,
    quantity INTEGER NOT NULL DEFAULT 1,
    line_total NUMERIC(10, 2) NOT NULL DEFAULT 0,
    special_instructions TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS public.order_events (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID REFERENCES public.tenants(id) ON DELETE SET NULL,
    branch_id UUID REFERENCES public.branches(id) ON DELETE SET NULL,
    order_id UUID NOT NULL REFERENCES public.orders(id) ON DELETE CASCADE,
    event_type TEXT NOT NULL,
    from_status TEXT,
    to_status TEXT,
    actor_type TEXT NOT NULL DEFAULT 'system',
    actor_user_id UUID REFERENCES public.users(id) ON DELETE SET NULL,
    actor_label TEXT,
    reason_code TEXT,
    reason_note TEXT,
    metadata_json JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT order_events_actor_type_check
        CHECK (actor_type IN ('system', 'customer', 'staff', 'ai', 'webhook'))
);

CREATE INDEX IF NOT EXISTS idx_orders_tracking_code ON public.orders(tracking_code);
CREATE UNIQUE INDEX IF NOT EXISTS uq_orders_order_number ON public.orders(order_number);
CREATE UNIQUE INDEX IF NOT EXISTS uq_orders_tracking_code ON public.orders(tracking_code);
CREATE INDEX IF NOT EXISTS idx_orders_customer_phone_snapshot
    ON public.orders(tenant_id, customer_phone_snapshot);
CREATE INDEX IF NOT EXISTS idx_orders_status_created_at
    ON public.orders(tenant_id, branch_id, status, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_order_items_order_id ON public.order_items(order_id);
CREATE INDEX IF NOT EXISTS idx_order_events_order_id_created_at
    ON public.order_events(order_id, created_at);
CREATE INDEX IF NOT EXISTS idx_order_events_tenant_order_created_at
    ON public.order_events(tenant_id, order_id, created_at);

INSERT INTO public.order_items (
    tenant_id,
    branch_id,
    order_id,
    menu_item_id,
    item_name_snapshot,
    unit_price,
    quantity,
    line_total,
    created_at
)
SELECT
    o.tenant_id,
    o.branch_id,
    o.id,
    COALESCE(item->>'item_id', item->>'id'),
    COALESCE(item->>'name', 'Unknown item'),
    COALESCE(NULLIF(item->>'unit_price', '')::numeric, 0),
    COALESCE(NULLIF(item->>'quantity', '')::integer, 1),
    COALESCE(
        NULLIF(item->>'total_price', '')::numeric,
        COALESCE(NULLIF(item->>'unit_price', '')::numeric, 0)
        * COALESCE(NULLIF(item->>'quantity', '')::integer, 1)
    ),
    o.created_at
FROM public.orders o
CROSS JOIN LATERAL jsonb_array_elements(COALESCE(o.items, '[]'::jsonb)) AS item
WHERE NOT EXISTS (
    SELECT 1
    FROM public.order_items oi
    WHERE oi.order_id = o.id
);

INSERT INTO public.order_events (
    tenant_id,
    branch_id,
    order_id,
    event_type,
    from_status,
    to_status,
    actor_type,
    actor_label,
    metadata_json,
    created_at
)
SELECT
    o.tenant_id,
    o.branch_id,
    o.id,
    'order_created',
    NULL,
    o.status,
    'system',
    'migration',
    jsonb_build_object('source', '0004_order_operations'),
    o.created_at
FROM public.orders o
WHERE NOT EXISTS (
    SELECT 1
    FROM public.order_events oe
    WHERE oe.order_id = o.id
);

ALTER TABLE public.order_items ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.order_events ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS "service_role_order_items" ON public.order_items;
CREATE POLICY "service_role_order_items"
ON public.order_items
FOR ALL
USING (auth.role() = 'service_role')
WITH CHECK (auth.role() = 'service_role');

DROP POLICY IF EXISTS "service_role_order_events" ON public.order_events;
CREATE POLICY "service_role_order_events"
ON public.order_events
FOR ALL
USING (auth.role() = 'service_role')
WITH CHECK (auth.role() = 'service_role');

