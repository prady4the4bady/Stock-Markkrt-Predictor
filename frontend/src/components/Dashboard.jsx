import { useState, useEffect, useRef, useCallback } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { RefreshCw, Clock, Zap, Target, TrendingUp, TrendingDown, AlertCircle, Star, StarOff, Bell, X, BarChart2, Microscope } from 'lucide-react'
import { useNavigate } from 'react-router-dom'
import axios from 'axios'
import api from '../utils/api'
import PredictionCard from './PredictionCard'
import VerdictPanel from './VerdictPanel'
import PredictionHistory from './PredictionHistory'
import YahooChart from './YahooChart'
import TechnicalChart from './TechnicalChart'
import ModelWeightsChart from './ModelWeightsChart'
import NewsFeed from './NewsFeed'
import ConfidenceMeter from './ConfidenceMeter'
import OpportunityScanner from './OpportunityScanner'
import VolumeAnalysis from './VolumeAnalysis'
import SupportResistance from './SupportResistance'
import MarketSentiment from './MarketSentiment'
import YahooStylePrice from './YahooStylePrice'
import AdvancedAnalysis from './AdvancedAnalysis'
import TradingViewChart from './TradingViewChart'
import PolywhaleAnalyzer from './PolywhaleAnalyzer'
import CouncilVerdict from './CouncilVerdict'
import PredictionAccuracy from './PredictionAccuracy'
import activityService from '../services/ActivityService'
import { useAuth } from '../context/AuthContext'
import { useTheme } from '../context/ThemeContext'
import { getCurrencyForSymbol, formatPriceWithCurrency, getCurrencySymbol } from '../utils/currencyUtils'

const API_URL = '/api'

export default function Dashboard({ selectedAsset, assetType, onAssetSelect }) {
    const { user } = useAuth()
    const { isDark, isLight, colors, classes } = useTheme()
    const navigate = useNavigate()
    const [prediction, setPrediction] = useState(null)
    const [historical, setHistorical] = useState(null)
    const [quote, setQuote] = useState(null)
    const [isLoading, setIsLoading] = useState(false)
    const [error, setError] = useState(null)
    const [predictionDays, setPredictionDays] = useState(0.04) // Default to 1h for free users
    const [period, setPeriod] = useState('1h') // Default to 1h for free users
    const [isInWatchlist, setIsInWatchlist] = useState(false)
    const [confidenceBoost, setConfidenceBoost] = useState(null)
    const [lastUpdate, setLastUpdate] = useState(null)
    const [notifications, setNotifications] = useState([])
    const [showAlertModal, setShowAlertModal] = useState(false)
    const [alertAbove, setAlertAbove] = useState('')
    const [alertBelow, setAlertBelow] = useState('')
    const [showTVChart, setShowTVChart] = useState(false)
    const [showPolywhale, setShowPolywhale] = useState(false)
    const [livePrice, setLivePrice] = useState(null)
    const [priceFlash, setPriceFlash] = useState(null) // 'up' | 'down' | null
    const [livePrices, setLivePrices] = useState({})   // symbol → {price, change_pct}
    const esRef = useRef(null)
    // Track session for activity tracking
    const sessionRef = useRef(null)
    const previousAssetRef = useRef(null)

    // Activity tracking: Start session when asset changes
    useEffect(() => {
        const trackAssetChange = async () => {
            if (!user || !selectedAsset) return
            
            // End previous session if exists
            if (sessionRef.current && previousAssetRef.current !== selectedAsset) {
                await activityService.endSession()
            }
            
            // Start new session
            const result = await activityService.startSession(
                selectedAsset,
                assetType || 'stock',
                quote?.price
            )
            
            if (result?.session_id) {
                sessionRef.current = result.session_id
            }
            
            previousAssetRef.current = selectedAsset
            
            // Check watchlist status
            checkWatchlistStatus()
            
            // Get confidence boost based on user history
            fetchConfidenceBoost()
        }
        
        trackAssetChange()
        
        // Cleanup on unmount
        return () => {
            if (sessionRef.current) {
                activityService.endSession()
            }
        }
    }, [selectedAsset, user])

    // Check if current asset is in watchlist
    const checkWatchlistStatus = async () => {
        if (!user || !selectedAsset) return
        try {
            const watchlist = await activityService.getWatchlist()
            const inList = watchlist.some(item => 
                item.symbol.toUpperCase() === selectedAsset.toUpperCase()
            )
            setIsInWatchlist(inList)
        } catch (e) {
            console.warn('Could not check watchlist status')
        }
    }

    // Fetch confidence boost based on user history
    const fetchConfidenceBoost = async () => {
        if (!user || !selectedAsset) return
        try {
            const boost = await activityService.getConfidenceBoost(selectedAsset)
            setConfidenceBoost(boost)
        } catch (e) {
            console.warn('Could not fetch confidence boost')
        }
    }

    // Toggle watchlist
    const toggleWatchlist = async () => {
        if (!user || !selectedAsset) return
        try {
            if (isInWatchlist) {
                await activityService.removeFromWatchlist(selectedAsset)
                setIsInWatchlist(false)
            } else {
                await activityService.addToWatchlist(selectedAsset, assetType || 'stock')
                setIsInWatchlist(true)
            }
        } catch (e) {
            console.error('Failed to update watchlist:', e)
        }
    }

    // Check price alerts and add notifications
    const checkPriceAlerts = useCallback((symbol, currentPrice) => {
        // Get stored alerts from localStorage
        const alerts = JSON.parse(localStorage.getItem('priceAlerts') || '{}')
        const symbolAlerts = alerts[symbol]
        
        if (!symbolAlerts) return
        
        const now = Date.now()
        const cooldown = 60000 // 1 minute cooldown between same alerts
        const currencyInfo = getCurrencyForSymbol(symbol)
        const currSymbol = getCurrencySymbol(currencyInfo.currency)
        
        if (symbolAlerts.above && currentPrice >= symbolAlerts.above.target) {
            if (!symbolAlerts.above.lastTriggered || now - symbolAlerts.above.lastTriggered > cooldown) {
                addNotification({
                    type: 'price_alert',
                    title: `${symbol} Price Alert`,
                    message: `Price reached ${currSymbol}${currentPrice.toFixed(2)} (target: ${currSymbol}${symbolAlerts.above.target})`,
                    icon: '📈'
                })
                // Update last triggered
                alerts[symbol].above.lastTriggered = now
                localStorage.setItem('priceAlerts', JSON.stringify(alerts))
            }
        }
        
        if (symbolAlerts.below && currentPrice <= symbolAlerts.below.target) {
            if (!symbolAlerts.below.lastTriggered || now - symbolAlerts.below.lastTriggered > cooldown) {
                addNotification({
                    type: 'price_alert',
                    title: `${symbol} Price Alert`,
                    message: `Price dropped to ${currSymbol}${currentPrice.toFixed(2)} (target: ${currSymbol}${symbolAlerts.below.target})`,
                    icon: '📉'
                })
                // Update last triggered
                alerts[symbol].below.lastTriggered = now
                localStorage.setItem('priceAlerts', JSON.stringify(alerts))
            }
        }
    }, [])
    
    // Add notification helper
    const addNotification = (notification) => {
        const id = Date.now()
        setNotifications(prev => [...prev, { ...notification, id }])
        // Auto-dismiss after 5 seconds
        setTimeout(() => {
            setNotifications(prev => prev.filter(n => n.id !== id))
        }, 5000)
    }
    
    // Dismiss notification
    const dismissNotification = (id) => {
        setNotifications(prev => prev.filter(n => n.id !== id))
    }
    
    // Save price alert
    const savePriceAlert = () => {
        if (!selectedAsset) return
        
        const alerts = JSON.parse(localStorage.getItem('priceAlerts') || '{}')
        alerts[selectedAsset] = {
            above: alertAbove ? { target: parseFloat(alertAbove), lastTriggered: null } : null,
            below: alertBelow ? { target: parseFloat(alertBelow), lastTriggered: null } : null
        }
        localStorage.setItem('priceAlerts', JSON.stringify(alerts))
        
        addNotification({
            type: 'success',
            title: 'Alert Set',
            message: `Price alerts saved for ${selectedAsset}`,
            icon: '🔔'
        })
        
        setShowAlertModal(false)
    }
    
    // Load existing alerts when asset changes
    useEffect(() => {
        if (selectedAsset) {
            const alerts = JSON.parse(localStorage.getItem('priceAlerts') || '{}')
            const symbolAlerts = alerts[selectedAsset]
            if (symbolAlerts) {
                setAlertAbove(symbolAlerts.above?.target?.toString() || '')
                setAlertBelow(symbolAlerts.below?.target?.toString() || '')
            } else {
                setAlertAbove('')
                setAlertBelow('')
            }
        }
    }, [selectedAsset])

    useEffect(() => {
        if (selectedAsset) {
            fetchPrediction()
        }
    }, [selectedAsset, assetType, predictionDays, period])

    // Real-time price streaming via SSE
    useEffect(() => {
        if (!selectedAsset) return

        // Close previous connection
        if (esRef.current) {
            esRef.current.close()
            esRef.current = null
        }

        const encoded = encodeURIComponent(selectedAsset)
        const es = new EventSource(`/api/prices/stream?symbols=${encoded}`)
        esRef.current = es

        es.onmessage = (e) => {
            try {
                const data = JSON.parse(e.data)
                const tick = data.ticks?.[selectedAsset.toUpperCase()]
                if (tick?.price && tick.price > 0) {
                    setLivePrice(prev => {
                        if (prev !== null) {
                            if (tick.price > prev) {
                                setPriceFlash('up')
                                setTimeout(() => setPriceFlash(null), 600)
                            } else if (tick.price < prev) {
                                setPriceFlash('down')
                                setTimeout(() => setPriceFlash(null), 600)
                            }
                        }
                        return tick.price
                    })
                    setLivePrices(data.ticks || {})
                }
            } catch {}
        }

        es.onerror = () => {
            if (esRef.current) {
                esRef.current.close()
                esRef.current = null
            }
        }

        return () => {
            if (esRef.current) {
                esRef.current.close()
                esRef.current = null
            }
        }
    }, [selectedAsset])

    // Real-time quote polling (every 60 seconds / 1 minute)
    useEffect(() => {
        let quoteInterval = null
        let predictionInterval = null
        
        const fetchQuote = async () => {
            if (!selectedAsset) return
            try {
                const response = await api.get(`/quote/${encodeURIComponent(selectedAsset)}`)
                if (response.data && !response.data.error) {
                    setQuote(response.data)
                    setLastUpdate(new Date())
                    
                    // Check for price alerts if user has watchlist items
                    if (user && response.data.price) {
                        checkPriceAlerts(selectedAsset, response.data.price)
                    }
                }
            } catch (e) {
                // Silently handle quote errors - don't spam console
                if (e.response?.status !== 500) {
                    console.warn("Quote poll error:", e.message)
                }
            }
        }
        
        if (selectedAsset) {
            // Initial fetch immediately
            fetchQuote()
            // Poll quote every 15 seconds for price updates (reduced load)
            quoteInterval = setInterval(fetchQuote, 15000)
            // Refresh predictions every 2 minutes (predictions don't change fast)
            predictionInterval = setInterval(() => {
                fetchPrediction()
            }, 120000)
        }
        
        return () => {
            if (quoteInterval) clearInterval(quoteInterval)
            if (predictionInterval) clearInterval(predictionInterval)
        }
    }, [selectedAsset, assetType, predictionDays, period])

    const fetchPrediction = async () => {
        if (!selectedAsset) return

        setIsLoading(true)
        setError(null)

        try {
            const isCrypto = assetType === 'crypto'

            // Fetch prediction
            const predRes = await api.get(`/predict/${selectedAsset}`, {
                params: { days: predictionDays, is_crypto: isCrypto }
            })
            setPrediction(predRes.data)

            // Track prediction request in activity
            if (user && sessionRef.current) {
                activityService.updateSession({
                    prediction_requested: true,
                    prediction_days: predictionDays
                })
            }

            // Fetch historical data with period
            const histRes = await api.get(`/historical/${selectedAsset}`, {
                params: {
                    is_crypto: isCrypto,
                    period: period
                }
            })
            setHistorical(histRes.data)

            // Track chart period selection
            if (user && sessionRef.current) {
                activityService.updateSession({
                    chart_period_selected: period
                })
            }

        } catch (err) {
            const status = err.nexus?.status ?? err.response?.status ?? 0
            const message = err.nexus?.message ?? err.response?.data?.detail ?? 'Failed to fetch prediction.'
            const detail  = err.nexus?.detail  ?? ''

            if (status === 429) {
                setError(message)
            } else if (status === 503) {
                // 503 = cache repaired or provider down — show with retry hint
                setError(`${message}${detail ? ` (${detail})` : ''}`)
            } else if (status === 404) {
                setError(`Symbol not found — "${selectedAsset}" returned no data. Check the ticker.`)
            } else if (status === 0) {
                setError('Cannot reach the server — make sure the backend is running.')
            } else {
                setError(message)
            }
            console.error('Prediction error:', { status, message, detail })
        } finally {
            setIsLoading(false)
        }
    }

    // Welcome screen when no asset selected
    if (!selectedAsset) {
        const QUICK_PICKS = [
            { symbol: 'AAPL', label: 'Apple', type: 'stock', tag: 'S&P 500' },
            { symbol: 'TSLA', label: 'Tesla', type: 'stock', tag: 'EV Leader' },
            { symbol: 'BTC/USDT', label: 'Bitcoin', type: 'crypto', tag: 'Crypto #1' },
        ]
        const FEATURES = [
            { icon: Zap, label: 'Real-time data', color: '#c8ff00' },
            { icon: Target, label: '95% accuracy target', color: '#00d4aa' },
            { icon: Clock, label: '7–30 day forecasts', color: 'rgba(255,255,255,0.5)' },
        ]

        return (
            <div className="h-screen flex items-center justify-center p-8 relative overflow-hidden">
                {/* Ambient glow */}
                <div className="absolute inset-0 pointer-events-none">
                    <div className="absolute top-1/3 left-1/2 -translate-x-1/2 w-[600px] h-[300px] rounded-full"
                        style={{ background: 'radial-gradient(ellipse, rgba(200,255,0,0.04) 0%, transparent 70%)', filter: 'blur(60px)' }} />
                </div>

                <motion.div
                    initial={{ opacity: 0, y: 24 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ duration: 0.7, ease: [0.16, 1, 0.3, 1] }}
                    className="relative text-center"
                    style={{ maxWidth: 560 }}
                >
                    {/* Orbital node mark */}
                    <div className="flex justify-center mb-8">
                        <div className="relative" style={{ width: 64, height: 64 }}>
                            <motion.div
                                className="absolute inset-0 rounded-full"
                                style={{ border: '1px solid rgba(200,255,0,0.2)' }}
                                animate={{ rotate: 360 }}
                                transition={{ duration: 10, repeat: Infinity, ease: 'linear' }}
                            >
                                <div className="absolute -top-1 left-1/2 -translate-x-1/2 w-2 h-2 rounded-full"
                                    style={{ background: '#c8ff00', boxShadow: '0 0 8px #c8ff00' }} />
                            </motion.div>
                            <motion.div
                                className="absolute rounded-full"
                                style={{ inset: 12, border: '1px solid rgba(0,212,170,0.2)' }}
                                animate={{ rotate: -360 }}
                                transition={{ duration: 7, repeat: Infinity, ease: 'linear' }}
                            >
                                <div className="absolute -top-0.5 left-1/2 -translate-x-1/2 w-1.5 h-1.5 rounded-full"
                                    style={{ background: '#00d4aa', boxShadow: '0 0 6px #00d4aa' }} />
                            </motion.div>
                            <div className="absolute inset-0 flex items-center justify-center">
                                <motion.div
                                    className="w-4 h-4 rounded-full"
                                    style={{ background: '#c8ff00' }}
                                    animate={{ scale: [1, 1.4, 1], opacity: [0.8, 1, 0.8] }}
                                    transition={{ duration: 2.5, repeat: Infinity, ease: 'easeInOut' }}
                                />
                            </div>
                        </div>
                    </div>

                    <h2
                        className="font-black mb-3"
                        style={{ fontFamily: "'Outfit', sans-serif", fontSize: 36, letterSpacing: '-0.025em', color: '#f0f0f0' }}
                    >
                        Select an asset<br />
                        <span style={{ color: '#c8ff00' }}>to begin analysis</span>
                    </h2>
                    <p className="mb-8" style={{ color: 'rgba(255,255,255,0.38)', fontSize: 15, lineHeight: 1.65 }}>
                        AI ensemble predictions powered by LSTM, Prophet, and XGBoost.
                        Pick any stock or crypto from the sidebar.
                    </p>

                    {/* Quick picks */}
                    <div className="grid grid-cols-3 gap-3 mb-8">
                        {QUICK_PICKS.map((item, i) => (
                            <motion.button
                                key={item.symbol}
                                initial={{ opacity: 0, y: 16 }}
                                animate={{ opacity: 1, y: 0 }}
                                transition={{ delay: 0.15 + i * 0.08, ease: [0.16, 1, 0.3, 1] }}
                                whileHover={{ y: -3, boxShadow: '0 0 28px rgba(200,255,0,0.12)' }}
                                whileTap={{ scale: 0.97 }}
                                onClick={() => onAssetSelect(item.symbol, item.type)}
                                className="rounded-xl p-4 text-left transition-all"
                                style={{
                                    background: 'rgba(255,255,255,0.04)',
                                    border: '1px solid rgba(255,255,255,0.08)',
                                    cursor: 'pointer',
                                }}
                                onMouseEnter={e => (e.currentTarget.style.borderColor = 'rgba(200,255,0,0.25)')}
                                onMouseLeave={e => (e.currentTarget.style.borderColor = 'rgba(255,255,255,0.08)')}
                            >
                                <div className="text-xs mb-2 px-1.5 py-0.5 rounded inline-block"
                                    style={{ background: item.type === 'crypto' ? 'rgba(0,212,170,0.12)' : 'rgba(200,255,0,0.1)', color: item.type === 'crypto' ? '#00d4aa' : '#c8ff00', fontFamily: "'JetBrains Mono', monospace", fontSize: 9, letterSpacing: '0.08em' }}>
                                    {item.tag}
                                </div>
                                <div className="font-bold text-sm mt-1.5" style={{ color: '#f0f0f0', fontFamily: "'Outfit', sans-serif" }}>{item.symbol.split('/')[0]}</div>
                                <div className="text-xs mt-0.5" style={{ color: 'rgba(255,255,255,0.35)' }}>{item.label}</div>
                            </motion.button>
                        ))}
                    </div>

                    {/* Feature pills */}
                    <div className="flex justify-center gap-4 flex-wrap">
                        {FEATURES.map(({ icon: Icon, label, color }) => (
                            <div key={label} className="flex items-center gap-1.5 text-xs" style={{ color: 'rgba(255,255,255,0.35)' }}>
                                <Icon size={13} style={{ color }} />
                                {label}
                            </div>
                        ))}
                    </div>
                </motion.div>
            </div>
        )
    }

    return (
        <div className={`p-6 space-y-6 relative ${isLight ? 'text-slate-900' : 'text-white'}`}>
            {/* Notifications Toast Container */}
            <div className="fixed top-4 right-4 z-50 flex flex-col gap-2">
                <AnimatePresence>
                    {notifications.map((notification) => (
                        <motion.div
                            key={notification.id}
                            initial={{ opacity: 0, x: 100, scale: 0.8 }}
                            animate={{ opacity: 1, x: 0, scale: 1 }}
                            exit={{ opacity: 0, x: 100, scale: 0.8 }}
                            className={`glass-card p-4 pr-8 min-w-[300px] shadow-lg relative ${
                                isLight ? 'border border-[#7cb800]/20' : 'border border-[#c8ff00]/20'
                            }`}
                        >
                            <button
                                onClick={() => dismissNotification(notification.id)}
                                className={`absolute top-2 right-2 ${isLight ? 'text-slate-400 hover:text-slate-700' : 'text-gray-400 hover:text-white'}`}
                            >
                                <X className="w-4 h-4" />
                            </button>
                            <div className="flex items-start gap-3">
                                <span className="text-2xl">{notification.icon || '🔔'}</span>
                                <div>
                                    <h4 className={`font-semibold ${classes.textPrimary}`}>{notification.title}</h4>
                                    <p className={`text-sm ${classes.textSecondary}`}>{notification.message}</p>
                                </div>
                            </div>
                        </motion.div>
                    ))}
                </AnimatePresence>
            </div>
            
            {/* Header */}
            <motion.div
                initial={{ opacity: 0, y: -20 }}
                animate={{ opacity: 1, y: 0 }}
                className={`p-6 rounded-2xl backdrop-blur-sm ${
                    isLight ? 'bg-white/80 border border-slate-200' : 'bg-[#131320]/50 border border-[#c8ff00]/10'
                }`}
            >
                {/* Top Row - Asset Info & Price */}
                <div className="flex items-start justify-between mb-4">
                    <div>
                        <div className="flex items-center gap-3 mb-2">
                            <h1 className={`text-3xl font-bold tracking-tight ${classes.textPrimary}`}>
                                {selectedAsset.split('/')[0].split('=')[0]}
                            </h1>
                            <span className={`px-2 py-0.5 rounded text-xs font-semibold ${
                                isLight ? 'bg-slate-100 text-slate-600' : 'bg-white/10 text-gray-400'
                            }`}>
                                {assetType ? assetType.toUpperCase() : 'ASSET'}
                            </span>
                            <span className={`text-sm ${classes.textMuted}`}>
                                {prediction?.asset_info?.name || 'Loading Market Data...'}
                            </span>
                            {/* Watchlist Button */}
                            {user && (
                                <motion.button
                                    whileHover={{ scale: 1.1 }}
                                    whileTap={{ scale: 0.95 }}
                                    onClick={toggleWatchlist}
                                    className={`p-2 rounded-lg transition-colors ${
                                        isInWatchlist 
                                            ? 'bg-yellow-500/20 text-yellow-400' 
                                            : 'bg-white/5 text-gray-400 hover:text-yellow-400'
                                    }`}
                                    title={isInWatchlist ? 'Remove from watchlist' : 'Add to watchlist'}
                                >
                                    {isInWatchlist ? (
                                        <Star className="w-5 h-5 fill-current" />
                                    ) : (
                                        <StarOff className="w-5 h-5" />
                                    )}
                                </motion.button>
                            )}
                            {/* Price Alert Button */}
                            <motion.button
                                whileHover={{ scale: 1.1 }}
                                whileTap={{ scale: 0.95 }}
                                onClick={() => setShowAlertModal(true)}
                                className="p-2 rounded-lg bg-white/5 text-gray-400 hover:text-[#c8ff00] transition-colors"
                                title="Set price alert"
                            >
                                <Bell className="w-5 h-5" />
                            </motion.button>
                            {/* Polywhale Button */}
                            <motion.button
                                whileHover={{ scale: 1.1 }}
                                whileTap={{ scale: 0.95 }}
                                onClick={() => setShowPolywhale(true)}
                                className="flex items-center gap-1.5 px-3 py-2 rounded-lg bg-white/5 text-gray-400 hover:text-[#c8ff00] hover:bg-[#c8ff00]/10 transition-colors text-xs font-medium"
                                title="Polywhale — analyze Polymarket screenshot with Claude Vision"
                            >
                                <Microscope className="w-4 h-4" />
                                <span className="hidden sm:inline">Polywhale</span>
                            </motion.button>
                            {/* Confidence Boost Indicator */}
                            {confidenceBoost && confidenceBoost.boost > 0 && (
                                <span className="px-2 py-0.5 rounded text-xs font-semibold bg-green-500/20 text-green-400">
                                    +{(confidenceBoost.boost * 100).toFixed(0)}% confidence
                                </span>
                            )}
                        </div>

                        {/* Price Display — YahooStylePrice with SSE live flash */}
                        {quote ? (
                            <YahooStylePrice
                                price={livePrice ?? quote.price}
                                change={quote.change}
                                changePercent={quote.change_percent}
                                open={quote.open}
                                high={quote.high}
                                low={quote.low}
                                prevClose={quote.prev_close}
                                volume={quote.volume}
                                showDetails={false}
                                size="large"
                                lastUpdate={lastUpdate}
                                symbol={selectedAsset}
                                livePrice={livePrice}
                                priceFlash={priceFlash}
                            />
                        ) : (
                            <div className="h-10 w-48 skeleton rounded-lg"></div>
                        )}
                    </div>

                    <div className="flex items-center gap-3">
                        <motion.button
                            whileHover={{ scale: 1.05 }}
                            whileTap={{ scale: 0.95 }}
                            onClick={fetchPrediction}
                            disabled={isLoading}
                            className="flex items-center gap-2 px-4 py-2 bg-gradient-to-r from-[#c8ff00] to-[#00ff88] hover:from-[#d4ff33] hover:to-[#33ff99] text-black rounded-lg transition-all text-sm font-medium shadow-lg shadow-[#c8ff00]/20"
                        >
                            <RefreshCw className={`w-4 h-4 ${isLoading ? 'animate-spin' : ''}`} />
                            Refresh
                        </motion.button>
                    </div>
                </div>

                {/* Bottom Row - Range & Forecast Controls */}
                <div className="flex flex-wrap items-center gap-4">
                    {/* Range selector */}
                    <div className="flex items-center gap-2 glass-card px-4 py-2">
                        <span className="text-sm text-gray-400">Range:</span>
                        {['1h', '12h', '1d', '1w', '1mo', '3mo', '6mo', '1y', '5y'].map(p => (
                            <button
                                key={p}
                                onClick={() => setPeriod(p)}
                                className={`px-2 py-1 rounded text-xs uppercase transition-all ${
                                    period === p
                                        ? 'bg-[#c8ff00] text-black font-bold'
                                        : 'text-gray-400 hover:text-white hover:bg-white/10'
                                }`}
                            >
                                {p}
                            </button>
                        ))}
                    </div>

                    {/* Prediction period selector */}
                    <div className="flex items-center gap-2 glass-card px-4 py-2">
                        <span className="text-sm text-gray-400">Forecast:</span>
                        {[
                            { value: 0.04, label: '1h' },
                            { value: 0.5, label: '12h' },
                            { value: 1, label: '1d' },
                            { value: 3, label: '3d' },
                            { value: 7, label: '7d' },
                            { value: 14, label: '14d' },
                            { value: 30, label: '30d' }
                        ].map(({ value, label }) => (
                            <button
                                key={value}
                                onClick={() => setPredictionDays(value)}
                                className={`px-3 py-1 rounded-lg text-sm transition-all ${
                                    predictionDays === value
                                        ? 'bg-[#c8ff00] text-black font-bold shadow-lg shadow-[#c8ff00]/20'
                                        : 'text-gray-400 hover:text-white hover:bg-white/10'
                                }`}
                            >
                                {label}
                            </button>
                        ))}
                    </div>
                </div>
            </motion.div>

            {/* Error state */}
            <AnimatePresence>
                {error && (
                    <motion.div
                        initial={{ opacity: 0, y: -10 }}
                        animate={{ opacity: 1, y: 0 }}
                        exit={{ opacity: 0, y: -10 }}
                        className="glass-card p-4 border border-red-500/30 flex items-center gap-3"
                    >
                        <AlertCircle className="w-5 h-5 text-red-400" />
                        <p className="text-red-400">{error}</p>
                    </motion.div>
                )}
            </AnimatePresence>

            {/* Loading state */}
            {isLoading && (
                <div className="grid grid-cols-4 gap-4">
                    {[1, 2, 3, 4].map(i => (
                        <div key={i} className="glass-card p-6 h-32 skeleton" />
                    ))}
                </div>
            )}

            {/* Main content */}
            {!isLoading && prediction && (
                <>
                    {/* Stats row */}
                    <div className="grid grid-cols-4 gap-4">
                        <PredictionCard
                            title="Current Price"
                            value={`$${prediction.current_price?.toLocaleString() || '0'}`}
                            icon={<TrendingUp className="w-5 h-5" />}
                            color="lime"
                            delay={0}
                            currencySymbol={getCurrencyForSymbol(selectedAsset).symbol}
                        />
                        <PredictionCard
                            title="Predicted (End)"
                            value={`$${prediction.predictions?.[prediction.predictions.length - 1]?.toLocaleString() || '0'}`}
                            icon={prediction.analysis?.price_change >= 0 ? <TrendingUp /> : <TrendingDown />}
                            color={prediction.analysis?.price_change >= 0 ? 'green' : 'red'}
                            change={prediction.analysis?.price_change_pct}
                            delay={0.1}
                            currencySymbol={getCurrencyForSymbol(selectedAsset).symbol}
                        />
                        <PredictionCard
                            title="Confidence"
                            value={`${prediction.confidence?.toFixed(1) || '0'}%`}
                            icon={<Target className="w-5 h-5" />}
                            color={
                                prediction.analysis?.signals_conflict ? 'yellow' :
                                (prediction.confidence ?? 0) >= 75 ? 'lime' :
                                (prediction.confidence ?? 0) >= 60 ? 'yellow' : 'red'
                            }
                            delay={0.2}
                        />
                        <PredictionCard
                            title="Recommendation"
                            value={prediction.analysis?.recommendation || 'HOLD'}
                            icon={<Zap className="w-5 h-5" />}
                            color={
                                prediction.analysis?.recommendation === 'BUY' ? 'green' :
                                    prediction.analysis?.recommendation === 'SELL' ? 'red' : 'yellow'
                            }
                            delay={0.3}
                        />
                    </div>

                    {/* Verdict Panel — replaces separate signal conflict / oracle banners */}
                    <VerdictPanel prediction={prediction} symbol={selectedAsset} />

                    {/* Confidence meter — Oracle signals always shown (gate quarantined) */}
                    <ConfidenceMeter
                        confidence={prediction.confidence}
                        individual={prediction.individual_predictions}
                        oracleSignals={prediction.analysis?.oracle_signals}
                    />

                    {/* Model Council Verdict */}
                    <CouncilVerdict verdict={prediction.council_verdict} symbol={selectedAsset} />

                    {/* Self-Learning Accuracy Panel */}
                    <PredictionAccuracy />

                    {/* Kimi K2.5 AI Brief */}
                    {prediction.ai_brief && (
                        <motion.div
                            initial={{ opacity: 0, y: 12 }}
                            animate={{ opacity: 1, y: 0 }}
                            transition={{ delay: 0.35 }}
                            className="rounded-2xl p-5"
                            style={{
                                background: 'linear-gradient(135deg, rgba(118,185,0,0.06) 0%, rgba(0,0,0,0) 60%)',
                                border: '1px solid rgba(118,185,0,0.18)',
                            }}
                        >
                            <div className="flex items-center gap-2 mb-3">
                                <div className="w-6 h-6 rounded-lg flex items-center justify-center"
                                    style={{ background: 'rgba(118,185,0,0.15)', border: '1px solid rgba(118,185,0,0.3)' }}>
                                    <Zap size={13} style={{ color: '#76b900' }} />
                                </div>
                                <span className="text-xs font-bold uppercase tracking-widest"
                                    style={{ color: '#76b900' }}>
                                    Kimi K2.5 · AI Trading Brief
                                </span>
                                <span className="ml-auto text-[10px] font-mono text-white/20">
                                    NVIDIA NIM
                                </span>
                            </div>
                            <p className="text-sm leading-relaxed" style={{ color: 'rgba(255,255,255,0.72)' }}>
                                {prediction.ai_brief}
                            </p>
                        </motion.div>
                    )}

                    {/* Chart Section — NexusTrader or TradingView */}
                    <motion.div
                        initial={{ opacity: 0, y: 20 }}
                        animate={{ opacity: 1, y: 0 }}
                        transition={{ delay: 0.4 }}
                    >
                        {/* Chart tab toggle */}
                        <div className="flex items-center gap-2 mb-3">
                            <button
                                onClick={() => setShowTVChart(false)}
                                className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-semibold transition-all ${
                                    !showTVChart
                                        ? 'bg-[#c8ff00] text-black shadow shadow-[#c8ff00]/20'
                                        : 'bg-white/5 text-gray-400 hover:text-white'
                                }`}
                            >
                                <Zap className="w-3.5 h-3.5" />
                                NexusTrader
                            </button>
                            <button
                                onClick={() => setShowTVChart(true)}
                                className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-semibold transition-all ${
                                    showTVChart
                                        ? 'bg-[#c8ff00] text-black shadow shadow-[#c8ff00]/20'
                                        : 'bg-white/5 text-gray-400 hover:text-white'
                                }`}
                            >
                                <BarChart2 className="w-3.5 h-3.5" />
                                TradingView
                            </button>
                        </div>

                        {showTVChart ? (
                            <TradingViewChart
                                symbol={selectedAsset}
                                assetType={assetType}
                                interval={period === '1h' ? '60' : period === '5d' ? 'D' : period === '1mo' ? 'W' : 'D'}
                                height={520}
                            />
                        ) : (
                            <YahooChart
                                historical={historical?.data}
                                predictions={prediction.predictions}
                                individual={prediction.individual_predictions}
                                dates={prediction.dates}
                                symbol={selectedAsset}
                                quote={quote}
                                period={period}
                                predictionDays={predictionDays}
                                onPeriodChange={(newPeriod) => {
                                    const periodMap = {
                                        '1d': '1d', '5d': '5d', '1mo': '1mo', '6mo': '6mo',
                                        'ytd': 'ytd', '1y': '1y', '5y': '5y', 'max': 'max'
                                    }
                                    setPeriod(periodMap[newPeriod] || newPeriod)
                                }}
                                onRefreshData={fetchPrediction}
                            />
                        )}
                    </motion.div>

                    {/* Technical Analysis & Model Weights Row */}
                    <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
                        <div className="lg:col-span-2">
                            <TechnicalChart data={prediction.technical_indicators} />
                        </div>
                        <div>
                            <ModelWeightsChart individual={prediction.individual_predictions} />
                        </div>
                    </div>

                    {/* New Analysis Row - Support/Resistance, Volume, Sentiment */}
                    <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
                        <SupportResistance 
                            historical={historical?.data} 
                            currentPrice={prediction.current_price} 
                        />
                        <VolumeAnalysis 
                            historical={historical?.data}
                            predictions={prediction.predictions}
                        />
                        <MarketSentiment 
                            prediction={prediction}
                            historical={historical?.data}
                        />
                    </div>

                    {/* Advanced AI Analysis */}
                    {prediction.advanced_analysis && (
                        <AdvancedAnalysis data={prediction.advanced_analysis} />
                    )}

                    {/* Prediction Track Record — self-learning accuracy */}
                    <PredictionHistory symbol={selectedAsset} />

                    {/* Bottom row */}
                    <div className="grid grid-cols-2 gap-6">
                        {/* Analysis */}
                        <motion.div
                            initial={{ opacity: 0, x: -20 }}
                            animate={{ opacity: 1, x: 0 }}
                            transition={{ delay: 0.5 }}
                            className="glass-card p-6"
                        >
                            <h3 className="text-lg font-semibold mb-4 flex items-center gap-2">
                                <span className="text-2xl">📊</span>
                                Analysis
                            </h3>
                            <div className="space-y-3">
                                <div className="flex justify-between items-center py-2 border-b border-white/5">
                                    <span className="text-gray-400">Trend</span>
                                    <span className="font-medium">{prediction.analysis?.trend}</span>
                                </div>
                                <div className="flex justify-between items-center py-2 border-b border-white/5">
                                    <span className="text-gray-400">Predicted High</span>
                                    <span className="font-medium text-green-400">
                                        ${prediction.analysis?.predicted_high?.toLocaleString()}
                                    </span>
                                </div>
                                <div className="flex justify-between items-center py-2 border-b border-white/5">
                                    <span className="text-gray-400">Predicted Low</span>
                                    <span className="font-medium text-red-400">
                                        ${prediction.analysis?.predicted_low?.toLocaleString()}
                                    </span>
                                </div>
                                <div className="flex justify-between items-center py-2 border-b border-white/5">
                                    <span className="text-gray-400">Volatility</span>
                                    <span className="font-medium capitalize">{prediction.analysis?.volatility}</span>
                                </div>
                            </div>
                            <p className="text-xs text-gray-500 mt-4 p-3 bg-white/5 rounded-lg">
                                {prediction.analysis?.note}
                            </p>
                        </motion.div>

                        {/* News Feed */}
                        <motion.div
                            initial={{ opacity: 0, x: 20 }}
                            animate={{ opacity: 1, x: 0 }}
                            transition={{ delay: 0.6 }}
                        >
                            <NewsFeed
                                symbol={selectedAsset}
                                newsVerdict={prediction.analysis?.news_verdict}
                            />
                        </motion.div>
                    </div>

                    {/* AI Scanner Widget */}
                    <OpportunityScanner onAssetSelect={onAssetSelect} />
                </>
            )}
            
            {/* Price Alert Modal */}
            <AnimatePresence>
                {showAlertModal && (
                    <motion.div
                        initial={{ opacity: 0 }}
                        animate={{ opacity: 1 }}
                        exit={{ opacity: 0 }}
                        className="fixed inset-0 bg-black/60 backdrop-blur-sm flex items-center justify-center z-50"
                        onClick={() => setShowAlertModal(false)}
                    >
                        <motion.div
                            initial={{ scale: 0.9, opacity: 0 }}
                            animate={{ scale: 1, opacity: 1 }}
                            exit={{ scale: 0.9, opacity: 0 }}
                            onClick={(e) => e.stopPropagation()}
                            className="glass-card p-6 w-full max-w-md border border-white/10"
                        >
                            <div className="flex items-center justify-between mb-4">
                                <h3 className="text-xl font-bold">Set Price Alerts</h3>
                                <button
                                    onClick={() => setShowAlertModal(false)}
                                    className="text-gray-400 hover:text-white"
                                >
                                    <X className="w-5 h-5" />
                                </button>
                            </div>
                            
                            <p className="text-sm text-gray-400 mb-4">
                                Get notified when <span className="text-white font-semibold">{selectedAsset}</span> reaches your target prices.
                            </p>
                            
                            <div className="space-y-4">
                                <div>
                                    <label htmlFor="alertAbove" className="block text-sm text-gray-400 mb-1">
                                        Alert when price goes above
                                    </label>
                                    <div className="relative">
                                        <span className="absolute left-3 top-2.5 text-gray-500">$</span>
                                        <input
                                            id="alertAbove"
                                            name="alertAbove"
                                            type="number"
                                            step="0.01"
                                            value={alertAbove}
                                            onChange={(e) => setAlertAbove(e.target.value)}
                                            placeholder={quote?.price ? (quote.price * 1.05).toFixed(2) : '0.00'}
                                            className="w-full bg-white/5 border border-white/10 rounded-lg py-2 pl-7 pr-4 text-white focus:outline-none focus:border-green-500"
                                        />
                                    </div>
                                </div>
                                
                                <div>
                                    <label htmlFor="alertBelow" className="block text-sm text-gray-400 mb-1">
                                        Alert when price goes below
                                    </label>
                                    <div className="relative">
                                        <span className="absolute left-3 top-2.5 text-gray-500">$</span>
                                        <input
                                            id="alertBelow"
                                            name="alertBelow"
                                            type="number"
                                            step="0.01"
                                            value={alertBelow}
                                            onChange={(e) => setAlertBelow(e.target.value)}
                                            placeholder={quote?.price ? (quote.price * 0.95).toFixed(2) : '0.00'}
                                            className="w-full bg-white/5 border border-white/10 rounded-lg py-2 pl-7 pr-4 text-white focus:outline-none focus:border-red-500"
                                        />
                                    </div>
                                </div>
                            </div>
                            
                            <div className="flex gap-3 mt-6">
                                <button
                                    onClick={() => setShowAlertModal(false)}
                                    className="flex-1 py-2 rounded-lg bg-white/5 text-gray-400 hover:bg-white/10 transition-colors"
                                >
                                    Cancel
                                </button>
                                <button
                                    onClick={savePriceAlert}
                                    className="flex-1 py-2 rounded-lg bg-gradient-to-r from-[#c8ff00] to-[#00ff88] text-black font-semibold hover:from-[#d4ff33] hover:to-[#33ff99] transition-colors"
                                >
                                    Save Alerts
                                </button>
                            </div>
                            
                            <p className="text-xs text-gray-500 mt-4 text-center">
                                Alerts are stored locally and will trigger while the app is open.
                            </p>
                        </motion.div>
                    </motion.div>
                )}
            </AnimatePresence>

            {/* Polywhale Analyzer Modal */}
            {showPolywhale && (
                <PolywhaleAnalyzer
                    symbol={selectedAsset}
                    assetType={assetType}
                    onClose={() => setShowPolywhale(false)}
                />
            )}

        </div>
    )
}
