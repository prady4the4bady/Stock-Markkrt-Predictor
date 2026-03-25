import { useState, useRef } from 'react'
import { motion } from 'framer-motion'
import { useAuth } from '../../context/AuthContext'
import { Lock, Mail, ArrowRight, AlertCircle, Loader2, Eye, EyeOff } from 'lucide-react'

const S = {
    card: {
        background: 'rgba(255,255,255,0.04)',
        backdropFilter: 'blur(40px)',
        WebkitBackdropFilter: 'blur(40px)',
        border: '1px solid rgba(255,255,255,0.09)',
        boxShadow: '0 0 80px rgba(200,255,0,0.06), inset 0 1px 0 rgba(255,255,255,0.08), 0 40px 80px rgba(0,0,0,0.4)',
    },
    input: {
        background: 'rgba(255,255,255,0.04)',
        border: '1px solid rgba(255,255,255,0.1)',
        color: '#f0f0f0',
        outline: 'none',
        transition: 'border-color 0.2s, box-shadow 0.2s',
        fontFamily: 'inherit',
    },
    inputFocus: {
        borderColor: 'rgba(200,255,0,0.5)',
        boxShadow: '0 0 20px rgba(200,255,0,0.1)',
    },
}

function Field({ label, icon: Icon, focused, children }) {
    return (
        <div>
            <label className="text-xs font-semibold uppercase tracking-widest mb-1.5 block"
                style={{ color: 'rgba(255,255,255,0.3)' }}>
                {label}
            </label>
            <div className="relative">
                <Icon size={14} className="absolute left-3 top-1/2 -translate-y-1/2 pointer-events-none"
                    style={{ color: focused ? '#c8ff00' : 'rgba(255,255,255,0.22)' }} />
                {children}
            </div>
        </div>
    )
}

export default function LoginPage({ onSwitchToRegister, onClose }) {
    const { login } = useAuth()
    const [email, setEmail] = useState('')
    const [password, setPassword] = useState('')
    const [showPw, setShowPw] = useState(false)
    const [error, setError] = useState(null)
    const [isLoading, setIsLoading] = useState(false)
    const [focused, setFocused] = useState(null)
    const cardRef = useRef(null)

    // 3D tilt on mouse move
    const handleMouseMove = (e) => {
        const el = cardRef.current
        if (!el) return
        const { left, top, width, height } = el.getBoundingClientRect()
        const x = (e.clientX - left) / width - 0.5
        const y = (e.clientY - top) / height - 0.5
        el.style.transform = `perspective(800px) rotateY(${x * 6}deg) rotateX(${-y * 6}deg) translateZ(4px)`
    }
    const handleMouseLeave = () => {
        if (cardRef.current)
            cardRef.current.style.transform = 'perspective(800px) rotateY(0deg) rotateX(0deg) translateZ(0px)'
    }

    const handleSubmit = async (e) => {
        e.preventDefault()
        if (!email.trim() || !password) return
        setIsLoading(true)
        setError(null)
        try {
            await login(email.trim().toLowerCase(), password)
            if (onClose) onClose()
        } catch (err) {
            setError(err.response?.data?.detail || 'Login failed. Please check your credentials.')
        } finally {
            setIsLoading(false)
        }
    }

    const inputStyle = (field) => ({ ...S.input, ...(focused === field ? S.inputFocus : {}) })

    return (
        <motion.div
            ref={cardRef}
            initial={{ opacity: 0, y: 16 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.55, ease: [0.16, 1, 0.3, 1] }}
            onMouseMove={handleMouseMove}
            onMouseLeave={handleMouseLeave}
            className="w-full max-w-sm relative overflow-hidden rounded-2xl"
            style={{ ...S.card, transition: 'transform 0.12s ease-out' }}
        >
            {/* Top shimmer */}
            <div className="absolute top-0 left-0 right-0 h-px"
                style={{ background: 'linear-gradient(90deg, transparent, rgba(200,255,0,0.5), transparent)' }} />

            <div className="p-6">
                {/* Brand */}
                <div className="flex items-center gap-2 mb-5">
                    <div className="w-7 h-7 rounded-lg flex items-center justify-center"
                        style={{ background: 'rgba(200,255,0,0.12)', border: '1px solid rgba(200,255,0,0.2)' }}>
                        <img src="/favicon.svg" alt="" className="w-4 h-4" />
                    </div>
                    <span className="text-xs font-bold tracking-widest uppercase"
                        style={{ color: '#c8ff00', fontFamily: "'Outfit', sans-serif" }}>NexusTrader</span>
                </div>

                <h2 className="text-2xl font-black mb-0.5"
                    style={{ fontFamily: "'Outfit', sans-serif", color: '#f0f0f0', letterSpacing: '-0.02em' }}>
                    Welcome back
                </h2>
                <p className="text-xs mb-5" style={{ color: 'rgba(255,255,255,0.35)' }}>
                    Sign in to your trading dashboard
                </p>

                {error && (
                    <motion.div initial={{ opacity: 0, y: -6 }} animate={{ opacity: 1, y: 0 }}
                        className="mb-4 p-3 rounded-xl flex items-center gap-2 text-xs"
                        style={{ background: 'rgba(239,68,68,0.1)', border: '1px solid rgba(239,68,68,0.2)', color: '#f87171' }}>
                        <AlertCircle size={13} className="shrink-0" />
                        {error}
                    </motion.div>
                )}

                <form onSubmit={handleSubmit} className="space-y-3">
                    <Field label="Email" icon={Mail} focused={focused === 'email'}>
                        <input
                            id="login-email" name="email" type="email" required autoComplete="email"
                            value={email} onChange={e => setEmail(e.target.value)}
                            onFocus={() => setFocused('email')} onBlur={() => setFocused(null)}
                            placeholder="trader@example.com"
                            className="w-full pl-9 pr-4 py-2.5 rounded-xl text-sm"
                            style={inputStyle('email')}
                        />
                    </Field>

                    <Field label="Password" icon={Lock} focused={focused === 'password'}>
                        <input
                            id="login-password" name="password" type={showPw ? 'text' : 'password'}
                            required autoComplete="current-password"
                            value={password} onChange={e => setPassword(e.target.value)}
                            onFocus={() => setFocused('password')} onBlur={() => setFocused(null)}
                            placeholder="••••••••"
                            className="w-full pl-9 pr-10 py-2.5 rounded-xl text-sm"
                            style={inputStyle('password')}
                        />
                        <button type="button" tabIndex={-1} onClick={() => setShowPw(v => !v)}
                            className="absolute right-3 top-1/2 -translate-y-1/2"
                            style={{ color: 'rgba(255,255,255,0.3)' }}>
                            {showPw ? <EyeOff size={14} /> : <Eye size={14} />}
                        </button>
                    </Field>

                    <div className="flex justify-end -mt-1">
                        <span className="text-xs" style={{ color: 'rgba(200,255,0,0.5)' }}>
                            Forgot password? Contact support.
                        </span>
                    </div>

                    <motion.button
                        type="submit" disabled={isLoading}
                        whileHover={{ boxShadow: '0 0 40px rgba(200,255,0,0.4)', scale: 1.02 }}
                        whileTap={{ scale: 0.98 }}
                        className="w-full py-3 rounded-xl font-bold text-sm text-black flex items-center justify-center gap-2 mt-1"
                        style={{ background: isLoading ? 'rgba(200,255,0,0.6)' : '#c8ff00', fontFamily: "'Outfit', sans-serif" }}
                    >
                        {isLoading
                            ? <Loader2 size={16} className="animate-spin" />
                            : <><span>Sign In</span><ArrowRight size={15} /></>
                        }
                    </motion.button>
                </form>

                <p className="mt-4 text-center text-xs" style={{ color: 'rgba(255,255,255,0.3)' }}>
                    Don't have an account?{' '}
                    <button onClick={onSwitchToRegister} className="font-semibold"
                        style={{ color: '#c8ff00' }}>
                        Create one free
                    </button>
                </p>
            </div>
        </motion.div>
    )
}
