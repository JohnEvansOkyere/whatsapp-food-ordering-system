import { useState, useCallback } from 'react'
import { MenuItem } from '../../lib/menuData'

export interface CartItem extends MenuItem {
  quantity: number
}

export function useCart() {
  const [items, setItems] = useState<CartItem[]>([])
  const [isOpen, setIsOpen] = useState(false)

  const addItem = useCallback((item: MenuItem) => {
    setItems(prev => {
      const existing = prev.find(i => i.id === item.id)
      if (existing) {
        return prev.map(i =>
          i.id === item.id ? { ...i, quantity: i.quantity + 1 } : i
        )
      }
      return [...prev, { ...item, quantity: 1 }]
    })
  }, [])

  const removeItem = useCallback((id: string) => {
    setItems(prev => {
      const existing = prev.find(i => i.id === id)
      if (existing && existing.quantity > 1) {
        return prev.map(i =>
          i.id === id ? { ...i, quantity: i.quantity - 1 } : i
        )
      }
      return prev.filter(i => i.id !== id)
    })
  }, [])

  const clearCart = useCallback(() => {
    setItems([])
  }, [])

  const getQuantity = useCallback(
    (id: string) => items.find(i => i.id === id)?.quantity || 0,
    [items]
  )

  const totalItems = items.reduce((sum, i) => sum + i.quantity, 0)
  const totalPrice = items.reduce((sum, i) => sum + i.price * i.quantity, 0)

  return {
    items,
    addItem,
    removeItem,
    clearCart,
    getQuantity,
    totalItems,
    totalPrice,
    isOpen,
    setIsOpen,
  }
}