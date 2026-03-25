import { motion } from 'framer-motion'
import { getCurrencySymbol, getCurrencyForSymbol } from '../utils/currencyUtils'

const SIGNAL_ICON = {
    'Macro Environment':  '🌍',
    'Market Breadth':     '📊',
    'Fundamentals':       '📋',
    'Options Flow':       '⚡',
    'Smart Money':        '🏦',
    'Earnings Catalyst':  '📅',
    'Sector Momentum':    '🔄',
    'Fear & Greed':       '😱',
    'Social Buzz':        '💬',
    'Google Trends':      '🔍',
    'Seasonal Pattern':   '🗓️',
    'Cross-Asset':        '🔗',
    'Chart Patterns':     '🕯️',
    'News Sentiment':     '📰',
}

function SignalPill({ label, type }) {
    const color = type === 'bull' ? '#00ff88' : '#ef4444'
    const bg    = type === 'bull' ? 'rgba(0,255,136,0.08)' : 'rgba(239,68,68,0.08)'
    const icon  = SIGNAL_ICON[label] || (type === 'bull' ? '📈' : '📉')
    return (
        <div className="flex items-center gap-1 px-2 py-0.5 rounded-full text-[11px] font-medium whitespace-nowrap"
             style={{ background: bg, color, border: `1px solid ${color}25` }}>
            <span style={{ fontSize: 10 }}>{icon}</span>
            {label}
        </div>
    )
}

function PriceBox({ label, value, sub, color, bg }) {
    return (
        <div className="flex flex-col items-center gap-0.5 px-3 py-2 rounded-lg flex-1"
             style={{ background: bg, border: `1px solid ${color}25` }}>
            <span className="text-[9px] text-gray-500 uppercase tracking-wide">{label}</span>
            <span className="text-sm font-black font-mono" style={{ color }}>
                {value}
            </span>
            {sub && <span className="text-[9px]" style={{ color: `${color}99` }}>{sub}</span>}
        </div>
    )
}

function RegimeBadge({ regime }) {
    const map = {
        'Strong Trend':               { color: '#c8ff00', icon: '⚡' },
        'Trending':                   { color: '#00d4aa', icon: '📈' },
        'Overbought — Reversal Risk': { color: '#ef4444', icon: '⚠️' },
        'Oversold — Potential Bounce':{ color: '#00ff88', icon: '🔄' },
        'High Volatility':            { color: '#f97316', icon: '🌪️' },
        'Consolidation':              { color: '#6b7280', icon: '➡️' },
    }
    const m = map[regime] || { color: '#6b7280', icon: '➡️' }
    return (
        <span className="flex items-center gap-1 text-[10px] font-semibold px-2 py-0.5 rounded-full"
              style={{ background: `${m.color}12`, color: m.color, border: `1px solid ${m.color}25` }}>
            {m.icon} {regime}
        </span>
    )
}

export default function VerdictPanel({ prediction, symbol }) {
    if (!prediction?.analysis) return null

    const {
        recommendation    = 'HOLD',
        signals_conflict  = false,
        oracle_direction  = 0,
        combined_signal   = 0,
        note              = '',
        news_verdict      = {},
        chart_patterns    = [],
        key_signals       = { bullish: [], bearish: [] },
        trade_plan        = {},
        trade_thesis      = '',
        market_regime     = 'Consolidation',
        key_levels        = {},
    } = prediction.analysis

    const confidence = prediction.confidence ?? 0
    const currSym = symbol ? getCurrencySymbol(getCurrencyForSymbol(symbol).currency) : '$'

    // Colours keyed to recommendation
    const recColour = recommendation === 'BUY'  ? '#00ff88'
                    : recommendation === 'SELL' ? '#ef4444' : '#eab308'
    const recBg     = recommendation === 'BUY'  ? 'rgba(0,255,136,0.06)'
                    : recommendation === 'SELL' ? 'rgba(239,68,68,0.06)' : 'rgba(234,179,8,0.06)'
    const recBorder = recommendation === 'BUY'  ? 'rgba(0,255,136,0.20)'
                    : recommendation === 'SELL' ? 'rgba(239,68,68,0.20)' : 'rgba(234,179,8,0.20)'

    const bullSignals = key_signals.bullish || []
    const bearSignals = key_signals.bearish || []

    const newsSupp    = news_verdict.supporting_count   ?? 0
    const newsContra  = news_verdict.contradicting_count ?? 0
    const newsTotal   = newsSupp + newsContra + (news_verdict.neutral_count ?? 0)
    const newsVerdict = news_verdict.verdict ?? 'neutral'
    const newsSumm    = news_verdict.summary ?? ''

    const entry  = trade_plan.entry
    const stop   = trade_plan.stop_loss
    const target = trade_plan.target
    const rr     = trade_plan.risk_reward   ?? 0
    const riskPct   = trade_plan.risk_pct   ?? 0
    const rewardPct = trade_plan.reward_pct ?? 0
    const strength  = trade_plan.position_strength ?? 'No Trade'

    const rrColor = rr >= 2.0 ? '#00ff88' : rr >= 1.5 ? '#eab308' : '#ef4444'
    const strengthColor = strength === 'Strong' ? '#00ff88'
                        : strength === 'Moderate' ? '#eab308'
                        : strength === 'Weak' ? '#f97316' : '#6b7280'

    const fmt = (n) => n != null
        ? `${currSym}${Number(n).toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`
        : '—'

    return (
        <motion.div
            initial={{ opacity: 0, y: 12 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.12, ease: [0.16, 1, 0.3, 1] }}
            className="rounded-xl overflow-hidden"
            style={{ background: recBg, border: `1px solid ${recBorder}` }}
        >
            <div className="p-5 space-y-5">

                {/* ── Row 1: Verdict badge + thesis ── */}
                <div className="flex items-start gap-5">
                    {/* Badge column */}
                    <div className="flex-shrink-0 flex flex-col items-center gap-2">
                        <motion.div
                            initial={{ scale: 0.6, opacity: 0 }}
                            animate={{ scale: 1, opacity: 1 }}
                            transition={{ type: 'spring', stiffness: 300, damping: 18, delay: 0.18 }}
                            className="rounded-xl px-5 py-2 font-black text-2xl tracking-widest"
                            style={{
                                background: recColour,
                                color: '#000',
                                fontFamily: "'Outfit', sans-serif",
                                boxShadow: `0 0 24px ${recColour}40`,
                            }}
                        >
                            {recommendation}
                        </motion.div>
                        <div className="flex flex-col items-center gap-1">
                            <span className="text-[11px] font-semibold" style={{ color: recColour }}>
                                {confidence.toFixed(1)}% confidence
                            </span>
                            <RegimeBadge regime={market_regime} />
                            {signals_conflict && (
                                <span className="text-[10px] font-semibold text-yellow-400">⚠️ Signal Conflict</span>
                            )}
                        </div>
                    </div>

                    {/* Thesis */}
                    <div className="flex-1 min-w-0 pt-1">
                        <p className="text-[13px] text-gray-200 leading-relaxed font-medium">
                            {trade_thesis || note}
                        </p>
                    </div>
                </div>

                {/* ── Row 2: Trade plan (entry / stop / target / R:R) ── */}
                {recommendation !== 'HOLD' && entry && stop && target && (
                    <div>
                        <p className="text-[9px] text-gray-600 uppercase tracking-[0.12em] mb-2 font-semibold">
                            Trade Plan
                        </p>
                        <div className="flex items-stretch gap-2">
                            <PriceBox
                                label="Entry"
                                value={fmt(entry)}
                                sub="Current price"
                                color="#c8ff00"
                                bg="rgba(200,255,0,0.05)"
                            />
                            <PriceBox
                                label="Stop Loss"
                                value={fmt(stop)}
                                sub={`-${riskPct.toFixed(1)}% risk`}
                                color="#ef4444"
                                bg="rgba(239,68,68,0.05)"
                            />
                            <PriceBox
                                label="Target"
                                value={fmt(target)}
                                sub={`+${rewardPct.toFixed(1)}% gain`}
                                color="#00ff88"
                                bg="rgba(0,255,136,0.05)"
                            />
                            {/* R:R box */}
                            <div className="flex flex-col items-center justify-center px-3 py-2 rounded-lg flex-1"
                                 style={{ background: `${rrColor}08`, border: `1px solid ${rrColor}25` }}>
                                <span className="text-[9px] text-gray-500 uppercase tracking-wide">Risk:Reward</span>
                                <span className="text-xl font-black font-mono" style={{ color: rrColor }}>
                                    {rr.toFixed(1)}:1
                                </span>
                                <span className="text-[9px] font-semibold mt-0.5" style={{ color: strengthColor }}>
                                    {strength}
                                </span>
                            </div>
                        </div>

                        {/* Pivot levels */}
                        {Object.keys(key_levels).length > 0 && (
                            <div className="flex gap-3 mt-2 flex-wrap">
                                {[
                                    { k: 'pivot',       label: 'Pivot' },
                                    { k: 'resistance1', label: 'R1' },
                                    { k: 'support1',    label: 'S1' },
                                    { k: 'resistance2', label: 'R2' },
                                    { k: 'support2',    label: 'S2' },
                                ].map(({ k, label }) => key_levels[k] != null && (
                                    <div key={k} className="flex items-center gap-1 text-[10px]">
                                        <span className="text-gray-600">{label}</span>
                                        <span className="text-gray-400 font-mono">{fmt(key_levels[k])}</span>
                                    </div>
                                ))}
                                <div className="flex items-center gap-1 text-[10px]">
                                    <span className="text-gray-600">ATR</span>
                                    <span className="text-gray-400 font-mono">{fmt(key_levels.atr)}</span>
                                </div>
                            </div>
                        )}
                    </div>
                )}

                {/* ── Row 3: Oracle signals | Chart patterns | News ── */}
                <div className="grid grid-cols-3 gap-4 pt-4"
                     style={{ borderTop: '1px solid rgba(255,255,255,0.05)' }}>

                    {/* Oracle signals */}
                    <div>
                        <p className="text-[9px] text-gray-600 uppercase tracking-[0.12em] mb-2.5 font-semibold">
                            Oracle Signals
                        </p>
                        {bullSignals.length === 0 && bearSignals.length === 0 ? (
                            <span className="text-[11px] text-gray-600">No strong signals</span>
                        ) : (
                            <div className="flex flex-col gap-1.5 flex-wrap">
                                {bullSignals.map(sig => <SignalPill key={sig} label={sig} type="bull" />)}
                                {bearSignals.map(sig => <SignalPill key={sig} label={sig} type="bear" />)}
                            </div>
                        )}
                    </div>

                    {/* Chart patterns */}
                    <div>
                        <p className="text-[9px] text-gray-600 uppercase tracking-[0.12em] mb-2.5 font-semibold">
                            Chart Patterns
                        </p>
                        {chart_patterns.length === 0 ? (
                            <span className="text-[11px] text-gray-600">No clear patterns</span>
                        ) : (
                            <div className="flex flex-col gap-1">
                                {chart_patterns.map((pat, i) => (
                                    <span key={i} className="text-[11px] text-gray-300">{pat}</span>
                                ))}
                            </div>
                        )}
                    </div>

                    {/* News alignment */}
                    <div>
                        <p className="text-[9px] text-gray-600 uppercase tracking-[0.12em] mb-2.5 font-semibold">
                            News Alignment
                        </p>
                        {newsTotal === 0 ? (
                            <span className="text-[11px] text-gray-600">Fetching news…</span>
                        ) : (
                            <div className="flex flex-col gap-1.5">
                                <div className="flex gap-0.5 h-1.5 rounded-full overflow-hidden w-full"
                                     style={{ background: 'rgba(255,255,255,0.06)' }}>
                                    {newsSupp > 0 && (
                                        <div style={{ width: `${(newsSupp / newsTotal) * 100}%`, background: '#00ff88', borderRadius: 99 }} />
                                    )}
                                    {newsContra > 0 && (
                                        <div style={{ width: `${(newsContra / newsTotal) * 100}%`, background: '#ef4444', borderRadius: 99 }} />
                                    )}
                                </div>
                                <div className="flex items-center gap-2 text-[10px]">
                                    {newsSupp   > 0 && <span className="text-green-400">{newsSupp} supporting</span>}
                                    {newsContra > 0 && <span className="text-red-400">{newsContra} against</span>}
                                </div>
                                {newsSumm && (
                                    <p className="text-[10px] text-gray-500 leading-relaxed">{newsSumm}</p>
                                )}
                                <span className="text-[10px] font-medium"
                                      style={{ color: newsVerdict === 'supports'    ? '#00ff88'
                                                    : newsVerdict === 'contradicts' ? '#ef4444' : '#6b7280' }}>
                                    {newsVerdict === 'supports'    ? '✅ News supports prediction'
                                   : newsVerdict === 'contradicts' ? '⚠️ News contradicts prediction'
                                   :                                 '→ News neutral'}
                                </span>
                            </div>
                        )}
                    </div>
                </div>
            </div>
        </motion.div>
    )
}
