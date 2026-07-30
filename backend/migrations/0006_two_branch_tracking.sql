-- ============================================================
-- 0006_two_branch_tracking.sql
-- Configure the Ashesi University and Abelemkpe launch branches
-- and add high-entropy public order tracking tokens.
-- ============================================================

CREATE EXTENSION IF NOT EXISTS pgcrypto;

ALTER TABLE public.branches ADD COLUMN IF NOT EXISTS slug TEXT;
ALTER TABLE public.branches ADD COLUMN IF NOT EXISTS latitude NUMERIC(10, 7);
ALTER TABLE public.branches ADD COLUMN IF NOT EXISTS longitude NUMERIC(10, 7);
ALTER TABLE public.branches
    ADD COLUMN IF NOT EXISTS order_enabled BOOLEAN NOT NULL DEFAULT true;
ALTER TABLE public.branches
    ADD COLUMN IF NOT EXISTS delivery_fee NUMERIC(10, 2) NOT NULL DEFAULT 0;
ALTER TABLE public.branches ADD COLUMN IF NOT EXISTS eta_min_minutes INTEGER;
ALTER TABLE public.branches ADD COLUMN IF NOT EXISTS eta_max_minutes INTEGER;

DO $$
DECLARE
    v_tenant_id UUID;
BEGIN
    SELECT id INTO v_tenant_id
    FROM public.tenants
    WHERE slug = 'default-tenant'
    ORDER BY created_at
    LIMIT 1;

    IF v_tenant_id IS NULL THEN
        INSERT INTO public.tenants (
            name,
            slug,
            status,
            subscription_plan,
            default_currency,
            default_timezone
        )
        VALUES (
            'Default Tenant',
            'default-tenant',
            'active',
            'starter',
            'GHS',
            'Africa/Accra'
        )
        RETURNING id INTO v_tenant_id;
    END IF;

    INSERT INTO public.branches (
        id,
        tenant_id,
        name,
        code,
        slug,
        address,
        city,
        country,
        is_default,
        is_active,
        order_enabled,
        opening_hours_json
    )
    VALUES (
        'a5010000-0000-4000-8000-000000000001'::uuid,
        v_tenant_id,
        'Ashesi University',
        'ASHESI',
        'ashesi-university',
        'Ashesi University campus',
        'Berekuso',
        'Ghana',
        true,
        true,
        true,
        '{}'::jsonb
    )
    ON CONFLICT (tenant_id, code) DO UPDATE
    SET
        name = EXCLUDED.name,
        slug = EXCLUDED.slug,
        address = COALESCE(public.branches.address, EXCLUDED.address),
        city = COALESCE(public.branches.city, EXCLUDED.city),
        is_default = true,
        is_active = true,
        order_enabled = true,
        updated_at = now();

    INSERT INTO public.branches (
        id,
        tenant_id,
        name,
        code,
        slug,
        address,
        city,
        country,
        is_default,
        is_active,
        order_enabled,
        opening_hours_json
    )
    VALUES (
        'abe10000-0000-4000-8000-000000000002'::uuid,
        v_tenant_id,
        'Abelemkpe',
        'ABELEMKPE',
        'abelemkpe',
        'Abelemkpe, Accra',
        'Accra',
        'Ghana',
        false,
        true,
        true,
        '{}'::jsonb
    )
    ON CONFLICT (tenant_id, code) DO UPDATE
    SET
        name = EXCLUDED.name,
        slug = EXCLUDED.slug,
        address = COALESCE(public.branches.address, EXCLUDED.address),
        city = COALESCE(public.branches.city, EXCLUDED.city),
        is_active = true,
        order_enabled = true,
        updated_at = now();

    UPDATE public.branches
    SET
        is_default = false,
        order_enabled = false,
        updated_at = now()
    WHERE tenant_id = v_tenant_id
      AND code = 'MAIN';
END $$;

CREATE UNIQUE INDEX IF NOT EXISTS uq_branches_tenant_slug
    ON public.branches(tenant_id, slug)
    WHERE slug IS NOT NULL;

CREATE OR REPLACE FUNCTION public.get_default_branch_id()
RETURNS UUID
LANGUAGE sql
STABLE
AS $$
    SELECT b.id
    FROM public.branches b
    JOIN public.tenants t ON t.id = b.tenant_id
    WHERE t.slug = 'default-tenant'
      AND b.code = 'ASHESI'
    ORDER BY b.created_at
    LIMIT 1
$$;

ALTER TABLE public.orders ADD COLUMN IF NOT EXISTS public_tracking_token TEXT;

UPDATE public.orders
SET public_tracking_token = encode(gen_random_bytes(24), 'hex')
WHERE public_tracking_token IS NULL;

ALTER TABLE public.orders
    ALTER COLUMN public_tracking_token
    SET DEFAULT encode(gen_random_bytes(24), 'hex');

CREATE UNIQUE INDEX IF NOT EXISTS uq_orders_public_tracking_token
    ON public.orders(public_tracking_token);

CREATE TABLE IF NOT EXISTS public.notification_events (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID REFERENCES public.tenants(id) ON DELETE SET NULL,
    branch_id UUID REFERENCES public.branches(id) ON DELETE SET NULL,
    order_id UUID NOT NULL REFERENCES public.orders(id) ON DELETE CASCADE,
    order_event_id UUID REFERENCES public.order_events(id) ON DELETE CASCADE,
    channel TEXT NOT NULL DEFAULT 'whatsapp',
    notification_type TEXT NOT NULL,
    recipient TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'pending',
    attempt_count INTEGER NOT NULL DEFAULT 0,
    provider_message_id TEXT,
    payload_json JSONB NOT NULL DEFAULT '{}'::jsonb,
    error_message TEXT,
    last_attempt_at TIMESTAMPTZ,
    sent_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT notification_events_status_check
        CHECK (status IN ('pending', 'sent', 'failed', 'delivered', 'read'))
);

CREATE UNIQUE INDEX IF NOT EXISTS uq_notification_events_order_event_type
    ON public.notification_events(order_event_id, channel, notification_type)
    WHERE order_event_id IS NOT NULL;

CREATE INDEX IF NOT EXISTS idx_notification_events_pending
    ON public.notification_events(status, created_at);

ALTER TABLE public.notification_events ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS "service_role_notification_events"
    ON public.notification_events;
CREATE POLICY "service_role_notification_events"
ON public.notification_events
FOR ALL
USING (auth.role() = 'service_role')
WITH CHECK (auth.role() = 'service_role');
