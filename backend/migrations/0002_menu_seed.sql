-- ============================================================
-- 0002_menu_seed.sql
-- Baseline menu seed
-- Safe to rerun; uses upsert behavior
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
        'Smoky Ghanaian jollof cooked in fresh tomato base, served with crispy fried chicken and coleslaw.',
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
        'Fluffy fried rice with mixed vegetables, egg, and seasoned fried chicken.',
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
        'Fluffy fried rice with mixed vegetables, egg, and tender stewed beef.',
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
        'Classic waakye with spaghetti, egg, stew, and your choice of meat. The full Ghanaian experience.',
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
        'Marinated in local spices, slow-grilled to perfection. Served with chips and pepper sauce.',
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
        'Golden crispy fried chicken with our house seasoning. Comes with coleslaw.',
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
        'Fiery hot wings tossed in our signature pepper sauce. Not for the faint-hearted.',
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
        'Classic pepperoni on rich tomato sauce with melted mozzarella. 10-inch.',
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
        'Smoky BBQ base, grilled chicken, red onions, and mozzarella. 10-inch.',
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
        'Chilled hibiscus drink with ginger and spices. Refreshing and local.',
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

