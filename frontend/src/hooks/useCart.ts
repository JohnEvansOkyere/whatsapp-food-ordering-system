import { useState, useCallback, useEffect } from 'react'
import { MenuItem, SelectedOption } from '../lib/menuData'

export interface CartItem extends MenuItem {
  cartKey: string
  selectedOptions: SelectedOption[]
  quantity: number
}

export function useCart() {
  const [items, setItems] = useState<CartItem[]>([])
  const [isOpen, setIsOpen] = useState(false)
  const [hydrated, setHydrated] = useState(false)

  useEffect(() => {
    try {
      const stored = window.localStorage.getItem('restaurant-cart-v1')
      if (stored) {
        const parsed = JSON.parse(stored)
        if (Array.isArray(parsed)) {
          setItems(
            parsed.map(item => ({
              ...item,
              cartKey: item.cartKey || item.id,
              selectedOptions: Array.isArray(item.selectedOptions)
                ? item.selectedOptions
                : [],
            }))
          )
        }
      }
    } catch {
      window.localStorage.removeItem('restaurant-cart-v1')
    } finally {
      setHydrated(true)
    }
  }, [])

  useEffect(() => {
    if (!hydrated) return
    window.localStorage.setItem('restaurant-cart-v1', JSON.stringify(items))
  }, [hydrated, items])

  const addItem = useCallback((item: MenuItem, quantity: number = 1) => {
    setItems(prev => {
      const incoming = item as CartItem
      const cartKey = incoming.cartKey || item.id
      const existing = prev.find(i => i.cartKey === cartKey)
      if (existing) {
        return prev.map(i =>
          i.cartKey === cartKey ? { ...i, quantity: i.quantity + quantity } : i
        )
      }
      return [
        ...prev,
        {
          ...item,
          cartKey,
          selectedOptions: incoming.selectedOptions || [],
          quantity,
        },
      ]
    })
  }, [])

  const addConfiguredItem = useCallback(
    (item: MenuItem, selectedOptions: SelectedOption[], quantity: number = 1) => {
      const signature = selectedOptions
        .map(option => `${option.groupId}:${option.optionId}`)
        .sort()
        .join('|')
      const optionsPrice = selectedOptions.reduce(
        (sum, option) => sum + option.price,
        0
      )
      addItem(
        {
          ...item,
          price: item.price + optionsPrice,
          cartKey: `${item.id}::${signature || 'base'}`,
          selectedOptions,
        } as CartItem,
        quantity
      )
    },
    [addItem]
  )

  const removeItem = useCallback((cartKey: string) => {
    setItems(prev => {
      const existing = prev.find(i => i.cartKey === cartKey)
      if (existing && existing.quantity > 1) {
        return prev.map(i =>
          i.cartKey === cartKey ? { ...i, quantity: i.quantity - 1 } : i
        )
      }
      return prev.filter(i => i.cartKey !== cartKey)
    })
  }, [])

  const removeOneByItemId = useCallback((id: string) => {
    setItems(prev => {
      const existing = prev.find(item => item.id === id)
      if (!existing) return prev
      if (existing.quantity > 1) {
        return prev.map(item =>
          item.cartKey === existing.cartKey
            ? { ...item, quantity: item.quantity - 1 }
            : item
        )
      }
      return prev.filter(item => item.cartKey !== existing.cartKey)
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
    addConfiguredItem,
    removeItem,
    removeOneByItemId,
    clearCart,
    getQuantity,
    totalItems,
    totalPrice,
    isOpen,
    setIsOpen,
    hydrated,
  }
}
