import { useState, useEffect, useCallback } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import {
    Zap, RefreshCw, AlertCircle, X, Radar, Clock,
    CheckCircle, Loader, ArrowLeft, Globe,
} from 'lucide-react'
import api from '../utils/api'

const POLL_MS = 30_000

function timeAgo(isoStr) {
    if (!isoStr) return 'Never'
    const diff = Math.floor((Date.now() - new Date(isoStr).getTime()) / 1000)
    if (diff < 60)   return `${diff}s ago`
    if (diff < 3600) return `${Math.floor(diff / 60)}m ago`
    return `${Math.floor(diff / 3600)}h ${Math.floor((diff % 3600) / 60)}m ago`
}

function timeUntil(isoStr) {
    if (!isoStr) return '—'
    const diff = Math.floor((new Date(isoStr).getTime() - Date.now()) / 1000)
    if (diff <= 0)   return 'soon'
    if (diff < 3600) return `${Math.floor(diff / 60)}m`
    return `${Math.floor(diff / 3600)}h ${Math.floor((diff % 3600) / 60)}m`
}

const REC = {
    BUY:  { bg: 'bg-green-500/20',  text: 'text-green-400',  label: 'BUY'  },
    HOLD: { bg: 'bg-yellow-500/20', text: 'text-yellow-400', label: 'HOLD' },
    SELL: { bg: 'bg-red-500/20',    text: 'text-red-400',    label: 'SELL' },
}

const STATUS_DOT = {
    pending:  'bg-gray-500',
    running:  'bg-yellow-400 animate-pulse',
    complete: 'bg-green-400',
    failed:   'bg-red-500',
}

// ── Shared stock row ──────────────────────────────────────────────────────────
function StockRow({ item, idx, onSelect, compact = false }) {
    const rec   = REC[item.recommendation] ?? REC.HOLD
    const isUp  = item.predicted_change >= 0
    const isTop = item.confidence >= 90

    const rawSymbol = item.symbol.split('/')[0]
        .replace('.NS', '').replace('.BO', '').replace('.SR', '')
        .replace('.L', '').replace('.TO', '').replace('.AX', '')

    return (
        <motion.button
            initial={{ opacity: 0, x: -8 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ delay: idx * 0.025 }}
            onClick={() => onSelect(item.symbol, item.is_crypto ? 'crypto' : 'stock')}
            className={`w-full px-4 flex items-center gap-3 hover:bg-white/5 transition-all text-left group ${compact ? 'py-2' : 'py-2.5'}`}
        >
            <span className="text-[10px] text-gray-600 w-4 shrink-0">#{idx + 1}</span>

            <div className="flex-1 min-w-0">
                <div className="flex items-center gap-1.5">
                    <span className="font-bold text-sm text-white group-hover:text-[#c8ff00] transition-colors">
                        {rawSymbol}
                    </span>
                    {!compact && (
                        <span className="text-[9px] px-1 py-0.5 rounded bg-white/5 text-gray-600">
                            {item.is_crypto ? 'CRYPTO' : 'STOCK'}
                        </span>
                    )}
                    {isTop && (
                        <span className="text-[8px] px-1 py-0.5 rounded bg-[#c8ff00]/15 text-[#c8ff00] font-bold">★</span>
                    )}
                </div>
                <p className="text-[10px] text-gray-500 truncate mt-0.5">{item.trend}</p>
            </div>

            <div className="text-right shrink-0">
                <p className="text-xs text-gray-300 font-mono">
                    {item.price > 1000
                        ? item.price.toLocaleString('en-US', { maximumFractionDigits: 0 })
                        : item.price.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
                </p>
                <p className={`text-[10px] font-semibold ${isUp ? 'text-green-400' : 'text-red-400'}`}>
                    {isUp ? '▲' : '▼'} {Math.abs(item.predicted_change).toFixed(1)}%
                </p>
            </div>

            <div className="shrink-0 flex flex-col items-end gap-1">
                <span className={`text-[10px] font-bold px-1.5 py-0.5 rounded ${rec.bg} ${rec.text}`}>
                    {rec.label}
                </span>
                <span className={`text-[10px] font-semibold ${isTop ? 'text-[#c8ff00]' : 'text-gray-500'}`}>
                    {item.confidence.toFixed(0)}%
                </span>
            </div>
        </motion.button>
    )
}

// ── Main component ────────────────────────────────────────────────────────────
export default function OpportunityScanner({ onAssetSelect }) {
    // Global scan
    const [scanData, setScanData]         = useState(null)
    const [refreshing, setRefreshing]     = useState(false)

    // Panel state
    const [isOpen, setIsOpen]             = useState(false)
    const [tab, setTab]                   = useState('buy')   // 'buy' | 'all' | 'markets'

    // Exchange browser
    const [exchanges, setExchanges]       = useState([])
    const [selExchange, setSelExchange]   = useState(null)   // clicked exchange meta
    const [exDetail, setExDetail]         = useState(null)   // drill-down results
    const [exLoading, setExLoading]       = useState(false)
    const [exFilter, setExFilter]         = useState('all')  // 'all' | 'buy'

    // Force time-ago re-renders
    const [, setTick] = useState(0)
    useEffect(() => {
        const id = setInterval(() => setTick(t => t + 1), 30_000)
        return () => clearInterval(id)
    }, [])

    // ── Global scan ───────────────────────────────────────────────────────────
    const fetchScan = useCallback(async () => {
        try {
            const res = await api.get('/scan/opportunities')
            setScanData(res.data)
            if (res.data?.opportunities?.length > 0 && !isOpen) setIsOpen(true)
        } catch (e) {
            console.warn('[Scanner]', e.message)
        }
    }, [isOpen])

    useEffect(() => {
        fetchScan()
        const id = setInterval(fetchScan, POLL_MS)
        return () => clearInterval(id)
    }, []) // eslint-disable-line

    const triggerRefresh = async () => {
        setRefreshing(true)
        try {
            await api.post('/scan/refresh')
            let n = 0
            const poll = setInterval(async () => {
                n++
                const res = await api.get('/scan/opportunities')
                setScanData(res.data)
                if (res.data?.status === 'complete' || n > 40) {
                    clearInterval(poll); setRefreshing(false)
                }
            }, 3000)
        } catch { setRefreshing(false) }
    }

    // ── Exchange browser ──────────────────────────────────────────────────────
    const fetchExchanges = useCallback(async () => {
        try {
            const res = await api.get('/scan/exchanges')
            setExchanges(res.data)
        } catch (e) {
            console.warn('[Scanner/exchanges]', e.message)
        }
    }, [])

    useEffect(() => {
        if (tab === 'markets') fetchExchanges()
    }, [tab]) // eslint-disable-line

    // Poll exchange overview when markets tab open (no drill-down)
    useEffect(() => {
        if (tab !== 'markets' || selExchange) return
        const id = setInterval(fetchExchanges, POLL_MS)
        return () => clearInterval(id)
    }, [tab, selExchange]) // eslint-disable-line

    const openExchange = async (ex) => {
        setSelExchange(ex)
        setExDetail(null)
        setExLoading(true)
        setExFilter('all')
        try {
            const res = await api.get(`/scan/exchange/${ex.id}`)
            setExDetail(res.data)
        } catch (e) {
            console.warn('[Scanner/exchange]', e.message)
        } finally {
            setExLoading(false)
        }
    }

    const backToExchanges = () => {
        setSelExchange(null)
        setExDetail(null)
        fetchExchanges()
    }

    const refreshExchange = async () => {
        if (!selExchange) return
        setExLoading(true)
        try {
            await api.post(`/scan/exchange/${selExchange.id}/refresh`)
            let n = 0
            const poll = setInterval(async () => {
                n++
                const res = await api.get(`/scan/exchange/${selExchange.id}`)
                setExDetail(res.data)
                if (res.data.status === 'complete' || n > 40) {
                    clearInterval(poll); setExLoading(false)
                }
            }, 3000)
        } catch { setExLoading(false) }
    }

    // ── Derived values ────────────────────────────────────────────────────────
    const isRunning  = scanData?.status === 'running' || refreshing
    const isPending  = !scanData || scanData?.status === 'pending'
    const buyList    = scanData?.opportunities ?? []
    const allList    = scanData?.all_results   ?? []
    const globalList = tab === 'buy' ? buyList : allList

    const exList = exDetail
        ? (exFilter === 'buy' ? exDetail.buy_signals : exDetail.results)
        : []

    // ── Render ────────────────────────────────────────────────────────────────
    return (
        <div className="fixed bottom-6 right-6 z-40 flex flex-col items-end gap-3">

            {/* Panel */}
            <AnimatePresence>
                {isOpen && (
                    <motion.div
                        initial={{ opacity: 0, y: 20, scale: 0.92 }}
                        animate={{ opacity: 1, y: 0, scale: 1 }}
                        exit={{ opacity: 0, scale: 0.92, y: 10 }}
                        className="rounded-2xl overflow-hidden shadow-2xl shadow-black/60"
                        style={{
                            width: 380,
                            background: 'rgba(10,10,18,0.97)',
                            border: '1px solid rgba(200,255,0,0.18)',
                        }}
                    >
                        {/* ── Header ─────────────────────────────────────── */}
                        <div className="px-4 py-3 flex items-center justify-between"
                             style={{ background: 'linear-gradient(90deg,rgba(200,255,0,0.08),rgba(0,255,136,0.06))' }}>
                            <div className="flex items-center gap-2.5">
                                <div className="relative p-1.5 rounded-lg bg-[#c8ff00]/15">
                                    <Radar className={`w-4 h-4 text-[#c8ff00] ${isRunning ? 'animate-spin' : ''}`} />
                                    {isRunning && <span className="absolute inset-0 rounded-lg animate-ping bg-[#c8ff00]/25" />}
                                </div>
                                <div>
                                    <p className="text-sm font-bold text-white leading-none">AI Market Scanner</p>
                                    <p className="text-[10px] mt-0.5" style={{ color: 'rgba(200,255,0,0.7)' }}>
                                        {tab === 'markets' && selExchange
                                            ? `${selExchange.flag} ${selExchange.name}`
                                            : isRunning   ? 'Scanning markets…'
                                            : isPending   ? 'Initialising…'
                                            : `${buyList.length} buy signal${buyList.length !== 1 ? 's' : ''} found`}
                                    </p>
                                </div>
                            </div>

                            <div className="flex items-center gap-1.5">
                                <button
                                    onClick={tab === 'markets' && selExchange ? refreshExchange : triggerRefresh}
                                    disabled={isRunning || exLoading}
                                    title="Refresh"
                                    className="p-1.5 rounded-lg transition-colors hover:bg-[#c8ff00]/15 text-gray-500 hover:text-[#c8ff00] disabled:opacity-40"
                                >
                                    <RefreshCw className={`w-3.5 h-3.5 ${(isRunning || exLoading) ? 'animate-spin' : ''}`} />
                                </button>
                                <button onClick={() => setIsOpen(false)}
                                    className="p-1.5 rounded-lg hover:bg-red-500/20 text-gray-500 hover:text-red-400 transition-colors">
                                    <X className="w-3.5 h-3.5" />
                                </button>
                            </div>
                        </div>

                        {/* ── Schedule bar ───────────────────────────────── */}
                        {tab !== 'markets' && scanData?.last_run && (
                            <div className="px-4 py-2 flex items-center justify-between text-[10px]"
                                 style={{ background: 'rgba(255,255,255,0.03)', borderBottom: '1px solid rgba(255,255,255,0.05)' }}>
                                <span className="flex items-center gap-1 text-gray-500">
                                    <Clock className="w-3 h-3" /> Scanned {timeAgo(scanData.last_run)}
                                </span>
                                <span className="flex items-center gap-1 text-gray-500">
                                    <CheckCircle className="w-3 h-3" />
                                    Next in {timeUntil(scanData.next_run)} · 4×/day
                                </span>
                            </div>
                        )}
                        {tab === 'markets' && selExchange && exDetail?.last_run && (
                            <div className="px-4 py-2 flex items-center justify-between text-[10px]"
                                 style={{ background: 'rgba(255,255,255,0.03)', borderBottom: '1px solid rgba(255,255,255,0.05)' }}>
                                <span className="flex items-center gap-1 text-gray-500">
                                    <Clock className="w-3 h-3" /> Scanned {timeAgo(exDetail.last_run)}
                                </span>
                                <span className="flex items-center gap-1 text-gray-500">
                                    <CheckCircle className="w-3 h-3" />
                                    {exDetail.scan_count} of {exDetail.total_symbols} scanned
                                </span>
                            </div>
                        )}

                        {/* ── Tabs / nav bar ─────────────────────────────── */}
                        <div className="flex px-4 pt-3 pb-1 gap-2">
                            {tab === 'markets' && selExchange ? (
                                /* Exchange drill-down nav */
                                <div className="flex items-center gap-2 w-full">
                                    <button onClick={backToExchanges}
                                        className="flex items-center gap-1 text-xs text-gray-400 hover:text-white transition-colors shrink-0">
                                        <ArrowLeft className="w-3.5 h-3.5" />
                                        <span>Exchanges</span>
                                    </button>
                                    <div className="flex-1 flex justify-end gap-1.5">
                                        {[
                                            { key: 'all', label: `All (${exDetail?.results?.length ?? '…'})` },
                                            { key: 'buy', label: `BUY (${exDetail?.buy_signals?.length ?? '…'})` },
                                        ].map(f => (
                                            <button key={f.key} onClick={() => setExFilter(f.key)}
                                                className={`px-2.5 py-1 rounded-lg text-xs font-semibold transition-all ${
                                                    exFilter === f.key
                                                        ? 'bg-[#c8ff00]/20 text-[#c8ff00]'
                                                        : 'text-gray-500 hover:text-gray-300 hover:bg-white/5'
                                                }`}>
                                                {f.label}
                                            </button>
                                        ))}
                                    </div>
                                </div>
                            ) : (
                                /* Main tabs */
                                [
                                    { key: 'buy',     label: `Buy (${buyList.length})` },
                                    { key: 'all',     label: `All (${allList.length})` },
                                    { key: 'markets', label: 'Markets', icon: <Globe className="w-3 h-3" /> },
                                ].map(t => (
                                    <button key={t.key} onClick={() => setTab(t.key)}
                                        className={`flex items-center gap-1.5 px-3 py-1 rounded-lg text-xs font-semibold transition-all ${
                                            tab === t.key
                                                ? 'bg-[#c8ff00]/20 text-[#c8ff00]'
                                                : 'text-gray-500 hover:text-gray-300 hover:bg-white/5'
                                        }`}>
                                        {t.icon ?? null}
                                        {t.label}
                                    </button>
                                ))
                            )}
                        </div>

                        {/* ── Content ────────────────────────────────────── */}
                        <div className="max-h-[340px] overflow-y-auto"
                             style={{ scrollbarWidth: 'thin', scrollbarColor: 'rgba(200,255,0,0.2) transparent' }}>

                            {/* Markets → exchange grid */}
                            {tab === 'markets' && !selExchange && (
                                exchanges.length === 0 ? (
                                    <div className="py-8 text-center">
                                        <Globe className="w-8 h-8 mx-auto mb-2 text-gray-600 animate-pulse" />
                                        <p className="text-xs text-gray-500">Loading exchanges…</p>
                                    </div>
                                ) : (
                                    <div className="p-3 grid grid-cols-2 gap-2">
                                        {exchanges.map(ex => (
                                            <motion.button
                                                key={ex.id}
                                                whileHover={{ scale: 1.02 }}
                                                whileTap={{ scale: 0.97 }}
                                                onClick={() => openExchange(ex)}
                                                className="relative rounded-xl p-3 text-left group"
                                                style={{
                                                    background: 'rgba(255,255,255,0.04)',
                                                    border: '1px solid rgba(255,255,255,0.07)',
                                                }}
                                            >
                                                {/* Status dot */}
                                                <span className={`absolute top-2.5 right-2.5 w-1.5 h-1.5 rounded-full ${STATUS_DOT[ex.status] ?? 'bg-gray-500'}`} />

                                                <div className="text-2xl mb-1.5 leading-none">{ex.flag}</div>
                                                <p className="text-xs font-bold text-white leading-tight group-hover:text-[#c8ff00] transition-colors">
                                                    {ex.name}
                                                </p>
                                                <p className="text-[9px] text-gray-600 mt-0.5">{ex.currency}</p>

                                                <div className="mt-2 flex flex-wrap gap-1">
                                                    {ex.buy_signals > 0 && (
                                                        <span className="text-[9px] px-1.5 py-0.5 rounded-full bg-green-500/20 text-green-400 font-bold">
                                                            {ex.buy_signals} BUY
                                                        </span>
                                                    )}
                                                    <span className="text-[9px] text-gray-600">
                                                        {ex.scan_count > 0 ? `${ex.scan_count} stocks` : 'Pending…'}
                                                    </span>
                                                </div>
                                            </motion.button>
                                        ))}
                                    </div>
                                )
                            )}

                            {/* Markets → exchange drill-down */}
                            {tab === 'markets' && selExchange && (
                                exLoading && exList.length === 0 ? (
                                    <div className="py-10 flex flex-col items-center gap-3">
                                        <div className="relative w-12 h-12">
                                            <span className="absolute inset-0 rounded-full border-2 border-[#c8ff00]/30 animate-ping" />
                                            <Loader className="absolute inset-3 w-6 h-6 text-[#c8ff00] animate-spin" />
                                        </div>
                                        <p className="text-xs text-gray-400">Scanning {selExchange.name}…</p>
                                    </div>
                                ) : exDetail?.status === 'pending' ? (
                                    <div className="py-8 text-center">
                                        <Radar className="w-8 h-8 mx-auto mb-2 text-gray-600 animate-pulse" />
                                        <p className="text-xs text-gray-500">Scan queued — check back shortly</p>
                                    </div>
                                ) : exList.length === 0 ? (
                                    <div className="py-8 text-center">
                                        <AlertCircle className="w-8 h-8 mx-auto mb-2 text-gray-600" />
                                        <p className="text-xs text-gray-500">No results yet</p>
                                    </div>
                                ) : (
                                    <div className="py-1">
                                        {exList.map((item, idx) => (
                                            <StockRow
                                                key={item.symbol}
                                                item={item}
                                                idx={idx}
                                                compact
                                                onSelect={(sym, type) => {
                                                    onAssetSelect(sym, type)
                                                    setIsOpen(false)
                                                }}
                                            />
                                        ))}
                                    </div>
                                )
                            )}

                            {/* Buy / All tabs */}
                            {tab !== 'markets' && (
                                isRunning && globalList.length === 0 ? (
                                    <div className="py-10 flex flex-col items-center gap-3">
                                        <div className="relative w-12 h-12">
                                            <span className="absolute inset-0 rounded-full border-2 border-[#c8ff00]/30 animate-ping" />
                                            <span className="absolute inset-2 rounded-full border-2 border-[#c8ff00]/50 animate-pulse" />
                                            <Loader className="absolute inset-3 w-6 h-6 text-[#c8ff00] animate-spin" />
                                        </div>
                                        <p className="text-xs text-gray-400">Scanning {scanData?.scan_count || 25} assets…</p>
                                    </div>
                                ) : isPending && globalList.length === 0 ? (
                                    <div className="py-8 text-center">
                                        <Radar className="w-8 h-8 mx-auto mb-2 text-gray-600 animate-pulse" />
                                        <p className="text-xs text-gray-500">Starting up scanner…</p>
                                    </div>
                                ) : globalList.length === 0 ? (
                                    <div className="py-8 text-center">
                                        <AlertCircle className="w-8 h-8 mx-auto mb-2 text-gray-600" />
                                        <p className="text-xs text-gray-500">
                                            No {tab === 'buy' ? 'buy signals' : 'results'} yet
                                        </p>
                                        <p className="text-[10px] text-gray-600 mt-1">Scanner updates every 6 hours</p>
                                    </div>
                                ) : (
                                    <div className="py-1">
                                        {globalList.map((item, idx) => (
                                            <StockRow
                                                key={item.symbol}
                                                item={item}
                                                idx={idx}
                                                onSelect={(sym, type) => {
                                                    onAssetSelect(sym, type)
                                                    setIsOpen(false)
                                                }}
                                            />
                                        ))}
                                    </div>
                                )
                            )}
                        </div>

                        {/* ── Footer ─────────────────────────────────────── */}
                        <div className="px-4 py-2.5 border-t text-[10px] text-gray-600 text-center"
                             style={{ borderColor: 'rgba(255,255,255,0.05)' }}>
                            {tab === 'markets' && selExchange && exDetail
                                ? `${exDetail.scan_count} stocks · ${exDetail.full_name} · Click any row to open chart`
                                : tab === 'markets'
                                ? `${exchanges.length} exchanges · 6 hr scan cycle · ★ = ≥90% confidence`
                                : `${scanData?.scan_count ?? 0} assets scanned · ★ = ≥90% confidence · Click to open chart`}
                        </div>
                    </motion.div>
                )}
            </AnimatePresence>

            {/* ── Trigger button ─────────────────────────────────────────── */}
            <motion.button
                whileHover={{ scale: 1.05 }}
                whileTap={{ scale: 0.95 }}
                onClick={() => setIsOpen(o => !o)}
                className={`relative flex items-center gap-2 px-5 py-3 rounded-xl font-bold shadow-lg transition-all ${
                    isRunning
                        ? 'bg-gray-800/80 text-gray-300 cursor-wait'
                        : 'bg-gradient-to-r from-[#c8ff00] to-[#00ff88] text-black hover:shadow-[#c8ff00]/30 hover:shadow-xl'
                }`}
            >
                {isRunning ? <Loader className="w-5 h-5 animate-spin" /> : <Zap className="w-5 h-5" />}
                <span className="text-sm">{isRunning ? 'Scanning…' : 'AI Scanner'}</span>

                {!isRunning && buyList.length > 0 && (
                    <span className="absolute -top-1.5 -right-1.5 flex items-center justify-center h-5 w-5 rounded-full text-[10px] font-bold bg-green-500 text-black shadow-lg">
                        {buyList.length}
                    </span>
                )}
                {!isRunning && buyList.length === 0 && (
                    <span className="absolute -top-1 -right-1 flex h-3 w-3">
                        <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-[#c8ff00] opacity-75" />
                        <span className="relative inline-flex rounded-full h-3 w-3 bg-[#c8ff00]" />
                    </span>
                )}
            </motion.button>
        </div>
    )
}
