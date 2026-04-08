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




 -- ============================================================
  -- MENU SEED
  -- ============================================================
  INSERT INTO public.menu_items (
      id,
      name,
      description,
      price,
      image_url,
      category,
      popular,
      spicy,
      active
  )
  VALUES
      (
          'jollof-chicken',
          'Jollof Rice + Chicken',
          'Smoky Ghanaian jollof cooked in fresh tomato base, served with crispy
  fried chicken and coleslaw.',
          45,

  'https://images.unsplash.com/photo-1604329760661-e71dc83f8f26?w=600&q=80',
          'rice',
          true,
          true,
          true
      ),
      (
          'fried-rice-chicken',
          'Fried Rice + Chicken',
          'Fluffy fried rice with mixed vegetables, egg, and seasoned fried
  chicken.',
          45,

  'https://images.unsplash.com/photo-1603133872878-684f208fb84b?w=600&q=80',
          'rice',
          true,
          false,
          true
      ),
      (
          'fried-rice-beef',
          'Fried Rice + Beef',
          'Fluffy fried rice with mixed vegetables, egg, and tender stewed
  beef.',
          42,

  'https://images.unsplash.com/photo-1603133872878-684f208fb84b?w=600&q=80',
          'rice',
          false,
          false,
          true
      ),
      (
          'waakye',
          'Waakye Special',
          'Classic waakye with spaghetti, egg, stew, and your choice of meat.
  The full Ghanaian experience.',
          40,

  'https://images.unsplash.com/photo-1567620905732-2d1ec7ab7445?w=600&q=80',
          'rice',
          true,
          true,
          true
      ),
      (
          'jollof-beef',
          'Jollof Rice + Beef',
          'Our signature smoky jollof with tender stewed beef and fresh salad.',
          42,

  'https://images.unsplash.com/photo-1512058564366-18510be2db19?w=600&q=80',
          'rice',
          false,
          false,
          true
      ),
      (
          'grilled-chicken',
          'Grilled Chicken (2 pcs)',
          'Marinated in local spices, slow-grilled to perfection. Served with
  chips and pepper sauce.',
          55,

  'https://images.unsplash.com/photo-1598103442097-8b74394b95c4?w=600&q=80',
          'chicken',
          true,
          false,
          true
      ),
      (
          'fried-chicken',
          'Fried Chicken (3 pcs)',
          'Golden crispy fried chicken with our house seasoning. Comes with
  coleslaw.',
          50,

  'https://images.unsplash.com/photo-1626082927389-6cd097cdc6ec?w=600&q=80',
          'chicken',
          false,
          false,
          true
      ),
      (
          'spicy-wings',
          'Spicy Wings (6 pcs)',
          'Fiery hot wings tossed in our signature pepper sauce. Not for the
  faint-hearted.',
          48,

  'https://images.unsplash.com/photo-1567620832903-9fc6debc209f?w=600&q=80',
          'chicken',
          false,
          true,
          true
      ),
      (
          'pepperoni-pizza',
          'Pepperoni Pizza',
          'Classic pepperoni on rich tomato sauce with melted mozzarella. 10-
  inch.',
          80,

  'https://images.unsplash.com/photo-1628840042765-356cda07504e?w=600&q=80',
          'pizza',
          false,
          false,
          true
      ),
      (
          'chicken-pizza',
          'BBQ Chicken Pizza',
          'Smoky BBQ base, grilled chicken, red onions, and mozzarella. 10-
  inch.',
          85,

  'https://images.unsplash.com/photo-1565299624946-b28f40a0ae38?w=600&q=80',
          'pizza',
          true,
          false,
          true
      ),
      (
          'chips',
          'Chips (Large)',
          'Crispy golden chips seasoned with our house spice blend.',
          20,

  'https://images.unsplash.com/photo-1573080496219-bb080dd4f877?w=600&q=80',
          'sides',
          false,
          false,
          true
      ),
      (
          'coleslaw',
          'Coleslaw',
          'Fresh creamy coleslaw made daily.',
          12,

  'https://images.unsplash.com/photo-1625944525533-473f1a3d54e7?w=600&q=80',
          'sides',
          false,
          false,
          true
      ),
      (
          'plantain',
          'Fried Plantain',
          'Sweet ripe plantain, perfectly fried. A Ghanaian classic.',
          18,

  'https://images.unsplash.com/photo-1604329760661-e71dc83f8f26?w=600&q=80',
          'sides',
          false,
          false,
          true
      ),
      (
          'sobolo',
          'Sobolo (Zobo)',
          'Chilled hibiscus drink with ginger and spices. Refreshing and
  local.',
          12,

  'https://images.unsplash.com/photo-1563227812-0ea4c22e6cc8?w=600&q=80',
          'drinks',
          false,
          false,
          true
      ),
      (
          'malt',
          'Malta Guinness',
          'The classic Ghanaian celebration drink. Cold and sweet.',
          10,

  'https://images.unsplash.com/photo-1622483767028-3f66f32aef97?w=600&q=80',
          'drinks',
          false,
          false,
          true
      ),
      (
          'water',
          'Voltic Water (1.5L)',
          'Ice cold Voltic mineral water.',
          8,

  'https://images.unsplash.com/photo-1548839140-29a749e1cf4d?w=600&q=80',
          'drinks',
          false,
          false,
          true
      )
  ON CONFLICT (id) DO UPDATE SET
      name = EXCLUDED.name,
      description = EXCLUDED.description,
      price = EXCLUDED.price,
      image_url = EXCLUDED.image_url,
      category = EXCLUDED.category,
      popular = EXCLUDED.popular,
      spicy = EXCLUDED.spicy,
      active = EXCLUDED.active;