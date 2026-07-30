-- ============================================================
-- 0003_multitenant_foundation.sql
-- Add multitenant and branch-aware foundation tables
-- Keeps compatibility with the current single-restaurant app
-- ============================================================

CREATE EXTENSION IF NOT EXISTS pgcrypto;

CREATE TABLE IF NOT EXISTS public.tenants (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name TEXT NOT NULL,
    slug TEXT NOT NULL UNIQUE,
    status TEXT NOT NULL DEFAULT 'active',
    subscription_plan TEXT NOT NULL DEFAULT 'starter',
    default_currency TEXT NOT NULL DEFAULT 'GHS',
    default_timezone TEXT NOT NULL DEFAULT 'Africa/Accra',
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT tenants_status_check CHECK (status IN ('active', 'inactive', 'suspended'))
);

CREATE TABLE IF NOT EXISTS public.branches (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL REFERENCES public.tenants(id) ON DELETE CASCADE,
    name TEXT NOT NULL,
    code TEXT NOT NULL,
    phone TEXT,
    address TEXT,
    city TEXT,
    country TEXT DEFAULT 'Ghana',
    is_default BOOLEAN NOT NULL DEFAULT false,
    is_active BOOLEAN NOT NULL DEFAULT true,
    opening_hours_json JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT branches_code_unique UNIQUE (tenant_id, code)
);

CREATE TABLE IF NOT EXISTS public.users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID REFERENCES public.tenants(id) ON DELETE CASCADE,
    auth_user_id UUID UNIQUE,
    email TEXT,
    full_name TEXT,
    phone TEXT,
    status TEXT NOT NULL DEFAULT 'active',
    last_login_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT users_status_check CHECK (status IN ('active', 'invited', 'disabled'))
);

CREATE TABLE IF NOT EXISTS public.user_branch_memberships (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL REFERENCES public.tenants(id) ON DELETE CASCADE,
    user_id UUID NOT NULL REFERENCES public.users(id) ON DELETE CASCADE,
    branch_id UUID NOT NULL REFERENCES public.branches(id) ON DELETE CASCADE,
    role_code TEXT NOT NULL,
    is_primary BOOLEAN NOT NULL DEFAULT false,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT user_branch_memberships_role_check
        CHECK (role_code IN (
            'platform_admin',
            'tenant_owner',
            'manager',
            'cashier',
            'kitchen',
            'dispatch',
            'support',
            'viewer'
        )),
    CONSTRAINT user_branch_memberships_unique UNIQUE (user_id, branch_id, role_code)
);

CREATE INDEX IF NOT EXISTS idx_branches_tenant_id ON public.branches(tenant_id);
CREATE INDEX IF NOT EXISTS idx_users_tenant_id ON public.users(tenant_id);
CREATE INDEX IF NOT EXISTS idx_user_branch_memberships_tenant_user_branch
    ON public.user_branch_memberships(tenant_id, user_id, branch_id);

DROP TRIGGER IF EXISTS tenants_updated_at ON public.tenants;
CREATE TRIGGER tenants_updated_at
    BEFORE UPDATE ON public.tenants
    FOR EACH ROW EXECUTE FUNCTION public.update_updated_at();

DROP TRIGGER IF EXISTS branches_updated_at ON public.branches;
CREATE TRIGGER branches_updated_at
    BEFORE UPDATE ON public.branches
    FOR EACH ROW EXECUTE FUNCTION public.update_updated_at();

DROP TRIGGER IF EXISTS users_updated_at ON public.users;
CREATE TRIGGER users_updated_at
    BEFORE UPDATE ON public.users
    FOR EACH ROW EXECUTE FUNCTION public.update_updated_at();

DROP TRIGGER IF EXISTS user_branch_memberships_updated_at ON public.user_branch_memberships;
CREATE TRIGGER user_branch_memberships_updated_at
    BEFORE UPDATE ON public.user_branch_memberships
    FOR EACH ROW EXECUTE FUNCTION public.update_updated_at();

DO $$
BEGIN
    IF EXISTS (
        SELECT 1
        FROM information_schema.columns
        WHERE table_schema = 'public'
          AND table_name = 'orders'
          AND column_name = 'branch_id'
          AND data_type = 'text'
    ) AND NOT EXISTS (
        SELECT 1
        FROM information_schema.columns
        WHERE table_schema = 'public'
          AND table_name = 'orders'
          AND column_name = 'legacy_branch_ref'
    ) THEN
        ALTER TABLE public.orders RENAME COLUMN branch_id TO legacy_branch_ref;
    END IF;
END $$;

ALTER TABLE public.orders ADD COLUMN IF NOT EXISTS tenant_id UUID;
ALTER TABLE public.orders ADD COLUMN IF NOT EXISTS branch_id UUID;
ALTER TABLE public.customers ADD COLUMN IF NOT EXISTS tenant_id UUID;
ALTER TABLE public.customers ADD COLUMN IF NOT EXISTS default_branch_id UUID;
ALTER TABLE public.menu_items ADD COLUMN IF NOT EXISTS tenant_id UUID;
ALTER TABLE public.menu_items ADD COLUMN IF NOT EXISTS branch_id UUID;

DO $$
DECLARE
    v_tenant_id UUID;
    v_branch_id UUID;
BEGIN
    INSERT INTO public.tenants (name, slug, status, subscription_plan, default_currency, default_timezone)
    VALUES ('Default Tenant', 'default-tenant', 'active', 'starter', 'GHS', 'Africa/Accra')
    ON CONFLICT (slug) DO UPDATE
    SET
        name = EXCLUDED.name,
        updated_at = now()
    RETURNING id INTO v_tenant_id;

    IF v_tenant_id IS NULL THEN
        SELECT id INTO v_tenant_id
        FROM public.tenants
        WHERE slug = 'default-tenant'
        LIMIT 1;
    END IF;

    INSERT INTO public.branches (
        tenant_id,
        name,
        code,
        city,
        country,
        is_default,
        is_active,
        opening_hours_json
    )
    VALUES (
        v_tenant_id,
        'Main Branch',
        'MAIN',
        'Accra',
        'Ghana',
        true,
        true,
        '{}'::jsonb
    )
    ON CONFLICT (tenant_id, code) DO UPDATE
    SET
        name = EXCLUDED.name,
        is_default = true,
        is_active = true,
        updated_at = now()
    RETURNING id INTO v_branch_id;

    IF v_branch_id IS NULL THEN
        SELECT id INTO v_branch_id
        FROM public.branches
        WHERE tenant_id = v_tenant_id
          AND code = 'MAIN'
        LIMIT 1;
    END IF;

    UPDATE public.orders
    SET
        tenant_id = COALESCE(tenant_id, v_tenant_id),
        branch_id = COALESCE(branch_id, v_branch_id)
    WHERE tenant_id IS NULL
       OR branch_id IS NULL;

    UPDATE public.customers
    SET
        tenant_id = COALESCE(tenant_id, v_tenant_id),
        default_branch_id = COALESCE(default_branch_id, v_branch_id)
    WHERE tenant_id IS NULL
       OR default_branch_id IS NULL;

    UPDATE public.menu_items
    SET tenant_id = COALESCE(tenant_id, v_tenant_id)
    WHERE tenant_id IS NULL;
END $$;

CREATE OR REPLACE FUNCTION public.get_default_tenant_id()
RETURNS UUID
LANGUAGE sql
STABLE
AS $$
    SELECT id
    FROM public.tenants
    WHERE slug = 'default-tenant'
    ORDER BY created_at
    LIMIT 1
$$;

CREATE OR REPLACE FUNCTION public.get_default_branch_id()
RETURNS UUID
LANGUAGE sql
STABLE
AS $$
    SELECT b.id
    FROM public.branches b
    JOIN public.tenants t ON t.id = b.tenant_id
    WHERE t.slug = 'default-tenant'
      AND b.code = 'MAIN'
    ORDER BY b.created_at
    LIMIT 1
$$;

ALTER TABLE public.orders ALTER COLUMN tenant_id SET DEFAULT public.get_default_tenant_id();
ALTER TABLE public.orders ALTER COLUMN branch_id SET DEFAULT public.get_default_branch_id();
ALTER TABLE public.customers ALTER COLUMN tenant_id SET DEFAULT public.get_default_tenant_id();
ALTER TABLE public.customers ALTER COLUMN default_branch_id SET DEFAULT public.get_default_branch_id();
ALTER TABLE public.menu_items ALTER COLUMN tenant_id SET DEFAULT public.get_default_tenant_id();

CREATE INDEX IF NOT EXISTS idx_orders_tenant_id ON public.orders(tenant_id);
CREATE INDEX IF NOT EXISTS idx_orders_tenant_branch_created_at
    ON public.orders(tenant_id, branch_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_customers_tenant_id ON public.customers(tenant_id);
CREATE INDEX IF NOT EXISTS idx_menu_items_tenant_branch_active
    ON public.menu_items(tenant_id, branch_id, active);

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint
        WHERE conname = 'orders_tenant_id_fkey'
    ) THEN
        ALTER TABLE public.orders
            ADD CONSTRAINT orders_tenant_id_fkey
            FOREIGN KEY (tenant_id) REFERENCES public.tenants(id) ON DELETE SET NULL;
    END IF;

    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint
        WHERE conname = 'orders_branch_id_fkey'
    ) THEN
        ALTER TABLE public.orders
            ADD CONSTRAINT orders_branch_id_fkey
            FOREIGN KEY (branch_id) REFERENCES public.branches(id) ON DELETE SET NULL;
    END IF;

    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint
        WHERE conname = 'customers_tenant_id_fkey'
    ) THEN
        ALTER TABLE public.customers
            ADD CONSTRAINT customers_tenant_id_fkey
            FOREIGN KEY (tenant_id) REFERENCES public.tenants(id) ON DELETE SET NULL;
    END IF;

    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint
        WHERE conname = 'customers_default_branch_id_fkey'
    ) THEN
        ALTER TABLE public.customers
            ADD CONSTRAINT customers_default_branch_id_fkey
            FOREIGN KEY (default_branch_id) REFERENCES public.branches(id) ON DELETE SET NULL;
    END IF;

    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint
        WHERE conname = 'menu_items_tenant_id_fkey'
    ) THEN
        ALTER TABLE public.menu_items
            ADD CONSTRAINT menu_items_tenant_id_fkey
            FOREIGN KEY (tenant_id) REFERENCES public.tenants(id) ON DELETE SET NULL;
    END IF;

    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint
        WHERE conname = 'menu_items_branch_id_fkey'
    ) THEN
        ALTER TABLE public.menu_items
            ADD CONSTRAINT menu_items_branch_id_fkey
            FOREIGN KEY (branch_id) REFERENCES public.branches(id) ON DELETE SET NULL;
    END IF;
END $$;

ALTER TABLE public.tenants ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.branches ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.users ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.user_branch_memberships ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS "service_role_tenants" ON public.tenants;
CREATE POLICY "service_role_tenants"
ON public.tenants
FOR ALL
USING (auth.role() = 'service_role')
WITH CHECK (auth.role() = 'service_role');

DROP POLICY IF EXISTS "service_role_branches" ON public.branches;
CREATE POLICY "service_role_branches"
ON public.branches
FOR ALL
USING (auth.role() = 'service_role')
WITH CHECK (auth.role() = 'service_role');

DROP POLICY IF EXISTS "service_role_users" ON public.users;
CREATE POLICY "service_role_users"
ON public.users
FOR ALL
USING (auth.role() = 'service_role')
WITH CHECK (auth.role() = 'service_role');

DROP POLICY IF EXISTS "service_role_user_branch_memberships" ON public.user_branch_memberships;
CREATE POLICY "service_role_user_branch_memberships"
ON public.user_branch_memberships
FOR ALL
USING (auth.role() = 'service_role')
WITH CHECK (auth.role() = 'service_role');

