import { motion, AnimatePresence } from 'framer-motion'
import { useState, useEffect } from 'react'

const PHASES = [
    { label: 'Connecting to exchanges', pct: 18 },
    { label: 'Loading ML ensemble', pct: 42 },
    { label: 'Streaming market data', pct: 66 },
    { label: 'Calibrating predictions', pct: 88 },
    { label: 'Ready to trade', pct: 100 },
]

function OrbitalRings() {
    return (
        <div className="relative flex items-center justify-center" style={{ width: 180, height: 180 }}>
            {/* Outer ring */}
            <motion.div
                className="absolute rounded-full"
                style={{
                    width: 180, height: 180,
                    border: '1px solid rgba(200,255,0,0.18)',
                }}
                animate={{ rotate: 360 }}
                transition={{ duration: 18, repeat: Infinity, ease: 'linear' }}
            >
                <div
                    className="absolute -top-1.5 left-1/2 -translate-x-1/2 w-3 h-3 rounded-full"
                    style={{ background: '#c8ff00', boxShadow: '0 0 12px #c8ff00, 0 0 24px rgba(200,255,0,0.5)' }}
                />
                <div
                    className="absolute -bottom-1 left-1/2 -translate-x-1/2 w-1.5 h-1.5 rounded-full"
                    style={{ background: 'rgba(200,255,0,0.35)' }}
                />
            </motion.div>

            {/* Mid ring */}
            <motion.div
                className="absolute rounded-full"
                style={{
                    width: 130, height: 130,
                    border: '1px solid rgba(0,212,170,0.22)',
                }}
                animate={{ rotate: -360 }}
                transition={{ duration: 12, repeat: Infinity, ease: 'linear' }}
            >
                <div
                    className="absolute -top-1 left-1/2 -translate-x-1/2 w-2 h-2 rounded-full"
                    style={{ background: '#00d4aa', boxShadow: '0 0 8px #00d4aa' }}
                />
                <div
                    className="absolute top-1/2 -right-1 -translate-y-1/2 w-1.5 h-1.5 rounded-full"
                    style={{ background: 'rgba(0,212,170,0.3)' }}
                />
            </motion.div>

            {/* Inner ring */}
            <motion.div
                className="absolute rounded-full"
                style={{
                    width: 82, height: 82,
                    border: '1px solid rgba(255,255,255,0.07)',
                }}
                animate={{ rotate: 360 }}
                transition={{ duration: 7, repeat: Infinity, ease: 'linear' }}
            >
                <div className="absolute -top-0.5 left-1/2 -translate-x-1/2 w-1 h-1 rounded-full bg-white/40" />
            </motion.div>

            {/* Core ambient glow */}
            <motion.div
                className="absolute w-14 h-14 rounded-full"
                style={{ background: 'radial-gradient(circle, rgba(200,255,0,0.35), transparent 70%)' }}
                animate={{ scale: [1, 1.6, 1], opacity: [0.4, 0.9, 0.4] }}
                transition={{ duration: 2.5, repeat: Infinity, ease: 'easeInOut' }}
            />

            {/* Core node */}
            <div
                className="relative w-9 h-9 rounded-full flex items-center justify-center"
                style={{
                    border: '1px solid rgba(200,255,0,0.55)',
                    background: 'radial-gradient(circle at 38% 38%, rgba(200,255,0,0.18), rgba(5,5,8,0.95))',
                    boxShadow: 'inset 0 1px 0 rgba(200,255,0,0.12)',
                }}
            >
                <div
                    className="w-3 h-3 rounded-full"
                    style={{ background: '#c8ff00', boxShadow: '0 0 12px #c8ff00' }}
                />
            </div>
        </div>
    )
}

export default function LoadingScreen() {
    const [phase, setPhase] = useState(0)
    const [pct, setPct] = useState(0)

    useEffect(() => {
        const id = setInterval(() => setPhase(p => Math.min(p + 1, PHASES.length - 1)), 780)
        return () => clearInterval(id)
    }, [])

    useEffect(() => {
        const target = PHASES[phase].pct
        const id = setInterval(() => {
            setPct(p => {
                if (p >= target) return p
                return Math.min(p + Math.ceil((target - p) / 10), target)
            })
        }, 30)
        return () => clearInterval(id)
    }, [phase])

    return (
        <motion.div
            exit={{ opacity: 0, scale: 1.03 }}
            transition={{ duration: 0.7, ease: [0.76, 0, 0.24, 1] }}
            className="fixed inset-0 flex flex-col items-center justify-center z-50 overflow-hidden"
            style={{ background: '#050508' }}
        >
            {/* Aurora orbs */}
            <div className="absolute inset-0 overflow-hidden pointer-events-none">
                <motion.div
                    className="absolute rounded-full"
                    style={{
                        width: 640, height: 640,
                        top: '-15%', left: '-10%',
                        background: 'radial-gradient(circle, rgba(200,255,0,0.06) 0%, transparent 70%)',
                        filter: 'blur(80px)',
                    }}
                    animate={{ x: [0, 60, 0], y: [0, -40, 0], scale: [1, 1.15, 1] }}
                    transition={{ duration: 14, repeat: Infinity, ease: 'easeInOut' }}
                />
                <motion.div
                    className="absolute rounded-full"
                    style={{
                        width: 520, height: 520,
                        bottom: '-10%', right: '-5%',
                        background: 'radial-gradient(circle, rgba(0,212,170,0.06) 0%, transparent 70%)',
                        filter: 'blur(80px)',
                    }}
                    animate={{ x: [0, -40, 0], y: [0, 50, 0], scale: [1, 1.1, 1] }}
                    transition={{ duration: 18, repeat: Infinity, ease: 'easeInOut', delay: 3 }}
                />
            </div>

            {/* Noise silk texture */}
            <div
                className="absolute inset-0 pointer-events-none"
                style={{
                    backgroundImage: `url("data:image/svg+xml,%3Csvg viewBox='0 0 512 512' xmlns='http://www.w3.org/2000/svg'%3E%3Cfilter id='n'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='0.75' numOctaves='4' stitchTiles='stitch'/%3E%3C/filter%3E%3Crect width='100%25' height='100%25' filter='url(%23n)'/%3E%3C/svg%3E")`,
                    backgroundRepeat: 'repeat',
                    backgroundSize: '256px 256px',
                    opacity: 0.025,
                }}
            />

            {/* Scan line */}
            <motion.div
                className="absolute w-full pointer-events-none"
                style={{
                    height: 1,
                    background: 'linear-gradient(90deg, transparent 0%, rgba(200,255,0,0.12) 50%, transparent 100%)',
                }}
                animate={{ y: ['-5vh', '105vh'] }}
                transition={{ duration: 5, repeat: Infinity, ease: 'linear', repeatDelay: 2 }}
            />

            <div className="relative z-10 flex flex-col items-center gap-10">
                <OrbitalRings />

                {/* Brand */}
                <div className="text-center space-y-2">
                    <motion.h1
                        initial={{ opacity: 0, y: 16 }}
                        animate={{ opacity: 1, y: 0 }}
                        transition={{ duration: 0.8, delay: 0.2, ease: [0.16, 1, 0.3, 1] }}
                        style={{
                            fontFamily: "'Outfit', sans-serif",
                            fontSize: 26,
                            fontWeight: 700,
                            letterSpacing: '0.28em',
                            color: '#c8ff00',
                            textTransform: 'uppercase',
                        }}
                    >
                        NexusTrader
                    </motion.h1>
                    <motion.p
                        initial={{ opacity: 0 }}
                        animate={{ opacity: 0.3 }}
                        transition={{ delay: 0.65 }}
                        style={{
                            fontFamily: "'JetBrains Mono', monospace",
                            fontSize: 10,
                            letterSpacing: '0.52em',
                            color: 'white',
                            textTransform: 'uppercase',
                        }}
                    >
                        AI · PREDICT · TRADE
                    </motion.p>
                </div>

                {/* Progress section */}
                <div style={{ width: 248 }} className="space-y-3">
                    {/* Slim progress bar */}
                    <div
                        className="relative h-px overflow-hidden"
                        style={{ background: 'rgba(255,255,255,0.07)' }}
                    >
                        <motion.div
                            className="absolute inset-y-0 left-0"
                            style={{
                                background: 'linear-gradient(90deg, #c8ff00, #00d4aa)',
                                boxShadow: '0 0 10px rgba(200,255,0,0.7)',
                            }}
                            animate={{ width: `${pct}%` }}
                            transition={{ duration: 0.35, ease: 'easeOut' }}
                        />
                    </div>

                    <div className="flex items-center justify-between">
                        <AnimatePresence mode="wait">
                            <motion.span
                                key={phase}
                                initial={{ opacity: 0, x: 10 }}
                                animate={{ opacity: 1, x: 0 }}
                                exit={{ opacity: 0, x: -10 }}
                                transition={{ duration: 0.2 }}
                                style={{
                                    fontFamily: "'JetBrains Mono', monospace",
                                    fontSize: 11,
                                    color: 'rgba(255,255,255,0.33)',
                                }}
                            >
                                {PHASES[phase].label}
                            </motion.span>
                        </AnimatePresence>
                        <span
                            style={{
                                fontFamily: "'JetBrains Mono', monospace",
                                fontSize: 11,
                                color: '#c8ff00',
                            }}
                        >
                            {pct}%
                        </span>
                    </div>
                </div>
            </div>
        </motion.div>
    )
}
