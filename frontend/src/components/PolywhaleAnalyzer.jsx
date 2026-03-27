/**
 * PolywhaleAnalyzer — Polymarket screenshot analysis panel.
 *
 * Drag-and-drop or click-to-upload a screenshot of any Polymarket page.
 * Sends it to /api/polymarket/analyze-screenshot (NVIDIA Llama-3.2-90B Vision).
 * If NVIDIA_API_KEY is not configured, shows setup instructions.
 *
 * Also shows live Polymarket prediction market signals in the sidebar.
 */

import { useState, useRef, useCallback } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import {
    Upload, X, Loader2, AlertCircle, ChevronRight,
    TrendingUp, TrendingDown, Minus, ExternalLink,
    BarChart2, Brain, Key, CheckCircle2,
} from 'lucide-react'
import axios from 'axios'

const API = '/api/polymarket'

// ─── Probability pill ────────────────────────────────────────────────────────
function ProbPill({ prob }) {
    if (prob == null) return null
    const pct = Math.round(prob * 100)
    const color = pct >= 60 ? '#c8ff00' : pct >= 40 ? '#ffffff80' : '#ff5500'
    return (
        <span
            className="text-[11px] font-mono font-bold px-2 py-0.5 rounded-full"
            style={{ background: `${color}18`, color, border: `1px solid ${color}40` }}
        >
            {pct}%
        </span>
    )
}

// ─── Direction badge ──────────────────────────────────────────────────────────
function DirectionBadge({ label }) {
    const map = {
        BULLISH:  { color: '#c8ff00', Icon: TrendingUp },
        BEARISH:  { color: '#ff5500', Icon: TrendingDown },
        NEUTRAL:  { color: '#ffffff60', Icon: Minus },
    }
    const { color, Icon } = map[label] || map.NEUTRAL
    return (
        <span
            className="inline-flex items-center gap-1.5 text-xs font-bold px-3 py-1 rounded-lg"
            style={{ background: `${color}15`, color, border: `1px solid ${color}30` }}
        >
            <Icon size={13} />
            {label}
        </span>
    )
}

// ─── Live Polymarket signals feed ────────────────────────────────────────────
function LiveSignalsFeed({ symbol }) {
    const [data,    setData]    = useState(null)
    const [loading, setLoading] = useState(false)
    const [error,   setError]   = useState(null)

    const fetch = useCallback(() => {
        if (!symbol) return
        setLoading(true)
        setError(null)
        axios.get(`${API}/signals/${symbol}`)
            .then(r => setData(r.data))
            .catch(e => setError(e.response?.data?.detail || 'Failed to fetch signals'))
            .finally(() => setLoading(false))
    }, [symbol])

    // Auto-fetch when symbol changes
    useState(() => { fetch() }, [symbol])

    if (!symbol) return (
        <p className="text-xs text-white/30 text-center py-4">
            Select an asset to see Polymarket signals
        </p>
    )

    return (
        <div className="space-y-3">
            <div className="flex items-center justify-between">
                <span className="text-[11px] text-white/40 uppercase tracking-wide">
                    Crowd Wisdom — {symbol}
                </span>
                <button
                    onClick={fetch}
                    disabled={loading}
                    className="text-[10px] text-white/30 hover:text-white/60 transition-colors"
                >
                    {loading ? <Loader2 size={11} className="animate-spin" /> : '↻ Refresh'}
                </button>
            </div>

            {loading && !data && (
                <div className="flex justify-center py-4">
                    <Loader2 size={18} color="#c8ff00" className="animate-spin" />
                </div>
            )}

            {error && (
                <div className="flex items-center gap-2 text-xs text-red-400/70">
                    <AlertCircle size={13} />
                    {error}
                </div>
            )}

            {data && (
                <div className="space-y-2">
                    <div className="flex items-center justify-between rounded-xl px-3 py-2.5"
                        style={{ background: 'rgba(255,255,255,0.04)', border: '1px solid rgba(255,255,255,0.07)' }}>
                        <span className="text-xs text-white/50">Signal</span>
                        <DirectionBadge label={data.signal_label} />
                    </div>
                    <div className="grid grid-cols-2 gap-2">
                        {[
                            { label: 'Bull markets', value: data.bull_market_count, color: '#c8ff00' },
                            { label: 'Bear markets', value: data.bear_market_count, color: '#ff5500' },
                            { label: 'Bull avg prob', value: `${Math.round((data.bull_avg_prob||0)*100)}%`, color: '#c8ff00' },
                            { label: 'Bear avg prob', value: `${Math.round((data.bear_avg_prob||0)*100)}%`, color: '#ff5500' },
                        ].map(({ label, value, color }) => (
                            <div key={label} className="rounded-lg px-2.5 py-2"
                                style={{ background: 'rgba(255,255,255,0.03)', border: '1px solid rgba(255,255,255,0.06)' }}>
                                <p className="text-[10px] text-white/35 mb-0.5">{label}</p>
                                <p className="text-sm font-bold font-mono" style={{ color }}>{value}</p>
                            </div>
                        ))}
                    </div>

                    {data.relevant_markets?.length > 0 && (
                        <div>
                            <p className="text-[10px] text-white/30 uppercase tracking-wide mb-2 mt-3">
                                Relevant markets ({data.total_scanned} scanned)
                            </p>
                            {data.relevant_markets.slice(0, 5).map((m, i) => (
                                <div key={i} className="flex items-start justify-between gap-2 py-2"
                                    style={{ borderBottom: '1px solid rgba(255,255,255,0.04)' }}>
                                    <p className="text-[11px] text-white/60 flex-1 leading-snug line-clamp-2">
                                        {m.question}
                                    </p>
                                    <div className="flex items-center gap-1.5 shrink-0">
                                        <ProbPill prob={m.yes_prob} />
                                        {m.url && (
                                            <a href={`https://polymarket.com/${m.url}`}
                                                target="_blank" rel="noopener noreferrer"
                                                className="text-white/20 hover:text-white/50 transition-colors">
                                                <ExternalLink size={10} />
                                            </a>
                                        )}
                                    </div>
                                </div>
                            ))}
                        </div>
                    )}
                </div>
            )}
        </div>
    )
}

// ─── Screenshot drop zone ─────────────────────────────────────────────────────
function DropZone({ onFile }) {
    const [dragging, setDragging] = useState(false)
    const inputRef = useRef(null)

    const handleDrop = useCallback((e) => {
        e.preventDefault()
        setDragging(false)
        const file = e.dataTransfer?.files?.[0]
        if (file && file.type.startsWith('image/')) onFile(file)
    }, [onFile])

    const handleChange = useCallback((e) => {
        const file = e.target.files?.[0]
        if (file) onFile(file)
        e.target.value = ''
    }, [onFile])

    return (
        <div
            onClick={() => inputRef.current?.click()}
            onDrop={handleDrop}
            onDragOver={e => { e.preventDefault(); setDragging(true) }}
            onDragLeave={() => setDragging(false)}
            className="cursor-pointer rounded-2xl flex flex-col items-center justify-center gap-3 p-8 transition-all"
            style={{
                border: `2px dashed ${dragging ? '#c8ff00' : 'rgba(200,255,0,0.2)'}`,
                background: dragging ? 'rgba(200,255,0,0.05)' : 'rgba(255,255,255,0.02)',
                minHeight: 160,
            }}
        >
            <div className="w-12 h-12 rounded-2xl flex items-center justify-center"
                style={{ background: 'rgba(200,255,0,0.1)', border: '1px solid rgba(200,255,0,0.2)' }}>
                <Upload size={22} color="#c8ff00" />
            </div>
            <div className="text-center">
                <p className="text-sm font-medium text-white/70">
                    {dragging ? 'Drop your screenshot here' : 'Upload Polymarket screenshot'}
                </p>
                <p className="text-xs text-white/30 mt-1">
                    Drag & drop or click · PNG, JPG, WEBP · max 10 MB
                </p>
            </div>
            <input
                ref={inputRef}
                type="file"
                accept="image/*"
                className="hidden"
                onChange={handleChange}
            />
        </div>
    )
}

// ─── Analysis result renderer ─────────────────────────────────────────────────
function AnalysisResult({ data, onClear }) {
    const { analysis } = data

    if (analysis.raw_analysis) {
        return (
            <div className="rounded-2xl p-4 space-y-3"
                style={{ background: 'rgba(255,255,255,0.03)', border: '1px solid rgba(255,255,255,0.08)' }}>
                <div className="flex items-center justify-between">
                    <div className="flex items-center gap-2">
                        <CheckCircle2 size={15} color="#c8ff00" />
                        <span className="text-sm font-semibold text-white">Analysis Complete</span>
                    </div>
                    <button onClick={onClear} className="text-white/30 hover:text-white/60 transition-colors">
                        <X size={14} />
                    </button>
                </div>
                <p className="text-xs text-white/60 leading-relaxed whitespace-pre-wrap">
                    {analysis.raw_analysis}
                </p>
                <p className="text-[10px] text-white/25 font-mono">
                    Model: {data.model} · {data.provider || 'NVIDIA NIM'}
                </p>
            </div>
        )
    }

    const positions = analysis.positions || []
    const summary   = analysis.portfolio_summary || {}
    const signal    = analysis.trading_signal || {}
    const risks     = analysis.risk_factors || []

    return (
        <div className="space-y-3">
            <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                    <CheckCircle2 size={15} color="#c8ff00" />
                    <span className="text-sm font-semibold text-white">Polywhale Analysis</span>
                </div>
                <button onClick={onClear} className="text-white/30 hover:text-white/60 transition-colors">
                    <X size={14} />
                </button>
            </div>

            {/* Trading signal */}
            {signal.macro_sentiment && (
                <div className="rounded-xl p-3 flex items-center justify-between"
                    style={{ background: 'rgba(200,255,0,0.06)', border: '1px solid rgba(200,255,0,0.15)' }}>
                    <span className="text-xs text-white/50">Implied Signal</span>
                    <DirectionBadge label={signal.macro_sentiment?.toUpperCase()} />
                </div>
            )}

            {/* Positions */}
            {positions.length > 0 && (
                <div>
                    <p className="text-[10px] text-white/30 uppercase tracking-wide mb-2">
                        Positions ({positions.length})
                    </p>
                    {positions.map((pos, i) => (
                        <div key={i} className="flex items-start justify-between gap-3 py-2.5"
                            style={{ borderBottom: '1px solid rgba(255,255,255,0.04)' }}>
                            <p className="text-[11px] text-white/70 leading-snug flex-1">
                                {pos.question || pos.market || `Position ${i + 1}`}
                            </p>
                            <div className="shrink-0 flex items-center gap-2">
                                {pos.probability != null && <ProbPill prob={pos.probability / 100} />}
                                {pos.position && (
                                    <span className="text-[10px] font-mono font-bold"
                                        style={{ color: pos.position === 'YES' ? '#c8ff00' : '#ff5500' }}>
                                        {pos.position}
                                    </span>
                                )}
                            </div>
                        </div>
                    ))}
                </div>
            )}

            {/* Recommendation */}
            {signal.recommended_action && (
                <div className="rounded-xl p-3"
                    style={{ background: 'rgba(0,212,170,0.06)', border: '1px solid rgba(0,212,170,0.15)' }}>
                    <p className="text-[10px] text-white/40 uppercase tracking-wide mb-1">Recommendation</p>
                    <p className="text-xs text-white/70">{signal.recommended_action}</p>
                </div>
            )}

            {/* Risk factors */}
            {risks.length > 0 && (
                <div className="rounded-xl p-3 space-y-1.5"
                    style={{ background: 'rgba(255,85,0,0.05)', border: '1px solid rgba(255,85,0,0.15)' }}>
                    <p className="text-[10px] text-white/40 uppercase tracking-wide">Risk Factors</p>
                    {(Array.isArray(risks) ? risks : [risks]).map((r, i) => (
                        <p key={i} className="text-[11px] text-white/55 flex items-start gap-1.5">
                            <span style={{ color: '#ff5500' }}>•</span>
                            {typeof r === 'string' ? r : r.factor || r.description || JSON.stringify(r)}
                        </p>
                    ))}
                </div>
            )}

            <p className="text-[10px] text-white/20 font-mono text-right">
                {data.model} · {data.provider || 'NVIDIA NIM'}
            </p>
        </div>
    )
}

// ─── API key setup notice ─────────────────────────────────────────────────────
function SetupNotice({ detail }) {
    const steps = detail?.setup_steps || []
    return (
        <div className="rounded-2xl p-4 space-y-3"
            style={{ background: 'rgba(255,200,0,0.05)', border: '1px solid rgba(255,200,0,0.15)' }}>
            <div className="flex items-center gap-2">
                <Key size={15} color="#76b900" />
                <span className="text-sm font-semibold text-white">NVIDIA API Key Required</span>
            </div>
            <p className="text-xs text-white/50">
                Polywhale uses NVIDIA Llama-3.2-90B Vision (free). One-time setup:
            </p>
            <div className="space-y-1.5">
                {steps.map((step, i) => (
                    <p key={i} className="text-xs text-white/60 flex items-start gap-2">
                        <span style={{ color: '#76b900' }}>›</span>
                        {i === 0 ? (
                            <span>
                                Go to{' '}
                                <a href="https://build.nvidia.com/"
                                    target="_blank" rel="noopener noreferrer"
                                    className="underline" style={{ color: '#c8ff00' }}>
                                    build.nvidia.com
                                </a>
                                {' '}→ Create free account → Get API Key
                            </span>
                        ) : step.replace(/^\d+\.\s*/, '')}
                    </p>
                ))}
            </div>
            <p className="text-[10px] text-white/30">
                Free tier. No credit card required. All Polymarket signals work without any key.
            </p>
        </div>
    )
}

// ─── Main component ───────────────────────────────────────────────────────────
export default function PolywhaleAnalyzer({ symbol, assetType, onClose }) {
    const [file,      setFile]      = useState(null)
    const [preview,   setPreview]   = useState(null)
    const [loading,   setLoading]   = useState(false)
    const [result,    setResult]    = useState(null)
    const [apiError,  setApiError]  = useState(null)
    const [setupInfo, setSetupInfo] = useState(null)

    const handleFile = useCallback((f) => {
        setFile(f)
        setResult(null)
        setApiError(null)
        setSetupInfo(null)
        const url = URL.createObjectURL(f)
        setPreview(url)
    }, [])

    const handleAnalyze = useCallback(async () => {
        if (!file) return
        setLoading(true)
        setApiError(null)
        setSetupInfo(null)

        const form = new FormData()
        form.append('file', file)

        try {
            const resp = await axios.post(`${API}/analyze-screenshot`, form, {
                headers: { 'Content-Type': 'multipart/form-data' }
            })
            setResult(resp.data)
        } catch (e) {
            const detail = e.response?.data?.detail
            if (e.response?.status === 402) {
                setSetupInfo(detail)
            } else {
                setApiError(typeof detail === 'string' ? detail : 'Analysis failed')
            }
        } finally {
            setLoading(false)
        }
    }, [file])

    const handleClear = useCallback(() => {
        setFile(null)
        if (preview) URL.revokeObjectURL(preview)
        setPreview(null)
        setResult(null)
        setApiError(null)
        setSetupInfo(null)
    }, [preview])

    return (
        <motion.div
            initial={{ opacity: 0, scale: 0.97, y: 8 }}
            animate={{ opacity: 1, scale: 1, y: 0 }}
            exit={{ opacity: 0, scale: 0.97, y: 8 }}
            transition={{ duration: 0.2 }}
            className="fixed inset-0 z-50 flex items-center justify-center p-4"
            style={{ background: 'rgba(2,2,9,0.85)', backdropFilter: 'blur(12px)' }}
            onClick={(e) => e.target === e.currentTarget && onClose()}
        >
            <div
                className="w-full max-w-4xl max-h-[90vh] overflow-hidden rounded-3xl flex flex-col"
                style={{
                    background: 'rgba(8,8,18,0.98)',
                    border: '1px solid rgba(200,255,0,0.12)',
                    boxShadow: '0 32px 80px rgba(0,0,0,0.7)',
                }}
            >
                {/* Header */}
                <div className="flex-none flex items-center justify-between px-6 py-4"
                    style={{ borderBottom: '1px solid rgba(255,255,255,0.06)' }}>
                    <div className="flex items-center gap-3">
                        <div className="w-9 h-9 rounded-xl flex items-center justify-center"
                            style={{ background: 'rgba(200,255,0,0.1)', border: '1px solid rgba(200,255,0,0.2)' }}>
                            <BarChart2 size={18} color="#c8ff00" />
                        </div>
                        <div>
                            <h2 className="text-base font-bold text-white">Polywhale Analyzer</h2>
                            <p className="text-[11px] text-white/35">
                                Prediction market signals · NVIDIA Llama Vision
                            </p>
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

                {/* Body — two-column */}
                <div className="flex-1 overflow-hidden flex">
                    {/* Left: Screenshot upload + result */}
                    <div className="flex-1 overflow-y-auto p-6 space-y-4"
                        style={{ borderRight: '1px solid rgba(255,255,255,0.05)', scrollbarWidth: 'thin' }}>
                        <div className="flex items-center gap-2 mb-1">
                            <Brain size={14} color="#c8ff00" />
                            <span className="text-xs font-semibold text-white/60 uppercase tracking-wide">
                                Polywhale — NVIDIA Llama Vision
                            </span>
                        </div>

                        {!file && <DropZone onFile={handleFile} />}

                        {file && !result && (
                            <div className="space-y-3">
                                {/* Preview */}
                                <div className="relative rounded-xl overflow-hidden"
                                    style={{ border: '1px solid rgba(255,255,255,0.08)' }}>
                                    <img src={preview} alt="Screenshot preview"
                                        className="w-full object-contain max-h-56" />
                                    <button
                                        onClick={handleClear}
                                        className="absolute top-2 right-2 w-7 h-7 rounded-lg flex items-center justify-center"
                                        style={{ background: 'rgba(0,0,0,0.7)' }}
                                    >
                                        <X size={13} color="white" />
                                    </button>
                                </div>
                                <p className="text-xs text-white/40 text-center">{file.name}</p>

                                {/* Analyze button */}
                                <button
                                    onClick={handleAnalyze}
                                    disabled={loading}
                                    className="w-full py-3 rounded-xl text-sm font-bold flex items-center justify-center gap-2 transition-all"
                                    style={{
                                        background: loading ? 'rgba(200,255,0,0.1)' : 'rgba(200,255,0,0.15)',
                                        border: '1px solid rgba(200,255,0,0.3)',
                                        color: '#c8ff00',
                                    }}
                                    onMouseEnter={e => !loading && (e.currentTarget.style.background = 'rgba(200,255,0,0.22)')}
                                    onMouseLeave={e => !loading && (e.currentTarget.style.background = 'rgba(200,255,0,0.15)')}
                                >
                                    {loading
                                        ? <><Loader2 size={15} className="animate-spin" /> Analyzing with NVIDIA…</>
                                        : <><Brain size={15} /> Analyze with NVIDIA Vision</>
                                    }
                                </button>
                            </div>
                        )}

                        {apiError && (
                            <div className="flex items-center gap-2 text-xs text-red-400/80 rounded-xl p-3"
                                style={{ background: 'rgba(255,50,50,0.07)', border: '1px solid rgba(255,50,50,0.15)' }}>
                                <AlertCircle size={14} />
                                {apiError}
                            </div>
                        )}

                        {setupInfo && <SetupNotice detail={setupInfo} />}
                        {result    && <AnalysisResult data={result} onClear={handleClear} />}
                    </div>

                    {/* Right: Live Polymarket signals */}
                    <div className="w-72 flex-none overflow-y-auto p-5"
                        style={{ scrollbarWidth: 'thin' }}>
                        <div className="flex items-center gap-2 mb-4">
                            <TrendingUp size={14} color="#c8ff00" />
                            <span className="text-xs font-semibold text-white/60 uppercase tracking-wide">
                                Live Signals
                            </span>
                        </div>
                        <LiveSignalsFeed symbol={symbol} />
                    </div>
                </div>
            </div>
        </motion.div>
    )
}
