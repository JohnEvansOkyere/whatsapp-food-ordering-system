-- ============================================================
-- 0005_menu_availability.sql
-- Add sold-out tracking for menu items
-- ============================================================

ALTER TABLE public.menu_items
    ADD COLUMN IF NOT EXISTS sold_out BOOLEAN NOT NULL DEFAULT false;

UPDATE public.menu_items
SET sold_out = false
WHERE sold_out IS NULL;

DROP POLICY IF EXISTS "public_read_menu" ON public.menu_items;
CREATE POLICY "public_read_menu"
ON public.menu_items
FOR SELECT
USING (active = true AND sold_out = false);
