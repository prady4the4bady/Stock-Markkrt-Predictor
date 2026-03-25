import { useState, useEffect, useRef, useCallback } from 'react'
import { motion, useScroll, useTransform, AnimatePresence, useSpring } from 'framer-motion'
import { useNavigate } from 'react-router-dom'
import {
    ArrowRight, Brain, Zap, Globe, LineChart,
    Shield, ChevronRight, Star, Activity, TrendingUp,
    Sparkles, BarChart3
} from 'lucide-react'
import { useAuth } from '../context/AuthContext'

const C = {
    lime: '#c8ff00',
    teal: '#00d4aa',
    bg: '#050508',
    bgCard: 'rgba(255,255,255,0.04)',
    border: 'rgba(255,255,255,0.08)',
    borderHover: 'rgba(255,255,255,0.14)',
    text: '#f0f0f0',
    muted: 'rgba(255,255,255,0.4)',
    dim: 'rgba(255,255,255,0.22)',
}

// ─── Background layers ────────────────────────────────────────
function AuroraBackground() {
    return (
        <div className="fixed inset-0 overflow-hidden pointer-events-none" style={{ zIndex: 0 }}>
            <motion.div
                className="absolute rounded-full"
                style={{
                    width: 900, height: 900,
                    top: '-30%', left: '-20%',
                    background: 'radial-gradient(circle, rgba(200,255,0,0.055) 0%, transparent 65%)',
                    filter: 'blur(80px)',
                }}
                animate={{ x: [0, 80, 30, 0], y: [0, 60, -40, 0] }}
                transition={{ duration: 22, repeat: Infinity, ease: 'easeInOut' }}
            />
            <motion.div
                className="absolute rounded-full"
                style={{
                    width: 700, height: 700,
                    bottom: '-20%', right: '-15%',
                    background: 'radial-gradient(circle, rgba(0,212,170,0.05) 0%, transparent 65%)',
                    filter: 'blur(80px)',
                }}
                animate={{ x: [0, -60, -20, 0], y: [0, -50, 40, 0] }}
                transition={{ duration: 28, repeat: Infinity, ease: 'easeInOut', delay: 6 }}
            />
            <motion.div
                className="absolute rounded-full"
                style={{
                    width: 500, height: 500,
                    top: '45%', left: '45%',
                    background: 'radial-gradient(circle, rgba(200,255,0,0.03) 0%, transparent 65%)',
                    filter: 'blur(60px)',
                }}
                animate={{ x: [0, 50, 0], y: [0, -60, 0] }}
                transition={{ duration: 18, repeat: Infinity, ease: 'easeInOut', delay: 10 }}
            />
            {/* Dot grid */}
            <div
                className="absolute inset-0"
                style={{
                    backgroundImage: 'radial-gradient(circle, rgba(255,255,255,0.055) 1px, transparent 1px)',
                    backgroundSize: '44px 44px',
                }}
            />
            {/* Noise silk overlay */}
            <div
                className="absolute inset-0"
                style={{
                    backgroundImage: `url("data:image/svg+xml,%3Csvg viewBox='0 0 512 512' xmlns='http://www.w3.org/2000/svg'%3E%3Cfilter id='n'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='0.75' numOctaves='4' stitchTiles='stitch'/%3E%3C/filter%3E%3Crect width='100%25' height='100%25' filter='url(%23n)'/%3E%3C/svg%3E")`,
                    backgroundRepeat: 'repeat',
                    backgroundSize: '256px 256px',
                    opacity: 0.022,
                }}
            />
        </div>
    )
}

// ─── Mock Prediction Card ─────────────────────────────────────
function MockPredictionCard() {
    const [tick, setTick] = useState(0)
    const [price, setPrice] = useState(186.42)
    const cardRef = useRef(null)
    const rotateX = useSpring(0, { stiffness: 200, damping: 20 })
    const rotateY = useSpring(0, { stiffness: 200, damping: 20 })

    useEffect(() => {
        const id = setInterval(() => {
            setPrice(p => +(p + (Math.random() - 0.46) * 0.6).toFixed(2))
            setTick(t => t + 1)
        }, 2200)
        return () => clearInterval(id)
    }, [])

    const handleMouseMove = useCallback((e) => {
        const el = cardRef.current
        if (!el) return
        const { left, top, width, height } = el.getBoundingClientRect()
        const x = (e.clientX - left) / width - 0.5
        const y = (e.clientY - top) / height - 0.5
        rotateY.set(x * 18)
        rotateX.set(-y * 18)
    }, [rotateX, rotateY])

    const handleMouseLeave = useCallback(() => {
        rotateX.set(0)
        rotateY.set(0)
    }, [rotateX, rotateY])

    return (
        <motion.div
            className="relative"
            animate={{ y: [0, -10, 0] }}
            transition={{ duration: 7, repeat: Infinity, ease: 'easeInOut' }}
            style={{ perspective: 900 }}
        >
            {/* Card */}
            <motion.div
                ref={cardRef}
                initial={{ opacity: 0, y: 40, rotateX: 12 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ duration: 1.1, delay: 0.5, ease: [0.16, 1, 0.3, 1] }}
                onMouseMove={handleMouseMove}
                onMouseLeave={handleMouseLeave}
                className="relative w-80 rounded-2xl overflow-hidden cursor-default"
                style={{
                    rotateX,
                    rotateY,
                    transformStyle: 'preserve-3d',
                    background: 'rgba(255,255,255,0.04)',
                    backdropFilter: 'blur(40px)',
                    border: '1px solid rgba(255,255,255,0.09)',
                    boxShadow: '0 0 80px rgba(200,255,0,0.06), inset 0 1px 0 rgba(255,255,255,0.09), 0 40px 80px rgba(0,0,0,0.5)',
                }}
            >
                {/* Shimmer top border */}
                <div
                    className="absolute top-0 left-0 right-0 h-px"
                    style={{ background: 'linear-gradient(90deg, transparent, rgba(200,255,0,0.4), transparent)' }}
                />

                {/* Header */}
                <div className="px-5 pt-5 pb-3 flex items-center justify-between">
                    <div className="flex items-center gap-3">
                        <div
                            className="w-8 h-8 rounded-lg flex items-center justify-center font-bold text-sm"
                            style={{ background: 'rgba(200,255,0,0.12)', color: C.lime }}
                        >A</div>
                        <div>
                            <p className="text-sm font-semibold text-white">AAPL</p>
                            <p className="text-xs" style={{ color: C.muted }}>Apple Inc.</p>
                        </div>
                    </div>
                    <motion.div
                        className="px-2.5 py-1 rounded-full text-xs font-bold"
                        style={{ background: 'rgba(200,255,0,0.12)', color: C.lime }}
                        animate={{ opacity: [0.8, 1, 0.8] }}
                        transition={{ duration: 2.5, repeat: Infinity }}
                    >
                        BULLISH ↑
                    </motion.div>
                </div>

                {/* Price */}
                <div className="px-5 pb-4">
                    <AnimatePresence mode="wait">
                        <motion.p
                            key={tick}
                            initial={{ opacity: 0.5, y: -4 }}
                            animate={{ opacity: 1, y: 0 }}
                            transition={{ duration: 0.25 }}
                            className="font-bold"
                            style={{
                                fontFamily: "'JetBrains Mono', monospace",
                                fontSize: 32,
                                color: '#fff',
                                lineHeight: 1,
                            }}
                        >
                            ${price.toFixed(2)}
                        </motion.p>
                    </AnimatePresence>
                    <p className="text-xs mt-1" style={{ color: C.teal }}>▲ +2.34% today</p>
                </div>

                {/* Mini area chart */}
                <div style={{ height: 72 }}>
                    <svg width="100%" height="72" viewBox="0 0 320 72" preserveAspectRatio="none">
                        <defs>
                            <linearGradient id="areaGrad" x1="0" y1="0" x2="0" y2="1">
                                <stop offset="0%" stopColor="#c8ff00" stopOpacity="0.25" />
                                <stop offset="100%" stopColor="#c8ff00" stopOpacity="0" />
                            </linearGradient>
                        </defs>
                        <motion.path
                            d="M0,60 C30,52 60,35 90,30 S140,18 180,14 S230,10 260,16 S290,20 320,12 L320,72 L0,72 Z"
                            fill="url(#areaGrad)"
                            initial={{ opacity: 0 }}
                            animate={{ opacity: 1 }}
                            transition={{ duration: 1, delay: 1 }}
                        />
                        <motion.path
                            d="M0,60 C30,52 60,35 90,30 S140,18 180,14 S230,10 260,16 S290,20 320,12"
                            fill="none"
                            stroke="#c8ff00"
                            strokeWidth="1.8"
                            strokeLinecap="round"
                            initial={{ pathLength: 0 }}
                            animate={{ pathLength: 1 }}
                            transition={{ duration: 2, delay: 0.8, ease: 'easeOut' }}
                            style={{ filter: 'drop-shadow(0 0 4px rgba(200,255,0,0.7))' }}
                        />
                        <motion.circle
                            cx="320" cy="12" r="3.5"
                            fill="#c8ff00"
                            initial={{ scale: 0 }}
                            animate={{ scale: [1, 1.6, 1] }}
                            transition={{ duration: 1.8, repeat: Infinity, delay: 2.8 }}
                            style={{ filter: 'drop-shadow(0 0 6px rgba(200,255,0,0.9))' }}
                        />
                    </svg>
                </div>

                {/* Confidence */}
                <div className="px-5 py-4" style={{ borderTop: `1px solid ${C.border}` }}>
                    <div className="flex items-center justify-between mb-2">
                        <span className="text-xs" style={{ color: C.muted }}>AI Confidence</span>
                        <span className="text-xs font-bold" style={{ color: C.lime, fontFamily: "'JetBrains Mono', monospace" }}>87%</span>
                    </div>
                    <div className="h-1 rounded-full overflow-hidden" style={{ background: 'rgba(255,255,255,0.07)' }}>
                        <motion.div
                            className="h-full rounded-full"
                            style={{ background: `linear-gradient(90deg, ${C.lime}, ${C.teal})`, boxShadow: '0 0 8px rgba(200,255,0,0.5)' }}
                            initial={{ width: 0 }}
                            animate={{ width: '87%' }}
                            transition={{ duration: 1.5, delay: 1, ease: 'easeOut' }}
                        />
                    </div>
                </div>

                {/* Model signals */}
                <div className="px-5 pb-5 grid grid-cols-3 gap-2">
                    {[
                        { label: 'LSTM', val: '▲', color: C.lime },
                        { label: 'XGBoost', val: '▲', color: C.teal },
                        { label: 'Prophet', val: '→', color: C.dim },
                    ].map((m, i) => (
                        <motion.div
                            key={m.label}
                            initial={{ opacity: 0, y: 8 }}
                            animate={{ opacity: 1, y: 0 }}
                            transition={{ delay: 1.4 + i * 0.1 }}
                            className="text-center py-2 px-1 rounded-lg"
                            style={{ background: 'rgba(255,255,255,0.04)' }}
                        >
                            <p className="text-xs mb-0.5" style={{ color: C.muted, fontFamily: "'JetBrains Mono', monospace" }}>{m.label}</p>
                            <p className="text-base font-bold" style={{ color: m.color }}>{m.val}</p>
                        </motion.div>
                    ))}
                </div>
            </motion.div>

            {/* Floating stat badges */}
            <motion.div
                initial={{ opacity: 0, x: -24 }}
                animate={{ opacity: 1, x: 0 }}
                transition={{ delay: 1.2, ease: [0.16, 1, 0.3, 1] }}
                className="absolute -left-16 top-1/4 px-4 py-3 rounded-xl"
                style={{
                    background: 'rgba(5,5,8,0.92)',
                    backdropFilter: 'blur(20px)',
                    border: '1px solid rgba(200,255,0,0.2)',
                    boxShadow: '0 0 20px rgba(200,255,0,0.07)',
                }}
            >
                <p className="text-xl font-bold" style={{ color: C.lime, fontFamily: "'JetBrains Mono', monospace" }}>+127%</p>
                <p className="text-xs" style={{ color: C.muted }}>Avg Return</p>
            </motion.div>

            <motion.div
                initial={{ opacity: 0, x: 24 }}
                animate={{ opacity: 1, x: 0 }}
                transition={{ delay: 1.5, ease: [0.16, 1, 0.3, 1] }}
                className="absolute -right-12 bottom-1/3 px-4 py-3 rounded-xl"
                style={{
                    background: 'rgba(5,5,8,0.92)',
                    backdropFilter: 'blur(20px)',
                    border: '1px solid rgba(0,212,170,0.2)',
                    boxShadow: '0 0 20px rgba(0,212,170,0.07)',
                }}
            >
                <div className="flex items-center gap-2 mb-0.5">
                    <motion.div
                        className="w-2 h-2 rounded-full"
                        style={{ background: C.teal }}
                        animate={{ opacity: [1, 0.3, 1] }}
                        transition={{ duration: 1.2, repeat: Infinity }}
                    />
                    <p className="text-sm font-bold" style={{ color: C.teal }}>LIVE</p>
                </div>
                <p className="text-xs" style={{ color: C.muted }}>Real-time</p>
            </motion.div>
        </motion.div>
    )
}

// ─── Marquee ticker ───────────────────────────────────────────
function MarqueeTicker() {
    const items = [
        '6 ML MODELS', '50+ EXCHANGES', '10K+ ASSETS', 'REAL-TIME DATA',
        'LSTM NEURAL NETS', 'XGBOOST', 'PROPHET', 'AI SIGNALS',
        'STOCKS · CRYPTO · FOREX', '95% ACCURACY', 'LIVE PREDICTIONS', '24/7 ANALYSIS',
    ]
    const doubled = [...items, ...items]

    return (
        <div
            className="relative overflow-hidden py-4"
            style={{ borderTop: `1px solid ${C.border}`, borderBottom: `1px solid ${C.border}` }}
        >
            <motion.div
                className="flex gap-0 whitespace-nowrap"
                animate={{ x: [0, '-50%'] }}
                transition={{ duration: 28, repeat: Infinity, ease: 'linear' }}
            >
                {doubled.map((item, i) => (
                    <div key={i} className="flex items-center gap-8 px-10">
                        <span
                            className="text-xs font-semibold tracking-[0.25em] uppercase"
                            style={{ color: C.muted }}
                        >
                            {item}
                        </span>
                        <span style={{ color: 'rgba(200,255,0,0.25)', fontSize: 16 }}>✦</span>
                    </div>
                ))}
            </motion.div>
        </div>
    )
}

// ─── Feature card (3D tilt) ────────────────────────────────────
function FeatureCard({ icon: Icon, title, desc, delay = 0, accent = C.lime }) {
    const [hovered, setHovered] = useState(false)
    const cardRef = useRef(null)
    const rotX = useSpring(0, { stiffness: 260, damping: 22 })
    const rotY = useSpring(0, { stiffness: 260, damping: 22 })
    const gX = useSpring(50, { stiffness: 200, damping: 20 })
    const gY = useSpring(50, { stiffness: 200, damping: 20 })

    const handleMouseMove = (e) => {
        const el = cardRef.current
        if (!el) return
        const { left, top, width, height } = el.getBoundingClientRect()
        const x = (e.clientX - left) / width
        const y = (e.clientY - top) / height
        rotY.set((x - 0.5) * 14)
        rotX.set(-(y - 0.5) * 14)
        gX.set(x * 100)
        gY.set(y * 100)
    }
    const handleMouseLeave = () => {
        rotX.set(0); rotY.set(0)
        gX.set(50); gY.set(50)
        setHovered(false)
    }

    return (
        <motion.div
            ref={cardRef}
            initial={{ opacity: 0, y: 32 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true, margin: '-60px' }}
            transition={{ delay, duration: 0.7, ease: [0.16, 1, 0.3, 1] }}
            onMouseMove={handleMouseMove}
            onMouseEnter={() => setHovered(true)}
            onMouseLeave={handleMouseLeave}
            className="relative p-6 rounded-2xl overflow-hidden cursor-default"
            style={{
                rotateX: rotX, rotateY: rotY,
                transformStyle: 'preserve-3d',
                perspective: 800,
                background: hovered ? 'rgba(255,255,255,0.06)' : C.bgCard,
                border: `1px solid ${hovered ? C.borderHover : C.border}`,
                transition: 'background 0.3s, border-color 0.3s',
            }}
        >
            {/* Dynamic spotlight */}
            <motion.div
                className="absolute inset-0 pointer-events-none"
                style={{
                    background: `radial-gradient(circle at ${gX}% ${gY}%, ${accent}18 0%, transparent 60%)`,
                    opacity: hovered ? 1 : 0,
                    transition: 'opacity 0.3s',
                }}
            />

            <div
                className="w-11 h-11 rounded-xl flex items-center justify-center mb-4"
                style={{
                    background: `${accent}14`,
                    border: `1px solid ${accent}25`,
                    boxShadow: hovered ? `0 0 24px ${accent}25` : 'none',
                    transition: 'box-shadow 0.3s',
                    transform: 'translateZ(20px)',
                }}
            >
                <Icon size={19} style={{ color: accent }} />
            </div>

            <h3
                className="text-sm font-semibold text-white mb-1.5"
                style={{ fontFamily: "'Outfit', sans-serif", transform: 'translateZ(16px)' }}
            >
                {title}
            </h3>
            <p className="text-xs leading-relaxed" style={{ color: C.muted, transform: 'translateZ(10px)' }}>{desc}</p>
        </motion.div>
    )
}

// ─── Scroll progress bar ──────────────────────────────────────
function ScrollProgressBar() {
    const { scrollYProgress } = useScroll()
    const scaleX = useSpring(scrollYProgress, { stiffness: 100, damping: 30 })
    return (
        <motion.div
            className="fixed top-0 left-0 right-0 h-0.5 z-[100] origin-left"
            style={{ scaleX, background: 'linear-gradient(90deg, #c8ff00, #00d4aa)' }}
        />
    )
}

// ─── Main component ───────────────────────────────────────────
export default function LandingPage() {
    const navigate = useNavigate()
    const { user } = useAuth()
    const { scrollYProgress } = useScroll()
    const heroY = useTransform(scrollYProgress, [0, 0.25], [0, -80])
    const heroOpacity = useTransform(scrollYProgress, [0, 0.22], [1, 0])


    const features = [
        { icon: Brain, title: 'Neural Network Core', desc: 'LSTM deep learning model trained on millions of candlesticks for precise pattern recognition.', accent: C.lime },
        { icon: BarChart3, title: '6-Model Ensemble', desc: 'XGBoost, Prophet, ARIMA, GARCH and more vote together — outliers get filtered, accuracy rises.', accent: C.teal },
        { icon: Globe, title: '50+ Global Exchanges', desc: 'NYSE, NASDAQ, NSE, TSE, LSE and 45+ more. One platform for every market.', accent: C.lime },
        { icon: Zap, title: 'Real-Time Signals', desc: 'Live BUY/SELL signals with confidence scores, price targets and risk assessments.', accent: C.teal },
        { icon: LineChart, title: 'Technical Indicators', desc: 'RSI, MACD, Bollinger Bands, Fibonacci — full indicator suite baked into the AI.', accent: C.lime },
        { icon: Shield, title: 'Risk Intelligence', desc: 'Volatility-adjusted signals. Know the risk before entering any position.', accent: C.teal },
    ]

    const testimonials = [
        { text: "NexusTrader's AI predictions transformed my strategy entirely. The ensemble accuracy is genuinely remarkable.", author: 'Michael R.', role: 'Day Trader, NYC' },
        { text: "Finally, institutional-grade analytics accessible to independent traders. This is the future.", author: 'Sarah K.', role: 'Portfolio Manager' },
        { text: "The multi-model approach gives me conviction I've never had before. Every trade is data-backed.", author: 'James L.', role: 'Crypto Investor' },
    ]

    return (
        <div className="relative min-h-screen text-white overflow-x-hidden" style={{ background: C.bg }}>
            <ScrollProgressBar />
            <AuroraBackground />

            {/* ── Navigation ──────────────────────────── */}
            <motion.nav
                initial={{ y: -100, opacity: 0 }}
                animate={{ y: 0, opacity: 1 }}
                transition={{ duration: 0.7, ease: [0.16, 1, 0.3, 1] }}
                className="fixed top-0 left-0 right-0 z-50 flex items-center justify-between px-8 py-4"
                style={{
                    background: 'rgba(5,5,8,0.75)',
                    backdropFilter: 'blur(24px)',
                    borderBottom: '1px solid rgba(255,255,255,0.06)',
                }}
            >
                <motion.div
                    className="flex items-center gap-3 cursor-pointer select-none"
                    whileHover={{ scale: 1.03 }}
                    whileTap={{ scale: 0.97 }}
                    onClick={() => navigate('/')}
                >
                    <img src="/favicon.svg" alt="NexusTrader" className="w-8 h-8" />
                    <span
                        className="text-xl font-bold tracking-wide"
                        style={{ fontFamily: "'Outfit', sans-serif", color: C.lime }}
                    >
                        NEXUSTRADER
                    </span>
                </motion.div>

                <div className="hidden md:flex items-center gap-8">
                    {['Features', 'How It Works', 'About'].map(item => (
                        <motion.a
                            key={item}
                            href={`#${item.toLowerCase().replace(/ /g, '-')}`}
                            className="text-sm font-medium tracking-wider uppercase"
                            style={{ color: C.muted, transition: 'color 0.2s' }}
                            whileHover={{ color: '#fff' }}
                        >
                            {item}
                        </motion.a>
                    ))}
                </div>

                <div className="flex items-center gap-3">
                    {user ? (
                        <motion.button
                            whileHover={{ boxShadow: `0 0 36px rgba(200,255,0,0.4)`, scale: 1.04 }}
                            whileTap={{ scale: 0.96 }}
                            onClick={() => navigate('/dashboard')}
                            className="px-5 py-2.5 text-sm font-bold rounded-full text-black flex items-center gap-2"
                            style={{ background: C.lime, fontFamily: "'Outfit', sans-serif" }}
                        >
                            Go to Dashboard <ArrowRight size={14} />
                        </motion.button>
                    ) : (
                        <>
                            <motion.button
                                whileHover={{ backgroundColor: 'rgba(255,255,255,0.07)' }}
                                whileTap={{ scale: 0.96 }}
                                onClick={() => navigate('/login')}
                                className="px-5 py-2.5 text-sm font-semibold rounded-full border transition-all"
                                style={{ borderColor: C.border, color: 'rgba(255,255,255,0.7)' }}
                            >
                                Sign In
                            </motion.button>
                            <motion.button
                                whileHover={{ boxShadow: `0 0 36px rgba(200,255,0,0.4)`, scale: 1.04 }}
                                whileTap={{ scale: 0.96 }}
                                onClick={() => navigate('/register')}
                                className="px-5 py-2.5 text-sm font-bold rounded-full text-black"
                                style={{ background: C.lime, fontFamily: "'Outfit', sans-serif" }}
                            >
                                Get Started
                            </motion.button>
                        </>
                    )}
                </div>
            </motion.nav>

            {/* ── Hero ────────────────────────────────── */}
            <motion.section
                style={{ y: heroY, opacity: heroOpacity }}
                className="relative min-h-screen flex items-center pt-20"
            >
                <div className="relative z-10 w-full max-w-7xl mx-auto px-8 lg:px-16">
                    <div className="grid lg:grid-cols-2 gap-16 items-center min-h-[85vh]">

                        {/* Left — display text */}
                        <div>
                            <motion.div
                                initial={{ opacity: 0, y: 24 }}
                                animate={{ opacity: 1, y: 0 }}
                                transition={{ duration: 0.6, delay: 0.1, ease: [0.16, 1, 0.3, 1] }}
                                className="inline-flex items-center gap-2 px-3.5 py-1.5 rounded-full mb-8 text-xs font-semibold uppercase tracking-widest"
                                style={{
                                    background: 'rgba(200,255,0,0.1)',
                                    border: '1px solid rgba(200,255,0,0.2)',
                                    color: C.lime,
                                }}
                            >
                                <Sparkles size={12} />
                                AI-Powered Market Intelligence
                            </motion.div>

                            {['WHERE AI', 'MEETS', 'MARKETS'].map((word, i) => (
                                <div key={word} className="overflow-hidden">
                                    <motion.h1
                                        initial={{ y: '100%' }}
                                        animate={{ y: 0 }}
                                        transition={{ duration: 0.9, delay: 0.25 + i * 0.12, ease: [0.16, 1, 0.3, 1] }}
                                        style={{
                                            fontFamily: "'Outfit', sans-serif",
                                            fontSize: 'clamp(52px, 7.5vw, 108px)',
                                            fontWeight: 900,
                                            lineHeight: 0.88,
                                            letterSpacing: '-0.03em',
                                            color: i === 1 ? C.lime : '#fff',
                                            display: 'block',
                                        }}
                                    >
                                        {word}
                                    </motion.h1>
                                </div>
                            ))}

                            <motion.p
                                initial={{ opacity: 0, y: 16 }}
                                animate={{ opacity: 1, y: 0 }}
                                transition={{ duration: 0.8, delay: 0.7, ease: [0.16, 1, 0.3, 1] }}
                                className="text-lg mt-8 mb-10 max-w-md leading-relaxed"
                                style={{ color: C.muted }}
                            >
                                Harness 6 ensemble ML models for smarter trading decisions across
                                50+ global exchanges — stocks, crypto, forex, indices.
                            </motion.p>

                            <motion.div
                                initial={{ opacity: 0, y: 16 }}
                                animate={{ opacity: 1, y: 0 }}
                                transition={{ duration: 0.8, delay: 0.9, ease: [0.16, 1, 0.3, 1] }}
                                className="flex flex-wrap items-center gap-4"
                            >
                                <motion.button
                                    whileHover={{ boxShadow: `0 0 60px rgba(200,255,0,0.45)`, scale: 1.04 }}
                                    whileTap={{ scale: 0.96 }}
                                    onClick={() => navigate(user ? '/dashboard' : '/register')}
                                    className="flex items-center gap-2.5 px-7 py-3.5 rounded-full text-base font-bold text-black"
                                    style={{ background: C.lime, fontFamily: "'Outfit', sans-serif" }}
                                >
                                    {user ? 'Open Dashboard' : 'Start Trading Free'}
                                    <ArrowRight size={18} />
                                </motion.button>
                                {!user && (
                                    <motion.button
                                        whileHover={{ borderColor: C.borderHover, color: '#fff' }}
                                        whileTap={{ scale: 0.96 }}
                                        onClick={() => navigate('/login')}
                                        className="flex items-center gap-2 px-7 py-3.5 rounded-full text-base font-semibold border transition-all"
                                        style={{ borderColor: C.border, color: C.muted }}
                                    >
                                        Sign in
                                    </motion.button>
                                )}
                            </motion.div>

                            {/* Social proof row */}
                            <motion.div
                                initial={{ opacity: 0 }}
                                animate={{ opacity: 1 }}
                                transition={{ delay: 1.2 }}
                                className="flex items-center gap-6 mt-10"
                            >
                                <div className="flex -space-x-2">
                                    {['M', 'S', 'J', 'A', 'K'].map((l, i) => (
                                        <div
                                            key={l}
                                            className="w-8 h-8 rounded-full flex items-center justify-center text-xs font-bold border-2"
                                            style={{
                                                background: `hsl(${i * 55}, 60%, 22%)`,
                                                borderColor: C.bg,
                                                color: C.muted,
                                                zIndex: 5 - i,
                                            }}
                                        >{l}</div>
                                    ))}
                                </div>
                                <div>
                                    <div className="flex items-center gap-1">
                                        {[...Array(5)].map((_, i) => (
                                            <Star key={i} size={12} style={{ color: C.lime, fill: C.lime }} />
                                        ))}
                                    </div>
                                    <p className="text-xs mt-0.5" style={{ color: C.muted }}>Trusted by 50K+ traders</p>
                                </div>
                            </motion.div>
                        </div>

                        {/* Right — prediction card */}
                        <div className="hidden lg:flex justify-center items-center pl-10">
                            <MockPredictionCard />
                        </div>
                    </div>
                </div>

                {/* Scroll indicator */}
                <motion.div
                    initial={{ opacity: 0 }}
                    animate={{ opacity: 1 }}
                    transition={{ delay: 2.5 }}
                    className="absolute bottom-10 left-1/2 -translate-x-1/2 flex flex-col items-center gap-2"
                >
                    <p className="text-xs tracking-[0.4em] uppercase" style={{ color: C.dim }}>Scroll</p>
                    <motion.div
                        className="w-px h-10"
                        style={{ background: `linear-gradient(to bottom, ${C.lime}70, transparent)` }}
                        animate={{ scaleY: [1, 0.3, 1], opacity: [0.5, 1, 0.5] }}
                        transition={{ duration: 1.8, repeat: Infinity }}
                    />
                </motion.div>
            </motion.section>

            {/* ── Marquee ticker ────────────────────── */}
            <MarqueeTicker />

            {/* ── Stats bar ────────────────────────── */}
            <section className="py-20 relative z-10">
                <div className="max-w-7xl mx-auto px-8 lg:px-16">
                    <div className="grid grid-cols-2 md:grid-cols-4 gap-px" style={{ background: C.border }}>
                        {[
                            { val: '95%', label: 'Prediction accuracy' },
                            { val: '50+', label: 'Global exchanges' },
                            { val: '10K+', label: 'Assets tracked' },
                            { val: '24/7', label: 'Live analysis' },
                        ].map((s, i) => (
                            <motion.div
                                key={s.label}
                                initial={{ opacity: 0 }}
                                whileInView={{ opacity: 1 }}
                                viewport={{ once: true }}
                                transition={{ delay: i * 0.08 }}
                                className="text-center py-10 px-6"
                                style={{ background: C.bg }}
                            >
                                <p
                                    className="text-4xl md:text-5xl font-black mb-1"
                                    style={{ fontFamily: "'Outfit', sans-serif", color: C.lime }}
                                >
                                    {s.val}
                                </p>
                                <p className="text-sm" style={{ color: C.muted }}>{s.label}</p>
                            </motion.div>
                        ))}
                    </div>
                </div>
            </section>

            {/* ── Features ─────────────────────────── */}
            <section id="features" className="py-24 relative z-10">
                <div className="max-w-7xl mx-auto px-8 lg:px-16">
                    <div className="mb-16">
                        <motion.p
                            initial={{ opacity: 0, y: 16 }}
                            whileInView={{ opacity: 1, y: 0 }}
                            viewport={{ once: true }}
                            className="text-xs font-semibold uppercase tracking-[0.35em] mb-4"
                            style={{ color: C.lime }}
                        >
                            Platform Features
                        </motion.p>
                        <div className="overflow-hidden">
                            <motion.h2
                                initial={{ y: '100%' }}
                                whileInView={{ y: 0 }}
                                viewport={{ once: true }}
                                transition={{ duration: 0.8, ease: [0.16, 1, 0.3, 1] }}
                                className="text-5xl md:text-7xl font-black"
                                style={{ fontFamily: "'Outfit', sans-serif", lineHeight: 0.9, letterSpacing: '-0.03em' }}
                            >
                                <span className="text-white">BUILT FOR</span>
                                <br />
                                <span style={{ color: C.lime }}>PRECISION.</span>
                            </motion.h2>
                        </div>
                    </div>

                    <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-4" style={{ perspective: '1200px' }}>
                        {features.map((f, i) => (
                            <FeatureCard key={f.title} {...f} delay={i * 0.07} />
                        ))}
                    </div>
                </div>
            </section>

            {/* ── How it works ─────────────────────── */}
            <section id="how-it-works" className="py-24 relative z-10 overflow-hidden">
                {/* Section background glow */}
                <div
                    className="absolute inset-0 pointer-events-none"
                    style={{ background: 'linear-gradient(180deg, transparent, rgba(200,255,0,0.02), transparent)' }}
                />
                <div className="max-w-7xl mx-auto px-8 lg:px-16 relative">
                    <motion.p
                        initial={{ opacity: 0 }}
                        whileInView={{ opacity: 1 }}
                        viewport={{ once: true }}
                        className="text-xs font-semibold uppercase tracking-[0.35em] mb-4 text-center"
                        style={{ color: C.lime }}
                    >
                        Process
                    </motion.p>
                    <motion.h2
                        initial={{ opacity: 0, y: 24 }}
                        whileInView={{ opacity: 1, y: 0 }}
                        viewport={{ once: true }}
                        transition={{ duration: 0.8, ease: [0.16, 1, 0.3, 1] }}
                        className="text-5xl md:text-7xl font-black text-center mb-20"
                        style={{ fontFamily: "'Outfit', sans-serif", letterSpacing: '-0.03em' }}
                    >
                        HOW IT{' '}
                        <span style={{ color: C.lime }}>WORKS</span>
                    </motion.h2>

                    <div className="grid md:grid-cols-3 gap-6">
                        {[
                            { n: '01', title: 'Select Asset', desc: 'Search 10,000+ stocks, crypto, forex pairs and indices across 50+ global exchanges.' },
                            { n: '02', title: 'AI Analysis', desc: '6 ML models analyse technicals, sentiment and patterns simultaneously in real-time.' },
                            { n: '03', title: 'Get Signal', desc: 'Receive a clear BUY/SELL signal with confidence score, price target and timeframe.' },
                        ].map((step, i) => (
                            <motion.div
                                key={step.n}
                                initial={{ opacity: 0, y: 32 }}
                                whileInView={{ opacity: 1, y: 0 }}
                                viewport={{ once: true }}
                                transition={{ delay: i * 0.14, duration: 0.7, ease: [0.16, 1, 0.3, 1] }}
                                className="relative p-8 rounded-2xl overflow-hidden group"
                                style={{
                                    background: C.bgCard,
                                    border: `1px solid ${C.border}`,
                                }}
                            >
                                {/* Large ghost number */}
                                <div
                                    className="absolute -top-4 -right-2 font-black select-none pointer-events-none"
                                    style={{
                                        fontFamily: "'Outfit', sans-serif",
                                        fontSize: 120,
                                        lineHeight: 1,
                                        color: 'rgba(200,255,0,0.06)',
                                        letterSpacing: '-0.05em',
                                    }}
                                >
                                    {step.n}
                                </div>

                                <div
                                    className="w-10 h-10 rounded-lg flex items-center justify-center font-bold text-sm mb-6"
                                    style={{
                                        background: 'rgba(200,255,0,0.1)',
                                        color: C.lime,
                                        fontFamily: "'JetBrains Mono', monospace",
                                    }}
                                >
                                    {step.n}
                                </div>
                                <h3
                                    className="text-xl font-bold text-white mb-3"
                                    style={{ fontFamily: "'Outfit', sans-serif" }}
                                >
                                    {step.title}
                                </h3>
                                <p className="text-sm leading-relaxed" style={{ color: C.muted }}>{step.desc}</p>

                                <motion.div
                                    className="absolute bottom-6 right-6 w-10 h-10 rounded-full flex items-center justify-center"
                                    style={{ background: C.lime }}
                                    initial={{ opacity: 0, scale: 0.7 }}
                                    whileInView={{ opacity: 0 }}
                                    whileHover={{ opacity: 1, scale: 1 }}
                                    viewport={{ once: false }}
                                >
                                    <ChevronRight size={18} color="#000" />
                                </motion.div>
                            </motion.div>
                        ))}
                    </div>
                </div>
            </section>

            {/* ── Social proof ──────────────────────── */}
            <section id="about" className="py-24 relative z-10">
                <div className="max-w-7xl mx-auto px-8 lg:px-16">
                    <div className="grid lg:grid-cols-2 gap-16 items-start">
                        <div>
                            <motion.p
                                initial={{ opacity: 0 }}
                                whileInView={{ opacity: 1 }}
                                viewport={{ once: true }}
                                className="text-xs font-semibold uppercase tracking-[0.35em] mb-4"
                                style={{ color: C.lime }}
                            >
                                Testimonials
                            </motion.p>
                            <div className="overflow-hidden">
                                <motion.h2
                                    initial={{ y: '100%' }}
                                    whileInView={{ y: 0 }}
                                    viewport={{ once: true }}
                                    transition={{ duration: 0.8, ease: [0.16, 1, 0.3, 1] }}
                                    className="text-5xl md:text-6xl font-black mb-8"
                                    style={{ fontFamily: "'Outfit', sans-serif", letterSpacing: '-0.03em', lineHeight: 0.9 }}
                                >
                                    TRUSTED BY
                                    <br />
                                    <span style={{ color: C.lime }}>TRADERS</span>
                                </motion.h2>
                            </div>

                            <motion.p
                                initial={{ opacity: 0, y: 16 }}
                                whileInView={{ opacity: 1, y: 0 }}
                                viewport={{ once: true }}
                                className="text-base leading-relaxed mb-10"
                                style={{ color: C.muted }}
                            >
                                Join thousands of independent traders who use NexusTrader's AI-powered
                                insights to make data-backed decisions every day.
                            </motion.p>

                            <div className="grid grid-cols-2 gap-6">
                                {[
                                    { val: '50K+', label: 'Active traders' },
                                    { val: '4.9', label: 'Average rating' },
                                ].map((s, i) => (
                                    <motion.div
                                        key={s.label}
                                        initial={{ opacity: 0, y: 16 }}
                                        whileInView={{ opacity: 1, y: 0 }}
                                        viewport={{ once: true }}
                                        transition={{ delay: i * 0.1 }}
                                    >
                                        <p
                                            className="text-4xl font-black mb-1"
                                            style={{ fontFamily: "'Outfit', sans-serif", color: i === 0 ? C.lime : C.teal }}
                                        >
                                            {s.val}
                                        </p>
                                        <p className="text-sm" style={{ color: C.muted }}>{s.label}</p>
                                    </motion.div>
                                ))}
                            </div>
                        </div>

                        <div className="space-y-4">
                            {testimonials.map((t, i) => (
                                <motion.div
                                    key={t.author}
                                    initial={{ opacity: 0, x: 24 }}
                                    whileInView={{ opacity: 1, x: 0 }}
                                    viewport={{ once: true }}
                                    transition={{ delay: i * 0.12, duration: 0.7, ease: [0.16, 1, 0.3, 1] }}
                                    className="p-6 rounded-2xl"
                                    style={{
                                        background: C.bgCard,
                                        border: `1px solid ${C.border}`,
                                        boxShadow: 'inset 0 1px 0 rgba(255,255,255,0.05)',
                                    }}
                                >
                                    <div className="flex gap-0.5 mb-4">
                                        {[...Array(5)].map((_, j) => (
                                            <Star key={j} size={12} style={{ color: C.lime, fill: C.lime }} />
                                        ))}
                                    </div>
                                    <p className="text-sm leading-relaxed mb-5" style={{ color: 'rgba(255,255,255,0.75)' }}>
                                        "{t.text}"
                                    </p>
                                    <div className="flex items-center gap-3">
                                        <div
                                            className="w-9 h-9 rounded-full flex items-center justify-center text-xs font-bold"
                                            style={{ background: 'rgba(200,255,0,0.12)', color: C.lime }}
                                        >
                                            {t.author[0]}
                                        </div>
                                        <div>
                                            <p className="text-sm font-semibold text-white">{t.author}</p>
                                            <p className="text-xs" style={{ color: C.muted }}>{t.role}</p>
                                        </div>
                                    </div>
                                </motion.div>
                            ))}
                        </div>
                    </div>
                </div>
            </section>

            {/* ── CTA ────────────────────────────────── */}
            <section className="py-28 relative z-10 overflow-hidden">
                {/* Intense glow backdrop */}
                <div
                    className="absolute inset-0 pointer-events-none"
                    style={{ background: 'radial-gradient(ellipse 80% 60% at 50% 50%, rgba(200,255,0,0.07), transparent)' }}
                />
                <div
                    className="absolute inset-0 pointer-events-none"
                    style={{ border: `1px solid ${C.border}`, borderLeft: 'none', borderRight: 'none' }}
                />

                <div className="max-w-4xl mx-auto px-8 text-center relative">
                    <motion.div
                        initial={{ opacity: 0, scale: 0.95 }}
                        whileInView={{ opacity: 1, scale: 1 }}
                        viewport={{ once: true }}
                        transition={{ duration: 0.8, ease: [0.16, 1, 0.3, 1] }}
                    >
                        <div className="overflow-hidden mb-2">
                            <motion.p
                                initial={{ y: '100%' }}
                                whileInView={{ y: 0 }}
                                viewport={{ once: true }}
                                transition={{ duration: 0.8, ease: [0.16, 1, 0.3, 1] }}
                                className="text-xs font-semibold uppercase tracking-[0.35em] mb-6 block"
                                style={{ color: C.lime }}
                            >
                                Start Today — Free Forever
                            </motion.p>
                        </div>
                        <h2
                            className="text-6xl md:text-8xl font-black mb-8 leading-[0.88]"
                            style={{ fontFamily: "'Outfit', sans-serif", letterSpacing: '-0.04em' }}
                        >
                            TRADE
                            <br />
                            <span style={{ color: C.lime }}>SMARTER.</span>
                        </h2>
                        <p className="text-lg mb-12 max-w-lg mx-auto" style={{ color: C.muted }}>
                            Join NexusTrader free and get access to AI predictions, live charts
                            and global market analysis — no credit card required.
                        </p>
                        <div className="flex flex-col sm:flex-row items-center justify-center gap-4">
                            <motion.button
                                whileHover={{ boxShadow: `0 0 80px rgba(200,255,0,0.5)`, scale: 1.05 }}
                                whileTap={{ scale: 0.96 }}
                                onClick={() => navigate(user ? '/dashboard' : '/register')}
                                className="flex items-center gap-3 px-10 py-4 rounded-full text-lg font-bold text-black"
                                style={{ background: C.lime, fontFamily: "'Outfit', sans-serif" }}
                            >
                                {user ? 'Go to Dashboard' : 'Create Free Account'}
                                <ArrowRight size={20} />
                            </motion.button>
                            {!user && (
                                <motion.button
                                    whileHover={{ borderColor: C.borderHover, color: '#fff' }}
                                    whileTap={{ scale: 0.96 }}
                                    onClick={() => navigate('/login')}
                                    className="flex items-center gap-2 px-10 py-4 rounded-full text-lg font-semibold border transition-all"
                                    style={{ borderColor: C.border, color: C.muted }}
                                >
                                    Already have an account
                                </motion.button>
                            )}
                        </div>
                    </motion.div>
                </div>
            </section>

            {/* ── Footer ────────────────────────────── */}
            <footer className="relative z-10 py-10" style={{ borderTop: `1px solid ${C.border}` }}>
                <div className="max-w-7xl mx-auto px-8 lg:px-16 flex flex-col md:flex-row items-center justify-between gap-6">
                    <div className="flex items-center gap-3">
                        <img src="/favicon.svg" alt="NexusTrader" className="w-7 h-7" />
                        <span
                            className="font-bold tracking-widest text-sm"
                            style={{ fontFamily: "'Outfit', sans-serif", color: C.lime }}
                        >
                            NEXUSTRADER
                        </span>
                    </div>
                    <p className="text-xs text-center" style={{ color: C.dim }}>
                        © {new Date().getFullYear()} NexusTrader. Market predictions are for informational purposes only.
                    </p>
                    <div className="flex items-center gap-6">
                        {['Privacy', 'Terms', 'Contact'].map(link => (
                            <a
                                key={link}
                                href="#"
                                className="text-xs transition-colors"
                                style={{ color: C.dim }}
                                onMouseEnter={e => (e.target.style.color = '#fff')}
                                onMouseLeave={e => (e.target.style.color = C.dim)}
                            >
                                {link}
                            </a>
                        ))}
                    </div>
                </div>
            </footer>
        </div>
    )
}
