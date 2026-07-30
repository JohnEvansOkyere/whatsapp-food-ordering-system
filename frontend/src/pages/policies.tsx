import Head from 'next/head'
import Link from 'next/link'
import { RESTAURANT } from '@/lib/menuData'

export default function PoliciesPage() {
  return (
    <>
      <Head>
        <title>Ordering policies | {RESTAURANT.name}</title>
      </Head>
      <main className="min-h-screen bg-[#fffaf4] px-4 py-12 text-[#1b0b04]">
        <article className="mx-auto max-w-3xl rounded-[32px] border border-black/[0.06] bg-white p-6 shadow-xl sm:p-10">
          <p className="text-xs font-black uppercase tracking-[0.2em] text-[#d95d20]">
            Provisional launch copy
          </p>
          <h1 className="mt-3 text-4xl font-black">Ordering and privacy</h1>
          <p className="mt-4 text-sm leading-7 text-black/55">
            This draft explains how the ordering system currently works. The
            restaurant must approve the final legal wording before launch.
          </p>

          <div className="mt-8 space-y-8 text-sm leading-7 text-black/65">
            <section>
              <h2 className="text-xl font-black text-[#1b0b04]">Order information</h2>
              <p className="mt-2">
                We use the name, phone number, delivery address and instructions
                you provide to prepare, deliver and support your order.
              </p>
            </section>
            <section>
              <h2 className="text-xl font-black text-[#1b0b04]">WhatsApp updates</h2>
              <p className="mt-2">
                Checkout asks for consent to send an order receipt and
                operational status updates. This consent does not include
                promotional marketing.
              </p>
            </section>
            <section>
              <h2 className="text-xl font-black text-[#1b0b04]">Tracking links</h2>
              <p className="mt-2">
                Tracking links are private, difficult to guess and expire after
                90 days. Customers should avoid forwarding them publicly.
              </p>
            </section>
            <section>
              <h2 className="text-xl font-black text-[#1b0b04]">Changes and cancellations</h2>
              <p className="mt-2">
                Contact the selected branch as early as possible. A cancellation
                may be unavailable once preparation or dispatch has started.
                Refund handling depends on the confirmed payment method and
                final restaurant policy.
              </p>
            </section>
            <section>
              <h2 className="text-xl font-black text-[#1b0b04]">Saved details</h2>
              <p className="mt-2">
                If you choose “remember my details,” they are stored only in
                this browser. Clearing the site’s browser storage removes them.
              </p>
            </section>
          </div>

          <Link
            href="/"
            className="mt-10 inline-flex rounded-full bg-[#1b0b04] px-5 py-3 text-sm font-black text-white"
          >
            Return to menu
          </Link>
        </article>
      </main>
    </>
  )
}
