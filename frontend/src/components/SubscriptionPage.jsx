import { useState, useEffect } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { Check, X, Zap, Crown, Sparkles, ArrowLeft, Shield, CreditCard } from 'lucide-react'
import axios from 'axios'
import { useAuth } from '../context/AuthContext'
import { useNavigate, useSearchParams } from 'react-router-dom'

const API_URL = '/api'

export default function SubscriptionPage() {
    const { user, refreshSubscription } = useAuth()
    const navigate = useNavigate()
    const [searchParams] = useSearchParams()
    const [plans, setPlans] = useState(null)
    const [currentPlan, setCurrentPlan] = useState(null)
    const [loading, setLoading] = useState(true)
    const [processing, setProcessing] = useState(false)
    const [paypalClientId, setPaypalClientId] = useState(null)
    const [error, setError] = useState(null)
    const [success, setSuccess] = useState(null)

    // Check for PayPal return
    useEffect(() => {
        const subscriptionId = searchParams.get('subscription_id')
        const plan = searchParams.get('plan')
        
        if (subscriptionId && plan && user) {
            // User returned from PayPal - activate subscription
            activateSubscription(plan, subscriptionId)
        }
    }, [searchParams, user])

    const activateSubscription = async (plan, subscriptionId) => {
        try {
            setProcessing(true)
            await axios.post(`${API_URL}/subscription/activate`, {
                plan,
                subscription_id: subscriptionId
            })
            setSuccess(`Successfully subscribed to ${plan.charAt(0).toUpperCase() + plan.slice(1)} plan!`)
            if (refreshSubscription) refreshSubscription()
            fetchSubscriptionStatus()
            // Clear URL params
            navigate('/subscription', { replace: true })
        } catch (err) {
            setError(err.response?.data?.detail || 'Failed to activate subscription')
        } finally {
            setProcessing(false)
        }
    }

    useEffect(() => {
        fetchPlans()
        if (user) {
            fetchSubscriptionStatus()
        }
    }, [user])

    // Load PayPal SDK
    useEffect(() => {
        if (paypalClientId && !window.paypal) {
            const script = document.createElement('script')
            script.src = `https://www.paypal.com/sdk/js?client-id=${paypalClientId}&currency=USD`
            script.async = true
            script.onload = () => console.log('PayPal SDK loaded')
            document.body.appendChild(script)
        }
    }, [paypalClientId])

    const fetchPlans = async () => {
        try {
            const response = await axios.get(`${API_URL}/subscription/plans`)
            setPlans(response.data.plans)
            setPaypalClientId(response.data.paypal_client_id)
        } catch (err) {
            console.error('Failed to fetch plans:', err)
        } finally {
            setLoading(false)
        }
    }

    const fetchSubscriptionStatus = async () => {
        try {
            const response = await axios.get(`${API_URL}/subscription/status`)
            setCurrentPlan(response.data)
        } catch (err) {
            console.error('Failed to fetch subscription status:', err)
        }
    }

    const handleSelectPlan = async (planKey) => {
        if (!user) {
            navigate('/login', { state: { from: '/subscription', plan: planKey } })
            return
        }

        if (planKey === 'free') {
            try {
                setProcessing(true)
                await axios.post(`${API_URL}/subscription/activate`, { plan: 'free' })
                setSuccess('Switched to Free plan')
                fetchSubscriptionStatus()
            } catch (err) {
                setError('Failed to switch plan')
            } finally {
                setProcessing(false)
            }
            return
        }

        // ── PAYMENT QUARANTINE ────────────────────────────────────────────────
        // PayPal integration is temporarily disabled. Plans activate directly.
        //
        // TO RE-ENABLE PAYPAL PAYMENTS (for vibe coders / future devs):
        //   1. Restore this block of code (git history has the full PayPal flow):
        //        - Call POST /api/subscription/create-order  →  get approve_url
        //        - Redirect user to approve_url (PayPal checkout)
        //        - On return from PayPal, call POST /api/subscription/capture-order/{orderId}
        //   2. Ensure .env has valid PAYPAL_CLIENT_ID and PAYPAL_CLIENT_SECRET
        //   3. Set PAYPAL_MODE=live for production (currently sandbox)
        //   4. Replace the handleDemoActivate call below with the restored PayPal flow
        //   5. Remove this quarantine comment block
        //
        // The backend endpoints (create-order, capture-order, webhook) remain fully
        // intact in backend/app/api/subscription_routes.py — nothing was deleted.
        // ─────────────────────────────────────────────────────────────────────
        await handleDemoActivate(planKey)
    }

    // Demo mode - activate without PayPal for testing
    const handleDemoActivate = async (planKey) => {
        if (!user) {
            navigate('/login')
            return
        }

        try {
            setProcessing(true)
            await axios.post(`${API_URL}/subscription/activate`,
                { plan: planKey }
            )
            setSuccess(`Activated ${planKey.charAt(0).toUpperCase() + planKey.slice(1)} plan!`)
            fetchSubscriptionStatus()
        } catch (err) {
            setError(err.response?.data?.detail || 'Failed to activate')
        } finally {
            setProcessing(false)
        }
    }

    const planIcons = {
        free: <Zap className="w-8 h-8" />,
        pro: <Crown className="w-8 h-8" />,
        elite: <Sparkles className="w-8 h-8" />
    }

    const planColors = {
        free: 'from-gray-500 to-gray-600',
        pro: 'from-[#c8ff00] to-[#00ff88]',
        elite: 'from-amber-500 to-orange-600'
    }

    if (loading) {
        return (
            <div className="min-h-screen bg-[#0a0a0f] flex items-center justify-center">
                <div className="animate-spin rounded-full h-12 w-12 border-t-2 border-b-2 border-[#c8ff00]"></div>
            </div>
        )
    }

    return (
        <div className="min-h-screen bg-[#0a0a0f] py-12 px-4">
            <div className="max-w-6xl mx-auto">
                {/* Header */}
                <motion.div
                    initial={{ opacity: 0, y: -20 }}
                    animate={{ opacity: 1, y: 0 }}
                    className="text-center mb-12"
                >
                    <button
                        onClick={() => navigate('/')}
                        className="flex items-center gap-2 text-gray-400 hover:text-white mb-8 transition-colors"
                    >
                        <ArrowLeft className="w-5 h-5" />
                        Back to Dashboard
                    </button>
                    
                    <h1 className="text-4xl md:text-5xl font-bold mb-4">
                        <span className="bg-gradient-to-r from-[#c8ff00] to-[#00ff88] bg-clip-text text-transparent">
                            Choose Your Plan
                        </span>
                    </h1>
                    <p className="text-xl text-gray-400 max-w-2xl mx-auto">
                        Unlock the full power of AI-driven market predictions with our premium plans
                    </p>
                    {/* Temporary banner — remove when PayPal is live */}
                    <div className="mt-6 inline-flex items-center gap-2 px-4 py-2 rounded-full bg-amber-500/10 border border-amber-500/30 text-amber-400 text-sm">
                        <Zap className="w-4 h-4" />
                        Beta access — upgrade is free while we finalize payment integration
                    </div>
                    
                    {currentPlan && (
                        <div className="mt-6 inline-flex items-center gap-2 px-4 py-2 rounded-full bg-white/5 border border-white/10">
                            <span className="text-gray-400">Current Plan:</span>
                            <span className={`font-semibold ${
                                currentPlan.plan === 'elite' ? 'text-amber-400' :
                                currentPlan.plan === 'pro' ? 'text-[#c8ff00]' : 'text-gray-300'
                            }`}>
                                {currentPlan.plan.charAt(0).toUpperCase() + currentPlan.plan.slice(1)}
                            </span>
                            {currentPlan.subscription_end && (
                                <span className="text-gray-500 text-sm">
                                    (until {new Date(currentPlan.subscription_end).toLocaleDateString()})
                                </span>
                            )}
                        </div>
                    )}
                </motion.div>

                {/* Alerts */}
                <AnimatePresence>
                    {error && (
                        <motion.div
                            initial={{ opacity: 0, y: -10 }}
                            animate={{ opacity: 1, y: 0 }}
                            exit={{ opacity: 0, y: -10 }}
                            className="mb-6 p-4 rounded-lg bg-red-500/10 border border-red-500/30 text-red-400 flex items-center gap-3"
                        >
                            <X className="w-5 h-5" />
                            {error}
                            <button onClick={() => setError(null)} className="ml-auto">
                                <X className="w-4 h-4" />
                            </button>
                        </motion.div>
                    )}
                    {success && (
                        <motion.div
                            initial={{ opacity: 0, y: -10 }}
                            animate={{ opacity: 1, y: 0 }}
                            exit={{ opacity: 0, y: -10 }}
                            className="mb-6 p-4 rounded-lg bg-green-500/10 border border-green-500/30 text-green-400 flex items-center gap-3"
                        >
                            <Check className="w-5 h-5" />
                            {success}
                            <button onClick={() => setSuccess(null)} className="ml-auto">
                                <X className="w-4 h-4" />
                            </button>
                        </motion.div>
                    )}
                </AnimatePresence>

                {/* Pricing Cards */}
                <div className="grid md:grid-cols-3 gap-8">
                    {plans && Object.entries(plans).map(([key, plan], index) => {
                        const isCurrentPlan = currentPlan?.plan === key
                        const isPremium = key !== 'free'
                        
                        return (
                            <motion.div
                                key={key}
                                initial={{ opacity: 0, y: 20 }}
                                animate={{ opacity: 1, y: 0 }}
                                transition={{ delay: index * 0.1 }}
                                className={`relative rounded-2xl overflow-hidden ${
                                    key === 'pro' ? 'md:-mt-4 md:mb-4' : ''
                                }`}
                            >
                                {/* Popular badge for Pro */}
                                {key === 'pro' && (
                                    <div className="absolute top-0 left-0 right-0 bg-gradient-to-r from-[#c8ff00] to-[#00ff88] text-black text-center py-1 text-sm font-semibold">
                                        Most Popular
                                    </div>
                                )}
                                
                                <div className={`h-full bg-white/5 backdrop-blur-sm border border-white/10 rounded-2xl p-8 ${
                                    key === 'pro' ? 'pt-12' : ''
                                } flex flex-col`}>
                                    {/* Plan Header */}
                                    <div className="text-center mb-6">
                                        <div className={`inline-flex p-4 rounded-2xl bg-gradient-to-br ${planColors[key]} mb-4`}>
                                            {planIcons[key]}
                                        </div>
                                        <h3 className="text-2xl font-bold">{plan.name}</h3>
                                        <div className="mt-4">
                                            <span className="text-4xl font-bold">${plan.price}</span>
                                            {isPremium && <span className="text-gray-400">/month</span>}
                                        </div>
                                    </div>

                                    {/* Features */}
                                    <ul className="space-y-3 mb-8 flex-grow">
                                        {plan.features.map((feature, i) => (
                                            <li key={i} className="flex items-start gap-3">
                                                <Check className="w-5 h-5 text-green-400 flex-shrink-0 mt-0.5" />
                                                <span className="text-gray-300">{feature}</span>
                                            </li>
                                        ))}
                                    </ul>

                                    {/* Action Buttons */}
                                    <div className="space-y-3">
                                        {isCurrentPlan ? (
                                            <button
                                                disabled
                                                className="w-full py-3 px-6 rounded-xl bg-white/10 text-gray-400 font-semibold cursor-not-allowed"
                                            >
                                                Current Plan
                                            </button>
                                        ) : (
                                            <>
                                                {isPremium ? (
                                                    <button
                                                        onClick={() => handleDemoActivate(key)}
                                                        disabled={processing}
                                                        className={`w-full py-3 px-6 rounded-xl font-semibold transition-all ${
                                                            key === 'elite'
                                                                ? 'bg-gradient-to-r from-amber-500 to-orange-600 hover:from-amber-600 hover:to-orange-700 text-white'
                                                                : 'bg-gradient-to-r from-[#c8ff00] to-[#00ff88] hover:from-[#d4ff33] hover:to-[#33ff99] text-black'
                                                        } ${processing ? 'opacity-50 cursor-not-allowed' : ''}`}
                                                    >
                                                        {processing ? 'Processing...' : `Activate ${plan.name}`}
                                                    </button>
                                                ) : (
                                                    <button
                                                        onClick={() => handleSelectPlan(key)}
                                                        disabled={processing}
                                                        className="w-full py-3 px-6 rounded-xl font-semibold bg-white/10 hover:bg-white/20 transition-all"
                                                    >
                                                        {processing ? 'Processing...' : 'Select Free Plan'}
                                                    </button>
                                                )}
                                            </>
                                        )}
                                    </div>
                                </div>
                            </motion.div>
                        )
                    })}
                </div>

                {/* Trust badges */}
                <motion.div
                    initial={{ opacity: 0 }}
                    animate={{ opacity: 1 }}
                    transition={{ delay: 0.5 }}
                    className="mt-16 text-center"
                >
                    <div className="flex flex-wrap justify-center items-center gap-8 text-gray-400">
                        <div className="flex items-center gap-2">
                            <Shield className="w-5 h-5 text-green-400" />
                            <span>Secure Payments</span>
                        </div>
                        <div className="flex items-center gap-2">
                            <Check className="w-5 h-5 text-[#c8ff00]" />
                            <span>Cancel Anytime</span>
                        </div>
                        <div className="flex items-center gap-2">
                            <Zap className="w-5 h-5 text-amber-400" />
                            <span>Instant Access</span>
                        </div>
                    </div>
                    
                    <p className="mt-8 text-gray-500 text-sm">
                        By subscribing, you agree to our Terms of Service and Privacy Policy.
                        <br />
                        All payments are processed securely through PayPal.
                    </p>
                </motion.div>
            </div>
        </div>
    )
}
