-- 0009_delivery_location.sql
-- Map coordinates for the delivery address.
--
-- Checkout used to ask for a free-text address plus a separate landmark note.
-- Customers now pick one address from Google Places autocomplete, or drop a pin
-- with "Use my location", so the order can carry the exact drop point a rider
-- can navigate to.
--
-- Additive and idempotent. Columns stay nullable: an address the customer typed
-- without a map match is still a valid order, it simply has no coordinates.

ALTER TABLE public.orders ADD COLUMN IF NOT EXISTS delivery_latitude NUMERIC(10, 7);
ALTER TABLE public.orders ADD COLUMN IF NOT EXISTS delivery_longitude NUMERIC(10, 7);

-- Google Places identifier for the chosen address, kept so a repeat order can
-- be matched to the same place even if the formatted label changes.
ALTER TABLE public.orders ADD COLUMN IF NOT EXISTS delivery_place_id TEXT;

-- Operational lookup: "which pinned orders are open right now".
CREATE INDEX IF NOT EXISTS idx_orders_delivery_point
    ON public.orders(delivery_latitude, delivery_longitude)
    WHERE delivery_latitude IS NOT NULL;
