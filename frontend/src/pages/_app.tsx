import type { AppProps } from 'next/app'
import Head from 'next/head'
import { useEffect } from 'react'
import '../styles/globals.css'

export default function App({ Component, pageProps }: AppProps) {
  useEffect(() => {
    if ('serviceWorker' in navigator && process.env.NODE_ENV === 'production') {
      void navigator.serviceWorker.register('/sw.js')
    }
  }, [])

  return (
    <>
      <Head>
        {/* One viewport for every page. `viewport-fit=cover` is what makes the
            env(safe-area-inset-*) padding on notched phones non-zero, and pinch
            zoom is deliberately left enabled. */}
        <meta
          name="viewport"
          content="width=device-width, initial-scale=1, viewport-fit=cover"
        />
      </Head>
      <Component {...pageProps} />
    </>
  )
}
