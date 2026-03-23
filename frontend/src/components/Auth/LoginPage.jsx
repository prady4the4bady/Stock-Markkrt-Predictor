import { useState } from 'react'
import { motion } from 'framer-motion'
import { useAuth } from '../../context/AuthContext'
import { Lock, Mail, ArrowRight, AlertCircle, Loader2 } from 'lucide-react'

const S = {
    card: {
        background: 'rgba(255,255,255,0.04)',
        backdropFilter: 'blur(40px)',
        WebkitBackdropFilter: 'blur(40px)',
        border: '1px solid rgba(255,255,255,0.09)',
        boxShadow: '0 0 80px rgba(200,255,0,0.05), inset 0 1px 0 rgba(255,255,255,0.08), 0 40px 80px rgba(0,0,0,0.4)',
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

export default function LoginPage({ onSwitchToRegister, onClose }) {
    const { login } = useAuth()
    const [email, setEmail] = useState('')
    const [password, setPassword] = useState('')
    const [error, setError] = useState(null)
    const [isLoading, setIsLoading] = useState(false)
    const [focused, setFocused] = useState(null)

    const handleSubmit = async (e) => {
        e.preventDefault()
        setIsLoading(true)
        setError(null)
        try {
            await login(email, password)
            if (onClose) onClose()
        } catch (err) {
            setError(err.response?.data?.detail || 'Login failed. Please check credentials.')
        } finally {
            setIsLoading(false)
        }
    }

    return (
        <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.6, ease: [0.16, 1, 0.3, 1] }}
            className="w-full max-w-md relative overflow-hidden rounded-2xl"
            style={S.card}
        >
            {/* Top shimmer border */}
            <div className="absolute top-0 left-0 right-0 h-px" style={{ background: 'linear-gradient(90deg, transparent, rgba(200,255,0,0.4), transparent)' }} />

            <div className="p-8">
                {/* Brand mark */}
                <div className="flex items-center gap-2.5 mb-8">
                    <img src="/favicon.svg" alt="NexusTrader" className="w-8 h-8" />
                    <span className="text-sm font-bold tracking-widest uppercase" style={{ color: '#c8ff00', fontFamily: "'Outfit', sans-serif" }}>NexusTrader</span>
                </div>

                <div className="mb-6">
                    <h2
                        className="text-3xl font-black mb-1.5"
                        style={{ fontFamily: "'Outfit', sans-serif", color: '#f0f0f0', letterSpacing: '-0.02em' }}
                    >
                        Welcome back
                    </h2>
                    <p className="text-sm" style={{ color: 'rgba(255,255,255,0.4)' }}>Sign in to your trading dashboard</p>
                </div>

                {error && (
                    <motion.div
                        initial={{ opacity: 0, y: -8 }}
                        animate={{ opacity: 1, y: 0 }}
                        className="mb-5 p-3.5 rounded-xl flex items-center gap-2.5 text-sm"
                        style={{ background: 'rgba(239,68,68,0.1)', border: '1px solid rgba(239,68,68,0.2)', color: '#f87171' }}
                    >
                        <AlertCircle size={15} />
                        {error}
                    </motion.div>
                )}

                <form onSubmit={handleSubmit} className="space-y-4">
                    <div>
                        <label className="text-xs font-semibold uppercase tracking-widest mb-2 block" style={{ color: 'rgba(255,255,255,0.35)' }}>
                            Email
                        </label>
                        <div className="relative">
                            <Mail
                                size={15}
                                className="absolute left-3.5 top-1/2 -translate-y-1/2"
                                style={{ color: focused === 'email' ? '#c8ff00' : 'rgba(255,255,255,0.25)' }}
                            />
                            <input
                                id="login-email"
                                name="email"
                                type="email"
                                required
                                autoComplete="email"
                                value={email}
                                onChange={e => setEmail(e.target.value)}
                                onFocus={() => setFocused('email')}
                                onBlur={() => setFocused(null)}
                                placeholder="trader@example.com"
                                className="w-full pl-10 pr-4 py-3 rounded-xl text-sm"
                                style={{
                                    ...S.input,
                                    ...(focused === 'email' ? S.inputFocus : {}),
                                }}
                            />
                        </div>
                    </div>

                    <div>
                        <label className="text-xs font-semibold uppercase tracking-widest mb-2 block" style={{ color: 'rgba(255,255,255,0.35)' }}>
                            Password
                        </label>
                        <div className="relative">
                            <Lock
                                size={15}
                                className="absolute left-3.5 top-1/2 -translate-y-1/2"
                                style={{ color: focused === 'password' ? '#c8ff00' : 'rgba(255,255,255,0.25)' }}
                            />
                            <input
                                id="login-password"
                                name="password"
                                type="password"
                                required
                                autoComplete="current-password"
                                value={password}
                                onChange={e => setPassword(e.target.value)}
                                onFocus={() => setFocused('password')}
                                onBlur={() => setFocused(null)}
                                placeholder="••••••••"
                                className="w-full pl-10 pr-4 py-3 rounded-xl text-sm"
                                style={{
                                    ...S.input,
                                    ...(focused === 'password' ? S.inputFocus : {}),
                                }}
                            />
                        </div>
                    </div>

                    <div className="flex justify-end">
                        <a href="#" className="text-xs transition-colors" style={{ color: 'rgba(200,255,0,0.6)' }}
                            onMouseEnter={e => (e.target.style.color = '#c8ff00')}
                            onMouseLeave={e => (e.target.style.color = 'rgba(200,255,0,0.6)')}
                        >
                            Forgot password?
                        </a>
                    </div>

                    <motion.button
                        type="submit"
                        disabled={isLoading}
                        whileHover={{ boxShadow: '0 0 40px rgba(200,255,0,0.35)', scale: 1.02 }}
                        whileTap={{ scale: 0.98 }}
                        className="w-full py-3.5 rounded-xl font-bold text-sm text-black flex items-center justify-center gap-2 mt-2"
                        style={{ background: isLoading ? 'rgba(200,255,0,0.6)' : '#c8ff00', fontFamily: "'Outfit', sans-serif" }}
                    >
                        {isLoading ? <Loader2 size={18} className="animate-spin" /> : (
                            <>Sign In <ArrowRight size={16} /></>
                        )}
                    </motion.button>
                </form>

                <div className="mt-6 text-center text-sm" style={{ color: 'rgba(255,255,255,0.35)' }}>
                    Don't have an account?{' '}
                    <button
                        onClick={onSwitchToRegister}
                        className="font-semibold transition-colors"
                        style={{ color: '#c8ff00' }}
                        onMouseEnter={e => (e.target.style.color = '#00d4aa')}
                        onMouseLeave={e => (e.target.style.color = '#c8ff00')}
                    >
                        Create one free
                    </button>
                </div>
            </div>
        </motion.div>
    )
}
