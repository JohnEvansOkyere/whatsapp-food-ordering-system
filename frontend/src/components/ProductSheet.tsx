import { useEffect, useMemo, useState } from 'react'
import Image from 'next/image'
import { Check, Minus, Plus, X } from 'lucide-react'
import { MenuItem, SelectedOption } from '@/lib/menuData'

interface ProductSheetProps {
  item: MenuItem | null
  onClose: () => void
  onAdd: (item: MenuItem, selections: SelectedOption[], quantity: number) => void
}

export default function ProductSheet({ item, onClose, onAdd }: ProductSheetProps) {
  const [selections, setSelections] = useState<SelectedOption[]>([])
  const [quantity, setQuantity] = useState(1)

  useEffect(() => {
    if (!item) return
    setQuantity(1)
    setSelections(
      (item.optionGroups || [])
        .filter(group => group.type === 'single')
        .flatMap(group => {
          const option = group.options[0]
          return option
            ? [{
                groupId: group.id,
                optionId: option.id,
                name: option.name,
                price: option.price,
              }]
            : []
        })
    )
  }, [item])

  const unitPrice = useMemo(
    () => (item?.price || 0) + selections.reduce((sum, option) => sum + option.price, 0),
    [item, selections]
  )
  const total = unitPrice * quantity

  if (!item) return null

  const toggleOption = (
    groupId: string,
    type: 'single' | 'multiple',
    maxSelections: number,
    option: { id: string; name: string; price: number }
  ) => {
    setSelections(current => {
      const selected = current.some(
        entry => entry.groupId === groupId && entry.optionId === option.id
      )
      if (type === 'single') {
        return [
          ...current.filter(entry => entry.groupId !== groupId),
          {
            groupId,
            optionId: option.id,
            name: option.name,
            price: option.price,
          },
        ]
      }
      if (selected) {
        return current.filter(
          entry => !(entry.groupId === groupId && entry.optionId === option.id)
        )
      }
      const groupSelections = current.filter(entry => entry.groupId === groupId)
      if (groupSelections.length >= maxSelections) return current
      return [
        ...current,
        {
          groupId,
          optionId: option.id,
          name: option.name,
          price: option.price,
        },
      ]
    })
  }

  return (
    <>
      <button
        type="button"
        aria-label="Close product details"
        onClick={onClose}
        className="fixed inset-0 z-[80] bg-black/60 backdrop-blur-sm"
      />
      {/* Text colour is set explicitly here: the global body colour is white,
          which would otherwise render on this light sheet as white-on-white. */}
      <section className="fixed inset-x-0 bottom-0 z-[81] mx-auto max-h-[92svh] max-w-2xl overflow-y-auto rounded-t-[32px] bg-white text-[#1a0a00] shadow-2xl">
        <div className="relative aspect-[16/9] overflow-hidden bg-[#ead8c6]">
          <Image
            src={item.image}
            alt={item.name}
            fill
            className="object-cover"
            sizes="(max-width: 768px) 100vw, 672px"
          />
          <div className="absolute inset-0 bg-gradient-to-t from-black/70 via-black/10 to-black/15" />
          <button
            type="button"
            onClick={onClose}
            aria-label="Close"
            className="absolute right-4 top-4 flex h-10 w-10 items-center justify-center rounded-full bg-white text-[#1a0a00] shadow-lg"
          >
            <X size={18} />
          </button>
          <div className="absolute inset-x-0 bottom-0 p-5 text-white">
            <h2 className="text-2xl font-black leading-tight sm:text-3xl">{item.name}</h2>
            <p className="mt-1 font-black text-[#ffc852]">
              GHS {item.price.toFixed(2)}
            </p>
          </div>
        </div>

        <div className="space-y-6 p-5 pb-8">
          <p className="text-sm leading-6 text-black/70">{item.description}</p>

          {(item.optionGroups || []).map(group => (
            <div key={group.id}>
              <div className="flex items-center justify-between gap-3">
                <h3 className="font-black text-[#1a0a00]">{group.name}</h3>
                <span className="text-xs font-bold uppercase tracking-[0.12em] text-black/50">
                  {group.type === 'single'
                    ? 'Choose one'
                    : `Up to ${group.maxSelections || group.options.length}`}
                </span>
              </div>
              <div className="mt-3 space-y-2">
                {group.options.map(option => {
                  const selected = selections.some(
                    entry =>
                      entry.groupId === group.id && entry.optionId === option.id
                  )
                  return (
                    <button
                      key={option.id}
                      type="button"
                      aria-pressed={selected}
                      onClick={() =>
                        toggleOption(
                          group.id,
                          group.type,
                          group.maxSelections || group.options.length,
                          option
                        )
                      }
                      className={`flex w-full items-center justify-between rounded-2xl border px-4 py-3 text-left transition ${
                        selected
                          ? 'border-[#d99400] bg-[#fff6e3]'
                          : 'border-black/[0.12] bg-white hover:border-black/25'
                      }`}
                    >
                      <span className="flex items-center gap-3">
                        <span
                          className={`flex h-6 w-6 flex-shrink-0 items-center justify-center rounded-full border ${
                            selected
                              ? 'border-[#d99400] bg-[#d99400] text-white'
                              : 'border-black/25'
                          }`}
                        >
                          {selected && <Check size={13} strokeWidth={3} />}
                        </span>
                        <span className="font-bold text-[#1a0a00]">{option.name}</span>
                      </span>
                      <span className="flex-shrink-0 text-sm font-black text-[#a8720a]">
                        {option.price > 0 ? `+ GHS ${option.price.toFixed(2)}` : 'Included'}
                      </span>
                    </button>
                  )
                })}
              </div>
            </div>
          ))}

          <div className="flex items-center justify-between gap-4">
            <span className="text-sm font-black uppercase tracking-[0.12em] text-black/60">
              Quantity
            </span>
            <div className="flex items-center gap-1 rounded-full border border-black/[0.12] p-1">
              <button
                type="button"
                aria-label="Decrease quantity"
                onClick={() => setQuantity(q => Math.max(1, q - 1))}
                disabled={quantity <= 1}
                className="flex h-9 w-9 items-center justify-center rounded-full text-[#1a0a00] transition hover:bg-black/5 active:scale-90 disabled:opacity-30"
              >
                <Minus size={16} strokeWidth={3} />
              </button>
              <span className="w-8 text-center text-base font-black tabular-nums">
                {quantity}
              </span>
              <button
                type="button"
                aria-label="Increase quantity"
                onClick={() => setQuantity(q => Math.min(20, q + 1))}
                className="flex h-9 w-9 items-center justify-center rounded-full text-[#1a0a00] transition hover:bg-black/5 active:scale-90"
              >
                <Plus size={16} strokeWidth={3} />
              </button>
            </div>
          </div>

          <button
            type="button"
            onClick={() => {
              onAdd(item, selections, quantity)
              onClose()
            }}
            className="flex w-full items-center justify-center gap-2 rounded-2xl bg-[#1a0a00] px-4 py-4 font-black text-white transition hover:bg-black active:scale-[.99]"
          >
            <Plus size={18} strokeWidth={3} />
            Add to order · GHS {total.toFixed(2)}
          </button>
        </div>
      </section>
    </>
  )
}
