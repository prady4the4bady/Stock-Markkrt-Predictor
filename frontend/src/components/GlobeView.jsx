/**
 * GlobeView — Interactive 3D World Market Globe
 *
 * Design direction: Deep-space observatory aesthetic.
 * A dark, rotating Earth with neon heat-mapped country polygons.
 * Click any country → glassmorphic info panel slides in with live
 * indices, 7-day predictions, and news headlines.
 *
 * Libraries: react-globe.gl (Three.js WebGL), Framer Motion
 * Brand: #c8ff00 lime / #00d4aa teal / #0a0a0f void-black
 */

import { useState, useEffect, useRef, useCallback, Suspense, lazy } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import {
  Globe2, TrendingUp, TrendingDown, Minus, X, RefreshCw,
  Newspaper, BarChart3, ExternalLink, ChevronRight, Wifi,
  AlertCircle, Loader2, ArrowUpRight, ArrowDownRight,
} from 'lucide-react'
import axios from 'axios'

// Lazy-load the heavy WebGL globe to avoid blocking initial render
const GlobeGL = lazy(() => import('react-globe.gl'))

const API = '/api/global'

// ─── Score → color mapping ──────────────────────────────────────────────────

function scoreToColor(score, alpha = 1) {
  if (score === null || score === undefined) return `rgba(255,255,255,${alpha * 0.07})`
  if (score >= 50)  return `rgba(200,255,0,${alpha * 0.85})`     // strong bull — lime
  if (score >= 20)  return `rgba(120,230,0,${alpha * 0.70})`     // bull — green
  if (score >= 5)   return `rgba(0,212,170,${alpha * 0.55})`     // mild bull — teal
  if (score >= -5)  return `rgba(200,200,200,${alpha * 0.15})`   // neutral — white ghost
  if (score >= -20) return `rgba(255,180,0,${alpha * 0.55})`     // mild bear — amber
  if (score >= -50) return `rgba(255,90,0,${alpha * 0.70})`      // bear — orange-red
  return `rgba(220,30,30,${alpha * 0.85})`                        // strong bear — red
}

function scoreToHex(score) {
  if (!score && score !== 0) return '#1a1a2e'
  if (score >= 50)  return '#c8ff00'
  if (score >= 20)  return '#78e600'
  if (score >= 5)   return '#00d4aa'
  if (score >= -5)  return '#404060'
  if (score >= -20) return '#ff9900'
  if (score >= -50) return '#ff5500'
  return '#dc1e1e'
}

function statusLabel(score) {
  if (!score && score !== 0) return 'No Data'
  if (score >= 50)  return 'Strong Bull'
  if (score >= 20)  return 'Bull'
  if (score >= 5)   return 'Mild Bull'
  if (score >= -5)  return 'Neutral'
  if (score >= -20) return 'Mild Bear'
  if (score >= -50) return 'Bear'
  return 'Strong Bear'
}

// ─── Mini trend indicator ───────────────────────────────────────────────────

function Trend({ pct, size = 'md' }) {
  const sz = size === 'sm' ? 'text-xs' : 'text-sm'
  const iconSz = size === 'sm' ? 14 : 16
  if (!pct && pct !== 0) return <span className={`${sz} text-white/30`}>—</span>
  const positive = pct >= 0
  const color = positive ? '#c8ff00' : '#ff5500'
  const Icon = pct > 0.05 ? ArrowUpRight : pct < -0.05 ? ArrowDownRight : Minus
  return (
    <span className={`inline-flex items-center gap-0.5 font-mono font-semibold ${sz}`} style={{ color }}>
      <Icon size={iconSz} />
      {positive ? '+' : ''}{pct?.toFixed(2)}%
    </span>
  )
}

// ─── Country Info Panel ─────────────────────────────────────────────────────

function CountryPanel({ code, onClose }) {
  const [markets, setMarkets] = useState(null)
  const [news, setNews] = useState([])
  const [tab, setTab] = useState('markets')
  const [loading, setLoading] = useState(true)
  const [newsLoading, setNewsLoading] = useState(false)
  const [error, setError] = useState(null)

  useEffect(() => {
    if (!code) return
    setLoading(true)
    setError(null)
    setMarkets(null)
    setNews([])
    setTab('markets')
    axios.get(`${API}/markets/${code}`)
      .then(r => setMarkets(r.data))
      .catch(e => setError(e.response?.data?.detail || 'Failed to load market data'))
      .finally(() => setLoading(false))
  }, [code])

  const loadNews = useCallback(() => {
    if (!code || newsLoading) return
    setNewsLoading(true)
    setTab('news')
    axios.get(`${API}/news/${code}?max_results=6`)
      .then(r => setNews(r.data.results || []))
      .catch(() => setNews([]))
      .finally(() => setNewsLoading(false))
  }, [code, newsLoading])

  const score = markets?.composite_score
  const accentColor = scoreToHex(score)

  return (
    <motion.div
      initial={{ x: '100%', opacity: 0 }}
      animate={{ x: 0, opacity: 1 }}
      exit={{ x: '100%', opacity: 0 }}
      transition={{ type: 'spring', stiffness: 300, damping: 32 }}
      className="absolute top-0 right-0 h-full w-[380px] flex flex-col z-20"
      style={{
        background: 'rgba(6,6,14,0.92)',
        backdropFilter: 'blur(24px)',
        borderLeft: '1px solid rgba(255,255,255,0.07)',
        boxShadow: '-12px 0 60px rgba(0,0,0,0.6)',
      }}
    >
      {/* Header */}
      <div className="flex-none px-5 pt-5 pb-4" style={{ borderBottom: '1px solid rgba(255,255,255,0.06)' }}>
        <div className="flex items-start justify-between">
          <div className="flex items-center gap-3">
            <div
              className="w-10 h-10 rounded-xl flex items-center justify-center text-lg"
              style={{ background: `${accentColor}18`, border: `1px solid ${accentColor}30` }}
            >
              {markets?.emoji || '🌍'}
            </div>
            <div>
              <h3 className="font-bold text-white text-base leading-tight">{markets?.name || code}</h3>
              <span className="text-[11px] font-mono" style={{ color: 'rgba(255,255,255,0.4)' }}>
                {markets?.currency || ''} · {markets?.code || code}
              </span>
            </div>
          </div>
          <button
            onClick={onClose}
            className="w-8 h-8 rounded-lg flex items-center justify-center transition-colors"
            style={{ background: 'rgba(255,255,255,0.05)' }}
            onMouseEnter={e => e.currentTarget.style.background = 'rgba(255,255,255,0.1)'}
            onMouseLeave={e => e.currentTarget.style.background = 'rgba(255,255,255,0.05)'}
          >
            <X size={15} color="rgba(255,255,255,0.5)" />
          </button>
        </div>

        {/* Market score badge */}
        {markets && (
          <div className="mt-3 flex items-center justify-between">
            <div className="flex items-center gap-2">
              <div
                className="px-2.5 py-1 rounded-lg text-xs font-bold"
                style={{ background: `${accentColor}20`, color: accentColor, border: `1px solid ${accentColor}35` }}
              >
                {statusLabel(score)}
              </div>
              <Trend pct={markets.avg_change_pct} />
            </div>
            <span className="text-[11px] text-white/30 font-mono">Score {score > 0 ? '+' : ''}{score}</span>
          </div>
        )}
      </div>

      {/* Tabs */}
      <div className="flex-none flex px-5 pt-3 gap-1" style={{ borderBottom: '1px solid rgba(255,255,255,0.04)' }}>
        {[
          { id: 'markets', label: 'Markets', icon: BarChart3 },
          { id: 'news', label: 'News', icon: Newspaper },
        ].map(({ id, label, icon: Icon }) => (
          <button
            key={id}
            onClick={() => id === 'news' ? loadNews() : setTab('markets')}
            className="flex items-center gap-1.5 px-3 py-2 rounded-t-lg text-xs font-medium transition-all"
            style={{
              color: tab === id ? '#c8ff00' : 'rgba(255,255,255,0.4)',
              borderBottom: tab === id ? '2px solid #c8ff00' : '2px solid transparent',
            }}
          >
            <Icon size={13} />
            {label}
          </button>
        ))}
      </div>

      {/* Content */}
      <div className="flex-1 overflow-y-auto px-5 py-4" style={{ scrollbarWidth: 'thin', scrollbarColor: 'rgba(200,255,0,0.15) transparent' }}>
        {loading ? (
          <div className="flex flex-col items-center justify-center h-32 gap-3">
            <Loader2 size={20} color="#c8ff00" className="animate-spin" />
            <span className="text-xs text-white/30">Fetching live data…</span>
          </div>
        ) : error ? (
          <div className="flex flex-col items-center justify-center h-32 gap-2">
            <AlertCircle size={20} color="#ff5500" />
            <span className="text-xs text-white/40 text-center">{error}</span>
          </div>
        ) : tab === 'markets' ? (
          <MarketsTab data={markets} accentColor={accentColor} />
        ) : (
          <NewsTab news={news} loading={newsLoading} />
        )}
      </div>
    </motion.div>
  )
}

// ─── Markets tab content ─────────────────────────────────────────────────────

function MarketsTab({ data, accentColor }) {
  if (!data) return null
  return (
    <div className="space-y-3">
      {data.indices?.map((idx, i) => (
        <motion.div
          key={idx.symbol}
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: i * 0.07 }}
          className="rounded-xl p-4"
          style={{ background: 'rgba(255,255,255,0.04)', border: '1px solid rgba(255,255,255,0.07)' }}
        >
          <div className="flex items-start justify-between mb-2">
            <div>
              <p className="text-white text-sm font-semibold">{idx.name}</p>
              <p className="text-[10px] font-mono text-white/30 mt-0.5">{idx.symbol}</p>
            </div>
            <Trend pct={idx.change_pct} />
          </div>

          <div className="flex items-baseline gap-1.5 mb-2">
            <span className="text-xl font-bold font-mono text-white">
              {idx.price?.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
            </span>
            <span className="text-xs font-mono text-white/30">
              {idx.change >= 0 ? '+' : ''}{idx.change?.toFixed(2)}
            </span>
          </div>

          {/* 7-day prediction */}
          {idx.prediction_7d && (
            <div
              className="mt-2 pt-2 flex items-center justify-between"
              style={{ borderTop: '1px solid rgba(255,255,255,0.05)' }}
            >
              <span className="text-[10px] text-white/30 uppercase tracking-wide">7-Day AI Target</span>
              <div className="flex items-center gap-2">
                <span className="text-xs font-mono text-white/70">
                  {idx.prediction_7d?.toLocaleString()}
                </span>
                <span
                  className="text-[11px] font-bold font-mono"
                  style={{ color: (idx.prediction_change_pct || 0) >= 0 ? '#c8ff00' : '#ff5500' }}
                >
                  {(idx.prediction_change_pct || 0) >= 0 ? '+' : ''}{idx.prediction_change_pct?.toFixed(2)}%
                </span>
              </div>
            </div>
          )}
        </motion.div>
      ))}

      {/* Trend line mini viz */}
      <div className="rounded-xl p-4" style={{ background: 'rgba(200,255,0,0.04)', border: '1px solid rgba(200,255,0,0.1)' }}>
        <div className="flex items-center gap-2 mb-1">
          <div className="w-2 h-2 rounded-full" style={{ background: accentColor }} />
          <span className="text-[11px] text-white/50 uppercase tracking-wide">Market Sentiment</span>
        </div>
        <p className="text-sm font-semibold" style={{ color: accentColor }}>
          {data.market_status}
        </p>
        <p className="text-[11px] text-white/35 mt-1">
          Composite score: {data.composite_score > 0 ? '+' : ''}{data.composite_score} / 100
        </p>
      </div>
    </div>
  )
}

// ─── News tab content ────────────────────────────────────────────────────────

function NewsTab({ news, loading }) {
  if (loading) {
    return (
      <div className="flex flex-col items-center justify-center h-32 gap-3">
        <Loader2 size={20} color="#c8ff00" className="animate-spin" />
        <span className="text-xs text-white/30">Searching live news…</span>
      </div>
    )
  }
  if (!news?.length) {
    return (
      <div className="flex flex-col items-center justify-center h-32 gap-2">
        <Newspaper size={20} color="rgba(255,255,255,0.2)" />
        <span className="text-xs text-white/30">No news found</span>
      </div>
    )
  }
  return (
    <div className="space-y-3">
      {news.map((item, i) => (
        <motion.div
          key={i}
          initial={{ opacity: 0, y: 8 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: i * 0.06 }}
          className="rounded-xl p-3"
          style={{ background: 'rgba(255,255,255,0.04)', border: '1px solid rgba(255,255,255,0.06)' }}
        >
          <p className="text-sm text-white leading-snug mb-1.5">
            {item.title || item.headline || item.text || 'News headline'}
          </p>
          <div className="flex items-center justify-between">
            <span className="text-[10px] text-white/30">{item.source || item.publisher || 'Market News'}</span>
            {(item.url || item.link) && (
              <a
                href={item.url || item.link}
                target="_blank"
                rel="noopener noreferrer"
                className="flex items-center gap-1 text-[10px] transition-colors"
                style={{ color: 'rgba(200,255,0,0.6)' }}
                onMouseEnter={e => e.currentTarget.style.color = '#c8ff00'}
                onMouseLeave={e => e.currentTarget.style.color = 'rgba(200,255,0,0.6)'}
              >
                Read <ExternalLink size={9} />
              </a>
            )}
          </div>
          {item.snippet && (
            <p className="text-[11px] text-white/35 mt-1 line-clamp-2">{item.snippet}</p>
          )}
        </motion.div>
      ))}
    </div>
  )
}

// ─── Legend ──────────────────────────────────────────────────────────────────

function GlobeLegend() {
  const items = [
    { label: 'Strong Bull', color: '#c8ff00' },
    { label: 'Bull',        color: '#78e600' },
    { label: 'Mild Bull',   color: '#00d4aa' },
    { label: 'Neutral',     color: '#404060' },
    { label: 'Mild Bear',   color: '#ff9900' },
    { label: 'Bear',        color: '#ff5500' },
    { label: 'Strong Bear', color: '#dc1e1e' },
  ]
  return (
    <div
      className="absolute bottom-6 left-6 rounded-xl px-4 py-3 space-y-1.5"
      style={{
        background: 'rgba(6,6,14,0.85)',
        backdropFilter: 'blur(16px)',
        border: '1px solid rgba(255,255,255,0.07)',
      }}
    >
      <p className="text-[10px] text-white/40 uppercase tracking-widest mb-2">Performance</p>
      {items.map(({ label, color }) => (
        <div key={label} className="flex items-center gap-2">
          <div className="w-3 h-3 rounded-sm" style={{ background: color }} />
          <span className="text-[11px] text-white/50">{label}</span>
        </div>
      ))}
    </div>
  )
}

// ─── Stats Bar ───────────────────────────────────────────────────────────────

function StatsBar({ countries }) {
  if (!countries?.length) return null
  const withData = countries.filter(c => c.score !== 0 || c.status !== 'no_data')
  const bulls = withData.filter(c => c.score >= 5).length
  const bears = withData.filter(c => c.score <= -5).length
  const neutral = withData.length - bulls - bears
  const avgScore = withData.length
    ? (withData.reduce((s, c) => s + c.score, 0) / withData.length).toFixed(1)
    : '0'
  const bias = avgScore > 5 ? 'BULLISH' : avgScore < -5 ? 'BEARISH' : 'NEUTRAL'
  const biasColor = avgScore > 5 ? '#c8ff00' : avgScore < -5 ? '#ff5500' : '#ffffff60'

  return (
    <div
      className="absolute top-4 left-1/2 -translate-x-1/2 flex items-center gap-5 rounded-2xl px-6 py-3"
      style={{
        background: 'rgba(6,6,14,0.85)',
        backdropFilter: 'blur(20px)',
        border: '1px solid rgba(255,255,255,0.07)',
      }}
    >
      <div className="text-center">
        <p className="text-[10px] text-white/35 uppercase tracking-wide">Global Bias</p>
        <p className="text-sm font-bold" style={{ color: biasColor }}>{bias}</p>
      </div>
      <div className="w-px h-6 bg-white/10" />
      <div className="text-center">
        <p className="text-[10px] text-white/35 uppercase tracking-wide">Bullish</p>
        <p className="text-sm font-bold text-[#c8ff00]">{bulls}</p>
      </div>
      <div className="text-center">
        <p className="text-[10px] text-white/35 uppercase tracking-wide">Neutral</p>
        <p className="text-sm font-bold text-white/50">{neutral}</p>
      </div>
      <div className="text-center">
        <p className="text-[10px] text-white/35 uppercase tracking-wide">Bearish</p>
        <p className="text-sm font-bold text-[#ff5500]">{bears}</p>
      </div>
      <div className="w-px h-6 bg-white/10" />
      <div className="text-center">
        <p className="text-[10px] text-white/35 uppercase tracking-wide">Avg Score</p>
        <p className="text-sm font-bold font-mono" style={{ color: biasColor }}>
          {avgScore > 0 ? '+' : ''}{avgScore}
        </p>
      </div>
    </div>
  )
}

// ─── Main GlobeView Component ────────────────────────────────────────────────

export default function GlobeView() {
  const globeEl = useRef()
  const containerRef = useRef()
  const [geoJson, setGeoJson] = useState(null)
  const [countries, setCountries] = useState([])   // overview data
  const [scoreMap, setScoreMap] = useState({})      // code → score
  const [selected, setSelected] = useState(null)    // selected country code
  const [loading, setLoading] = useState(true)
  const [dataLoading, setDataLoading] = useState(true)
  const [lastUpdate, setLastUpdate] = useState(null)
  const [hoveredCountry, setHoveredCountry] = useState(null)
  const [dims, setDims] = useState({ w: 800, h: 600 })

  // Responsive sizing
  useEffect(() => {
    const update = () => {
      if (containerRef.current) {
        setDims({
          w: containerRef.current.clientWidth,
          h: containerRef.current.clientHeight,
        })
      }
    }
    update()
    window.addEventListener('resize', update)
    return () => window.removeEventListener('resize', update)
  }, [])

  // Load GeoJSON once (countries polygons for the globe)
  useEffect(() => {
    fetch('https://raw.githubusercontent.com/datasets/geo-countries/master/data/countries.geojson')
      .then(r => r.json())
      .then(data => {
        setGeoJson(data)
        setLoading(false)
      })
      .catch(() => {
        // Fallback: minimal placeholder so globe still renders
        setGeoJson({ type: 'FeatureCollection', features: [] })
        setLoading(false)
      })
  }, [])

  // Fetch live market overview for globe coloring
  const fetchOverview = useCallback(() => {
    setDataLoading(true)
    axios.get(`${API}/overview`)
      .then(r => {
        const list = r.data.countries || []
        setCountries(list)
        const map = {}
        list.forEach(c => { map[c.code] = c.score })
        setScoreMap(map)
        setLastUpdate(new Date())
      })
      .catch(console.error)
      .finally(() => setDataLoading(false))
  }, [])

  useEffect(() => {
    fetchOverview()
    const iv = setInterval(fetchOverview, 5 * 60 * 1000) // refresh every 5min
    return () => clearInterval(iv)
  }, [fetchOverview])

  // Auto-rotate (halt when panel open or hovering)
  useEffect(() => {
    if (!globeEl.current) return
    const controls = globeEl.current.controls?.()
    if (!controls) return
    controls.autoRotate = !selected
    controls.autoRotateSpeed = 0.35
  }, [selected])

  // Initial camera position
  useEffect(() => {
    if (!globeEl.current) return
    globeEl.current.pointOfView({ lat: 20, lng: 0, altitude: 2.2 }, 1000)
  }, [geoJson])

  // Map GeoJSON feature to score via ISO_A2
  const getCountryScore = useCallback((feat) => {
    const code = feat.properties?.ISO_A2 || feat.properties?.iso_a2 || ''
    return scoreMap[code.toUpperCase()] ?? null
  }, [scoreMap])

  const handlePolygonClick = useCallback((feat) => {
    const code = feat.properties?.ISO_A2 || feat.properties?.iso_a2 || ''
    if (code && code !== '-99') {
      setSelected(code.toUpperCase())
    }
  }, [])

  const handlePolygonHover = useCallback((feat) => {
    setHoveredCountry(feat ? (feat.properties?.ADMIN || feat.properties?.admin || '') : null)
  }, [])

  // Major financial centre point markers
  const financialCentres = [
    { name: 'New York',   lat: 40.71,  lng: -74.01, score: scoreMap['US'] },
    { name: 'London',     lat: 51.51,  lng: -0.13,  score: scoreMap['GB'] },
    { name: 'Tokyo',      lat: 35.69,  lng: 139.69, score: scoreMap['JP'] },
    { name: 'Frankfurt',  lat: 50.11,  lng: 8.68,   score: scoreMap['DE'] },
    { name: 'Shanghai',   lat: 31.23,  lng: 121.47, score: scoreMap['CN'] },
    { name: 'Mumbai',     lat: 19.08,  lng: 72.88,  score: scoreMap['IN'] },
    { name: 'Singapore',  lat: 1.35,   lng: 103.82, score: scoreMap['SG'] },
    { name: 'Sydney',     lat: -33.87, lng: 151.21, score: scoreMap['AU'] },
    { name: 'Hong Kong',  lat: 22.32,  lng: 114.17, score: scoreMap['HK'] },
    { name: 'Toronto',    lat: 43.65,  lng: -79.38, score: scoreMap['CA'] },
    { name: 'São Paulo',  lat: -23.55, lng: -46.63, score: scoreMap['BR'] },
    { name: 'Seoul',      lat: 37.57,  lng: 126.98, score: scoreMap['KR'] },
  ]

  const globeReady = !loading && geoJson

  return (
    <div className="relative w-full h-full flex flex-col" style={{ background: '#020209', minHeight: '100vh' }}>

      {/* Starfield background */}
      <div className="absolute inset-0 pointer-events-none overflow-hidden">
        <div style={{
          position: 'absolute', inset: 0,
          background: 'radial-gradient(ellipse at 50% 50%, rgba(0,10,30,0.95) 0%, #020209 100%)',
        }} />
        {/* Static star field */}
        {Array.from({ length: 80 }).map((_, i) => (
          <div key={i} className="absolute rounded-full" style={{
            width: Math.random() * 2 + 0.5 + 'px',
            height: Math.random() * 2 + 0.5 + 'px',
            left: Math.random() * 100 + '%',
            top: Math.random() * 100 + '%',
            background: `rgba(255,255,255,${Math.random() * 0.6 + 0.2})`,
            animation: `pulse ${2 + Math.random() * 4}s ease-in-out infinite`,
            animationDelay: Math.random() * 4 + 's',
          }} />
        ))}
      </div>

      {/* Header bar */}
      <div
        className="relative z-10 flex-none flex items-center justify-between px-6 py-4"
        style={{ borderBottom: '1px solid rgba(255,255,255,0.05)' }}
      >
        <div className="flex items-center gap-3">
          <div
            className="w-9 h-9 rounded-xl flex items-center justify-center"
            style={{ background: 'rgba(200,255,0,0.12)', border: '1px solid rgba(200,255,0,0.2)' }}
          >
            <Globe2 size={18} color="#c8ff00" />
          </div>
          <div>
            <h1 className="text-base font-bold text-white leading-tight">Global Market Globe</h1>
            <p className="text-[11px] text-white/35">
              {countries.length} markets · Live
              {lastUpdate && ` · Updated ${lastUpdate.toLocaleTimeString()}`}
            </p>
          </div>
        </div>

        <div className="flex items-center gap-2">
          {hoveredCountry && (
            <motion.span
              initial={{ opacity: 0, x: 8 }}
              animate={{ opacity: 1, x: 0 }}
              className="text-xs text-white/50 font-mono mr-2"
            >
              {hoveredCountry}
            </motion.span>
          )}
          <div className={`w-2 h-2 rounded-full ${dataLoading ? 'bg-amber-400 animate-pulse' : 'bg-[#c8ff00]'}`} />
          <button
            onClick={fetchOverview}
            disabled={dataLoading}
            className="flex items-center gap-1.5 text-xs text-white/40 hover:text-white/70 transition-colors px-3 py-1.5 rounded-lg"
            style={{ background: 'rgba(255,255,255,0.05)' }}
          >
            <RefreshCw size={12} className={dataLoading ? 'animate-spin' : ''} />
            Refresh
          </button>
        </div>
      </div>

      {/* Hint */}
      <div className="relative z-10 flex-none text-center py-1">
        <span className="text-[10px] text-white/20 tracking-wide">
          Click any country to view live markets & news · Drag to rotate · Scroll to zoom
        </span>
      </div>

      {/* Globe + panel */}
      <div ref={containerRef} className="relative flex-1 overflow-hidden">

        {/* Stats overlay */}
        <StatsBar countries={countries} />

        {/* Globe */}
        {loading ? (
          <div className="absolute inset-0 flex flex-col items-center justify-center gap-4">
            <div className="relative">
              <div className="w-16 h-16 rounded-full animate-spin" style={{
                border: '2px solid rgba(200,255,0,0.1)',
                borderTopColor: '#c8ff00',
              }} />
              <Globe2 size={24} color="#c8ff00" className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2" />
            </div>
            <p className="text-white/40 text-sm">Loading globe…</p>
          </div>
        ) : (
          <Suspense fallback={
            <div className="absolute inset-0 flex items-center justify-center">
              <Loader2 size={28} color="#c8ff00" className="animate-spin" />
            </div>
          }>
            <GlobeGL
              ref={globeEl}
              width={selected ? dims.w - 380 : dims.w}
              height={dims.h}

              // Globe appearance
              globeImageUrl={null}
              backgroundColor="rgba(0,0,0,0)"
              atmosphereColor="#00d4aa"
              atmosphereAltitude={0.18}

              // Country polygons
              polygonsData={geoJson?.features || []}
              polygonCapColor={feat => {
                const score = getCountryScore(feat)
                const code = (feat.properties?.ISO_A2 || feat.properties?.iso_a2 || '').toUpperCase()
                const isSelected = code === selected
                const isHovered  = feat === (hoveredCountry === (feat.properties?.ADMIN || feat.properties?.admin) ? feat : null)
                if (isSelected) return 'rgba(200,255,0,0.9)'
                return scoreToColor(score, 0.75)
              }}
              polygonSideColor={feat => {
                const score = getCountryScore(feat)
                return scoreToColor(score, 0.3)
              }}
              polygonStrokeColor={() => 'rgba(200,255,0,0.08)'}
              polygonAltitude={feat => {
                const code = (feat.properties?.ISO_A2 || feat.properties?.iso_a2 || '').toUpperCase()
                return code === selected ? 0.045 : 0.006
              }}
              onPolygonClick={handlePolygonClick}
              onPolygonHover={handlePolygonHover}
              polygonLabel={feat => {
                const code = (feat.properties?.ISO_A2 || feat.properties?.iso_a2 || '').toUpperCase()
                const country = countries.find(c => c.code === code)
                const name = feat.properties?.ADMIN || feat.properties?.admin || code
                const score = country?.score
                const change = country?.change_pct
                if (!score && score !== 0) return `<div style="font-family:monospace;padding:4px 8px;background:rgba(6,6,14,0.9);border-radius:6px;border:1px solid rgba(255,255,255,0.1);color:white;font-size:11px">${name}</div>`
                return `<div style="font-family:monospace;padding:6px 10px;background:rgba(6,6,14,0.95);border-radius:8px;border:1px solid rgba(200,255,0,0.2);font-size:11px">
                  <div style="color:white;font-weight:600">${name} ${country?.emoji || ''}</div>
                  <div style="color:${scoreToHex(score)};margin-top:2px">${statusLabel(score)} (${change >= 0 ? '+' : ''}${change?.toFixed(2)}%)</div>
                </div>`
              }}

              // Financial centre point markers
              pointsData={financialCentres}
              pointLat={d => d.lat}
              pointLng={d => d.lng}
              pointAltitude={0.02}
              pointRadius={d => d.score != null ? 0.35 : 0.2}
              pointColor={d => scoreToColor(d.score, 0.9)}
              pointLabel={d => `<div style="font-family:monospace;padding:4px 8px;background:rgba(6,6,14,0.9);border-radius:6px;border:1px solid rgba(200,255,0,0.2);color:white;font-size:11px"><b>${d.name}</b></div>`}
              pointsMerge={false}
            />
          </Suspense>
        )}

        {/* Legend */}
        <GlobeLegend />

        {/* Country info panel */}
        <AnimatePresence>
          {selected && (
            <CountryPanel key={selected} code={selected} onClose={() => setSelected(null)} />
          )}
        </AnimatePresence>
      </div>

      {/* Pulse animation keyframe */}
      <style>{`
        @keyframes pulse {
          0%, 100% { opacity: 0.4; transform: scale(1); }
          50% { opacity: 1; transform: scale(1.5); }
        }
      `}</style>
    </div>
  )
}
