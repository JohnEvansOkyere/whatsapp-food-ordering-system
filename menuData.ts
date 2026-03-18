export interface MenuItem {
  id: string
  name: string
  description: string
  price: number // in GHS
  image: string
  category: string
  popular?: boolean
  spicy?: boolean
}

export interface Category {
  id: string
  name: string
  emoji: string
}

export const RESTAURANT = {
  name: 'Accra Eats',
  tagline: 'Real Ghanaian Flavours, Delivered Fast',
  whatsapp: process.env.NEXT_PUBLIC_RESTAURANT_WHATSAPP || '233200000000',
  address: 'Osu, Accra',
  hours: 'Mon–Sun: 10am – 10pm',
  currency: 'GHS',
}

export const CATEGORIES: Category[] = [
  { id: 'all', name: 'All', emoji: '🍽️' },
  { id: 'rice', name: 'Rice Dishes', emoji: '🍚' },
  { id: 'chicken', name: 'Chicken', emoji: '🍗' },
  { id: 'pizza', name: 'Pizza', emoji: '🍕' },
  { id: 'sides', name: 'Sides', emoji: '🍟' },
  { id: 'drinks', name: 'Drinks', emoji: '🥤' },
]

export const MENU_ITEMS: MenuItem[] = [
  // Rice Dishes
  {
    id: 'jollof-chicken',
    name: 'Jollof Rice + Chicken',
    description: 'Smoky Ghanaian jollof cooked in fresh tomato base, served with crispy fried chicken and coleslaw.',
    price: 45,
    image: 'https://images.unsplash.com/photo-1604329760661-e71dc83f8f26?w=600&q=80',
    category: 'rice',
    popular: true,
    spicy: true,
  },
  {
    id: 'fried-rice-chicken',
    name: 'Fried Rice + Chicken',
    description: 'Fluffy fried rice with mixed vegetables, egg, and seasoned fried chicken.',
    price: 45,
    image: 'https://images.unsplash.com/photo-1603133872878-684f208fb84b?w=600&q=80',
    category: 'rice',
    popular: true,
  },
  {
    id: 'waakye',
    name: 'Waakye Special',
    description: 'Classic waakye with spaghetti, egg, stew, and your choice of meat. The full Ghanaian experience.',
    price: 40,
    image: 'https://images.unsplash.com/photo-1567620905732-2d1ec7ab7445?w=600&q=80',
    category: 'rice',
    popular: true,
    spicy: true,
  },
  {
    id: 'jollof-beef',
    name: 'Jollof Rice + Beef',
    description: 'Our signature smoky jollof with tender stewed beef and fresh salad.',
    price: 42,
    image: 'https://images.unsplash.com/photo-1512058564366-18510be2db19?w=600&q=80',
    category: 'rice',
  },

  // Chicken
  {
    id: 'grilled-chicken',
    name: 'Grilled Chicken (2 pcs)',
    description: 'Marinated in local spices, slow-grilled to perfection. Served with chips and pepper sauce.',
    price: 55,
    image: 'https://images.unsplash.com/photo-1598103442097-8b74394b95c4?w=600&q=80',
    category: 'chicken',
    popular: true,
  },
  {
    id: 'fried-chicken',
    name: 'Fried Chicken (3 pcs)',
    description: 'Golden crispy fried chicken with our house seasoning. Comes with coleslaw.',
    price: 50,
    image: 'https://images.unsplash.com/photo-1626082927389-6cd097cdc6ec?w=600&q=80',
    category: 'chicken',
  },
  {
    id: 'spicy-wings',
    name: 'Spicy Wings (6 pcs)',
    description: 'Fiery hot wings tossed in our signature pepper sauce. Not for the faint-hearted.',
    price: 48,
    image: 'https://images.unsplash.com/photo-1567620832903-9fc6debc209f?w=600&q=80',
    category: 'chicken',
    spicy: true,
  },

  // Pizza
  {
    id: 'pepperoni-pizza',
    name: 'Pepperoni Pizza',
    description: 'Classic pepperoni on rich tomato sauce with melted mozzarella. 10-inch.',
    price: 80,
    image: 'https://images.unsplash.com/photo-1628840042765-356cda07504e?w=600&q=80',
    category: 'pizza',
  },
  {
    id: 'chicken-pizza',
    name: 'BBQ Chicken Pizza',
    description: 'Smoky BBQ base, grilled chicken, red onions, and mozzarella. 10-inch.',
    price: 85,
    image: 'https://images.unsplash.com/photo-1565299624946-b28f40a0ae38?w=600&q=80',
    category: 'pizza',
    popular: true,
  },

  // Sides
  {
    id: 'chips',
    name: 'Chips (Large)',
    description: 'Crispy golden chips seasoned with our house spice blend.',
    price: 20,
    image: 'https://images.unsplash.com/photo-1573080496219-bb080dd4f877?w=600&q=80',
    category: 'sides',
  },
  {
    id: 'coleslaw',
    name: 'Coleslaw',
    description: 'Fresh creamy coleslaw made daily.',
    price: 12,
    image: 'https://images.unsplash.com/photo-1625944525533-473f1a3d54e7?w=600&q=80',
    category: 'sides',
  },
  {
    id: 'plantain',
    name: 'Fried Plantain',
    description: 'Sweet ripe plantain, perfectly fried. A Ghanaian classic.',
    price: 18,
    image: 'https://images.unsplash.com/photo-1604329760661-e71dc83f8f26?w=600&q=80',
    category: 'sides',
  },

  // Drinks
  {
    id: 'sobolo',
    name: 'Sobolo (Zobo)',
    description: 'Chilled hibiscus drink with ginger and spices. Refreshing and local.',
    price: 12,
    image: 'https://images.unsplash.com/photo-1563227812-0ea4c22e6cc8?w=600&q=80',
    category: 'drinks',
  },
  {
    id: 'malt',
    name: 'Malta Guinness',
    description: 'The classic Ghanaian celebration drink. Cold and sweet.',
    price: 10,
    image: 'https://images.unsplash.com/photo-1622483767028-3f66f32aef97?w=600&q=80',
    category: 'drinks',
  },
  {
    id: 'water',
    name: 'Voltic Water (1.5L)',
    description: 'Ice cold Voltic mineral water.',
    price: 8,
    image: 'https://images.unsplash.com/photo-1548839140-29a749e1cf4d?w=600&q=80',
    category: 'drinks',
  },
]
