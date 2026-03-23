import { useState } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { useAuth } from '../../context/AuthContext'
import { Lock, Mail, User, ArrowRight, AlertCircle, Loader2, Shield, Eye, X, CheckCircle2 } from 'lucide-react'

const S = {
    card: {
        background: 'rgba(255,255,255,0.04)',
        backdropFilter: 'blur(40px)',
        WebkitBackdropFilter: 'blur(40px)',
        border: '1px solid rgba(255,255,255,0.09)',
        boxShadow: '0 0 80px rgba(200,255,0,0.04), inset 0 1px 0 rgba(255,255,255,0.08), 0 40px 80px rgba(0,0,0,0.4)',
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
    modal: {
        background: 'rgba(8,8,14,0.98)',
        backdropFilter: 'blur(40px)',
        WebkitBackdropFilter: 'blur(40px)',
        border: '1px solid rgba(255,255,255,0.1)',
        boxShadow: '0 0 80px rgba(0,0,0,0.8), inset 0 1px 0 rgba(255,255,255,0.06)',
    },
}

function LegalModal({ title, icon: Icon, onClose, children }) {
    return (
        <AnimatePresence>
            <motion.div
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                exit={{ opacity: 0 }}
                className="fixed inset-0 flex items-center justify-center z-50 p-4"
                style={{ background: 'rgba(0,0,0,0.85)' }}
                onClick={e => e.target === e.currentTarget && onClose()}
            >
                <motion.div
                    initial={{ opacity: 0, scale: 0.96, y: 12 }}
                    animate={{ opacity: 1, scale: 1, y: 0 }}
                    exit={{ opacity: 0, scale: 0.96, y: 12 }}
                    transition={{ duration: 0.3, ease: [0.16, 1, 0.3, 1] }}
                    className="w-full max-w-2xl max-h-[80vh] overflow-hidden rounded-2xl flex flex-col"
                    style={S.modal}
                >
                    {/* Header */}
                    <div className="flex items-center justify-between px-6 py-4" style={{ borderBottom: '1px solid rgba(255,255,255,0.07)' }}>
                        <div className="flex items-center gap-3">
                            <div className="w-8 h-8 rounded-lg flex items-center justify-center" style={{ background: 'rgba(200,255,0,0.1)', border: '1px solid rgba(200,255,0,0.2)' }}>
                                <Icon size={15} style={{ color: '#c8ff00' }} />
                            </div>
                            <span className="font-bold text-base" style={{ color: '#f0f0f0', fontFamily: "'Outfit', sans-serif" }}>{title}</span>
                        </div>
                        <button
                            onClick={onClose}
                            className="w-8 h-8 rounded-lg flex items-center justify-center transition-all"
                            style={{ background: 'rgba(255,255,255,0.05)', border: '1px solid rgba(255,255,255,0.08)' }}
                            onMouseEnter={e => (e.currentTarget.style.background = 'rgba(255,255,255,0.1)')}
                            onMouseLeave={e => (e.currentTarget.style.background = 'rgba(255,255,255,0.05)')}
                        >
                            <X size={14} style={{ color: 'rgba(255,255,255,0.5)' }} />
                        </button>
                    </div>

                    {/* Content */}
                    <div className="overflow-y-auto px-6 py-5 flex-1 text-sm space-y-4" style={{ color: 'rgba(255,255,255,0.55)', scrollbarWidth: 'thin', scrollbarColor: 'rgba(200,255,0,0.2) transparent' }}>
                        {children}
                    </div>

                    {/* Footer */}
                    <div className="px-6 py-4" style={{ borderTop: '1px solid rgba(255,255,255,0.07)' }}>
                        <motion.button
                            onClick={onClose}
                            whileHover={{ scale: 1.01, boxShadow: '0 0 30px rgba(200,255,0,0.3)' }}
                            whileTap={{ scale: 0.99 }}
                            className="w-full py-2.5 rounded-xl font-bold text-sm text-black"
                            style={{ background: '#c8ff00', fontFamily: "'Outfit', sans-serif" }}
                        >
                            I Understand
                        </motion.button>
                    </div>
                </motion.div>
            </motion.div>
        </AnimatePresence>
    )
}

function ConsentRow({ id, checked, onChange, required, children }) {
    return (
        <label htmlFor={id} className="flex items-start gap-3 cursor-pointer group">
            <div className="relative mt-0.5 flex-shrink-0">
                <input
                    type="checkbox"
                    id={id}
                    name={id}
                    checked={checked}
                    onChange={onChange}
                    className="sr-only"
                />
                <div
                    className="w-4 h-4 rounded flex items-center justify-center transition-all"
                    style={{
                        background: checked ? '#c8ff00' : 'rgba(255,255,255,0.05)',
                        border: checked ? '1px solid #c8ff00' : '1px solid rgba(255,255,255,0.2)',
                        boxShadow: checked ? '0 0 10px rgba(200,255,0,0.3)' : 'none',
                    }}
                >
                    {checked && <CheckCircle2 size={10} className="text-black" strokeWidth={3} />}
                </div>
            </div>
            <span className="text-sm leading-relaxed" style={{ color: 'rgba(255,255,255,0.45)' }}>
                {required && <span style={{ color: 'rgba(239,68,68,0.8)' }}>* </span>}
                {children}
            </span>
        </label>
    )
}

export default function RegisterPage({ onSwitchToLogin, onClose }) {
    const { register } = useAuth()
    const [fullName, setFullName] = useState('')
    const [email, setEmail] = useState('')
    const [password, setPassword] = useState('')
    const [privacyConsent, setPrivacyConsent] = useState(false)
    const [termsAccepted, setTermsAccepted] = useState(false)
    const [activityTrackingConsent, setActivityTrackingConsent] = useState(false)
    const [showPrivacyPolicy, setShowPrivacyPolicy] = useState(false)
    const [showTerms, setShowTerms] = useState(false)
    const [error, setError] = useState(null)
    const [isLoading, setIsLoading] = useState(false)
    const [focused, setFocused] = useState(null)

    const handleSubmit = async (e) => {
        e.preventDefault()

        if (!privacyConsent) {
            setError('You must accept the Privacy Policy to create an account')
            return
        }
        if (!termsAccepted) {
            setError('You must accept the Terms of Service to create an account')
            return
        }

        // Client-side validation: password byte-length and min length
        const passwordBytes = new TextEncoder().encode(password)
        if (passwordBytes.length > 72) {
            setError('Password too long (max 72 bytes). Please use a shorter password.')
            return
        }
        if (password.length < 8) {
            setError('Password too short (minimum 8 characters).')
            return
        }

        setIsLoading(true)
        setError(null)
        try {
            await register(email, password, fullName, privacyConsent, termsAccepted, activityTrackingConsent)
            if (onClose) onClose()
        } catch (err) {
            setError(err.response?.data?.detail || 'Registration failed.')
        } finally {
            setIsLoading(false)
        }
    }

    const canSubmit = privacyConsent && termsAccepted

    const inputStyle = (field) => ({
        ...S.input,
        ...(focused === field ? S.inputFocus : {}),
    })

    return (
        <>
            <motion.div
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ duration: 0.6, ease: [0.16, 1, 0.3, 1] }}
                className="w-full max-w-md relative overflow-hidden rounded-2xl"
                style={S.card}
            >
                {/* Top shimmer border */}
                <div className="absolute top-0 left-0 right-0 h-px" style={{ background: 'linear-gradient(90deg, transparent, rgba(200,255,0,0.35), rgba(0,212,170,0.35), transparent)' }} />

                <div className="p-8">
                    {/* Brand mark */}
                    <div className="flex items-center gap-2.5 mb-7">
                        <img src="/favicon.svg" alt="NexusTrader" className="w-8 h-8" />
                        <span className="text-sm font-bold tracking-widest uppercase" style={{ color: '#c8ff00', fontFamily: "'Outfit', sans-serif" }}>NexusTrader</span>
                    </div>

                    <div className="mb-6">
                        <h2
                            className="text-3xl font-black mb-1.5"
                            style={{ fontFamily: "'Outfit', sans-serif", color: '#f0f0f0', letterSpacing: '-0.02em' }}
                        >
                            Join the edge
                        </h2>
                        <p className="text-sm" style={{ color: 'rgba(255,255,255,0.4)' }}>Create your free trading intelligence account</p>
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
                        {/* Full Name */}
                        <div>
                            <label className="text-xs font-semibold uppercase tracking-widest mb-2 block" style={{ color: 'rgba(255,255,255,0.35)' }}>
                                Full Name
                            </label>
                            <div className="relative">
                                <User
                                    size={15}
                                    className="absolute left-3.5 top-1/2 -translate-y-1/2"
                                    style={{ color: focused === 'name' ? '#c8ff00' : 'rgba(255,255,255,0.25)' }}
                                />
                                <input
                                    id="register-fullname"
                                    name="fullName"
                                    type="text"
                                    required
                                    autoComplete="name"
                                    value={fullName}
                                    onChange={e => setFullName(e.target.value)}
                                    onFocus={() => setFocused('name')}
                                    onBlur={() => setFocused(null)}
                                    placeholder="John Doe"
                                    className="w-full pl-10 pr-4 py-3 rounded-xl text-sm"
                                    style={inputStyle('name')}
                                />
                            </div>
                        </div>

                        {/* Email */}
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
                                    id="register-email"
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
                                    style={inputStyle('email')}
                                />
                            </div>
                        </div>

                        {/* Password */}
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
                                    id="register-password"
                                    name="password"
                                    type="password"
                                    required
                                    autoComplete="new-password"
                                    value={password}
                                    onChange={e => setPassword(e.target.value)}
                                    onFocus={() => setFocused('password')}
                                    onBlur={() => setFocused(null)}
                                    placeholder="Min 8 characters"
                                    className="w-full pl-10 pr-4 py-3 rounded-xl text-sm"
                                    style={inputStyle('password')}
                                />
                            </div>
                        </div>

                        {/* Consent section */}
                        <div className="space-y-3 pt-1">
                            <ConsentRow
                                id="privacyConsent"
                                checked={privacyConsent}
                                onChange={e => setPrivacyConsent(e.target.checked)}
                                required
                            >
                                I have read and agree to the{' '}
                                <button
                                    type="button"
                                    onClick={() => setShowPrivacyPolicy(true)}
                                    className="font-semibold transition-colors"
                                    style={{ color: '#c8ff00' }}
                                    onMouseEnter={e => (e.target.style.color = '#00d4aa')}
                                    onMouseLeave={e => (e.target.style.color = '#c8ff00')}
                                >
                                    Privacy Policy
                                </button>
                            </ConsentRow>

                            <ConsentRow
                                id="termsAccepted"
                                checked={termsAccepted}
                                onChange={e => setTermsAccepted(e.target.checked)}
                                required
                            >
                                I accept the{' '}
                                <button
                                    type="button"
                                    onClick={() => setShowTerms(true)}
                                    className="font-semibold transition-colors"
                                    style={{ color: '#c8ff00' }}
                                    onMouseEnter={e => (e.target.style.color = '#00d4aa')}
                                    onMouseLeave={e => (e.target.style.color = '#c8ff00')}
                                >
                                    Terms of Service
                                </button>
                            </ConsentRow>

                            {/* Optional tracking — visually distinct */}
                            <div
                                className="rounded-xl p-3.5 mt-1"
                                style={{ background: 'rgba(0,212,170,0.05)', border: '1px solid rgba(0,212,170,0.12)' }}
                            >
                                <ConsentRow
                                    id="activityTracking"
                                    checked={activityTrackingConsent}
                                    onChange={e => setActivityTrackingConsent(e.target.checked)}
                                >
                                    <span style={{ color: 'rgba(255,255,255,0.6)' }} className="flex items-center gap-1.5 mb-0.5">
                                        <Eye size={13} style={{ color: '#00d4aa', flexShrink: 0 }} />
                                        <span className="font-semibold text-xs uppercase tracking-widest" style={{ color: '#00d4aa' }}>Smart Insights</span>
                                        <span className="text-xs px-1.5 py-0.5 rounded" style={{ background: 'rgba(0,212,170,0.12)', color: 'rgba(0,212,170,0.8)', fontSize: 9, letterSpacing: '0.08em' }}>OPTIONAL</span>
                                    </span>
                                    <p className="text-xs mt-1" style={{ color: 'rgba(255,255,255,0.35)' }}>
                                        Allow in-app activity tracking for personalized predictions. You can change this anytime in settings.
                                    </p>
                                </ConsentRow>
                            </div>
                        </div>

                        <motion.button
                            type="submit"
                            disabled={isLoading || !canSubmit}
                            whileHover={canSubmit && !isLoading ? { boxShadow: '0 0 40px rgba(200,255,0,0.35)', scale: 1.02 } : {}}
                            whileTap={canSubmit && !isLoading ? { scale: 0.98 } : {}}
                            className="w-full py-3.5 rounded-xl font-bold text-sm text-black flex items-center justify-center gap-2 mt-1"
                            style={{
                                background: !canSubmit ? 'rgba(200,255,0,0.3)' : isLoading ? 'rgba(200,255,0,0.6)' : '#c8ff00',
                                fontFamily: "'Outfit', sans-serif",
                                cursor: !canSubmit ? 'not-allowed' : 'pointer',
                            }}
                        >
                            {isLoading ? <Loader2 size={18} className="animate-spin" /> : (
                                <>Get Started Free <ArrowRight size={16} /></>
                            )}
                        </motion.button>
                    </form>

                    <div className="mt-6 text-center text-sm" style={{ color: 'rgba(255,255,255,0.35)' }}>
                        Already have an account?{' '}
                        <button
                            onClick={onSwitchToLogin}
                            className="font-semibold transition-colors"
                            style={{ color: '#c8ff00' }}
                            onMouseEnter={e => (e.target.style.color = '#00d4aa')}
                            onMouseLeave={e => (e.target.style.color = '#c8ff00')}
                        >
                            Sign in
                        </button>
                    </div>
                </div>
            </motion.div>

            {/* Privacy Policy Modal */}
            {showPrivacyPolicy && (
                <LegalModal title="Privacy Policy" icon={Shield} onClose={() => setShowPrivacyPolicy(false)}>
                    <p><strong style={{ color: 'rgba(255,255,255,0.7)' }}>Last Updated:</strong> January 15, 2026</p>

                    <h4 style={{ color: 'rgba(255,255,255,0.75)', fontFamily: "'Outfit', sans-serif" }} className="font-semibold">1. Information We Collect</h4>
                    <p>We collect the following types of information:</p>
                    <ul className="list-disc list-inside space-y-1" style={{ color: 'rgba(255,255,255,0.4)' }}>
                        <li><strong style={{ color: 'rgba(255,255,255,0.6)' }}>Account Information:</strong> Email, name, and encrypted password</li>
                        <li><strong style={{ color: 'rgba(255,255,255,0.6)' }}>Usage Data:</strong> Stocks you view, predictions you request, and time spent on the platform</li>
                        <li><strong style={{ color: 'rgba(255,255,255,0.6)' }}>Device Information:</strong> Browser type, device type (anonymized)</li>
                    </ul>

                    <h4 style={{ color: 'rgba(255,255,255,0.75)', fontFamily: "'Outfit', sans-serif" }} className="font-semibold">2. Activity Tracking (With Your Consent)</h4>
                    <p>If you enable &quot;Smart Insights,&quot; we track:</p>
                    <ul className="list-disc list-inside space-y-1" style={{ color: 'rgba(255,255,255,0.4)' }}>
                        <li>Which stocks/cryptocurrencies you view within our app</li>
                        <li>How often you view specific assets</li>
                        <li>Prediction requests and chart interactions</li>
                        <li>Time spent analyzing different assets</li>
                    </ul>
                    <p style={{ color: 'rgba(200,255,0,0.7)' }}>We do NOT track your activity outside of this application.</p>

                    <h4 style={{ color: 'rgba(255,255,255,0.75)', fontFamily: "'Outfit', sans-serif" }} className="font-semibold">3. How We Use Your Data</h4>
                    <ul className="list-disc list-inside space-y-1" style={{ color: 'rgba(255,255,255,0.4)' }}>
                        <li>Provide personalized stock predictions</li>
                        <li>Improve our AI models with aggregated, anonymized data</li>
                        <li>Send relevant alerts about your watchlist</li>
                        <li>Improve user experience</li>
                    </ul>

                    <h4 style={{ color: 'rgba(255,255,255,0.75)', fontFamily: "'Outfit', sans-serif" }} className="font-semibold">4. Data Security</h4>
                    <ul className="list-disc list-inside space-y-1" style={{ color: 'rgba(255,255,255,0.4)' }}>
                        <li>Industry-standard encryption (bcrypt for passwords)</li>
                        <li>Secure JWT authentication</li>
                        <li>IP address hashing for privacy</li>
                        <li>Regular security audits</li>
                    </ul>

                    <h4 style={{ color: 'rgba(255,255,255,0.75)', fontFamily: "'Outfit', sans-serif" }} className="font-semibold">5. Your Rights (GDPR/CCPA)</h4>
                    <ul className="list-disc list-inside space-y-1" style={{ color: 'rgba(255,255,255,0.4)' }}>
                        <li><strong style={{ color: 'rgba(255,255,255,0.6)' }}>Access:</strong> Export all your data anytime</li>
                        <li><strong style={{ color: 'rgba(255,255,255,0.6)' }}>Deletion:</strong> Request complete data deletion</li>
                        <li><strong style={{ color: 'rgba(255,255,255,0.6)' }}>Opt-out:</strong> Disable activity tracking in settings</li>
                        <li><strong style={{ color: 'rgba(255,255,255,0.6)' }}>Portability:</strong> Download your data in JSON format</li>
                    </ul>

                    <h4 style={{ color: 'rgba(255,255,255,0.75)', fontFamily: "'Outfit', sans-serif" }} className="font-semibold">6. Contact Us</h4>
                    <p>Questions? Contact privacy@marketoracle.app</p>
                </LegalModal>
            )}

            {/* Terms of Service Modal */}
            {showTerms && (
                <LegalModal title="Terms of Service" icon={Shield} onClose={() => setShowTerms(false)}>
                    <p><strong style={{ color: 'rgba(255,255,255,0.7)' }}>Last Updated:</strong> January 15, 2026</p>

                    <h4 style={{ color: 'rgba(255,255,255,0.75)', fontFamily: "'Outfit', sans-serif" }} className="font-semibold">1. Acceptance of Terms</h4>
                    <p>By creating an account, you agree to these terms and our Privacy Policy.</p>

                    <h4 style={{ color: 'rgba(255,255,255,0.75)', fontFamily: "'Outfit', sans-serif" }} className="font-semibold">2. Service Description</h4>
                    <p>NexusTrader provides AI-powered stock and cryptocurrency price predictions using ensemble machine learning models. Our predictions are for informational purposes only.</p>

                    <h4 style={{ color: 'rgba(255,255,255,0.75)', fontFamily: "'Outfit', sans-serif" }} className="font-semibold">3. Important Disclaimer</h4>
                    <p style={{ color: 'rgba(234,179,8,0.7)', fontWeight: 600 }}>INVESTMENT RISK WARNING</p>
                    <p>Trade on your own risk.</p>

                    <h4 style={{ color: 'rgba(255,255,255,0.75)', fontFamily: "'Outfit', sans-serif" }} className="font-semibold">4. User Responsibilities</h4>
                    <ul className="list-disc list-inside space-y-1" style={{ color: 'rgba(255,255,255,0.4)' }}>
                        <li>Provide accurate account information</li>
                        <li>Keep your password secure</li>
                        <li>Use the service for personal, non-commercial purposes</li>
                        <li>Not attempt to reverse-engineer our algorithms</li>
                    </ul>

                    <h4 style={{ color: 'rgba(255,255,255,0.75)', fontFamily: "'Outfit', sans-serif" }} className="font-semibold">5. Data Usage Consent</h4>
                    <p>If you enable activity tracking, you consent to us analyzing your in-app behavior to improve predictions. This data is:</p>
                    <ul className="list-disc list-inside space-y-1" style={{ color: 'rgba(255,255,255,0.4)' }}>
                        <li>Used only within NexusTrader</li>
                        <li>Never sold to third parties</li>
                        <li>Deletable upon request</li>
                    </ul>

                    <h4 style={{ color: 'rgba(255,255,255,0.75)', fontFamily: "'Outfit', sans-serif" }} className="font-semibold">6. Limitation of Liability</h4>
                    <p>NexusTrader is not liable for any financial losses resulting from investment decisions made using our predictions.</p>

                    <h4 style={{ color: 'rgba(255,255,255,0.75)', fontFamily: "'Outfit', sans-serif" }} className="font-semibold">7. Termination</h4>
                    <p>We may terminate accounts that violate these terms. You may delete your account at any time.</p>
                </LegalModal>
            )}
        </>
    )
}
