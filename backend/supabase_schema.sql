-- ============================================================
-- WhatsApp Food Ordering System — Supabase Schema
-- Run this in your Supabase SQL editor
-- ============================================================

-- Orders table
CREATE TABLE IF NOT EXISTS orders (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    customer_phone TEXT NOT NULL,
    customer_name TEXT,
    delivery_address TEXT NOT NULL,
    items JSONB NOT NULL DEFAULT '[]',
    total_amount NUMERIC(10, 2) NOT NULL DEFAULT 0,
    payment_method TEXT NOT NULL DEFAULT 'cash'
        CHECK (payment_method IN ('momo', 'cash')),
    status TEXT NOT NULL DEFAULT 'pending'
        CHECK (status IN ('pending','confirmed','preparing','ready','delivered','cancelled')),
    branch_id TEXT,
    notes TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Customers table — for returning customer memory
CREATE TABLE IF NOT EXISTS customers (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    phone TEXT UNIQUE NOT NULL,
    name TEXT,
    order_count INTEGER NOT NULL DEFAULT 0,
    first_seen TIMESTAMPTZ NOT NULL DEFAULT now(),
    last_seen TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Menu items table
CREATE TABLE IF NOT EXISTS menu_items (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    description TEXT,
    price NUMERIC(10, 2) NOT NULL,
    image_url TEXT,
    category TEXT NOT NULL,
    popular BOOLEAN DEFAULT false,
    spicy BOOLEAN DEFAULT false,
    active BOOLEAN DEFAULT true,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Auto-update updated_at on orders
CREATE OR REPLACE FUNCTION update_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = now();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS orders_updated_at ON orders;
CREATE TRIGGER orders_updated_at
    BEFORE UPDATE ON orders
    FOR EACH ROW EXECUTE FUNCTION update_updated_at();

-- Indexes
CREATE INDEX IF NOT EXISTS idx_orders_customer_phone ON orders(customer_phone);
CREATE INDEX IF NOT EXISTS idx_orders_status ON orders(status);
CREATE INDEX IF NOT EXISTS idx_orders_created_at ON orders(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_orders_branch_id ON orders(branch_id);
CREATE INDEX IF NOT EXISTS idx_customers_phone ON customers(phone);
CREATE INDEX IF NOT EXISTS idx_menu_items_category ON menu_items(category);
CREATE INDEX IF NOT EXISTS idx_menu_items_active ON menu_items(active);

-- Row Level Security
ALTER TABLE orders ENABLE ROW LEVEL SECURITY;
ALTER TABLE customers ENABLE ROW LEVEL SECURITY;
ALTER TABLE menu_items ENABLE ROW LEVEL SECURITY;

-- Service role full access
DROP POLICY IF EXISTS "service_role_orders" ON orders;
CREATE POLICY "service_role_orders" ON orders FOR ALL USING (auth.role() = 'service_role');

DROP POLICY IF EXISTS "service_role_customers" ON customers;
CREATE POLICY "service_role_customers" ON customers FOR ALL USING (auth.role() = 'service_role');

DROP POLICY IF EXISTS "service_role_menu" ON menu_items;
CREATE POLICY "service_role_menu" ON menu_items FOR ALL USING (auth.role() = 'service_role');

-- Public read on menu items
DROP POLICY IF EXISTS "public_read_menu" ON menu_items;
CREATE POLICY "public_read_menu" ON menu_items FOR SELECT USING (active = true);
