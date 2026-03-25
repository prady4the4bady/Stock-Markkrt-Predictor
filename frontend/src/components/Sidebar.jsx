import { useState, useEffect, useCallback } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { Search, Bitcoin, Globe, BarChart2, Star, X, Settings, LogOut, Gem, Sun, Moon, Building2, ArrowLeft, Zap } from 'lucide-react'
import { useNavigate } from 'react-router-dom'
import axios from 'axios'
import { useAuth } from '../context/AuthContext'
import activityService from '../services/ActivityService'

const API_URL = '/api'
const FAVORITES_STORAGE_KEY = 'market_oracle_favorites'

// Design tokens
const D = {
    dark: {
        bg: 'rgba(5,5,8,0.88)',
        surface: 'rgba(255,255,255,0.04)',
        surfaceHover: 'rgba(255,255,255,0.07)',
        surfaceActive: 'rgba(200,255,0,0.12)',
        border: 'rgba(255,255,255,0.07)',
        borderActive: 'rgba(200,255,0,0.3)',
        text: '#f0f0f0',
        muted: 'rgba(255,255,255,0.4)',
        dim: 'rgba(255,255,255,0.22)',
        accent: '#c8ff00',
        accentGlow: 'rgba(200,255,0,0.15)',
        accentText: '#c8ff00',
    },
    light: {
        bg: 'rgba(248,250,252,0.92)',
        surface: 'rgba(0,0,0,0.04)',
        surfaceHover: 'rgba(0,0,0,0.07)',
        surfaceActive: 'rgba(100,180,0,0.1)',
        border: 'rgba(0,0,0,0.07)',
        borderActive: 'rgba(100,180,0,0.35)',
        text: '#0f172a',
        muted: 'rgba(0,0,0,0.45)',
        dim: 'rgba(0,0,0,0.28)',
        accent: '#7cb800',
        accentGlow: 'rgba(124,184,0,0.1)',
        accentText: '#7cb800',
    },
}

export default function Sidebar({ onAssetSelect, selectedAsset, assetType, onOpenSettings, theme, onToggleTheme, activeView, onViewChange }) {
    const { user, logout } = useAuth()
    const navigate = useNavigate()
    const [searchQuery, setSearchQuery] = useState('')
    const [globalSearchQuery, setGlobalSearchQuery] = useState('')
    const [activeTab, setActiveTab] = useState('stocks')
    const [selectedExchange, setSelectedExchange] = useState(null)
    const [showGlobalSearch, setShowGlobalSearch] = useState(false)
    const [globalSearchResults, setGlobalSearchResults] = useState([])

    const [favorites, setFavorites] = useState(() => {
        try {
            const saved = localStorage.getItem(FAVORITES_STORAGE_KEY)
            return saved ? JSON.parse(saved) || [] : []
        } catch { return [] }
    })

    const [assets, setAssets] = useState({ stocks: [], crypto: [], forex: [], indices: [], commodities: [], exchanges: {} })
    const [commoditiesGrouped, setCommoditiesGrouped] = useState({})
    const isLight = theme === 'light'
    const t = isLight ? D.light : D.dark

    // Keyboard shortcut for global search (Ctrl+K / ⌘K)
    useEffect(() => {
        const handleKeyDown = (e) => {
            if ((e.metaKey || e.ctrlKey) && e.key === 'k') {
                e.preventDefault()
                setShowGlobalSearch(true)
            }
            if (e.key === 'Escape' && showGlobalSearch) {
                setShowGlobalSearch(false)
                setGlobalSearchQuery('')
            }
        }
        window.addEventListener('keydown', handleKeyDown)
        return () => window.removeEventListener('keydown', handleKeyDown)
    }, [showGlobalSearch])

    useEffect(() => { localStorage.setItem(FAVORITES_STORAGE_KEY, JSON.stringify(favorites)) }, [favorites])

    useEffect(() => {
        if (!user) return
        const sync = async () => {
            try {
                const list = await activityService.getWatchlist(true)
                if (list?.length > 0) {
                    const symbols = list.map(i => i.symbol)
                    setFavorites(symbols)
                    localStorage.setItem(FAVORITES_STORAGE_KEY, JSON.stringify(symbols))
                }
            } catch { }
        }
        sync()
    }, [user])

    useEffect(() => {
        axios.get(`${API_URL}/assets`).then(r => setAssets(r.data)).catch(() => { })
        axios.get(`${API_URL}/commodities`).then(r => setCommoditiesGrouped(r.data)).catch(() => { })
    }, [])

    const mainTabs = [
        { id: 'stocks', label: 'Stocks', emoji: '📈', fullName: 'Stock Markets' },
        { id: 'crypto', label: 'Crypto', emoji: '₿', fullName: 'Cryptocurrencies' },
        { id: 'forex', label: 'Forex', emoji: '💱', fullName: 'Foreign Exchange' },
        { id: 'indices', label: 'Indices', emoji: '📊', fullName: 'Market Indices' },
        { id: 'commodities', label: 'Commod.', emoji: '🛢️', fullName: 'Commodities & Futures' },
    ]

    const exchanges = [
        // Americas
        { id: 'nyse', name: 'NYSE', fullName: 'New York Stock Exchange', flag: '🇺🇸', currency: 'USD', region: 'Americas' },
        { id: 'nasdaq', name: 'NASDAQ', fullName: 'NASDAQ', flag: '🇺🇸', currency: 'USD', region: 'Americas' },
        { id: 'tsx', name: 'Toronto', fullName: 'Toronto Stock Exchange', flag: '🇨🇦', currency: 'CAD', region: 'Americas' },
        { id: 'tsxv', name: 'TSX-V', fullName: 'TSX Venture Exchange', flag: '🇨🇦', currency: 'CAD', region: 'Americas' },
        { id: 'cse', name: 'CSE', fullName: 'Canadian Securities Exchange', flag: '🇨🇦', currency: 'CAD', region: 'Americas' },
        { id: 'bmv', name: 'BMV', fullName: 'Bolsa Mexicana de Valores', flag: '🇲🇽', currency: 'MXN', region: 'Americas' },
        { id: 'b3', name: 'B3', fullName: 'Brasil Bolsa Balcão', flag: '🇧🇷', currency: 'BRL', region: 'Americas' },
        { id: 'byma', name: 'BYMA', fullName: 'Buenos Aires Stock Exchange', flag: '🇦🇷', currency: 'ARS', region: 'Americas' },
        { id: 'santiago', name: 'Santiago', fullName: 'Santiago Stock Exchange', flag: '🇨🇱', currency: 'CLP', region: 'Americas' },
        { id: 'bvc', name: 'BVC', fullName: 'Colombia Stock Exchange', flag: '🇨🇴', currency: 'COP', region: 'Americas' },
        // Europe - Western
        { id: 'lse', name: 'London', fullName: 'London Stock Exchange', flag: '🇬🇧', currency: 'GBP', region: 'Europe' },
        { id: 'euronext', name: 'Euronext', fullName: 'Euronext (Amsterdam, Paris, Brussels)', flag: '🇪🇺', currency: 'EUR', region: 'Europe' },
        { id: 'xetra', name: 'Xetra', fullName: 'Deutsche Börse Xetra', flag: '🇩🇪', currency: 'EUR', region: 'Europe' },
        { id: 'six', name: 'SIX', fullName: 'SIX Swiss Exchange', flag: '🇨🇭', currency: 'CHF', region: 'Europe' },
        { id: 'bme', name: 'BME', fullName: 'Bolsa de Madrid', flag: '🇪🇸', currency: 'EUR', region: 'Europe' },
        { id: 'vienna', name: 'Vienna', fullName: 'Vienna Stock Exchange', flag: '🇦🇹', currency: 'EUR', region: 'Europe' },
        { id: 'dublin', name: 'Dublin', fullName: 'Euronext Dublin', flag: '🇮🇪', currency: 'EUR', region: 'Europe' },
        { id: 'lisbon', name: 'Lisbon', fullName: 'Euronext Lisbon', flag: '🇵🇹', currency: 'EUR', region: 'Europe' },
        // Europe - Nordic
        { id: 'copenhagen', name: 'Copenhagen', fullName: 'Nasdaq OMX Copenhagen', flag: '🇩🇰', currency: 'DKK', region: 'Nordics' },
        { id: 'stockholm', name: 'Stockholm', fullName: 'Nasdaq OMX Stockholm', flag: '🇸🇪', currency: 'SEK', region: 'Nordics' },
        { id: 'helsinki', name: 'Helsinki', fullName: 'Nasdaq OMX Helsinki', flag: '🇫🇮', currency: 'EUR', region: 'Nordics' },
        { id: 'oslo', name: 'Oslo', fullName: 'Oslo Stock Exchange', flag: '🇳🇴', currency: 'NOK', region: 'Nordics' },
        { id: 'iceland', name: 'Iceland', fullName: 'Nasdaq OMX Iceland', flag: '🇮🇸', currency: 'ISK', region: 'Nordics' },
        // Europe - Eastern
        { id: 'warsaw', name: 'Warsaw', fullName: 'Warsaw Stock Exchange', flag: '🇵🇱', currency: 'PLN', region: 'Eastern Europe' },
        { id: 'prague', name: 'Prague', fullName: 'Prague Stock Exchange', flag: '🇨🇿', currency: 'CZK', region: 'Eastern Europe' },
        { id: 'budapest', name: 'Budapest', fullName: 'Budapest Stock Exchange', flag: '🇭🇺', currency: 'HUF', region: 'Eastern Europe' },
        { id: 'bucharest', name: 'Bucharest', fullName: 'Bucharest Stock Exchange', flag: '🇷🇴', currency: 'RON', region: 'Eastern Europe' },
        { id: 'athens', name: 'Athens', fullName: 'Athens Stock Exchange', flag: '🇬🇷', currency: 'EUR', region: 'Eastern Europe' },
        { id: 'istanbul', name: 'Istanbul', fullName: 'Borsa Istanbul', flag: '🇹🇷', currency: 'TRY', region: 'Eastern Europe' },
        // Europe - Baltics
        { id: 'tallinn', name: 'Tallinn', fullName: 'Nasdaq OMX Tallinn', flag: '🇪🇪', currency: 'EUR', region: 'Baltics' },
        { id: 'riga', name: 'Riga', fullName: 'Nasdaq OMX Riga', flag: '🇱🇻', currency: 'EUR', region: 'Baltics' },
        { id: 'vilnius', name: 'Vilnius', fullName: 'Nasdaq OMX Vilnius', flag: '🇱🇹', currency: 'EUR', region: 'Baltics' },
        // Asia Pacific
        { id: 'tse', name: 'Tokyo', fullName: 'Tokyo Stock Exchange', flag: '🇯🇵', currency: 'JPY', region: 'Asia' },
        { id: 'sse', name: 'Shanghai', fullName: 'Shanghai Stock Exchange', flag: '🇨🇳', currency: 'CNY', region: 'Asia' },
        { id: 'szse', name: 'Shenzhen', fullName: 'Shenzhen Stock Exchange', flag: '🇨🇳', currency: 'CNY', region: 'Asia' },
        { id: 'hkex', name: 'Hong Kong', fullName: 'Hong Kong Stock Exchange', flag: '🇭🇰', currency: 'HKD', region: 'Asia' },
        { id: 'krx', name: 'KRX', fullName: 'Korea Exchange', flag: '🇰🇷', currency: 'KRW', region: 'Asia' },
        { id: 'twse', name: 'TWSE', fullName: 'Taiwan Stock Exchange', flag: '🇹🇼', currency: 'TWD', region: 'Asia' },
        { id: 'sgx', name: 'SGX', fullName: 'Singapore Exchange', flag: '🇸🇬', currency: 'SGD', region: 'Asia' },
        { id: 'asx', name: 'ASX', fullName: 'Australian Securities Exchange', flag: '🇦🇺', currency: 'AUD', region: 'Oceania' },
        { id: 'nzx', name: 'NZX', fullName: 'New Zealand Exchange', flag: '🇳🇿', currency: 'NZD', region: 'Oceania' },
        { id: 'idx', name: 'IDX', fullName: 'Indonesia Stock Exchange', flag: '🇮🇩', currency: 'IDR', region: 'Asia' },
        { id: 'set', name: 'SET', fullName: 'Stock Exchange of Thailand', flag: '🇹🇭', currency: 'THB', region: 'Asia' },
        { id: 'klse', name: 'Bursa', fullName: 'Bursa Malaysia', flag: '🇲🇾', currency: 'MYR', region: 'Asia' },
        { id: 'pse', name: 'PSE', fullName: 'Philippine Stock Exchange', flag: '🇵🇭', currency: 'PHP', region: 'Asia' },
        { id: 'hose', name: 'HOSE', fullName: 'Ho Chi Minh Stock Exchange', flag: '🇻🇳', currency: 'VND', region: 'Asia' },
        // India
        { id: 'nse', name: 'NSE', fullName: 'National Stock Exchange', flag: '🇮🇳', currency: 'INR', region: 'India' },
        { id: 'bse', name: 'BSE', fullName: 'Bombay Stock Exchange', flag: '🇮🇳', currency: 'INR', region: 'India' },
        // Middle East
        { id: 'tadawul', name: 'Tadawul', fullName: 'Saudi Stock Exchange', flag: '🇸🇦', currency: 'SAR', region: 'Middle East' },
        { id: 'adx', name: 'ADX', fullName: 'Abu Dhabi Securities Exchange', flag: '🇦🇪', currency: 'AED', region: 'Middle East' },
        { id: 'dfm', name: 'DFM', fullName: 'Dubai Financial Market', flag: '🇦🇪', currency: 'AED', region: 'Middle East' },
        { id: 'qse', name: 'QSE', fullName: 'Qatar Stock Exchange', flag: '🇶🇦', currency: 'QAR', region: 'Middle East' },
        { id: 'boursa_kuwait', name: 'Kuwait', fullName: 'Boursa Kuwait', flag: '🇰🇼', currency: 'KWD', region: 'Middle East' },
        { id: 'tase', name: 'TASE', fullName: 'Tel Aviv Stock Exchange', flag: '🇮🇱', currency: 'ILS', region: 'Middle East' },
        // Africa
        { id: 'jse', name: 'JSE', fullName: 'Johannesburg Stock Exchange', flag: '🇿🇦', currency: 'ZAR', region: 'Africa' },
        { id: 'egx', name: 'EGX', fullName: 'Egyptian Exchange', flag: '🇪🇬', currency: 'EGP', region: 'Africa' },
    ]

    const getCurrentAssets = () => {
        if (activeTab === 'stocks' && selectedExchange) return assets.exchanges?.[selectedExchange]?.stocks || []
        if (activeTab === 'stocks') return []
        if (activeTab === 'commodities') {
            const all = []
            Object.values(commoditiesGrouped || {}).forEach(list => list.forEach(c => all.push(c.symbol)))
            return all
        }
        return assets[activeTab] || []
    }

    const currentAssets = getCurrentAssets()
    const filteredAssets = currentAssets.filter(a => a.toLowerCase().includes(searchQuery.toLowerCase()))

    const handleGlobalSearch = (q) => {
        if (!q.trim()) { setGlobalSearchResults([]); return }
        const results = [], query = q.toLowerCase()
        Object.entries(assets.exchanges || {}).forEach(([id, ex]) => {
            ex.stocks?.forEach(s => { if (s.toLowerCase().includes(query)) results.push({ symbol: s, type: 'stock', exchange: id }) })
        })
        assets.crypto?.forEach(c => { if (c.toLowerCase().includes(query)) results.push({ symbol: c, type: 'crypto' }) })
        assets.forex?.forEach(f => { if (f.toLowerCase().includes(query)) results.push({ symbol: f, type: 'forex' }) })
        assets.indices?.forEach(i => { if (i.toLowerCase().includes(query)) results.push({ symbol: i, type: 'index' }) })
        assets.commodities?.forEach(c => { if (c.toLowerCase().includes(query)) results.push({ symbol: c, type: 'commodity' }) })
        setGlobalSearchResults(results.slice(0, 50))
    }

    useEffect(() => {
        const timeout = setTimeout(() => showGlobalSearch && handleGlobalSearch(globalSearchQuery), 300)
        return () => clearTimeout(timeout)
    }, [globalSearchQuery, showGlobalSearch, assets])

    const addFavorite = (asset) => {
        setFavorites(p => p.includes(asset) ? p : [...p, asset])
        if (user) activityService.addToWatchlist(asset, asset.includes('/') ? 'crypto' : 'stock').catch(() => { })
    }

    const removeFavorite = (asset) => {
        setFavorites(p => p.filter(a => a !== asset))
        if (user) activityService.removeFromWatchlist(asset).catch(() => { })
    }

    const getDisplayName = (asset) => {
        const names = {
            'GC=F': 'Gold', 'SI=F': 'Silver', 'CL=F': 'Crude Oil', 'BZ=F': 'Brent', 'NG=F': 'Natural Gas',
            '^GSPC': 'S&P 500', '^DJI': 'Dow Jones', '^IXIC': 'NASDAQ', '^NDX': 'NASDAQ 100', '^RUT': 'Russell 2000', '^VIX': 'VIX',
            '^NSEI': 'Nifty 50', '^BSESN': 'Sensex', '^NSEBANK': 'Nifty Bank',
            '^FTSE': 'FTSE 100', '^GDAXI': 'DAX', '^FCHI': 'CAC 40', '^STOXX50E': 'Euro Stoxx 50',
            '^N225': 'Nikkei 225', '^HSI': 'Hang Seng', '^KS11': 'KOSPI', '^TWII': 'TAIEX',
            '^BVSP': 'Bovespa', '^MXX': 'IPC Mexico', '^MERVAL': 'Merval',
            'EURUSD=X': 'EUR/USD', 'USDINR=X': 'USD/INR', 'GBPUSD=X': 'GBP/USD', 'USDJPY=X': 'USD/JPY'
        }
        if (names[asset]) return names[asset]
        const suffixes = [
            '.NS', '.BO', '.SS', '.SZ', '.T', '.HK', '.L', '.IL', '.AQ', '.XC',
            '.AS', '.PA', '.BR', '.MI', '.LS', '.IR', '.DE', '.BE', '.BM', '.DU', '.F', '.HM', '.HA', '.MU', '.SG',
            '.SW', '.MC', '.VI', '.CO', '.HE', '.ST', '.OL', '.IC', '.TL', '.RG', '.VS',
            '.PR', '.WA', '.BD', '.RO', '.AT', '.IS', '.TO', '.V', '.CN', '.NE',
            '.SR', '.SAU', '.AE', '.QA', '.KW', '.TA', '.KS', '.KQ', '.TW', '.TWO',
            '.SI', '.AX', '.XA', '.NZ', '.JK', '.BK', '.PS', '.VN', '.KL',
            '.MX', '.SA', '.BA', '.SN', '.CL', '.JO', '.CA'
        ]
        for (const s of suffixes) if (asset.endsWith(s)) return asset.replace(s, '')
        return asset.split('/')[0].split('=')[0]
    }

    const getAssetIcon = (asset, type) => {
        if (type === 'crypto' || asset.includes('/')) return '₿'
        if (asset.endsWith('.NS') || asset.endsWith('.BO')) return '🇮🇳'
        if (asset.endsWith('.SS') || asset.endsWith('.SZ')) return '🇨🇳'
        if (asset.endsWith('.T')) return '🇯🇵'
        if (asset.endsWith('.HK')) return '🇭🇰'
        if (asset.endsWith('.L') || asset.endsWith('.IL')) return '🇬🇧'
        if (asset.endsWith('.AS')) return '🇳🇱'
        if (asset.endsWith('.PA')) return '🇫🇷'
        if (asset.endsWith('.MI')) return '🇮🇹'
        if (asset.endsWith('.BR')) return '🇧🇪'
        if (asset.endsWith('.LS')) return '🇵🇹'
        if (asset.endsWith('.IR')) return '🇮🇪'
        if (asset.endsWith('.DE') || asset.endsWith('.F') || asset.endsWith('.MU') || asset.endsWith('.SG')) return '🇩🇪'
        if (asset.endsWith('.SW')) return '🇨🇭'
        if (asset.endsWith('.MC')) return '🇪🇸'
        if (asset.endsWith('.VI')) return '🇦🇹'
        if (asset.endsWith('.CO')) return '🇩🇰'
        if (asset.endsWith('.HE')) return '🇫🇮'
        if (asset.endsWith('.ST')) return '🇸🇪'
        if (asset.endsWith('.OL')) return '🇳🇴'
        if (asset.endsWith('.IC')) return '🇮🇸'
        if (asset.endsWith('.TL')) return '🇪🇪'
        if (asset.endsWith('.RG')) return '🇱🇻'
        if (asset.endsWith('.VS')) return '🇱🇹'
        if (asset.endsWith('.PR')) return '🇨🇿'
        if (asset.endsWith('.WA')) return '🇵🇱'
        if (asset.endsWith('.BD')) return '🇭🇺'
        if (asset.endsWith('.RO')) return '🇷🇴'
        if (asset.endsWith('.AT')) return '🇬🇷'
        if (asset.endsWith('.IS')) return '🇹🇷'
        if (asset.endsWith('.TO') || asset.endsWith('.V') || asset.endsWith('.CN')) return '🇨🇦'
        if (asset.endsWith('.SR') || asset.endsWith('.SAU')) return '🇸🇦'
        if (asset.endsWith('.AE')) return '🇦🇪'
        if (asset.endsWith('.QA')) return '🇶🇦'
        if (asset.endsWith('.KW')) return '🇰🇼'
        if (asset.endsWith('.TA')) return '🇮🇱'
        if (asset.endsWith('.KS') || asset.endsWith('.KQ')) return '🇰🇷'
        if (asset.endsWith('.TW') || asset.endsWith('.TWO')) return '🇹🇼'
        if (asset.endsWith('.SI')) return '🇸🇬'
        if (asset.endsWith('.AX')) return '🇦🇺'
        if (asset.endsWith('.NZ')) return '🇳🇿'
        if (asset.endsWith('.JK')) return '🇮🇩'
        if (asset.endsWith('.BK')) return '🇹🇭'
        if (asset.endsWith('.PS')) return '🇵🇭'
        if (asset.endsWith('.VN')) return '🇻🇳'
        if (asset.endsWith('.KL')) return '🇲🇾'
        if (asset.endsWith('.MX')) return '🇲🇽'
        if (asset.endsWith('.SA')) return '🇧🇷'
        if (asset.endsWith('.BA')) return '🇦🇷'
        if (asset.endsWith('.SN')) return '🇨🇱'
        if (asset.endsWith('.CL')) return '🇨🇴'
        if (asset.endsWith('.JO')) return '🇿🇦'
        if (asset.endsWith('.CA')) return '🇪🇬'
        return '📈'
    }

    const handleAssetClick = (asset, type) => { onAssetSelect(asset, type); setShowGlobalSearch(false); setGlobalSearchQuery('') }
    const handleLogoClick = () => navigate('/')

    const planLabel = 'Free Access'

    return (
        <motion.aside
            initial={{ x: -300, opacity: 0 }}
            animate={{ x: 0, opacity: 1 }}
            transition={{ duration: 0.5, ease: [0.16, 1, 0.3, 1] }}
            className="w-80 h-screen flex flex-col"
            style={{
                background: t.bg,
                backdropFilter: 'blur(28px)',
                WebkitBackdropFilter: 'blur(28px)',
                borderRight: `1px solid ${t.border}`,
                boxShadow: isLight ? '1px 0 20px rgba(0,0,0,0.06)' : '1px 0 40px rgba(0,0,0,0.4)',
            }}
        >
            {/* Noise texture overlay */}
            <div
                className="absolute inset-0 pointer-events-none"
                style={{
                    backgroundImage: `url("data:image/svg+xml,%3Csvg viewBox='0 0 512 512' xmlns='http://www.w3.org/2000/svg'%3E%3Cfilter id='n'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='0.75' numOctaves='4' stitchTiles='stitch'/%3E%3C/filter%3E%3Crect width='100%25' height='100%25' filter='url(%23n)'/%3E%3C/svg%3E")`,
                    backgroundRepeat: 'repeat',
                    backgroundSize: '256px 256px',
                    opacity: 0.018,
                    zIndex: 0,
                }}
            />

            {/* ── Header ──────────────────────────────── */}
            <div
                className="relative z-10 px-4 pt-4 pb-3"
                style={{ borderBottom: `1px solid ${t.border}` }}
            >
                <div className="flex items-center justify-between mb-3.5">
                    <div
                        className="flex items-center gap-2.5 cursor-pointer select-none"
                        onClick={handleLogoClick}
                    >
                        <motion.div whileHover={{ scale: 1.08 }} whileTap={{ scale: 0.94 }}>
                            <img src="/favicon.svg" alt="NexusTrader" className="w-9 h-9" />
                        </motion.div>
                        <div>
                            <h1
                                className="text-base font-bold leading-tight"
                                style={{ color: t.text, fontFamily: "'Outfit', sans-serif" }}
                            >
                                NexusTrader
                            </h1>
                            <p
                                className="text-[10px] font-medium"
                                style={{
                                    color: t.accentText,
                                    fontFamily: "'JetBrains Mono', monospace",
                                    letterSpacing: '0.05em',
                                }}
                            >
                                {planLabel}
                            </p>
                        </div>
                    </div>
                    <motion.button
                        whileHover={{ scale: 1.1 }}
                        whileTap={{ scale: 0.9 }}
                        onClick={onToggleTheme}
                        className="w-8 h-8 rounded-lg flex items-center justify-center transition-colors"
                        style={{ color: t.muted, background: t.surface }}
                    >
                        {isLight ? <Moon size={14} /> : <Sun size={14} />}
                    </motion.button>
                </div>

                {/* Global search trigger */}
                <motion.button
                    whileHover={{ borderColor: t.borderActive }}
                    onClick={() => setShowGlobalSearch(true)}
                    className="w-full flex items-center gap-2.5 px-3.5 py-2.5 rounded-xl text-sm transition-all"
                    style={{
                        background: t.surface,
                        border: `1px solid ${t.border}`,
                        color: t.muted,
                    }}
                >
                    <Search size={14} style={{ color: t.muted }} />
                    <span className="flex-1 text-left text-sm" style={{ color: t.muted }}>Search all markets...</span>
                    <span
                        className="text-xs px-1.5 py-0.5 rounded"
                        style={{ background: t.surface, color: t.dim, fontFamily: "'JetBrains Mono', monospace" }}
                    >
                        ⌘K
                    </span>
                </motion.button>
            </div>

            {/* ── Globe Button ─────────────────────────── */}
            <div className="relative z-10 px-3 pb-2">
                <motion.button
                    whileTap={{ scale: 0.97 }}
                    onClick={() => onViewChange?.(activeView === 'globe' ? 'dashboard' : 'globe')}
                    className="w-full flex items-center gap-2.5 px-3 py-2.5 rounded-xl transition-all"
                    style={{
                        background: activeView === 'globe'
                            ? 'rgba(200,255,0,0.13)'
                            : t.surface,
                        border: `1px solid ${activeView === 'globe' ? 'rgba(200,255,0,0.3)' : t.border}`,
                        color: activeView === 'globe' ? t.accent : t.muted,
                    }}
                >
                    <Globe size={15} />
                    <span className="text-xs font-semibold flex-1 text-left">Global Market Globe</span>
                    {activeView === 'globe' && (
                        <span className="text-[9px] px-1.5 py-0.5 rounded font-bold"
                            style={{ background: 'rgba(200,255,0,0.2)', color: t.accent }}>
                            LIVE
                        </span>
                    )}
                </motion.button>
            </div>

            {/* ── New Listings Button ───────────────────── */}
            <div className="relative z-10 px-3 pb-2">
                <motion.button
                    whileTap={{ scale: 0.97 }}
                    onClick={() => onViewChange?.(activeView === 'listings' ? 'dashboard' : 'listings')}
                    className="w-full flex items-center gap-2.5 px-3 py-2.5 rounded-xl transition-all"
                    style={{
                        background: activeView === 'listings'
                            ? 'rgba(0,212,255,0.13)'
                            : t.surface,
                        border: `1px solid ${activeView === 'listings' ? 'rgba(0,212,255,0.3)' : t.border}`,
                        color: activeView === 'listings' ? '#00d4ff' : t.muted,
                    }}
                >
                    <Zap size={15} />
                    <span className="text-xs font-semibold flex-1 text-left">New Listings</span>
                    {activeView === 'listings' && (
                        <span className="text-[9px] px-1.5 py-0.5 rounded font-bold"
                            style={{ background: 'rgba(0,212,255,0.2)', color: '#00d4ff' }}>
                            LIVE
                        </span>
                    )}
                </motion.button>
            </div>

            {/* ── Main Tabs ────────────────────────────── */}
            <div
                className="relative z-10 px-3 py-2.5"
                style={{ borderBottom: `1px solid ${t.border}` }}
            >
                <div className="flex gap-1">
                    {mainTabs.map(tab => {
                        const isActive = activeTab === tab.id
                        return (
                            <motion.button
                                key={tab.id}
                                onClick={() => { setActiveTab(tab.id); setSelectedExchange(null); setSearchQuery('') }}
                                title={tab.fullName}
                                whileTap={{ scale: 0.94 }}
                                className="flex-1 flex flex-col items-center py-2 px-1 rounded-lg transition-all"
                                style={{
                                    background: isActive ? t.surfaceActive : 'transparent',
                                    border: `1px solid ${isActive ? t.borderActive : 'transparent'}`,
                                    boxShadow: isActive ? `0 0 12px ${t.accentGlow}` : 'none',
                                    color: isActive ? t.accentText : t.muted,
                                    transition: 'all 0.2s ease',
                                }}
                            >
                                <span className="text-sm mb-0.5">{tab.emoji}</span>
                                <span className="text-[10px] font-semibold tracking-wide">{tab.label}</span>
                            </motion.button>
                        )
                    })}
                </div>
            </div>

            {/* ── Favorites ────────────────────────────── */}
            {favorites.length > 0 && (
                <div
                    className="relative z-10 px-4 py-3"
                    style={{ borderBottom: `1px solid ${t.border}` }}
                >
                    <h3
                        className="text-[10px] font-bold uppercase tracking-widest mb-2.5 flex items-center gap-1.5"
                        style={{ color: t.dim }}
                    >
                        <Star size={10} style={{ fill: 'currentColor' }} />
                        Watchlist ({favorites.length})
                    </h3>
                    <div className="flex flex-wrap gap-1.5">
                        {favorites.map(asset => {
                            const isSelected = selectedAsset === asset
                            return (
                                <motion.div
                                    key={asset}
                                    whileHover={{ scale: 1.04 }}
                                    whileTap={{ scale: 0.96 }}
                                    className="group flex items-center gap-1.5 pl-2.5 pr-1.5 py-1 rounded-full text-xs font-semibold cursor-pointer"
                                    style={{
                                        background: isSelected ? t.surfaceActive : t.surface,
                                        border: `1px solid ${isSelected ? t.borderActive : t.border}`,
                                        color: isSelected ? t.accentText : t.muted,
                                        boxShadow: isSelected ? `0 0 10px ${t.accentGlow}` : 'none',
                                        transition: 'all 0.2s ease',
                                    }}
                                >
                                    <span onClick={() => handleAssetClick(asset, 'stock')}>{getDisplayName(asset)}</span>
                                    <button
                                        onClick={(e) => { e.stopPropagation(); removeFavorite(asset) }}
                                        className="w-4 h-4 rounded-full flex items-center justify-center text-red-400 opacity-0 group-hover:opacity-100 transition-opacity"
                                        style={{ background: 'rgba(239,68,68,0.15)' }}
                                    >×</button>
                                </motion.div>
                            )
                        })}
                    </div>
                </div>
            )}

            {/* ── Asset Content ──────────────────────── */}
            <div className="relative z-10 flex-1 overflow-hidden flex flex-col">

                {/* Exchange grid */}
                {activeTab === 'stocks' && !selectedExchange && (
                    <div className="flex-1 overflow-y-auto p-4">
                        <p
                            className="text-[10px] font-bold uppercase tracking-widest mb-3"
                            style={{ color: t.dim }}
                        >
                            Select Exchange
                        </p>
                        <div className="grid grid-cols-2 gap-2">
                            {exchanges.map(ex => (
                                <motion.button
                                    key={ex.id}
                                    whileHover={{ scale: 1.03, borderColor: t.borderActive }}
                                    whileTap={{ scale: 0.97 }}
                                    onClick={() => setSelectedExchange(ex.id)}
                                    title={`${ex.fullName} (${ex.region})`}
                                    className="p-3 rounded-xl text-left transition-all"
                                    style={{
                                        background: t.surface,
                                        border: `1px solid ${t.border}`,
                                    }}
                                >
                                    <div className="flex items-center gap-2 mb-1">
                                        <span className="text-base">{ex.flag}</span>
                                        <span className="font-semibold text-sm" style={{ color: t.text }}>{ex.name}</span>
                                    </div>
                                    <p className="text-[11px]" style={{ color: t.dim }}>
                                        {assets.exchanges?.[ex.id]?.stocks?.length || 0} stocks · {ex.currency}
                                    </p>
                                </motion.button>
                            ))}
                        </div>
                    </div>
                )}

                {/* Asset list */}
                {(activeTab !== 'stocks' || selectedExchange) && (
                    <>
                        {activeTab === 'stocks' && selectedExchange && (
                            <div
                                className="px-4 py-3"
                                style={{ borderBottom: `1px solid ${t.border}` }}
                            >
                                <button
                                    onClick={() => setSelectedExchange(null)}
                                    className="flex items-center gap-1.5 text-xs font-semibold mb-1.5 transition-opacity hover:opacity-60"
                                    style={{ color: t.accentText }}
                                >
                                    <ArrowLeft size={13} /> Back to Exchanges
                                </button>
                                <p className="text-sm font-medium" style={{ color: t.text }}>
                                    {exchanges.find(e => e.id === selectedExchange)?.flag}{' '}
                                    {exchanges.find(e => e.id === selectedExchange)?.fullName}
                                </p>
                            </div>
                        )}

                        {/* Search input */}
                        <div className="px-4 py-2.5">
                            <div className="relative">
                                <Search
                                    size={13}
                                    className="absolute left-3 top-1/2 -translate-y-1/2"
                                    style={{ color: t.dim }}
                                />
                                <input
                                    type="text"
                                    placeholder={`Search ${activeTab}...`}
                                    value={searchQuery}
                                    onChange={e => setSearchQuery(e.target.value)}
                                    className="w-full pl-9 pr-4 py-2.5 text-sm rounded-xl outline-none transition-all"
                                    style={{
                                        background: t.surface,
                                        border: `1px solid ${t.border}`,
                                        color: t.text,
                                        fontFamily: 'inherit',
                                    }}
                                    onFocus={e => (e.target.style.borderColor = t.borderActive)}
                                    onBlur={e => (e.target.style.borderColor = t.border)}
                                />
                            </div>
                        </div>

                        <p className="px-4 text-[10px] font-semibold uppercase tracking-widest mb-1" style={{ color: t.dim }}>
                            {filteredAssets.length} results
                        </p>

                        <div className="flex-1 overflow-y-auto px-3 pb-4">
                            {activeTab === 'commodities' ? (
                                Object.entries(commoditiesGrouped).map(([country, list]) => (
                                    <div key={country} className="mb-3">
                                        <p
                                            className="text-[10px] font-bold uppercase tracking-widest mb-2 px-1"
                                            style={{ color: t.dim }}
                                        >
                                            {country} · {list.length}
                                        </p>
                                        {list.map((c, idx) => {
                                            const isActive = selectedAsset === c.symbol
                                            return (
                                                <motion.div
                                                    key={c.symbol}
                                                    initial={{ opacity: 0, y: 6 }}
                                                    animate={{ opacity: 1, y: 0 }}
                                                    transition={{ delay: Math.min(idx * 0.015, 0.4) }}
                                                    onClick={() => handleAssetClick(c.symbol, 'commodity')}
                                                    className="flex items-center justify-between px-3 py-2.5 rounded-xl cursor-pointer mb-0.5 transition-all"
                                                    style={{
                                                        background: isActive ? t.surfaceActive : 'transparent',
                                                        border: `1px solid ${isActive ? t.borderActive : 'transparent'}`,
                                                        boxShadow: isActive ? `0 0 10px ${t.accentGlow}` : 'none',
                                                    }}
                                                    onMouseEnter={e => !isActive && (e.currentTarget.style.background = t.surfaceHover)}
                                                    onMouseLeave={e => !isActive && (e.currentTarget.style.background = 'transparent')}
                                                >
                                                    <div className="flex items-center gap-2.5">
                                                        <span className="text-base">🛢️</span>
                                                        <div>
                                                            <p className="font-medium text-sm leading-tight" style={{ color: t.text }}>{c.name}</p>
                                                            <p className="text-[11px]" style={{ color: t.dim }}>{c.symbol} · {c.exchange} · {c.currency}</p>
                                                        </div>
                                                    </div>
                                                    <p
                                                        className="text-sm font-semibold"
                                                        style={{ color: t.muted, fontFamily: "'JetBrains Mono', monospace" }}
                                                    >
                                                        {c.price ? `${Number(c.price).toFixed(2)}` : '—'}
                                                    </p>
                                                </motion.div>
                                            )
                                        })}
                                    </div>
                                ))
                            ) : (
                                filteredAssets.map((asset, i) => {
                                    const isActive = selectedAsset === asset
                                    return (
                                        <motion.div
                                            key={asset}
                                            initial={{ opacity: 0, y: 6 }}
                                            animate={{ opacity: 1, y: 0 }}
                                            transition={{ delay: Math.min(i * 0.015, 0.4) }}
                                            onClick={() => handleAssetClick(asset, activeTab)}
                                            className="flex items-center justify-between px-3 py-2.5 rounded-xl cursor-pointer mb-0.5 transition-all"
                                            style={{
                                                background: isActive ? t.surfaceActive : 'transparent',
                                                border: `1px solid ${isActive ? t.borderActive : 'transparent'}`,
                                                boxShadow: isActive ? `0 0 10px ${t.accentGlow}` : 'none',
                                            }}
                                            onMouseEnter={e => !isActive && (e.currentTarget.style.background = t.surfaceHover)}
                                            onMouseLeave={e => !isActive && (e.currentTarget.style.background = 'transparent')}
                                        >
                                            <div className="flex items-center gap-2.5">
                                                <span className="text-base">{getAssetIcon(asset, activeTab)}</span>
                                                <div>
                                                    <p className="font-medium text-sm leading-tight" style={{ color: t.text }}>{getDisplayName(asset)}</p>
                                                    <p className="text-[11px]" style={{ color: t.dim, fontFamily: "'JetBrains Mono', monospace" }}>{asset}</p>
                                                </div>
                                            </div>
                                            <motion.button
                                                whileHover={{ scale: 1.2 }}
                                                whileTap={{ scale: 0.9 }}
                                                onClick={e => {
                                                    e.stopPropagation()
                                                    favorites.includes(asset) ? removeFavorite(asset) : addFavorite(asset)
                                                }}
                                                style={{ color: favorites.includes(asset) ? '#f59e0b' : t.dim }}
                                            >
                                                <Star size={14} style={{ fill: favorites.includes(asset) ? '#f59e0b' : 'none' }} />
                                            </motion.button>
                                        </motion.div>
                                    )
                                })
                            )}
                        </div>
                    </>
                )}
            </div>

            {/* ── Footer / User ──────────────────────── */}
            <div
                className="relative z-10 p-4"
                style={{ borderTop: `1px solid ${t.border}` }}
            >
                {user ? (
                    <div className="flex items-center justify-between">
                        <div className="flex items-center gap-2.5 min-w-0">
                            <div
                                className="w-8 h-8 rounded-full flex items-center justify-center text-xs font-bold flex-shrink-0"
                                style={{
                                    background: t.surfaceActive,
                                    border: `1px solid ${t.borderActive}`,
                                    color: t.accentText,
                                    boxShadow: `0 0 10px ${t.accentGlow}`,
                                }}
                            >
                                {(user.username || user.full_name || user.email)?.[0]?.toUpperCase() || 'U'}
                            </div>
                            <div className="min-w-0">
                                <p className="text-sm font-semibold truncate leading-tight" style={{ color: t.text }}>
                                    {user.username || user.full_name || user.email?.split('@')[0]}
                                </p>
                                <p className="text-[11px] truncate" style={{ color: t.dim }}>{user.email}</p>
                            </div>
                        </div>
                        <div className="flex gap-1 flex-shrink-0">
                            <motion.button
                                whileHover={{ scale: 1.1, background: t.surfaceHover }}
                                whileTap={{ scale: 0.9 }}
                                onClick={onOpenSettings}
                                className="w-8 h-8 rounded-lg flex items-center justify-center transition-colors"
                                style={{ color: t.muted, background: 'transparent' }}
                            >
                                <Settings size={14} />
                            </motion.button>
                            <motion.button
                                whileHover={{ scale: 1.1, background: 'rgba(239,68,68,0.12)' }}
                                whileTap={{ scale: 0.9 }}
                                onClick={logout}
                                className="w-8 h-8 rounded-lg flex items-center justify-center transition-colors"
                                style={{ color: 'rgba(239,68,68,0.7)', background: 'transparent' }}
                            >
                                <LogOut size={14} />
                            </motion.button>
                        </div>
                    </div>
                ) : (
                    <motion.button
                        whileHover={{ boxShadow: `0 0 28px ${t.accentGlow}`, scale: 1.02 }}
                        whileTap={{ scale: 0.97 }}
                        onClick={() => navigate('/login')}
                        className="w-full py-2.5 rounded-xl font-bold text-sm text-black transition-all"
                        style={{
                            background: `linear-gradient(135deg, ${t.accent}, #00d4aa)`,
                            fontFamily: "'Outfit', sans-serif",
                        }}
                    >
                        Sign In
                    </motion.button>
                )}
            </div>

            {/* ── Global Search Modal ─────────────────── */}
            <AnimatePresence>
                {showGlobalSearch && (
                    <motion.div
                        initial={{ opacity: 0 }}
                        animate={{ opacity: 1 }}
                        exit={{ opacity: 0 }}
                        transition={{ duration: 0.18 }}
                        className="fixed inset-0 z-50 flex items-start justify-center pt-16 px-4"
                        style={{ background: 'rgba(5,5,8,0.7)', backdropFilter: 'blur(8px)' }}
                        onClick={() => setShowGlobalSearch(false)}
                    >
                        <motion.div
                            initial={{ opacity: 0, y: -16, scale: 0.97 }}
                            animate={{ opacity: 1, y: 0, scale: 1 }}
                            exit={{ opacity: 0, y: -16, scale: 0.97 }}
                            transition={{ duration: 0.22, ease: [0.16, 1, 0.3, 1] }}
                            onClick={e => e.stopPropagation()}
                            className="w-full max-w-2xl rounded-2xl overflow-hidden"
                            style={{
                                background: isLight ? 'rgba(248,250,252,0.96)' : 'rgba(12,12,18,0.96)',
                                backdropFilter: 'blur(40px)',
                                border: `1px solid ${t.border}`,
                                boxShadow: '0 24px 80px rgba(0,0,0,0.5), inset 0 1px 0 rgba(255,255,255,0.06)',
                            }}
                        >
                            {/* Top border shimmer */}
                            <div
                                className="h-px w-full"
                                style={{ background: `linear-gradient(90deg, transparent, ${t.accent}60, transparent)` }}
                            />

                            <div
                                className="flex items-center gap-3 px-5 py-4"
                                style={{ borderBottom: `1px solid ${t.border}` }}
                            >
                                <Search size={18} style={{ color: t.accentText }} />
                                <input
                                    type="text"
                                    placeholder="Search stocks, crypto, forex, indices..."
                                    value={globalSearchQuery}
                                    onChange={e => setGlobalSearchQuery(e.target.value)}
                                    autoFocus
                                    className="flex-1 text-base bg-transparent outline-none"
                                    style={{ color: t.text }}
                                />
                                <motion.button
                                    whileHover={{ scale: 1.1 }}
                                    whileTap={{ scale: 0.9 }}
                                    onClick={() => setShowGlobalSearch(false)}
                                    className="w-7 h-7 rounded-lg flex items-center justify-center"
                                    style={{ background: t.surface, color: t.muted }}
                                >
                                    <X size={14} />
                                </motion.button>
                            </div>

                            <div className="max-h-96 overflow-y-auto">
                                {globalSearchQuery && globalSearchResults.length === 0 && (
                                    <div className="px-5 py-10 text-center text-sm" style={{ color: t.muted }}>No results found for "{globalSearchQuery}"</div>
                                )}
                                {globalSearchResults.map((r, i) => (
                                    <motion.div
                                        key={`${r.symbol}-${i}`}
                                        initial={{ opacity: 0, x: -8 }}
                                        animate={{ opacity: 1, x: 0 }}
                                        transition={{ delay: i * 0.02 }}
                                        onClick={() => handleAssetClick(r.symbol, r.type)}
                                        className="flex items-center justify-between px-5 py-3 cursor-pointer transition-colors"
                                        onMouseEnter={e => (e.currentTarget.style.background = t.surfaceHover)}
                                        onMouseLeave={e => (e.currentTarget.style.background = 'transparent')}
                                    >
                                        <div className="flex items-center gap-3">
                                            <span className="text-lg">{getAssetIcon(r.symbol, r.type)}</span>
                                            <div>
                                                <p className="font-semibold text-sm" style={{ color: t.text }}>{getDisplayName(r.symbol)}</p>
                                                <p
                                                    className="text-[11px]"
                                                    style={{ color: t.dim, fontFamily: "'JetBrains Mono', monospace" }}
                                                >
                                                    {r.symbol} · {r.type.toUpperCase()}{r.exchange && ` · ${r.exchange.toUpperCase()}`}
                                                </p>
                                            </div>
                                        </div>
                                        <button
                                            onClick={e => { e.stopPropagation(); favorites.includes(r.symbol) ? removeFavorite(r.symbol) : addFavorite(r.symbol) }}
                                            style={{ color: favorites.includes(r.symbol) ? '#f59e0b' : t.dim }}
                                        >
                                            <Star size={14} style={{ fill: favorites.includes(r.symbol) ? '#f59e0b' : 'none' }} />
                                        </button>
                                    </motion.div>
                                ))}
                            </div>

                            {!globalSearchQuery && (
                                <div
                                    className="px-5 py-4"
                                    style={{ borderTop: `1px solid ${t.border}` }}
                                >
                                    <p
                                        className="text-[10px] font-bold uppercase tracking-widest mb-3"
                                        style={{ color: t.dim }}
                                    >
                                        Quick Access
                                    </p>
                                    <div className="flex flex-wrap gap-2">
                                        {['AAPL', 'TSLA', 'BTC/USDT', 'RELIANCE.NS', 'EURUSD=X'].map(s => (
                                            <motion.button
                                                key={s}
                                                whileHover={{ scale: 1.06 }}
                                                whileTap={{ scale: 0.94 }}
                                                onClick={() => handleAssetClick(s, 'stock')}
                                                className="px-3 py-1.5 rounded-full text-xs font-semibold transition-colors"
                                                style={{
                                                    background: t.surfaceActive,
                                                    border: `1px solid ${t.borderActive}`,
                                                    color: t.accentText,
                                                }}
                                            >
                                                {getDisplayName(s)}
                                            </motion.button>
                                        ))}
                                    </div>
                                </div>
                            )}
                        </motion.div>
                    </motion.div>
                )}
            </AnimatePresence>
        </motion.aside>
    )
}
