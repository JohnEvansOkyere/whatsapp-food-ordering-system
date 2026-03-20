import { useState, useMemo } from 'react'
import Head from 'next/head'
import Header from '@/components/Header'
import CategoryNav from '@/components/CategoryNav'
import FoodCard from '@/components/FoodCard'
import CartDrawer from '@/components/CartDrawer'
import FloatingCart from '@/components/FloatingCart'
import { useCart } from '@/hooks/useCart'
import { MENU_ITEMS, RESTAURANT } from '../lib/menuData'

export default function MenuPage() {
  const [activeCategory, setActiveCategory] = useState('all')
  const cart = useCart()

  const filteredItems = useMemo(() => {
    if (activeCategory === 'all') return MENU_ITEMS
    return MENU_ITEMS.filter(item => item.category === activeCategory)
  }, [activeCategory])

  // Group by category for "All" view
  const groupedItems = useMemo(() => {
    if (activeCategory !== 'all') return null
    const groups: Record<string, typeof MENU_ITEMS> = {}
    MENU_ITEMS.forEach(item => {
      if (!groups[item.category]) groups[item.category] = []
      groups[item.category].push(item)
    })
    return groups
  }, [activeCategory])

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
        <title>{RESTAURANT.name} — Order on WhatsApp</title>
        <meta name="description" content={RESTAURANT.tagline} />
        <meta name="viewport" content="width=device-width, initial-scale=1, maximum-scale=1" />
        <link rel="icon" href="/favicon.ico" />
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

        {/* Menu Grid */}
        <main className="px-4 pt-4 pb-32">
          {activeCategory === 'all' && groupedItems ? (
            // Grouped view
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
            // Filtered view
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

        {/* Floating cart bar */}
        <FloatingCart
          totalItems={cart.totalItems}
          totalPrice={cart.totalPrice}
          onOpen={() => cart.setIsOpen(true)}
        />

        {/* Cart drawer */}
        <CartDrawer
          isOpen={cart.isOpen}
          items={cart.items}
          totalItems={cart.totalItems}
          totalPrice={cart.totalPrice}
          onClose={() => cart.setIsOpen(false)}
          onAdd={cart.addItem}
          onRemove={cart.removeItem}
          buildWhatsAppMessage={cart.buildWhatsAppMessage}
        />
      </div>
    </>
  )
}
