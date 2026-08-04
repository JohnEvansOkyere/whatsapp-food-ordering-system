import { ReactNode, useEffect } from 'react'

interface MobileCartSheetProps {
  open: boolean
  onClose: () => void
  children: ReactNode
}

/**
 * Bottom-sheet shell for small screens. It wraps the same CartSidebar used on
 * desktop so the checkout flow has one implementation, not two.
 */
export default function MobileCartSheet({
  open,
  onClose,
  children,
}: MobileCartSheetProps) {
  useEffect(() => {
    if (!open) return
    const previous = document.body.style.overflow
    document.body.style.overflow = 'hidden'
    const onKeyDown = (event: KeyboardEvent) => {
      if (event.key === 'Escape') onClose()
    }
    window.addEventListener('keydown', onKeyDown)
    return () => {
      document.body.style.overflow = previous
      window.removeEventListener('keydown', onKeyDown)
    }
  }, [open, onClose])

  return (
    <div className="lg:hidden" aria-hidden={!open}>
      {open && (
        <button
          type="button"
          aria-label="Close cart"
          onClick={onClose}
          className="fixed inset-0 z-[60] bg-black/65 backdrop-blur-sm"
        />
      )}
      <div
        role="dialog"
        aria-modal={open}
        aria-label="Your cart"
        className={`sheet-enter fixed inset-x-0 bottom-0 z-[61] overflow-hidden rounded-t-[28px] border-t border-white/10 bg-[#161616] shadow-[0_-20px_60px_rgba(0,0,0,0.6)] ${
          open ? 'translate-y-0' : 'pointer-events-none translate-y-full'
        }`}
      >
        <div className="flex justify-center pb-1 pt-2.5">
          <div className="h-1 w-10 rounded-full bg-white/25" />
        </div>
        {/* dvh, not svh: the sheet should use the space the browser chrome
            gives back once the customer has scrolled. */}
        <div className="h-[82dvh] max-h-[calc(100dvh-72px)]">{children}</div>
      </div>
    </div>
  )
}
