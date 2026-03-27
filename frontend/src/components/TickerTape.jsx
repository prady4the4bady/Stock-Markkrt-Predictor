/**
 * TickerTape — Real-time scrolling price tape
 * Connects to /api/prices/snapshot and auto-refreshes every 5 seconds.
 * Yahoo Finance / Bloomberg terminal aesthetic.
 */
import { useState, useEffect, useRef } from 'react'
import { TrendingUp, TrendingDown, Minus } from 'lucide-react'
import axios from 'axios'

const TAPE_SYMBOLS = [
  'AAPL', 'TSLA', 'NVDA', 'MSFT', 'AMZN', 'GOOGL', 'META', 'AMD',
  'BTC/USDT', 'ETH/USDT', 'SOL/USDT', 'BNB/USDT',
  'SPY', 'QQQ', 'GLD',
]

const REFRESH_MS = 5000

function fmt(price, sym) {
  if (!price || price === 0) return '—'
  if (price >= 1000) return price.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })
  if (price >= 1)    return price.toFixed(2)
  return price.toFixed(4)
}

function TickerItem({ sym, data, prevData }) {
  const price     = data?.price ?? 0
  const changePct = data?.change_pct ?? 0
  const prevPrice = prevData?.price ?? price
  const flashing  = useRef(null)
  const [flash, setFlash] = useState(null)

  useEffect(() => {
    if (prevPrice && price && price !== prevPrice) {
      const dir = price > prevPrice ? 'up' : 'down'
      setFlash(dir)
      const t = setTimeout(() => setFlash(null), 700)
      return () => clearTimeout(t)
    }
  }, [price])

  const isPos  = changePct >= 0
  const color  = changePct > 0.05 ? '#c8ff00' : changePct < -0.05 ? '#ff5500' : 'rgba(255,255,255,0.5)'
  const Icon   = changePct > 0.05 ? TrendingUp : changePct < -0.05 ? TrendingDown : Minus

  const label = sym.includes('/') ? sym.split('/')[0] : sym

  return (
    <span
      className="inline-flex items-center gap-1.5 px-3 whitespace-nowrap"
      style={{
        borderRight: '1px solid rgba(255,255,255,0.06)',
        transition: 'background 0.15s',
        background: flash === 'up' ? 'rgba(200,255,0,0.08)' : flash === 'down' ? 'rgba(255,85,0,0.08)' : 'transparent',
        borderRadius: '4px',
      }}
    >
      <span className="text-[11px] font-mono text-white/60 font-medium">{label}</span>
      <span className="text-[12px] font-mono font-bold text-white">{fmt(price, sym)}</span>
      <span className="inline-flex items-center gap-0.5 text-[10px] font-mono font-semibold" style={{ color }}>
        <Icon size={9} />
        {isPos ? '+' : ''}{changePct?.toFixed(2)}%
      </span>
    </span>
  )
}

export default function TickerTape() {
  const [prices, setPrices]     = useState({})
  const [prevPrices, setPrev]   = useState({})
  const [loaded, setLoaded]     = useState(false)
  const animRef                 = useRef(null)
  const trackRef                = useRef(null)
  const posRef                  = useRef(0)

  const fetch = async () => {
    try {
      const syms = TAPE_SYMBOLS.join(',')
      const res  = await axios.get(`/api/prices/snapshot?symbols=${encodeURIComponent(syms)}`)
      setPrev(p => ({ ...p, ...prices }))
      setPrices(res.data.prices || {})
      setLoaded(true)
    } catch {}
  }

  useEffect(() => {
    fetch()
    const iv = setInterval(fetch, REFRESH_MS)
    return () => clearInterval(iv)
  }, [])

  // Smooth CSS marquee animation
  if (!loaded) return null

  // Duplicate items for seamless loop
  const items = [...TAPE_SYMBOLS, ...TAPE_SYMBOLS]

  return (
    <div
      className="relative overflow-hidden flex-none"
      style={{
        height: '32px',
        background: 'rgba(4,4,12,0.95)',
        borderBottom: '1px solid rgba(255,255,255,0.05)',
      }}
    >
      {/* Fade masks */}
      <div className="absolute left-0 top-0 bottom-0 w-8 z-10 pointer-events-none"
        style={{ background: 'linear-gradient(to right, rgba(4,4,12,1), transparent)' }} />
      <div className="absolute right-0 top-0 bottom-0 w-8 z-10 pointer-events-none"
        style={{ background: 'linear-gradient(to left, rgba(4,4,12,1), transparent)' }} />

      <div
        className="flex items-center h-full"
        style={{
          animation: 'nexus-ticker 60s linear infinite',
          width: 'max-content',
        }}
      >
        {items.map((sym, i) => (
          <TickerItem
            key={`${sym}-${i}`}
            sym={sym}
            data={prices[sym.toUpperCase()]}
            prevData={prevPrices[sym.toUpperCase()]}
          />
        ))}
      </div>

      <style>{`
        @keyframes nexus-ticker {
          0%   { transform: translateX(0); }
          100% { transform: translateX(-50%); }
        }
      `}</style>
    </div>
  )
}
