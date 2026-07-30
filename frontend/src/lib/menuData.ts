export interface MenuItem {
  id: string
  name: string
  description: string
  price: number // in GHS
  image: string
  category: string
  popular?: boolean
  spicy?: boolean
  soldOut?: boolean
  optionGroups?: MenuOptionGroup[]
}

export interface MenuOption {
  id: string
  name: string
  price: number
}

export interface MenuOptionGroup {
  id: string
  name: string
  type: 'single' | 'multiple'
  maxSelections?: number
  options: MenuOption[]
}

export interface SelectedOption {
  groupId: string
  optionId: string
  name: string
  price: number
}

export interface Category {
  id: string
  name: string
  emoji: string
}

export const RESTAURANT = {
  name: process.env.NEXT_PUBLIC_RESTAURANT_NAME || 'Accra Eats',
  tagline: 'Real Ghanaian Flavours, Delivered Fast',
  whatsapp: process.env.NEXT_PUBLIC_RESTAURANT_WHATSAPP || '',
  address: 'Ashesi University · Abelemkpe',
  hours: 'Hours configured per branch',
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
    image: '/images/menu/jollof-fried-chicken.png',
    category: 'rice',
    popular: true,
    spicy: true,
    optionGroups: [
      {
        id: 'extras',
        name: 'Add something extra',
        type: 'multiple',
        maxSelections: 2,
        options: [
          { id: 'plantain', name: 'Fried plantain', price: 8 },
          { id: 'coleslaw', name: 'Extra coleslaw', price: 5 },
        ],
      },
    ],
  },
  {
    id: 'fried-rice-chicken',
    name: 'Fried Rice + Chicken',
    description: 'Fluffy fried rice with mixed vegetables, egg, and seasoned fried chicken.',
    price: 45,
    image: '/images/menu/fried-rice-grilled-chicken.png',
    category: 'rice',
    popular: true,
    optionGroups: [
      {
        id: 'extras',
        name: 'Add something extra',
        type: 'multiple',
        maxSelections: 2,
        options: [
          { id: 'plantain', name: 'Fried plantain', price: 8 },
          { id: 'coleslaw', name: 'Extra coleslaw', price: 5 },
        ],
      },
    ],
  },
  {
    id: 'fried-rice-beef',
    name: 'Fried Rice + Beef',
    description: 'Fluffy fried rice with mixed vegetables, egg, and tender stewed beef.',
    price: 42,
    image: '/images/menu/fried-rice-grilled-chicken.png',
    category: 'rice',
  },
  {
    id: 'waakye',
    name: 'Waakye Special',
    description: 'Classic waakye with spaghetti, egg, stew, and your choice of meat. The full Ghanaian experience.',
    price: 40,
    image: '/images/menu/waakye-special.png',
    category: 'rice',
    popular: true,
    spicy: true,
  },
  {
    id: 'jollof-beef',
    name: 'Jollof Rice + Beef',
    description: 'Our signature smoky jollof with tender stewed beef and fresh salad.',
    price: 42,
    image: '/images/menu/jollof-fried-chicken.png',
    category: 'rice',
  },

  // Chicken
  {
    id: 'grilled-chicken',
    name: 'Grilled Chicken (2 pcs)',
    description: 'Marinated in local spices, slow-grilled to perfection. Served with chips and pepper sauce.',
    price: 55,
    image: '/images/menu/grilled-chicken-fries.png',
    category: 'chicken',
    popular: true,
  },
  {
    id: 'fried-chicken',
    name: 'Fried Chicken (3 pcs)',
    description: 'Golden crispy fried chicken with our house seasoning. Comes with coleslaw.',
    price: 50,
    image: '/images/menu/jollof-fried-chicken.png',
    category: 'chicken',
  },
  {
    id: 'spicy-wings',
    name: 'Spicy Wings (6 pcs)',
    description: 'Fiery hot wings tossed in our signature pepper sauce. Not for the faint-hearted.',
    price: 48,
    image: '/images/menu/spicy-wings-fries.png',
    category: 'chicken',
    spicy: true,
  },

  // Pizza
  {
    id: 'pepperoni-pizza',
    name: 'Pepperoni Pizza',
    description: 'Classic pepperoni on rich tomato sauce with melted mozzarella. 10-inch.',
    price: 80,
    image: '/images/menu/bbq-chicken-pizza.png',
    category: 'pizza',
    optionGroups: [
      {
        id: 'size',
        name: 'Choose a size',
        type: 'single',
        options: [
          { id: 'regular', name: 'Regular 10-inch', price: 0 },
          { id: 'large', name: 'Large 12-inch', price: 25 },
        ],
      },
      {
        id: 'extras',
        name: 'Pizza extras',
        type: 'multiple',
        maxSelections: 2,
        options: [
          { id: 'cheese', name: 'Extra cheese', price: 12 },
          { id: 'chicken', name: 'Extra chicken', price: 15 },
        ],
      },
    ],
  },
  {
    id: 'chicken-pizza',
    name: 'BBQ Chicken Pizza',
    description: 'Smoky BBQ base, grilled chicken, red onions, and mozzarella. 10-inch.',
    price: 85,
    image: '/images/menu/bbq-chicken-pizza.png',
    category: 'pizza',
    popular: true,
    optionGroups: [
      {
        id: 'size',
        name: 'Choose a size',
        type: 'single',
        options: [
          { id: 'regular', name: 'Regular 10-inch', price: 0 },
          { id: 'large', name: 'Large 12-inch', price: 25 },
        ],
      },
      {
        id: 'extras',
        name: 'Pizza extras',
        type: 'multiple',
        maxSelections: 2,
        options: [
          { id: 'cheese', name: 'Extra cheese', price: 12 },
          { id: 'chicken', name: 'Extra chicken', price: 15 },
        ],
      },
    ],
  },

  // Sides
  {
    id: 'chips',
    name: 'Chips (Large)',
    description: 'Crispy golden chips seasoned with our house spice blend.',
    price: 20,
    image: '/images/menu/sides-platter.png',
    category: 'sides',
  },
  {
    id: 'coleslaw',
    name: 'Coleslaw',
    description: 'Fresh creamy coleslaw made daily.',
    price: 12,
    image: '/images/menu/sides-platter.png',
    category: 'sides',
  },
  {
    id: 'plantain',
    name: 'Fried Plantain',
    description: 'Sweet ripe plantain, perfectly fried. A Ghanaian classic.',
    price: 18,
    image: '/images/menu/sides-platter.png',
    category: 'sides',
  },

  // Drinks
  {
    id: 'sobolo',
    name: 'Sobolo (Zobo)',
    description: 'Chilled hibiscus drink with ginger and spices. Refreshing and local.',
    price: 12,
    image: '/images/menu/cold-drinks.png',
    category: 'drinks',
  },
  {
    id: 'malt',
    name: 'Malta Guinness',
    description: 'The classic Ghanaian celebration drink. Cold and sweet.',
    price: 10,
    image: '/images/menu/cold-drinks.png',
    category: 'drinks',
  },
  {
    id: 'water',
    name: 'Voltic Water (1.5L)',
    description: 'Ice cold Voltic mineral water.',
    price: 8,
    image: '/images/menu/cold-drinks.png',
    category: 'drinks',
  },
]
