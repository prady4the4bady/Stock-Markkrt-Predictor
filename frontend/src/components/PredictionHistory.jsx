import { useState, useEffect } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { ChevronDown, ChevronUp, RefreshCw } from 'lucide-react'
import api from '../utils/api'

function StatBadge({ label, value, color }) {
    return (
        <div className="flex flex-col items-center gap-0.5">
            <span className="text-xl font-black" style={{ color, fontFamily: "'Outfit', sans-serif" }}>
                {value}
            </span>
            <span className="text-[10px] text-gray-500 uppercase tracking-wide">{label}</span>
        </div>
    )
}

function OutcomeRow({ item, index }) {
    const correct = item.direction_correct
    const hitTarget = item.target_hit
    const hitStop  = item.stop_hit
    const pct = item.pct_change_actual

    const rec = item.recommendation || 'HOLD'
    const recColor = rec === 'BUY' ? '#00ff88' : rec === 'SELL' ? '#ef4444' : '#eab308'

    const outcomeColor = correct ? '#00ff88' : '#ef4444'
    const outcomeLabel = correct ? '✓ Correct' : '✗ Wrong'

    const dateStr = item.predicted_at
        ? new Date(item.predicted_at).toLocaleDateString('en-US', { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' })
        : '—'

    return (
        <motion.div
            initial={{ opacity: 0, x: -8 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ delay: index * 0.04 }}
            className="grid items-center gap-2 py-2 px-3 rounded-lg text-[11px]"
            style={{
                gridTemplateColumns: '80px 52px 1fr 1fr 1fr 70px 60px',
                background: correct ? 'rgba(0,255,136,0.03)' : 'rgba(239,68,68,0.03)',
                borderLeft: `2px solid ${outcomeColor}40`,
            }}
        >
            <span className="text-gray-400">{dateStr}</span>
            <span className="font-bold text-center" style={{ color: recColor }}>{rec}</span>
            <span className="text-gray-400 text-right">
                ${item.price_at_prediction?.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
            </span>
            <span className="text-gray-400 text-right">
                {item.price_at_outcome
                    ? `$${item.price_at_outcome.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`
                    : '—'}
            </span>
            <span className={`text-right font-semibold ${pct >= 0 ? 'text-green-400' : 'text-red-400'}`}>
                {pct !== null && pct !== undefined ? `${pct >= 0 ? '+' : ''}${pct.toFixed(2)}%` : '—'}
            </span>
            <div className="flex items-center gap-1 justify-center">
                {hitTarget && <span className="text-[9px] text-green-400 font-semibold">🎯 Target</span>}
                {hitStop   && <span className="text-[9px] text-red-400  font-semibold">🛑 Stop</span>}
            </div>
            <span className="font-semibold text-center" style={{ color: outcomeColor }}>
                {outcomeLabel}
            </span>
        </motion.div>
    )
}

export default function PredictionHistory({ symbol }) {
    const [outcomes, setOutcomes]   = useState([])
    const [stats, setStats]         = useState(null)
    const [layerAcc, setLayerAcc]   = useState({})
    const [isLoading, setIsLoading] = useState(false)
    const [expanded, setExpanded]   = useState(false)
    const [showLayers, setShowLayers] = useState(false)

    useEffect(() => {
        if (symbol) fetchData()
    }, [symbol])

    const fetchData = async () => {
        setIsLoading(true)
        try {
            const clean = symbol.split('/')[0]
            const [outRes, accRes] = await Promise.allSettled([
                api.get(`/predict-outcomes/${clean}`, { params: { limit: 15 } }),
                api.get('/accuracy-stats', { params: { symbol: clean, days: 30 } }),
            ])

            if (outRes.status === 'fulfilled') {
                setOutcomes(outRes.value.data.outcomes || [])
            }
            if (accRes.status === 'fulfilled') {
                setStats(accRes.value.data.overall)
                setLayerAcc(accRes.value.data.layer_accuracy || {})
            }
        } catch (e) {
            console.warn('[PredictionHistory] fetch failed:', e)
        } finally {
            setIsLoading(false)
        }
    }

    const hasData = outcomes.length > 0
    const dirAcc  = stats?.direction_accuracy
    const tgtRate = stats?.target_hit_rate
    const avgRR   = stats?.avg_risk_reward
    const calib   = stats?.calibration_factor

    const accColor = (acc) =>
        acc >= 65 ? '#00ff88' : acc >= 50 ? '#eab308' : '#ef4444'

    return (
        <motion.div
            initial={{ opacity: 0, y: 16 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.3 }}
            className="rounded-xl border border-white/[0.06] overflow-hidden"
            style={{ background: '#0a0a12' }}
        >
            {/* Header */}
            <div
                className="flex items-center justify-between px-4 py-3 border-b border-white/[0.05] cursor-pointer select-none"
                onClick={() => setExpanded(e => !e)}
            >
                <div className="flex items-center gap-3">
                    <span className="text-base">📋</span>
                    <h3 className="text-sm font-semibold text-white">Prediction Track Record</h3>
                    {hasData && (
                        <span className="text-[10px] px-1.5 py-0.5 rounded bg-white/5 text-gray-400">
                            {outcomes.length} verified
                        </span>
                    )}
                    {!hasData && !isLoading && (
                        <span className="text-[10px] text-gray-600">No verified predictions yet</span>
                    )}
                </div>

                <div className="flex items-center gap-3">
                    {stats && stats.total > 0 && (
                        <span
                            className="text-xs font-bold px-2 py-0.5 rounded"
                            style={{
                                background: `${accColor(dirAcc)}15`,
                                color: accColor(dirAcc),
                            }}
                        >
                            {dirAcc?.toFixed(0)}% accurate
                        </span>
                    )}
                    <motion.button
                        whileHover={{ scale: 1.1 }}
                        whileTap={{ scale: 0.9 }}
                        onClick={(e) => { e.stopPropagation(); fetchData() }}
                        disabled={isLoading}
                        className="p-1.5 rounded hover:bg-white/5"
                    >
                        <RefreshCw className={`w-3.5 h-3.5 text-gray-500 ${isLoading ? 'animate-spin' : ''}`} />
                    </motion.button>
                    {expanded ? <ChevronUp className="w-4 h-4 text-gray-500" /> : <ChevronDown className="w-4 h-4 text-gray-500" />}
                </div>
            </div>

            <AnimatePresence>
            {expanded && (
                <motion.div
                    initial={{ height: 0, opacity: 0 }}
                    animate={{ height: 'auto', opacity: 1 }}
                    exit={{ height: 0, opacity: 0 }}
                    transition={{ duration: 0.25 }}
                    style={{ overflow: 'hidden' }}
                >
                    {/* Accuracy stats bar */}
                    {stats && stats.total > 0 && (
                        <div className="flex items-center justify-around px-6 py-4 border-b border-white/[0.04]">
                            <StatBadge
                                label="Direction Accuracy"
                                value={`${dirAcc?.toFixed(0)}%`}
                                color={accColor(dirAcc)}
                            />
                            <div className="w-px h-10 bg-white/5" />
                            <StatBadge
                                label="Target Hit Rate"
                                value={`${tgtRate?.toFixed(0)}%`}
                                color={accColor(tgtRate)}
                            />
                            <div className="w-px h-10 bg-white/5" />
                            <StatBadge
                                label="Avg R:R"
                                value={`${avgRR?.toFixed(1)}:1`}
                                color={avgRR >= 2 ? '#00ff88' : avgRR >= 1.5 ? '#eab308' : '#ef4444'}
                            />
                            <div className="w-px h-10 bg-white/5" />
                            <StatBadge
                                label="Confidence Cal."
                                value={`${((calib || 1) * 100).toFixed(0)}%`}
                                color={calib >= 0.9 ? '#00ff88' : calib >= 0.7 ? '#eab308' : '#ef4444'}
                            />
                            <div className="w-px h-10 bg-white/5" />
                            <StatBadge
                                label="Total Verified"
                                value={stats.total}
                                color="rgba(255,255,255,0.5)"
                            />
                        </div>
                    )}

                    {/* Calibration note */}
                    {calib && calib < 0.85 && (
                        <div className="mx-4 mt-3 px-3 py-2 rounded-lg text-[11px] text-yellow-400"
                             style={{ background: 'rgba(234,179,8,0.08)', border: '1px solid rgba(234,179,8,0.2)' }}>
                            ⚙️ Self-learning active: Confidence is being scaled to {((calib || 1) * 100).toFixed(0)}% of stated values based on historical accuracy.
                        </div>
                    )}

                    {/* Layer accuracy toggle */}
                    {Object.keys(layerAcc).length > 0 && (
                        <div className="px-4 pt-3 pb-1">
                            <button
                                className="flex items-center gap-1.5 text-[10px] text-gray-500 hover:text-gray-300 transition-colors"
                                onClick={() => setShowLayers(l => !l)}
                            >
                                {showLayers ? <ChevronUp className="w-3 h-3" /> : <ChevronDown className="w-3 h-3" />}
                                Oracle Layer Accuracy
                            </button>

                            <AnimatePresence>
                            {showLayers && (
                                <motion.div
                                    initial={{ height: 0, opacity: 0 }}
                                    animate={{ height: 'auto', opacity: 1 }}
                                    exit={{ height: 0, opacity: 0 }}
                                    className="mt-2 grid grid-cols-2 gap-1.5 overflow-hidden"
                                >
                                    {Object.entries(layerAcc)
                                        .sort((a, b) => b[1].accuracy - a[1].accuracy)
                                        .map(([layer, data]) => (
                                            <div key={layer}
                                                 className="flex items-center justify-between px-2 py-1 rounded"
                                                 style={{ background: 'rgba(255,255,255,0.03)' }}>
                                                <span className="text-[10px] text-gray-400 capitalize">
                                                    {layer.replace(/_/g, ' ')}
                                                </span>
                                                <div className="flex items-center gap-1.5">
                                                    <div className="w-16 h-1 rounded-full bg-white/5 overflow-hidden">
                                                        <div
                                                            className="h-full rounded-full"
                                                            style={{
                                                                width: `${data.accuracy}%`,
                                                                background: accColor(data.accuracy),
                                                            }}
                                                        />
                                                    </div>
                                                    <span className="text-[10px] font-semibold w-8 text-right"
                                                          style={{ color: accColor(data.accuracy) }}>
                                                        {data.accuracy.toFixed(0)}%
                                                    </span>
                                                </div>
                                            </div>
                                        ))
                                    }
                                </motion.div>
                            )}
                            </AnimatePresence>
                        </div>
                    )}

                    {/* Outcomes table */}
                    <div className="px-4 pb-4 mt-3">
                        {isLoading ? (
                            <div className="flex justify-center py-6">
                                <RefreshCw className="w-4 h-4 text-gray-600 animate-spin" />
                            </div>
                        ) : hasData ? (
                            <>
                                {/* Column headers */}
                                <div className="grid text-[9px] text-gray-600 uppercase tracking-wide px-3 mb-1"
                                     style={{ gridTemplateColumns: '80px 52px 1fr 1fr 1fr 70px 60px' }}>
                                    <span>Date</span>
                                    <span className="text-center">Signal</span>
                                    <span className="text-right">At Predict</span>
                                    <span className="text-right">Actual</span>
                                    <span className="text-right">Move</span>
                                    <span className="text-center">Result</span>
                                    <span className="text-center">Verdict</span>
                                </div>
                                <div className="space-y-1">
                                    {outcomes.map((item, i) => (
                                        <OutcomeRow key={item.id} item={item} index={i} />
                                    ))}
                                </div>
                            </>
                        ) : (
                            <div className="text-center py-8 text-gray-600">
                                <div className="text-3xl mb-2">🕐</div>
                                <p className="text-xs">
                                    Predictions are tracked automatically.<br />
                                    Outcomes appear here after the forecast window expires.
                                </p>
                            </div>
                        )}
                    </div>
                </motion.div>
            )}
            </AnimatePresence>
        </motion.div>
    )
}
