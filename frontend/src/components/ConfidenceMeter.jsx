import { motion } from 'framer-motion'

const LAYER_META = {
    macro:           { label: 'Macro Environment',  icon: '🌍', desc: 'VIX · Yield Curve · Dollar' },
    market_breadth:  { label: 'Market Breadth',     icon: '📊', desc: 'SPY · QQQ · IWM trend' },
    fundamentals:    { label: 'Fundamentals',        icon: '📋', desc: 'P/E · PEG · Analyst consensus' },
    options:         { label: 'Options Flow',        icon: '⚡', desc: 'Put/Call ratio · IV skew' },
    smart_money:     { label: 'Smart Money',         icon: '🏦', desc: 'Insider buys · Institutional' },
    earnings:        { label: 'Earnings Catalyst',   icon: '📅', desc: 'Days-to-earnings · Beat rate' },
    sector:          { label: 'Sector Momentum',     icon: '🔄', desc: 'Relative strength vs ETF' },
    fear_greed:      { label: 'Fear & Greed',        icon: '😱', desc: 'CNN index · Sentiment' },
    social:          { label: 'Social Buzz',          icon: '💬', desc: 'Reddit WSB · StockTwits' },
    google_trends:   { label: 'Google Trends',       icon: '🔍', desc: 'Search interest surge' },
    seasonal:        { label: 'Seasonal Pattern',    icon: '🗓️', desc: 'Month/quarter effects' },
    cross_asset:     { label: 'Cross-Asset',          icon: '🔗', desc: 'Gold · Oil · Bonds' },
    chart_patterns:  { label: 'Chart Patterns',      icon: '🕯️', desc: 'Candlestick · MA cross · Volume' },
    news_sentiment:  { label: 'News Sentiment',      icon: '📰', desc: 'Yahoo · Finviz · Bing News' },
}

function SignalBar({ name, score, index }) {
    const meta = LAYER_META[name] || { label: name, icon: '📈', desc: '' }
    const pct = Math.abs(score || 0)
    const isPos = (score || 0) >= 0
    const isBull = (score || 0) > 0.05
    const isBear = (score || 0) < -0.05
    const isNeutral = !isBull && !isBear

    const barColor = isBull ? '#00ff88' : isBear ? '#ef4444' : '#6b7280'
    const textColor = isBull ? 'text-green-400' : isBear ? 'text-red-400' : 'text-gray-500'
    const label = isBull ? 'Bullish' : isBear ? 'Bearish' : 'Neutral'

    return (
        <motion.div
            initial={{ opacity: 0, x: -8 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ delay: 0.1 + index * 0.04 }}
            className="group"
        >
            <div className="flex items-center justify-between mb-1">
                <div className="flex items-center gap-1.5 min-w-0">
                    <span className="text-xs">{meta.icon}</span>
                    <span className="text-[11px] font-medium text-gray-300 truncate">{meta.label}</span>
                    <span className="text-[10px] text-gray-600 hidden sm:block truncate">{meta.desc}</span>
                </div>
                <span className={`text-[10px] font-semibold shrink-0 ml-2 ${textColor}`}>
                    {label}
                </span>
            </div>
            {/* Symmetric bar — neutral centre, extends left (bear) or right (bull) */}
            <div className="h-1 rounded-full bg-white/5 overflow-hidden relative">
                {/* Center marker */}
                <div className="absolute inset-y-0 left-1/2 w-px bg-white/10" />
                {/* Signal bar */}
                <motion.div
                    initial={{ width: 0, left: isPos ? '50%' : undefined, right: !isPos ? '50%' : undefined }}
                    animate={{ width: `${pct * 50}%` }}
                    transition={{ duration: 0.8, delay: 0.15 + index * 0.04, ease: 'easeOut' }}
                    className="absolute top-0 bottom-0 rounded-full"
                    style={{
                        backgroundColor: barColor,
                        left: isNeutral ? 'calc(50% - 1px)' : isBull ? '50%' : undefined,
                        right: isBear ? '50%' : undefined,
                        width: isNeutral ? '2px' : undefined,
                    }}
                />
            </div>
        </motion.div>
    )
}

export default function ConfidenceMeter({ confidence, individual, oracleSignals }) {
    const getConfidenceColor = (v) => {
        if (v >= 85) return '#00ff88'
        if (v >= 75) return '#c8ff00'
        if (v >= 60) return '#eab308'
        return '#ef4444'
    }

    const getConfidenceLabel = (v) => {
        if (v >= 90) return 'Exceptional'
        if (v >= 85) return 'Very High'
        if (v >= 75) return 'High'
        if (v >= 60) return 'Moderate'
        return 'Low'
    }

    const models = individual ? [
        { name: 'LSTM',    ...individual.lstm,    icon: '🧠', desc: 'Deep Learning',   color: '#3b82f6' },
        { name: 'Prophet', ...individual.prophet,  icon: '📈', desc: 'Time Series',     color: '#f97316' },
        { name: 'XGBoost', ...individual.xgboost,  icon: '🌲', desc: 'Gradient Boost',  color: '#00ff88' },
        { name: 'ARIMA',   ...individual.arima,    icon: '📊', desc: 'Statistical',     color: '#c8ff00' },
    ].filter(m => m.confidence !== undefined) : []

    // Sort oracle signals by absolute strength (strongest first)
    const oracleLayers = oracleSignals
        ? Object.entries(oracleSignals).sort((a, b) => Math.abs(b[1]) - Math.abs(a[1]))
        : []

    const bullCount  = oracleLayers.filter(([, v]) => v > 0.05).length
    const bearCount  = oracleLayers.filter(([, v]) => v < -0.05).length
    const totalCount = oracleLayers.length

    return (
        <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.3 }}
            className="bg-[#0d0d15] rounded-xl border border-[#c8ff00]/10 overflow-hidden"
        >
            {/* Header */}
            <div className="flex items-center justify-between px-4 py-3 border-b border-[#c8ff00]/10">
                <div className="flex items-center gap-3">
                    <span className="text-lg">🎯</span>
                    <h3 className="text-sm font-semibold text-white">AI Confidence</h3>
                    {totalCount > 0 && (
                        <div className="flex items-center gap-1">
                            <span className="text-[10px] px-1.5 py-0.5 rounded bg-green-500/15 text-green-400 font-medium">
                                {bullCount}↑
                            </span>
                            <span className="text-[10px] px-1.5 py-0.5 rounded bg-red-500/15 text-red-400 font-medium">
                                {bearCount}↓
                            </span>
                        </div>
                    )}
                </div>
                <div className="px-2 py-0.5 rounded bg-[#c8ff00]/20 text-[#c8ff00] text-xs font-medium">
                    {totalCount > 0 ? `${totalCount} Signals` : `${models.length} Models`}
                </div>
            </div>

            <div className="p-4">
                {/* Overall confidence — Circular gauge */}
                <div className="flex items-center gap-6 mb-5">
                    <div className="relative w-24 h-24 flex-shrink-0">
                        <svg className="w-full h-full transform -rotate-90">
                            <circle cx="48" cy="48" r="42" stroke="rgba(200,255,0,0.05)"
                                strokeWidth="8" fill="none" />
                            <motion.circle
                                cx="48" cy="48" r="42"
                                stroke={getConfidenceColor(confidence)}
                                strokeWidth="8" fill="none" strokeLinecap="round"
                                strokeDasharray={`${2 * Math.PI * 42}`}
                                initial={{ strokeDashoffset: 2 * Math.PI * 42 }}
                                animate={{ strokeDashoffset: 2 * Math.PI * 42 * (1 - (confidence || 0) / 100) }}
                                transition={{ duration: 1.5, ease: 'easeOut', delay: 0.3 }}
                            />
                        </svg>
                        <div className="absolute inset-0 flex flex-col items-center justify-center">
                            <motion.span
                                initial={{ opacity: 0 }}
                                animate={{ opacity: 1 }}
                                transition={{ delay: 0.5 }}
                                className="text-2xl font-bold text-white"
                            >
                                {confidence?.toFixed(0)}%
                            </motion.span>
                            <span className="text-[10px] text-gray-500">confidence</span>
                        </div>
                    </div>

                    <div className="flex-1">
                        <div className="flex items-center gap-2 mb-1">
                            <span className="text-sm font-semibold" style={{ color: getConfidenceColor(confidence) }}>
                                {getConfidenceLabel(confidence)} Confidence
                            </span>
                        </div>
                        <p className="text-[11px] text-gray-500 leading-relaxed">
                            {totalCount > 0
                                ? `Oracle fused ${totalCount} market signals — macro, fundamentals, options flow, smart money, social buzz, earnings, sector momentum & more.`
                                : 'Ensemble prediction based on model agreement, backtesting accuracy, and technical indicators.'}
                        </p>
                        {totalCount > 0 && (
                            <div className="mt-2 flex items-center gap-2 text-[10px]">
                                <span className="text-green-400 font-medium">{bullCount} bullish</span>
                                <span className="text-gray-600">·</span>
                                <span className="text-gray-400">{totalCount - bullCount - bearCount} neutral</span>
                                <span className="text-gray-600">·</span>
                                <span className="text-red-400 font-medium">{bearCount} bearish</span>
                            </div>
                        )}
                    </div>
                </div>

                {/* Oracle signal layers */}
                {oracleLayers.length > 0 && (
                    <div className="mb-4">
                        <div className="flex items-center gap-2 mb-3">
                            <div className="h-px flex-1 bg-white/5" />
                            <span className="text-[10px] text-gray-600 uppercase tracking-widest">Market Oracle — 12 Signal Layers</span>
                            <div className="h-px flex-1 bg-white/5" />
                        </div>
                        <div className="space-y-2.5">
                            {oracleLayers.map(([name, score], i) => (
                                <SignalBar key={name} name={name} score={score} index={i} />
                            ))}
                        </div>
                    </div>
                )}

                {/* Individual ML model bars (shown when no oracle, or always) */}
                {models.length > 0 && (
                    <div>
                        {oracleLayers.length > 0 && (
                            <div className="flex items-center gap-2 mb-3">
                                <div className="h-px flex-1 bg-white/5" />
                                <span className="text-[10px] text-gray-600 uppercase tracking-widest">ML Models</span>
                                <div className="h-px flex-1 bg-white/5" />
                            </div>
                        )}
                        <div className="space-y-3">
                            {models.map((model, index) => (
                                <motion.div
                                    key={model.name}
                                    initial={{ opacity: 0, x: -10 }}
                                    animate={{ opacity: 1, x: 0 }}
                                    transition={{ delay: 0.4 + index * 0.1 }}
                                >
                                    <div className="flex items-center justify-between mb-1.5">
                                        <div className="flex items-center gap-2">
                                            <div className="w-2 h-2 rounded-full" style={{ backgroundColor: model.color }} />
                                            <span className="text-xs font-medium text-gray-300">{model.name}</span>
                                            <span className="text-[10px] text-gray-600">{model.desc}</span>
                                        </div>
                                        <div className="flex items-center gap-3">
                                            <span className="text-xs text-gray-500">
                                                Weight: <span className="text-gray-400">{((model.weight || 0.25) * 100).toFixed(0)}%</span>
                                            </span>
                                            <span className="text-xs font-semibold" style={{ color: getConfidenceColor(model.confidence) }}>
                                                {model.confidence?.toFixed(1)}%
                                            </span>
                                        </div>
                                    </div>
                                    <div className="h-1.5 rounded-full bg-white/5 overflow-hidden">
                                        <motion.div
                                            initial={{ width: 0 }}
                                            animate={{ width: `${model.confidence || 0}%` }}
                                            transition={{ duration: 1, delay: 0.5 + index * 0.1 }}
                                            className="h-full rounded-full"
                                            style={{ backgroundColor: model.color }}
                                        />
                                    </div>
                                </motion.div>
                            ))}
                        </div>
                    </div>
                )}
            </div>
        </motion.div>
    )
}
