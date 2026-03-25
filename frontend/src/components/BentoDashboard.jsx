import { useState, useEffect, useRef } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import {
    TrendingUp, TrendingDown, RefreshCw, Target, Zap, Clock,
    BarChart3, Activity, Brain, Newspaper, ChevronUp, ChevronDown,
    ArrowUpRight, ArrowDownRight, Sparkles
} from 'lucide-react'
import axios from 'axios'
import { useAuth } from '../context/AuthContext'

const API_URL = '/api'

// Animated number component
const AnimatedNumber = ({ value, prefix = '', suffix = '', decimals = 2 }) => {
    const [displayValue, setDisplayValue] = useState(value)
    
    useEffect(() => {
        const duration = 500
        const start = displayValue
        const end = value
        const startTime = Date.now()
        
        const animate = () => {
            const now = Date.now()
            const progress = Math.min((now - startTime) / duration, 1)
            const eased = 1 - Math.pow(1 - progress, 3)
            setDisplayValue(start + (end - start) * eased)
            
            if (progress < 1) {
                requestAnimationFrame(animate)
            }
        }
        
        requestAnimationFrame(animate)
    }, [value])
    
    return <span>{prefix}{displayValue?.toFixed(decimals)}{suffix}</span>
}

export default function BentoDashboard({ selectedAsset, assetType, onAssetSelect }) {
    const { user } = useAuth()
    const [prediction, setPrediction] = useState(null)
    const [quote, setQuote] = useState(null)
    const [historical, setHistorical] = useState(null)
    const [isLoading, setIsLoading] = useState(false)
    const [error, setError] = useState(null)
    const [predictionDays, setPredictionDays] = useState(0.04)
    const [period, setPeriod] = useState('1h')
    
    // Fetch data
    useEffect(() => {
        if (selectedAsset) {
            fetchData()
        }
    }, [selectedAsset, assetType, predictionDays, period])
    
    // Quote polling
    useEffect(() => {
        if (!selectedAsset) return
        
        const fetchQuote = async () => {
            try {
                const res = await axios.get(`${API_URL}/quote/${encodeURIComponent(selectedAsset)}`)
                if (res.data && !res.data.error) {
                    setQuote(res.data)
                }
            } catch (e) {
                console.warn('Quote error:', e.message)
            }
        }
        
        fetchQuote()
        const interval = setInterval(fetchQuote, 3000)
        return () => clearInterval(interval)
    }, [selectedAsset])
    
    const fetchData = async () => {
        if (!selectedAsset) return
        setIsLoading(true)
        setError(null)
        
        try {
            const isCrypto = assetType === 'crypto'
            
            const [predRes, histRes] = await Promise.all([
                axios.get(`${API_URL}/predict/${selectedAsset}`, {
                    params: { days: predictionDays, is_crypto: isCrypto }
                }),
                axios.get(`${API_URL}/historical/${selectedAsset}`, {
                    params: { is_crypto: isCrypto, period: period }
                })
            ])
            
            setPrediction(predRes.data)
            setHistorical(histRes.data)
        } catch (err) {
            setError(err.response?.data?.detail || 'Failed to fetch data')
        } finally {
            setIsLoading(false)
        }
    }
    
    // Welcome screen
    if (!selectedAsset) {
        return (
            <div className="h-screen flex items-center justify-center p-8 bg-gradient-to-br from-slate-50 to-slate-100">
                <motion.div
                    initial={{ opacity: 0, y: 20 }}
                    animate={{ opacity: 1, y: 0 }}
                    className="text-center max-w-2xl"
                >
                    <motion.div
                        animate={{ y: [0, -10, 0] }}
                        transition={{ duration: 3, repeat: Infinity }}
                        className="text-8xl mb-8"
                    >
                        🔮
                    </motion.div>
                    <h2 className="text-4xl font-bold mb-4 text-slate-800">
                        Welcome to NexusTrader
                    </h2>
                    <p className="text-slate-500 text-lg mb-8">
                        Select an asset from the sidebar to view AI-powered predictions
                    </p>
                    
                    <div className="grid grid-cols-3 gap-4">
                        {['AAPL', 'TSLA', 'BTC/USDT'].map((asset, i) => (
                            <motion.button
                                key={asset}
                                initial={{ opacity: 0, y: 20 }}
                                animate={{ opacity: 1, y: 0 }}
                                transition={{ delay: i * 0.1 }}
                                whileHover={{ scale: 1.05, y: -5 }}
                                whileTap={{ scale: 0.95 }}
                                onClick={() => onAssetSelect(asset, asset.includes('/') ? 'crypto' : 'stock')}
                                className="bg-white p-6 rounded-2xl shadow-lg hover:shadow-xl transition-all border border-slate-200"
                            >
                                <div className="text-3xl mb-2">{asset.includes('/') ? '₿' : '📈'}</div>
                                <div className="font-semibold text-slate-800">{asset.split('/')[0]}</div>
                                <div className="text-xs text-slate-400">
                                    {asset.includes('/') ? 'Crypto' : 'Stock'}
                                </div>
                            </motion.button>
                        ))}
                    </div>
                </motion.div>
            </div>
        )
    }
    
    const priceChange = quote?.change || 0
    const priceChangePercent = quote?.change_percent || 0
    const isPositive = priceChange >= 0
    const confidence = prediction?.confidence || 0
    const predictedPrice = prediction?.predictions?.[prediction.predictions.length - 1] || 0
    const currentPrice = quote?.price || prediction?.current_price || 0
    const predictedChange = currentPrice ? ((predictedPrice - currentPrice) / currentPrice) * 100 : 0
    
    return (
        <div className="min-h-screen bg-gradient-to-br from-slate-50 via-white to-slate-100 p-6">
            {/* Header */}
            <motion.div 
                initial={{ opacity: 0, y: -20 }}
                animate={{ opacity: 1, y: 0 }}
                className="flex items-center justify-between mb-6"
            >
                <div className="flex items-center gap-4">
                    <h1 className="text-3xl font-bold text-slate-800">
                        {selectedAsset.split('/')[0]}
                    </h1>
                    <span className="px-3 py-1 rounded-full text-xs font-medium bg-slate-200 text-slate-600">
                        {assetType?.toUpperCase()}
                    </span>
                </div>
                
                <motion.button
                    whileHover={{ scale: 1.05 }}
                    whileTap={{ scale: 0.95 }}
                    onClick={fetchData}
                    disabled={isLoading}
                    className="flex items-center gap-2 px-4 py-2 bg-slate-800 text-white rounded-xl text-sm font-medium hover:bg-slate-700 transition-colors"
                >
                    <RefreshCw className={`w-4 h-4 ${isLoading ? 'animate-spin' : ''}`} />
                    Refresh
                </motion.button>
            </motion.div>
            
            {/* Error */}
            {error && (
                <motion.div 
                    initial={{ opacity: 0 }}
                    animate={{ opacity: 1 }}
                    className="mb-6 p-4 bg-red-50 border border-red-200 rounded-2xl text-red-600"
                >
                    {error}
                </motion.div>
            )}
            
            {/* Bento Grid */}
            <div className="grid grid-cols-12 gap-4 auto-rows-[120px]">
                {/* Main Price Card - Large */}
                <motion.div
                    initial={{ opacity: 0, scale: 0.95 }}
                    animate={{ opacity: 1, scale: 1 }}
                    transition={{ delay: 0.1 }}
                    className="col-span-12 md:col-span-6 row-span-2 bg-white rounded-3xl p-6 shadow-sm border border-slate-200 flex flex-col justify-between"
                >
                    <div className="flex items-start justify-between">
                        <div>
                            <p className="text-slate-400 text-sm font-medium mb-1">Current Price</p>
                            <h2 className="text-5xl font-bold text-slate-800">
                                {quote ? (
                                    <AnimatedNumber value={quote.price} prefix="$" />
                                ) : (
                                    <span className="text-slate-300">--</span>
                                )}
                            </h2>
                        </div>
                        <div className={`flex items-center gap-1 px-3 py-1.5 rounded-full text-sm font-semibold ${
                            isPositive ? 'bg-emerald-100 text-emerald-700' : 'bg-red-100 text-red-700'
                        }`}>
                            {isPositive ? <ArrowUpRight className="w-4 h-4" /> : <ArrowDownRight className="w-4 h-4" />}
                            {Math.abs(priceChangePercent).toFixed(2)}%
                        </div>
                    </div>
                    
                    <div className="grid grid-cols-4 gap-4 mt-4">
                        <div>
                            <p className="text-xs text-slate-400">Open</p>
                            <p className="font-semibold text-slate-700">${quote?.open?.toFixed(2) || '--'}</p>
                        </div>
                        <div>
                            <p className="text-xs text-slate-400">High</p>
                            <p className="font-semibold text-emerald-600">${quote?.high?.toFixed(2) || '--'}</p>
                        </div>
                        <div>
                            <p className="text-xs text-slate-400">Low</p>
                            <p className="font-semibold text-red-600">${quote?.low?.toFixed(2) || '--'}</p>
                        </div>
                        <div>
                            <p className="text-xs text-slate-400">Volume</p>
                            <p className="font-semibold text-slate-700">
                                {quote?.volume ? (quote.volume / 1000000).toFixed(1) + 'M' : '--'}
                            </p>
                        </div>
                    </div>
                </motion.div>
                
                {/* Prediction Card */}
                <motion.div
                    initial={{ opacity: 0, scale: 0.95 }}
                    animate={{ opacity: 1, scale: 1 }}
                    transition={{ delay: 0.2 }}
                    className="col-span-6 md:col-span-3 row-span-2 bg-gradient-to-br from-[#c8ff00] to-[#00ff88] rounded-3xl p-6 shadow-sm text-black flex flex-col justify-between"
                >
                    <div className="flex items-center gap-2">
                        <Sparkles className="w-5 h-5" />
                        <span className="text-sm font-medium opacity-90">AI Prediction</span>
                    </div>
                    
                    <div>
                        <h3 className="text-4xl font-bold mb-1">
                            ${predictedPrice.toFixed(2)}
                        </h3>
                        <div className={`flex items-center gap-1 text-sm ${predictedChange >= 0 ? 'text-emerald-300' : 'text-red-300'}`}>
                            {predictedChange >= 0 ? <ChevronUp className="w-4 h-4" /> : <ChevronDown className="w-4 h-4" />}
                            {Math.abs(predictedChange).toFixed(2)}% from current
                        </div>
                    </div>
                    
                    <div className="text-xs opacity-75">
                        {predictionDays < 1 ? `${Math.round(predictionDays * 24)}h` : `${predictionDays}d`} forecast
                    </div>
                </motion.div>
                
                {/* Confidence Gauge */}
                <motion.div
                    initial={{ opacity: 0, scale: 0.95 }}
                    animate={{ opacity: 1, scale: 1 }}
                    transition={{ delay: 0.3 }}
                    className="col-span-6 md:col-span-3 row-span-2 bg-white rounded-3xl p-6 shadow-sm border border-slate-200 flex flex-col justify-between"
                >
                    <div className="flex items-center gap-2 text-slate-400">
                        <Target className="w-5 h-5" />
                        <span className="text-sm font-medium">Confidence</span>
                    </div>
                    
                    <div className="relative flex items-center justify-center">
                        <svg className="w-28 h-28 transform -rotate-90">
                            <circle
                                cx="56" cy="56" r="48"
                                stroke="#e2e8f0"
                                strokeWidth="8"
                                fill="none"
                            />
                            <motion.circle
                                cx="56" cy="56" r="48"
                                stroke={confidence >= 70 ? '#10b981' : confidence >= 50 ? '#f59e0b' : '#ef4444'}
                                strokeWidth="8"
                                fill="none"
                                strokeLinecap="round"
                                initial={{ strokeDasharray: '0 302' }}
                                animate={{ strokeDasharray: `${(confidence / 100) * 302} 302` }}
                                transition={{ duration: 1, ease: 'easeOut' }}
                            />
                        </svg>
                        <div className="absolute text-center">
                            <span className="text-3xl font-bold text-slate-800">{confidence.toFixed(0)}</span>
                            <span className="text-slate-400 text-sm">%</span>
                        </div>
                    </div>
                    
                    <p className="text-center text-xs text-slate-500">
                        {confidence >= 70 ? 'High confidence' : confidence >= 50 ? 'Moderate' : 'Low confidence'}
                    </p>
                </motion.div>
                
                {/* Range Selector */}
                <motion.div
                    initial={{ opacity: 0, scale: 0.95 }}
                    animate={{ opacity: 1, scale: 1 }}
                    transition={{ delay: 0.4 }}
                    className="col-span-12 md:col-span-6 row-span-1 bg-white rounded-3xl p-4 shadow-sm border border-slate-200"
                >
                    <div className="flex items-center justify-between h-full">
                        <span className="text-sm font-medium text-slate-500">Range</span>
                        <div className="flex gap-1">
                            {['1h', '12h', '1d', '1w', '1mo', '3mo', '6mo', '1y'].map(p => (
                                <button
                                    key={p}
                                    onClick={() => setPeriod(p)}
                                    className={`px-3 py-1.5 rounded-lg text-xs font-medium transition-all ${
                                        period === p
                                            ? 'bg-slate-800 text-white'
                                            : 'bg-slate-100 text-slate-600 hover:bg-slate-200'
                                    }`}
                                >
                                    {p.toUpperCase()}
                                </button>
                            ))}
                        </div>
                    </div>
                </motion.div>
                
                {/* Forecast Selector */}
                <motion.div
                    initial={{ opacity: 0, scale: 0.95 }}
                    animate={{ opacity: 1, scale: 1 }}
                    transition={{ delay: 0.5 }}
                    className="col-span-12 md:col-span-6 row-span-1 bg-white rounded-3xl p-4 shadow-sm border border-slate-200"
                >
                    <div className="flex items-center justify-between h-full">
                        <span className="text-sm font-medium text-slate-500">Forecast</span>
                        <div className="flex gap-1">
                            {[
                                { value: 0.04, label: '1H' },
                                { value: 0.5, label: '12H' },
                                { value: 1, label: '1D' },
                                { value: 7, label: '7D' },
                                { value: 14, label: '14D' },
                                { value: 30, label: '30D' }
                            ].map(({ value, label }) => (
                                <button
                                    key={value}
                                    onClick={() => setPredictionDays(value)}
                                    className={`px-3 py-1.5 rounded-lg text-xs font-medium transition-all ${
                                        predictionDays === value
                                            ? 'bg-[#7cb800] text-white'
                                            : 'bg-[#c8ff00]/20 text-[#7cb800] hover:bg-[#c8ff00]/30'
                                    }`}
                                >
                                    {label}
                                </button>
                            ))}
                        </div>
                    </div>
                </motion.div>
                
                {/* Recommendation Card */}
                <motion.div
                    initial={{ opacity: 0, scale: 0.95 }}
                    animate={{ opacity: 1, scale: 1 }}
                    transition={{ delay: 0.6 }}
                    className={`col-span-6 md:col-span-3 row-span-1 rounded-3xl p-5 shadow-sm flex items-center justify-between ${
                        prediction?.analysis?.recommendation === 'BUY' 
                            ? 'bg-gradient-to-r from-emerald-500 to-green-500 text-white'
                            : prediction?.analysis?.recommendation === 'SELL'
                                ? 'bg-gradient-to-r from-red-500 to-rose-500 text-white'
                                : 'bg-gradient-to-r from-amber-400 to-orange-400 text-white'
                    }`}
                >
                    <div>
                        <p className="text-xs opacity-80">Recommendation</p>
                        <p className="text-2xl font-bold">{prediction?.analysis?.recommendation || 'HOLD'}</p>
                    </div>
                    <Zap className="w-8 h-8 opacity-50" />
                </motion.div>
                
                {/* Model Weights Preview */}
                <motion.div
                    initial={{ opacity: 0, scale: 0.95 }}
                    animate={{ opacity: 1, scale: 1 }}
                    transition={{ delay: 0.7 }}
                    className="col-span-6 md:col-span-3 row-span-1 bg-white rounded-3xl p-5 shadow-sm border border-slate-200"
                >
                    <div className="flex items-center justify-between h-full">
                        <div className="flex items-center gap-2">
                            <Brain className="w-5 h-5 text-slate-400" />
                            <span className="text-sm font-medium text-slate-500">Models</span>
                        </div>
                        <div className="flex gap-2">
                            {['LSTM', 'Prophet', 'XGB'].map((model, i) => (
                                <div key={model} className="text-center">
                                    <div className={`w-8 h-8 rounded-full flex items-center justify-center text-xs font-bold ${
                                        i === 0 ? 'bg-cyan-100 text-cyan-700' :
                                        i === 1 ? 'bg-purple-100 text-purple-700' :
                                        'bg-emerald-100 text-emerald-700'
                                    }`}>
                                        {Math.round((prediction?.individual_predictions?.[['lstm', 'prophet', 'xgboost'][i]]?.weight || 0.33) * 100)}
                                    </div>
                                </div>
                            ))}
                        </div>
                    </div>
                </motion.div>
                
                {/* Technical Indicators Preview */}
                <motion.div
                    initial={{ opacity: 0, scale: 0.95 }}
                    animate={{ opacity: 1, scale: 1 }}
                    transition={{ delay: 0.8 }}
                    className="col-span-6 md:col-span-3 row-span-1 bg-white rounded-3xl p-5 shadow-sm border border-slate-200"
                >
                    <div className="flex items-center justify-between h-full">
                        <div className="flex items-center gap-2">
                            <Activity className="w-5 h-5 text-slate-400" />
                            <span className="text-sm font-medium text-slate-500">RSI</span>
                        </div>
                        <div className="text-right">
                            <p className="text-2xl font-bold text-slate-800">
                                {prediction?.technical_indicators?.rsi?.toFixed(0) || '--'}
                            </p>
                            <p className="text-xs text-slate-400">
                                {(prediction?.technical_indicators?.rsi || 50) > 70 ? 'Overbought' :
                                 (prediction?.technical_indicators?.rsi || 50) < 30 ? 'Oversold' : 'Neutral'}
                            </p>
                        </div>
                    </div>
                </motion.div>
                
                {/* MACD Indicator */}
                <motion.div
                    initial={{ opacity: 0, scale: 0.95 }}
                    animate={{ opacity: 1, scale: 1 }}
                    transition={{ delay: 0.9 }}
                    className="col-span-6 md:col-span-3 row-span-1 bg-white rounded-3xl p-5 shadow-sm border border-slate-200"
                >
                    <div className="flex items-center justify-between h-full">
                        <div className="flex items-center gap-2">
                            <BarChart3 className="w-5 h-5 text-slate-400" />
                            <span className="text-sm font-medium text-slate-500">MACD</span>
                        </div>
                        <div className={`px-3 py-1 rounded-full text-xs font-semibold ${
                            (prediction?.technical_indicators?.macd || 0) >= 0
                                ? 'bg-emerald-100 text-emerald-700'
                                : 'bg-red-100 text-red-700'
                        }`}>
                            {(prediction?.technical_indicators?.macd || 0) >= 0 ? 'Bullish' : 'Bearish'}
                        </div>
                    </div>
                </motion.div>
                
                {/* Volume Card */}
                <motion.div
                    initial={{ opacity: 0, scale: 0.95 }}
                    animate={{ opacity: 1, scale: 1 }}
                    transition={{ delay: 1.0 }}
                    className="col-span-6 md:col-span-3 row-span-1 bg-gradient-to-br from-slate-700 to-slate-800 rounded-3xl p-5 shadow-sm text-white"
                >
                    <div className="flex items-center justify-between h-full">
                        <div>
                            <p className="text-xs text-slate-400">24h Volume</p>
                            <p className="text-xl font-bold">
                                {quote?.volume ? `$${(quote.volume * (quote.price || 1) / 1000000000).toFixed(2)}B` : '--'}
                            </p>
                        </div>
                        <div className="w-12 h-12 rounded-full bg-white/10 flex items-center justify-center">
                            <Activity className="w-6 h-6" />
                        </div>
                    </div>
                </motion.div>
                
            </div>
        </div>
    )
}
