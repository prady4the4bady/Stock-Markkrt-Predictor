/**
 * PredictionAccuracy — Live self-learning feedback loop stats
 * Shows directional accuracy, model weights, and recent prediction outcomes.
 */
import { useState, useEffect } from 'react'
import { motion } from 'framer-motion'
import { Brain, TrendingUp, TrendingDown, Activity, RefreshCw, CheckCircle2, XCircle, Minus } from 'lucide-react'
import axios from 'axios'

const API = '/api'

function AccuracyBar({ value, max = 100, color = '#c8ff00' }) {
  const pct = Math.min(100, Math.max(0, (value / max) * 100))
  return (
    <div className="relative h-1.5 rounded-full overflow-hidden" style={{ background: 'rgba(255,255,255,0.06)' }}>
      <motion.div
        className="absolute inset-y-0 left-0 rounded-full"
        style={{ background: color }}
        initial={{ width: 0 }}
        animate={{ width: `${pct}%` }}
        transition={{ duration: 0.8, ease: 'easeOut' }}
      />
    </div>
  )
}

export default function PredictionAccuracy({ compact = false }) {
  const [stats, setStats] = useState(null)
  const [recent, setRecent] = useState([])
  const [loading, setLoading] = useState(true)
  const [lastRefresh, setLastRefresh] = useState(null)

  const load = async () => {
    try {
      const [accRes, recRes] = await Promise.all([
        axios.get(`${API}/performance/accuracy`),
        axios.get(`${API}/performance/recent?limit=10`),
      ])
      setStats(accRes.data)
      setRecent(recRes.data.outcomes || [])
      setLastRefresh(new Date())
    } catch (e) {
      // Graceful — not critical
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { load() }, [])

  if (loading) {
    return (
      <div className="rounded-2xl p-4" style={{ background: 'rgba(255,255,255,0.03)', border: '1px solid rgba(255,255,255,0.06)' }}>
        <div className="flex items-center gap-2 animate-pulse">
          <Brain size={14} color="#c8ff00" />
          <span className="text-xs text-white/30">Loading accuracy data…</span>
        </div>
      </div>
    )
  }

  const dirAcc = stats?.last_30d_directional_accuracy ?? 0
  const mae    = stats?.last_30d_mae_pct ?? 0
  const total  = stats?.total_predictions_recorded ?? 0
  const evaluated = stats?.total_outcomes_evaluated ?? 0
  const modelWeights = stats?.current_model_weights ?? {}

  const accColor = dirAcc >= 65 ? '#c8ff00' : dirAcc >= 55 ? '#00d4aa' : dirAcc >= 45 ? '#fbbf24' : '#ff5500'

  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      className="rounded-2xl overflow-hidden"
      style={{ background: 'rgba(10,10,20,0.7)', border: '1px solid rgba(255,255,255,0.07)', backdropFilter: 'blur(12px)' }}
    >
      {/* Header */}
      <div className="flex items-center justify-between px-4 pt-4 pb-3" style={{ borderBottom: '1px solid rgba(255,255,255,0.05)' }}>
        <div className="flex items-center gap-2">
          <div className="w-7 h-7 rounded-lg flex items-center justify-center" style={{ background: 'rgba(200,255,0,0.12)' }}>
            <Brain size={14} color="#c8ff00" />
          </div>
          <div>
            <h3 className="text-sm font-bold text-white">Self-Learning Engine</h3>
            <p className="text-[10px] text-white/30">{total.toLocaleString()} predictions recorded · {evaluated} evaluated</p>
          </div>
        </div>
        <button
          onClick={load}
          className="w-7 h-7 rounded-lg flex items-center justify-center transition-colors"
          style={{ background: 'rgba(255,255,255,0.05)' }}
          title="Refresh stats"
        >
          <RefreshCw size={12} color="rgba(255,255,255,0.4)" />
        </button>
      </div>

      <div className="px-4 py-3 space-y-4">
        {/* Key Metrics Row */}
        <div className="grid grid-cols-2 gap-3">
          <div className="rounded-xl p-3" style={{ background: 'rgba(255,255,255,0.03)' }}>
            <p className="text-[10px] text-white/40 uppercase tracking-wider mb-1">Directional Accuracy</p>
            <p className="text-xl font-bold font-mono" style={{ color: accColor }}>{dirAcc.toFixed(1)}%</p>
            <p className="text-[10px] text-white/30 mt-0.5">last 30 days</p>
          </div>
          <div className="rounded-xl p-3" style={{ background: 'rgba(255,255,255,0.03)' }}>
            <p className="text-[10px] text-white/40 uppercase tracking-wider mb-1">Mean Abs Error</p>
            <p className="text-xl font-bold font-mono text-white">{mae.toFixed(2)}%</p>
            <p className="text-[10px] text-white/30 mt-0.5">price deviation</p>
          </div>
        </div>

        {/* Model Weights */}
        {Object.keys(modelWeights).length > 0 && (
          <div>
            <p className="text-[10px] text-white/40 uppercase tracking-wider mb-2">Learned Model Weights</p>
            <div className="space-y-2">
              {Object.entries(modelWeights)
                .sort((a, b) => b[1] - a[1])
                .map(([model, weight]) => (
                  <div key={model}>
                    <div className="flex justify-between mb-1">
                      <span className="text-[11px] text-white/60 capitalize">{model}</span>
                      <span className="text-[11px] font-mono text-white/70">{(weight * 100).toFixed(1)}%</span>
                    </div>
                    <AccuracyBar value={weight * 100} max={40} color={weight >= 0.25 ? '#c8ff00' : '#00d4aa'} />
                  </div>
                ))}
            </div>
          </div>
        )}

        {/* Recent Outcomes */}
        {recent.length > 0 && !compact && (
          <div>
            <p className="text-[10px] text-white/40 uppercase tracking-wider mb-2">Recent Outcomes</p>
            <div className="space-y-1.5">
              {recent.slice(0, 6).map((outcome, i) => {
                const correct = outcome.direction_correct === 1
                const neutral = outcome.direction_correct === null
                return (
                  <div key={i} className="flex items-center justify-between rounded-lg px-2.5 py-1.5" style={{ background: 'rgba(255,255,255,0.03)' }}>
                    <div className="flex items-center gap-2">
                      {neutral
                        ? <Minus size={12} color="rgba(255,255,255,0.3)" />
                        : correct
                          ? <CheckCircle2 size={12} color="#c8ff00" />
                          : <XCircle size={12} color="#ff5500" />
                      }
                      <span className="text-[11px] font-mono text-white/70">{outcome.symbol}</span>
                    </div>
                    <div className="flex items-center gap-3">
                      <span className="text-[10px] text-white/30">{outcome.horizon}d horizon</span>
                      {outcome.price_error_pct != null && (
                        <span className="text-[11px] font-mono" style={{ color: outcome.price_error_pct < 2 ? '#c8ff00' : outcome.price_error_pct < 5 ? '#fbbf24' : '#ff5500' }}>
                          ±{outcome.price_error_pct.toFixed(2)}%
                        </span>
                      )}
                    </div>
                  </div>
                )
              })}
            </div>
          </div>
        )}

        {total === 0 && (
          <div className="text-center py-4">
            <Activity size={20} color="rgba(255,255,255,0.15)" className="mx-auto mb-2" />
            <p className="text-xs text-white/30">Collecting prediction data…</p>
            <p className="text-[10px] text-white/20 mt-1">Accuracy stats appear after 1-day horizons pass</p>
          </div>
        )}
      </div>
    </motion.div>
  )
}
