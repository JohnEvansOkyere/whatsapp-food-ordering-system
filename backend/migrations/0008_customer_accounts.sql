-- 0008_customer_accounts.sql
-- Customer accounts with phone-OTP verification.
--
-- Customers previously checked out as guests, identified only by the phone
-- number typed at checkout. They now register once (username + password +
-- phone), verify the phone by OTP, and that verified number becomes the
-- authoritative destination for order SMS.
--
-- Additive and idempotent: existing guest orders keep working because
-- orders.customer_id stays nullable.

-- ---------------------------------------------------------------------------
-- 1. Auth columns on the existing customers table
-- ---------------------------------------------------------------------------

ALTER TABLE public.customers ADD COLUMN IF NOT EXISTS username TEXT;
ALTER TABLE public.customers ADD COLUMN IF NOT EXISTS password_hash TEXT;
ALTER TABLE public.customers ADD COLUMN IF NOT EXISTS phone_verified BOOLEAN NOT NULL DEFAULT false;
ALTER TABLE public.customers ADD COLUMN IF NOT EXISTS phone_verified_at TIMESTAMPTZ;
ALTER TABLE public.customers ADD COLUMN IF NOT EXISTS created_at TIMESTAMPTZ NOT NULL DEFAULT now();
ALTER TABLE public.customers ADD COLUMN IF NOT EXISTS updated_at TIMESTAMPTZ NOT NULL DEFAULT now();

-- Usernames are stored lower-cased by the application; enforce uniqueness only
-- across rows that actually have one so legacy guest rows are unaffected.
CREATE UNIQUE INDEX IF NOT EXISTS idx_customers_username
    ON public.customers(username)
    WHERE username IS NOT NULL;

-- ---------------------------------------------------------------------------
-- 2. One-time passcodes
-- ---------------------------------------------------------------------------
-- Codes are stored hashed, never in clear text. A row is consumed by setting
-- consumed_at; expired and consumed rows are safe to purge.

CREATE TABLE IF NOT EXISTS public.otp_codes (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    phone TEXT NOT NULL,
    code_hash TEXT NOT NULL,
    purpose TEXT NOT NULL DEFAULT 'phone_verification',
    attempt_count INTEGER NOT NULL DEFAULT 0,
    consumed_at TIMESTAMPTZ,
    expires_at TIMESTAMPTZ NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

ALTER TABLE public.otp_codes DROP CONSTRAINT IF EXISTS otp_codes_purpose_check;
ALTER TABLE public.otp_codes ADD CONSTRAINT otp_codes_purpose_check
    CHECK (purpose IN ('phone_verification', 'password_reset', 'login'));

CREATE INDEX IF NOT EXISTS idx_otp_codes_phone_purpose
    ON public.otp_codes(phone, purpose, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_otp_codes_expires_at
    ON public.otp_codes(expires_at);

-- ---------------------------------------------------------------------------
-- 3. Link orders to a registered customer
-- ---------------------------------------------------------------------------
-- Nullable so historical guest orders remain valid.

ALTER TABLE public.orders ADD COLUMN IF NOT EXISTS customer_id UUID;

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint WHERE conname = 'orders_customer_id_fkey'
    ) THEN
        ALTER TABLE public.orders
            ADD CONSTRAINT orders_customer_id_fkey
            FOREIGN KEY (customer_id) REFERENCES public.customers(id)
            ON DELETE SET NULL;
    END IF;
END $$;

CREATE INDEX IF NOT EXISTS idx_orders_customer_id ON public.orders(customer_id);

-- ---------------------------------------------------------------------------
-- 4. Row level security
-- ---------------------------------------------------------------------------
-- OTP hashes must never be reachable with the anon key.

ALTER TABLE public.otp_codes ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS "service_role_otp_codes" ON public.otp_codes;
CREATE POLICY "service_role_otp_codes"
ON public.otp_codes
FOR ALL
USING (auth.role() = 'service_role')
WITH CHECK (auth.role() = 'service_role');

-- ---------------------------------------------------------------------------
-- 5. updated_at maintenance
-- ---------------------------------------------------------------------------

DROP TRIGGER IF EXISTS customers_set_updated_at ON public.customers;
CREATE TRIGGER customers_set_updated_at
    BEFORE UPDATE ON public.customers
    FOR EACH ROW
    EXECUTE FUNCTION public.update_updated_at();
