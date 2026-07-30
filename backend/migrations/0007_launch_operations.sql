-- ============================================================
-- 0007_launch_operations.sql
-- Provisional two-branch operations, branch menu overrides,
-- and duplicate-order protection.
-- Replace provisional values before launch.
-- ============================================================

CREATE EXTENSION IF NOT EXISTS pgcrypto;

ALTER TABLE public.orders DROP CONSTRAINT IF EXISTS orders_status_check;
ALTER TABLE public.orders ADD CONSTRAINT orders_status_check
    CHECK (status IN (
        'pending',
        'new',
        'confirmed',
        'preparing',
        'ready',
        'out_for_delivery',
        'delayed',
        'delivered',
        'cancel_requested',
        'cancelled',
        'rejected'
    ));

ALTER TABLE public.branches ADD COLUMN IF NOT EXISTS hours_label TEXT;
ALTER TABLE public.branches ADD COLUMN IF NOT EXISTS service_area_label TEXT;
ALTER TABLE public.branches
    ADD COLUMN IF NOT EXISTS minimum_order NUMERIC(10, 2) NOT NULL DEFAULT 0;

UPDATE public.branches
SET
    hours_label = COALESCE(hours_label, 'Daily 10:00–22:00 (provisional)'),
    opening_hours_json = CASE
        WHEN opening_hours_json = '{}'::jsonb
        THEN '{"label":"Daily 10:00–22:00 (provisional)","daily":{"open":"10:00","close":"22:00"}}'::jsonb
        ELSE opening_hours_json
    END,
    service_area_label = CASE
        WHEN code = 'ASHESI' THEN COALESCE(service_area_label, 'Ashesi campus and nearby Berekuso')
        WHEN code = 'ABELEMKPE' THEN COALESCE(service_area_label, 'Abelemkpe and nearby Accra areas')
        ELSE service_area_label
    END,
    delivery_fee = CASE
        WHEN code = 'ASHESI' AND delivery_fee = 0 THEN 5
        WHEN code = 'ABELEMKPE' AND delivery_fee = 0 THEN 8
        ELSE delivery_fee
    END,
    minimum_order = CASE
        WHEN code IN ('ASHESI', 'ABELEMKPE') AND minimum_order = 0 THEN 25
        ELSE minimum_order
    END,
    eta_min_minutes = COALESCE(eta_min_minutes, 35),
    eta_max_minutes = COALESCE(eta_max_minutes, 60),
    updated_at = now()
WHERE code IN ('ASHESI', 'ABELEMKPE');

CREATE TABLE IF NOT EXISTS public.branch_menu_overrides (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID REFERENCES public.tenants(id) ON DELETE CASCADE,
    branch_id UUID NOT NULL REFERENCES public.branches(id) ON DELETE CASCADE,
    menu_item_id TEXT NOT NULL,
    price_override NUMERIC(10, 2),
    sold_out BOOLEAN NOT NULL DEFAULT false,
    active BOOLEAN NOT NULL DEFAULT true,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT branch_menu_overrides_unique UNIQUE (branch_id, menu_item_id),
    CONSTRAINT branch_menu_overrides_price_check
        CHECK (price_override IS NULL OR price_override >= 0)
);

CREATE INDEX IF NOT EXISTS idx_branch_menu_overrides_branch_active
    ON public.branch_menu_overrides(branch_id, active, sold_out);

DROP TRIGGER IF EXISTS branch_menu_overrides_updated_at
    ON public.branch_menu_overrides;
CREATE TRIGGER branch_menu_overrides_updated_at
    BEFORE UPDATE ON public.branch_menu_overrides
    FOR EACH ROW EXECUTE FUNCTION public.update_updated_at();

ALTER TABLE public.branch_menu_overrides ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS "service_role_branch_menu_overrides"
    ON public.branch_menu_overrides;
CREATE POLICY "service_role_branch_menu_overrides"
ON public.branch_menu_overrides
FOR ALL
USING (auth.role() = 'service_role')
WITH CHECK (auth.role() = 'service_role');

ALTER TABLE public.orders ADD COLUMN IF NOT EXISTS idempotency_key TEXT;
ALTER TABLE public.orders
    ADD COLUMN IF NOT EXISTS whatsapp_consent BOOLEAN NOT NULL DEFAULT false;
ALTER TABLE public.orders ADD COLUMN IF NOT EXISTS tracking_expires_at TIMESTAMPTZ;
ALTER TABLE public.orders ADD COLUMN IF NOT EXISTS accepted_eta_minutes INTEGER;
ALTER TABLE public.orders ADD COLUMN IF NOT EXISTS dispatched_at TIMESTAMPTZ;
UPDATE public.orders
SET tracking_expires_at = COALESCE(created_at, now()) + interval '90 days'
WHERE tracking_expires_at IS NULL;
ALTER TABLE public.orders
    ALTER COLUMN tracking_expires_at SET DEFAULT (now() + interval '90 days');
CREATE UNIQUE INDEX IF NOT EXISTS uq_orders_branch_idempotency_key
    ON public.orders(branch_id, idempotency_key)
    WHERE idempotency_key IS NOT NULL;

ALTER TABLE public.order_items
    ADD COLUMN IF NOT EXISTS selections_json JSONB NOT NULL DEFAULT '[]'::jsonb;

CREATE TABLE IF NOT EXISTS public.order_feedback (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    order_id UUID NOT NULL UNIQUE REFERENCES public.orders(id) ON DELETE CASCADE,
    rating INTEGER NOT NULL,
    comment TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT order_feedback_rating_check CHECK (rating BETWEEN 1 AND 5)
);

ALTER TABLE public.order_feedback ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS "service_role_order_feedback" ON public.order_feedback;
CREATE POLICY "service_role_order_feedback"
ON public.order_feedback
FOR ALL
USING (auth.role() = 'service_role')
WITH CHECK (auth.role() = 'service_role');

CREATE TABLE IF NOT EXISTS public.payments (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    order_id UUID NOT NULL REFERENCES public.orders(id) ON DELETE CASCADE,
    provider TEXT NOT NULL DEFAULT 'manual',
    provider_reference TEXT,
    method TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'pending',
    amount NUMERIC(10, 2) NOT NULL,
    currency TEXT NOT NULL DEFAULT 'GHS',
    metadata_json JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT payments_method_check CHECK (method IN ('momo', 'cash')),
    CONSTRAINT payments_status_check
        CHECK (status IN ('unpaid', 'pending', 'paid', 'failed', 'refunded'))
);

CREATE UNIQUE INDEX IF NOT EXISTS uq_payments_provider_reference
    ON public.payments(provider, provider_reference)
    WHERE provider_reference IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_payments_order_created
    ON public.payments(order_id, created_at DESC);

ALTER TABLE public.payments ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS "service_role_payments" ON public.payments;
CREATE POLICY "service_role_payments"
ON public.payments
FOR ALL
USING (auth.role() = 'service_role')
WITH CHECK (auth.role() = 'service_role');

CREATE TABLE IF NOT EXISTS public.analytics_events (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    event_name TEXT NOT NULL,
    branch_id UUID REFERENCES public.branches(id) ON DELETE SET NULL,
    anonymous_session_id TEXT,
    metadata_json JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_analytics_events_name_created
    ON public.analytics_events(event_name, created_at DESC);
ALTER TABLE public.analytics_events ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS "service_role_analytics_events" ON public.analytics_events;
CREATE POLICY "service_role_analytics_events"
ON public.analytics_events
FOR ALL
USING (auth.role() = 'service_role')
WITH CHECK (auth.role() = 'service_role');
