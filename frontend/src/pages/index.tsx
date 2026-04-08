import { useEffect, useMemo, useState } from 'react'
import Head from 'next/head'
import Header from '@/components/Header'
import CategoryNav from '@/components/CategoryNav'
import FoodCard from '@/components/FoodCard'
import CartDrawer from '@/components/CartDrawer'
import FloatingCart from '@/components/FloatingCart'
import { useCart } from '@/hooks/useCart'
import { MENU_ITEMS, MenuItem, RESTAURANT } from '@/lib/menuData'

interface ApiMenuItem {
  id: string
  name: string
  description: string
  price: number
  image_url?: string | null
  category: string
  popular?: boolean
  spicy?: boolean
}

const FALLBACK_MENU_BY_ID = new Map(MENU_ITEMS.map(item => [item.id, item]))

function toUiMenuItem(item: ApiMenuItem): MenuItem {
  const fallback = FALLBACK_MENU_BY_ID.get(item.id)

  return {
    id: item.id,
    name: item.name,
    description: item.description,
    price: Number(item.price),
    image: item.image_url || fallback?.image || '',
    category: item.category,
    popular: item.popular ?? fallback?.popular,
    spicy: item.spicy ?? fallback?.spicy,
  }
}

export default function MenuPage() {
  const [activeCategory, setActiveCategory] = useState('all')
  const [menuItems, setMenuItems] = useState<MenuItem[]>(MENU_ITEMS)
  const cart = useCart()

  useEffect(() => {
    let cancelled = false

    async function loadMenu() {
      try {
        const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'
        const res = await fetch(`${apiUrl}/menu/`)
        if (!res.ok) {
          throw new Error(`Menu request failed with status ${res.status}`)
        }

        const data = await res.json()
        if (!Array.isArray(data.items)) {
          throw new Error('Menu payload is invalid')
        }

        const nextItems = data.items
          .map((item: ApiMenuItem) => toUiMenuItem(item))
          .filter((item: MenuItem) => item.image)

        if (!cancelled && nextItems.length > 0) {
          setMenuItems(nextItems)
        }
      } catch (error) {
        console.error('Failed to load menu from API, using local fallback.', error)
      }
    }

    loadMenu()

    return () => {
      cancelled = true
    }
  }, [])

  const filteredItems = useMemo(() => {
    if (activeCategory === 'all') return menuItems
    return menuItems.filter(item => item.category === activeCategory)
  }, [activeCategory, menuItems])

  const groupedItems = useMemo(() => {
    if (activeCategory !== 'all') return null
    const groups: Record<string, MenuItem[]> = {}
    menuItems.forEach(item => {
      if (!groups[item.category]) groups[item.category] = []
      groups[item.category].push(item)
    })
    return groups
  }, [activeCategory, menuItems])

  const categoryLabels: Record<string, string> = {
    rice: '🍚 Rice Dishes',
    chicken: '🍗 Chicken',
    pizza: '🍕 Pizza',
    sides: '🍟 Sides',
    drinks: '🥤 Drinks',
  }

  return (
    <>
      <Head>
        <title>{RESTAURANT.name} — Order Online</title>
        <meta name="description" content={RESTAURANT.tagline} />
        <meta name="viewport" content="width=device-width, initial-scale=1, maximum-scale=1" />
      </Head>

      <div className="min-h-screen bg-brand-cream">
        <Header
          totalItems={cart.totalItems}
          onCartOpen={() => cart.setIsOpen(true)}
        />

        <CategoryNav
          active={activeCategory}
          onSelect={setActiveCategory}
        />

        <main className="px-4 pt-4 pb-32">
          {activeCategory === 'all' && groupedItems ? (
            Object.entries(groupedItems).map(([category, items]) => (
              <section key={category} className="mb-8">
                <h2
                  className="text-lg font-black text-brand-dark mb-3"
                  style={{ fontFamily: 'var(--font-display)' }}
                >
                  {categoryLabels[category] || category}
                </h2>
                <div className="grid grid-cols-2 gap-3">
                  {items.map(item => (
                    <FoodCard
                      key={item.id}
                      item={item}
                      quantity={cart.getQuantity(item.id)}
                      onAdd={() => cart.addItem(item)}
                      onRemove={() => cart.removeItem(item.id)}
                    />
                  ))}
                </div>
              </section>
            ))
          ) : (
            <div className="grid grid-cols-2 gap-3">
              {filteredItems.map(item => (
                <FoodCard
                  key={item.id}
                  item={item}
                  quantity={cart.getQuantity(item.id)}
                  onAdd={() => cart.addItem(item)}
                  onRemove={() => cart.removeItem(item.id)}
                />
              ))}
            </div>
          )}

          {filteredItems.length === 0 && (
            <div className="py-20 text-center">
              <div className="text-5xl mb-3">🍽️</div>
              <p className="text-gray-400 font-medium">No items in this category</p>
            </div>
          )}
        </main>

        <FloatingCart
          totalItems={cart.totalItems}
          totalPrice={cart.totalPrice}
          onOpen={() => cart.setIsOpen(true)}
        />

        <CartDrawer
          isOpen={cart.isOpen}
          items={cart.items}
          totalItems={cart.totalItems}
          totalPrice={cart.totalPrice}
          onClose={() => cart.setIsOpen(false)}
          onAdd={cart.addItem}
          onRemove={cart.removeItem}
          onClear={cart.clearCart}
        />
      </div>
    </>
  )
}
