import { useEffect, useMemo, useState } from 'react'
import Image from 'next/image'
import { Check, Plus, X } from 'lucide-react'
import { MenuItem, SelectedOption } from '@/lib/menuData'

interface ProductSheetProps {
  item: MenuItem | null
  onClose: () => void
  onAdd: (item: MenuItem, selections: SelectedOption[]) => void
}

export default function ProductSheet({ item, onClose, onAdd }: ProductSheetProps) {
  const [selections, setSelections] = useState<SelectedOption[]>([])

  useEffect(() => {
    if (!item) return
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

  const total = useMemo(
    () => (item?.price || 0) + selections.reduce((sum, option) => sum + option.price, 0),
    [item, selections]
  )

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
        className="fixed inset-0 z-[80] bg-black/55 backdrop-blur-sm"
      />
      <section className="fixed inset-x-0 bottom-0 z-[81] mx-auto max-h-[92vh] max-w-2xl overflow-y-auto rounded-t-[32px] bg-white shadow-2xl">
        <div className="relative aspect-[16/9] overflow-hidden bg-[#ead8c6]">
          <Image
            src={item.image}
            alt={item.name}
            fill
            className="object-cover"
            sizes="(max-width: 768px) 100vw, 672px"
          />
          <div className="absolute inset-0 bg-gradient-to-t from-black/55 via-transparent to-black/10" />
          <button
            type="button"
            onClick={onClose}
            className="absolute right-4 top-4 flex h-10 w-10 items-center justify-center rounded-full bg-white text-[#1b0b04] shadow-lg"
          >
            <X size={18} />
          </button>
          <div className="absolute inset-x-0 bottom-0 p-5 text-white">
            <h2 className="text-3xl font-black">{item.name}</h2>
            <p className="mt-1 font-black text-[#f7b32b]">
              From GHS {item.price.toFixed(2)}
            </p>
          </div>
        </div>

        <div className="space-y-6 p-5 pb-8">
          <p className="text-sm leading-6 text-black/55">{item.description}</p>

          {(item.optionGroups || []).map(group => (
            <div key={group.id}>
              <div className="flex items-center justify-between gap-3">
                <h3 className="font-black">{group.name}</h3>
                <span className="text-xs font-bold uppercase tracking-[0.12em] text-black/35">
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
                      onClick={() =>
                        toggleOption(
                          group.id,
                          group.type,
                          group.maxSelections || group.options.length,
                          option
                        )
                      }
                      className={`flex w-full items-center justify-between rounded-2xl border px-4 py-3 text-left ${
                        selected
                          ? 'border-[#d95d20] bg-orange-50'
                          : 'border-black/[0.08] bg-white'
                      }`}
                    >
                      <span className="flex items-center gap-3">
                        <span
                          className={`flex h-6 w-6 items-center justify-center rounded-full border ${
                            selected
                              ? 'border-[#d95d20] bg-[#d95d20] text-white'
                              : 'border-black/15'
                          }`}
                        >
                          {selected && <Check size={13} />}
                        </span>
                        <span className="font-bold">{option.name}</span>
                      </span>
                      <span className="text-sm font-black text-[#d95d20]">
                        {option.price > 0 ? `+ GHS ${option.price.toFixed(2)}` : 'Included'}
                      </span>
                    </button>
                  )
                })}
              </div>
            </div>
          ))}

          <button
            type="button"
            onClick={() => {
              onAdd(item, selections)
              onClose()
            }}
            className="flex w-full items-center justify-center gap-2 rounded-2xl bg-[#1b0b04] px-4 py-4 font-black text-white"
          >
            <Plus size={18} />
            Add to order · GHS {total.toFixed(2)}
          </button>
        </div>
      </section>
    </>
  )
}
