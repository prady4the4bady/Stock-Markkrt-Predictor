import { useState, useEffect, useCallback } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { 
    Settings, Shield, Eye, EyeOff, Download, Trash2, 
    Bell, Moon, Sun, Save, Loader2, CheckCircle, AlertTriangle,
    ChevronRight, Lock, CreditCard, Star, Zap, Crown, ExternalLink, RefreshCw
} from 'lucide-react'
import { useAuth } from '../context/AuthContext'
import activityService from '../services/ActivityService'
import subscriptionService from '../services/SubscriptionService'

export default function SettingsPage({ onClose }) {
    const { user, logout, refreshSubscription } = useAuth()
    const [preferences, setPreferences] = useState(null)
    const [isLoading, setIsLoading] = useState(true)
    const [isSaving, setIsSaving] = useState(false)
    const [saveStatus, setSaveStatus] = useState(null)
    const [activeSection, setActiveSection] = useState('privacy')
    const [showDeleteConfirm, setShowDeleteConfirm] = useState(false)
    const [isExporting, setIsExporting] = useState(false)
    const [isDeleting, setIsDeleting] = useState(false)
    
    // Subscription state
    const [subscriptionStatus, setSubscriptionStatus] = useState(null)
    const [availablePlans, setAvailablePlans] = useState(null)
    const [billingHistory, setBillingHistory] = useState([])
    const [paymentMethods, setPaymentMethods] = useState([])
    const [isLoadingSubscription, setIsLoadingSubscription] = useState(false)
    const [isUpgrading, setIsUpgrading] = useState(false)
    const [isCancelling, setIsCancelling] = useState(false)
    const [showCancelConfirm, setShowCancelConfirm] = useState(false)
    const [subscriptionError, setSubscriptionError] = useState(null)

    useEffect(() => {
        loadPreferences()
    }, [])

    // Load subscription data when plans section is active
    useEffect(() => {
        if (activeSection === 'plans') {
            loadSubscriptionData()
        }
    }, [activeSection])

    const loadPreferences = async () => {
        try {
            const prefs = await activityService.getPreferences()
            setPreferences(prefs)
        } catch (error) {
            console.error('Failed to load preferences:', error)
        } finally {
            setIsLoading(false)
        }
    }

    const loadSubscriptionData = useCallback(async () => {
        setIsLoadingSubscription(true)
        setSubscriptionError(null)
        try {
            const [status, plansData, billing, methods] = await Promise.all([
                subscriptionService.getStatus(),
                subscriptionService.getPlans(),
                subscriptionService.getBillingHistory(),
                subscriptionService.getPaymentMethods()
            ])
            
            setSubscriptionStatus(status)
            setAvailablePlans(plansData.plans)
            setBillingHistory(billing.invoices || [])
            setPaymentMethods(methods.methods || [])
        } catch (error) {
            console.error('Failed to load subscription data:', error)
            setSubscriptionError('Failed to load subscription data. Please try again.')
        } finally {
            setIsLoadingSubscription(false)
        }
    }, [])

    const handleUpgrade = async (planId) => {
        if (planId === 'free') {
            // Downgrade to free
            await handleDowngrade()
            return
        }

        setIsUpgrading(true)
        setSubscriptionError(null)
        
        try {
            const orderData = await subscriptionService.createOrder(planId)
            
            if (orderData.approve_url) {
                // Redirect to PayPal for approval
                window.location.href = orderData.approve_url
            } else {
                // For demo/development - activate directly
                const result = await subscriptionService.activateSubscription(planId)
                if (result.status === 'success') {
                    await loadSubscriptionData()
                    if (refreshSubscription) refreshSubscription()
                    setSaveStatus('success')
                    setTimeout(() => setSaveStatus(null), 3000)
                }
            }
        } catch (error) {
            console.error('Upgrade failed:', error)
            setSubscriptionError(error.response?.data?.detail || 'Failed to upgrade. Please try again.')
        } finally {
            setIsUpgrading(false)
        }
    }

    const handleDowngrade = async () => {
        setIsUpgrading(true)
        try {
            await subscriptionService.activateSubscription('free')
            await loadSubscriptionData()
            if (refreshSubscription) refreshSubscription()
        } catch (error) {
            setSubscriptionError('Failed to downgrade. Please try again.')
        } finally {
            setIsUpgrading(false)
        }
    }

    const handleCancelSubscription = async () => {
        setIsCancelling(true)
        try {
            const result = await subscriptionService.cancelSubscription()
            setShowCancelConfirm(false)
            await loadSubscriptionData()
            alert(result.message)
        } catch (error) {
            setSubscriptionError(error.response?.data?.detail || 'Failed to cancel subscription.')
        } finally {
            setIsCancelling(false)
        }
    }

    const handleSave = async () => {
        setIsSaving(true)
        setSaveStatus(null)
        try {
            await activityService.updatePreferences(preferences)
            setSaveStatus('success')
            setTimeout(() => setSaveStatus(null), 3000)
        } catch (error) {
            setSaveStatus('error')
        } finally {
            setIsSaving(false)
        }
    }

    const handleExportData = async () => {
        setIsExporting(true)
        try {
            const data = await activityService.exportData()
            const blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' })
            const url = URL.createObjectURL(blob)
            const a = document.createElement('a')
            a.href = url
            a.download = `market-oracle-data-${new Date().toISOString().split('T')[0]}.json`
            document.body.appendChild(a)
            a.click()
            document.body.removeChild(a)
            URL.revokeObjectURL(url)
        } catch (error) {
            alert('Failed to export data. Please try again.')
        } finally {
            setIsExporting(false)
        }
    }

    const handleDeleteRequest = async () => {
        setIsDeleting(true)
        try {
            await activityService.requestDataDeletion()
            alert('Data deletion request submitted. Your account and all data will be deleted within 30 days.')
            logout()
            if (onClose) onClose()
        } catch (error) {
            alert('Failed to request deletion. Please try again.')
        } finally {
            setIsDeleting(false)
            setShowDeleteConfirm(false)
        }
    }

    const updatePreference = (key, value) => {
        setPreferences(prev => ({ ...prev, [key]: value }))
    }

    if (isLoading) {
        return (
            <div className="flex items-center justify-center h-64">
                <Loader2 className="w-8 h-8 animate-spin text-[#c8ff00]" />
            </div>
        )
    }

    const sections = [
        { id: 'privacy', label: 'Privacy & Tracking', icon: Shield },
        { id: 'plans', label: 'Plans & Billing', icon: CreditCard },
        { id: 'notifications', label: 'Notifications', icon: Bell },
        { id: 'display', label: 'Display', icon: Moon },
        { id: 'data', label: 'Your Data', icon: Download },
    ]

    return (
        <div className="fixed inset-0 bg-black/80 flex items-center justify-center z-50 p-4">
            <motion.div
                initial={{ opacity: 0, scale: 0.95 }}
                animate={{ opacity: 1, scale: 1 }}
                className="bg-[#0d0d18] rounded-2xl w-full max-w-4xl max-h-[85vh] overflow-hidden border border-[#c8ff00]/20"
            >
                {/* Header */}
                <div className="flex items-center justify-between p-6 border-b border-[#c8ff00]/10">
                    <div className="flex items-center gap-3">
                        <Settings className="w-6 h-6 text-[#c8ff00]" />
                        <h2 className="text-xl font-bold text-white">Settings</h2>
                    </div>
                    <button
                        onClick={onClose}
                        className="text-gray-400 hover:text-white transition-colors"
                    >
                        ✕
                    </button>
                </div>

                <div className="flex h-[calc(85vh-80px)]">
                    {/* Sidebar */}
                    <div className="w-64 border-r border-[#c8ff00]/10 p-4">
                        <nav className="space-y-1">
                            {sections.map(section => (
                                <button
                                    key={section.id}
                                    onClick={() => setActiveSection(section.id)}
                                    className={`w-full flex items-center gap-3 px-4 py-3 rounded-lg transition-colors ${
                                        activeSection === section.id
                                            ? 'bg-[#c8ff00]/20 text-[#c8ff00]'
                                            : 'text-gray-400 hover:bg-[#c8ff00]/5 hover:text-white'
                                    }`}
                                >
                                    <section.icon className="w-5 h-5" />
                                    {section.label}
                                    <ChevronRight className={`w-4 h-4 ml-auto transition-transform ${
                                        activeSection === section.id ? 'rotate-90' : ''
                                    }`} />
                                </button>
                            ))}
                        </nav>
                    </div>

                    {/* Content */}
                    <div className="flex-1 p-6 overflow-y-auto">
                        {/* Privacy Section */}
                        {activeSection === 'privacy' && (
                            <div className="space-y-6">
                                <div>
                                    <h3 className="text-lg font-semibold text-white mb-4">Privacy & Activity Tracking</h3>
                                    <p className="text-gray-400 text-sm mb-6">
                                        Control how we track your activity within NexusTrader to provide personalized insights.
                                    </p>
                                </div>

                                {/* Activity Tracking Toggle */}
                                <div className="p-4 bg-[#c8ff00]/5 rounded-xl border border-[#c8ff00]/10">
                                    <div className="flex items-start justify-between">
                                        <div className="flex items-start gap-3">
                                            {preferences?.track_activity ? (
                                                <Eye className="w-5 h-5 text-green-400 mt-0.5" />
                                            ) : (
                                                <EyeOff className="w-5 h-5 text-gray-400 mt-0.5" />
                                            )}
                                            <div>
                                                <h4 className="text-white font-medium">Smart Insights Tracking</h4>
                                                <p className="text-gray-400 text-sm mt-1">
                                                    Allow us to track which stocks you view and analyze within this app to provide better predictions and personalized insights.
                                                </p>
                                                <p className="text-yellow-400/80 text-xs mt-2">
                                                    ⚠️ We only track activity within NexusTrader - never your other apps, tabs, or websites.
                                                </p>
                                            </div>
                                        </div>
                                        <label className="relative inline-flex items-center cursor-pointer">
                                            <input
                                                type="checkbox"
                                                checked={preferences?.track_activity || false}
                                                onChange={(e) => updatePreference('track_activity', e.target.checked)}
                                                className="sr-only peer"
                                            />
                                            <div className="w-11 h-6 bg-gray-700 peer-focus:outline-none rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-[#c8ff00]"></div>
                                        </label>
                                    </div>
                                </div>

                                {/* What we track info */}
                                <div className="p-4 bg-[#c8ff00]/10 rounded-xl border border-[#c8ff00]/20">
                                    <h4 className="text-[#c8ff00] font-medium mb-3">What we track (when enabled):</h4>
                                    <ul className="space-y-2 text-sm text-gray-300">
                                        <li className="flex items-center gap-2">
                                            <CheckCircle className="w-4 h-4 text-green-400" />
                                            Stocks and crypto you view in this app
                                        </li>
                                        <li className="flex items-center gap-2">
                                            <CheckCircle className="w-4 h-4 text-green-400" />
                                            Predictions you request
                                        </li>
                                        <li className="flex items-center gap-2">
                                            <CheckCircle className="w-4 h-4 text-green-400" />
                                            Time spent analyzing each asset
                                        </li>
                                        <li className="flex items-center gap-2">
                                            <CheckCircle className="w-4 h-4 text-green-400" />
                                            Your watchlist preferences
                                        </li>
                                    </ul>
                                </div>

                                {/* What we DON'T track */}
                                <div className="p-4 bg-red-500/10 rounded-xl border border-red-500/20">
                                    <h4 className="text-red-400 font-medium mb-3">What we NEVER track:</h4>
                                    <ul className="space-y-2 text-sm text-gray-300">
                                        <li className="flex items-center gap-2">
                                            <Lock className="w-4 h-4 text-red-400" />
                                            Other browser tabs or windows
                                        </li>
                                        <li className="flex items-center gap-2">
                                            <Lock className="w-4 h-4 text-red-400" />
                                            Other applications on your device
                                        </li>
                                        <li className="flex items-center gap-2">
                                            <Lock className="w-4 h-4 text-red-400" />
                                            Websites you visit outside our app
                                        </li>
                                        <li className="flex items-center gap-2">
                                            <Lock className="w-4 h-4 text-red-400" />
                                            Your personal files or documents
                                        </li>
                                    </ul>
                                </div>
                            </div>
                        )}

                        {/* Plans Section */}
                        {activeSection === 'plans' && (
                            <div className="space-y-6">
                                <div className="flex items-center justify-between">
                                    <div>
                                        <h3 className="text-lg font-semibold text-white mb-2">Plans & Billing</h3>
                                        <p className="text-gray-400 text-sm">
                                            Choose the plan that best fits your trading needs.
                                        </p>
                                    </div>
                                    <button
                                        onClick={loadSubscriptionData}
                                        disabled={isLoadingSubscription}
                                        className="flex items-center gap-2 text-sm text-[#c8ff00] hover:text-[#00ff88]"
                                    >
                                        <RefreshCw className={`w-4 h-4 ${isLoadingSubscription ? 'animate-spin' : ''}`} />
                                        Refresh
                                    </button>
                                </div>

                                {/* Error Message */}
                                {subscriptionError && (
                                    <div className="p-4 bg-red-500/10 rounded-xl border border-red-500/20">
                                        <div className="flex items-center gap-2 text-red-400">
                                            <AlertTriangle className="w-5 h-5" />
                                            <span>{subscriptionError}</span>
                                        </div>
                                    </div>
                                )}

                                {/* Loading State */}
                                {isLoadingSubscription && !subscriptionStatus ? (
                                    <div className="flex items-center justify-center py-12">
                                        <Loader2 className="w-8 h-8 animate-spin text-[#c8ff00]" />
                                    </div>
                                ) : (
                                    <>
                                        {/* Current Plan Badge */}
                                        <div className="p-4 bg-[#c8ff00]/10 rounded-xl border border-[#c8ff00]/20">
                                            <div className="flex items-center justify-between">
                                                <div className="flex items-center gap-3">
                                                    <div className="w-10 h-10 rounded-full bg-[#c8ff00]/20 flex items-center justify-center">
                                                        {subscriptionStatus?.plan === 'elite' ? (
                                                            <Crown className="w-5 h-5 text-yellow-400" />
                                                        ) : subscriptionStatus?.plan === 'pro' ? (
                                                            <Zap className="w-5 h-5 text-[#c8ff00]" />
                                                        ) : (
                                                            <Star className="w-5 h-5 text-gray-400" />
                                                        )}
                                                    </div>
                                                    <div>
                                                        <p className="text-white font-medium">
                                                            Current Plan: <span className="text-[#c8ff00] capitalize">{subscriptionStatus?.plan_name || 'Free'}</span>
                                                        </p>
                                                        <p className="text-gray-400 text-sm">
                                                            {subscriptionStatus?.is_premium && subscriptionStatus?.subscription_end
                                                                ? `Renews ${new Date(subscriptionStatus.subscription_end).toLocaleDateString()}`
                                                                : 'Upgrade to unlock more features'}
                                                        </p>
                                                        {subscriptionStatus?.predictions_today !== undefined && (
                                                            <p className="text-xs text-gray-500 mt-1">
                                                                Predictions today: {subscriptionStatus.predictions_today} / {subscriptionStatus.limits?.predictions_per_day === -1 ? '∞' : subscriptionStatus.limits?.predictions_per_day}
                                                            </p>
                                                        )}
                                                    </div>
                                                </div>
                                                {subscriptionStatus?.is_premium && (
                                                    <button 
                                                        onClick={() => setShowCancelConfirm(true)}
                                                        className="text-sm text-red-400 hover:text-red-300"
                                                    >
                                                        Cancel subscription
                                                    </button>
                                                )}
                                            </div>
                                        </div>

                                        {/* Plans Grid */}
                                        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                                            {availablePlans && Object.entries(availablePlans).map(([planId, plan]) => {
                                                const isCurrent = subscriptionStatus?.plan === planId
                                                const isPro = planId === 'pro'
                                                const isElite = planId === 'elite'
                                                
                                                return (
                                                    <div
                                                        key={planId}
                                                        className={`relative p-5 rounded-xl border transition-all ${
                                                            isCurrent
                                                                ? 'bg-[#c8ff00]/10 border-[#c8ff00]/40'
                                                                : 'bg-white/5 border-white/10 hover:border-white/20'
                                                        } ${isPro ? 'ring-2 ring-[#c8ff00]' : ''}`}
                                                    >
                                                        {isPro && (
                                                            <div className="absolute -top-3 left-1/2 -translate-x-1/2 px-3 py-1 bg-[#c8ff00] text-black text-xs font-medium rounded-full">
                                                                Most Popular
                                                            </div>
                                                        )}
                                                        
                                                        <div className="flex items-center gap-2 mb-3">
                                                            {isElite ? (
                                                                <Crown className="w-5 h-5 text-yellow-400" />
                                                            ) : isPro ? (
                                                                <Zap className="w-5 h-5 text-[#c8ff00]" />
                                                            ) : (
                                                                <Star className="w-5 h-5 text-gray-400" />
                                                            )}
                                                            <h4 className="text-white font-semibold">{plan.name}</h4>
                                                        </div>
                                                        
                                                        <div className="mb-4">
                                                            <span className="text-3xl font-bold text-white">
                                                                ${plan.price}
                                                            </span>
                                                            <span className="text-gray-400 text-sm">
                                                                {plan.price === 0 ? 'forever' : '/month'}
                                                            </span>
                                                        </div>
                                                        
                                                        <ul className="space-y-2 mb-5">
                                                            {plan.features?.map((feature, i) => (
                                                                <li key={i} className="flex items-start gap-2 text-sm">
                                                                    <CheckCircle className="w-4 h-4 text-green-400 mt-0.5 flex-shrink-0" />
                                                                    <span className="text-gray-300">{feature}</span>
                                                                </li>
                                                            ))}
                                                        </ul>
                                                        
                                                        <button
                                                            onClick={() => handleUpgrade(planId)}
                                                            disabled={isCurrent || isUpgrading}
                                                            className={`w-full py-2.5 rounded-lg font-medium transition-colors flex items-center justify-center gap-2 ${
                                                                isCurrent
                                                                    ? 'bg-white/10 text-gray-400 cursor-not-allowed'
                                                                    : isPro
                                                                        ? 'bg-[#c8ff00] hover:bg-[#d4ff33] text-black'
                                                                        : 'bg-white/10 hover:bg-white/20 text-white'
                                                            }`}
                                                        >
                                                            {isUpgrading && <Loader2 className="w-4 h-4 animate-spin" />}
                                                            {isCurrent ? 'Current Plan' : planId === 'free' ? 'Downgrade' : 'Upgrade'}
                                                            {!isCurrent && planId !== 'free' && <ExternalLink className="w-3.5 h-3.5" />}
                                                        </button>
                                                    </div>
                                                )
                                            })}
                                        </div>

                                        {/* Payment Methods */}
                                        <div className="p-4 bg-white/5 rounded-xl border border-white/10">
                                            <h4 className="text-white font-medium mb-3">Payment Methods</h4>
                                            {paymentMethods.length > 0 ? (
                                                paymentMethods.map((method, idx) => (
                                                    <div key={idx} className="flex items-center justify-between">
                                                        <div className="flex items-center gap-3">
                                                            <div className="w-12 h-8 bg-[#c8ff00] rounded flex items-center justify-center text-black text-xs font-bold">
                                                                {method.type === 'paypal' ? 'PayPal' : 'CARD'}
                                                            </div>
                                                            <div>
                                                                <p className="text-white text-sm">{method.email || '•••• •••• •••• ••••'}</p>
                                                                <p className="text-gray-500 text-xs">{method.isDefault ? 'Default' : ''}</p>
                                                            </div>
                                                        </div>
                                                        <button className="text-sm text-[#c8ff00] hover:text-[#d4ff33]">
                                                            Update
                                                        </button>
                                                    </div>
                                                ))
                                            ) : (
                                                <p className="text-gray-500 text-sm">No payment methods on file. Add one when upgrading.</p>
                                            )}
                                        </div>

                                        {/* Billing History */}
                                        <div className="p-4 bg-white/5 rounded-xl border border-white/10">
                                            <h4 className="text-white font-medium mb-3">Recent Invoices</h4>
                                            {billingHistory.length > 0 ? (
                                                <div className="space-y-2">
                                                    {billingHistory.map((invoice, i) => (
                                                        <div key={i} className="flex items-center justify-between py-2 border-b border-white/5 last:border-0">
                                                            <span className="text-gray-400 text-sm">
                                                                {new Date(invoice.date).toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' })}
                                                            </span>
                                                            <span className="text-white text-sm">${invoice.amount.toFixed(2)}</span>
                                                            <span className="text-green-400 text-xs capitalize">{invoice.status}</span>
                                                            <button className="text-xs text-[#c8ff00] hover:text-[#d4ff33]">Download</button>
                                                        </div>
                                                    ))}
                                                </div>
                                            ) : (
                                                <p className="text-gray-500 text-sm">No billing history available.</p>
                                            )}
                                        </div>
                                    </>
                                )}

                                {/* Cancel Subscription Confirmation Modal */}
                                <AnimatePresence>
                                    {showCancelConfirm && (
                                        <motion.div
                                            initial={{ opacity: 0 }}
                                            animate={{ opacity: 1 }}
                                            exit={{ opacity: 0 }}
                                            className="fixed inset-0 bg-black/80 flex items-center justify-center z-[60] p-4"
                                        >
                                            <motion.div
                                                initial={{ scale: 0.95 }}
                                                animate={{ scale: 1 }}
                                                exit={{ scale: 0.95 }}
                                                className="bg-[#1a1a2e] rounded-xl p-6 max-w-md w-full border border-red-500/20"
                                            >
                                                <h3 className="text-xl font-bold text-red-400 mb-4">Cancel Subscription?</h3>
                                                <p className="text-gray-300 mb-4">
                                                    Are you sure you want to cancel your subscription? You'll lose access to:
                                                </p>
                                                <ul className="text-gray-400 text-sm space-y-1 mb-6">
                                                    <li>• Extended forecast periods</li>
                                                    <li>• Unlimited predictions</li>
                                                    <li>• Real-time data access</li>
                                                    <li>• Technical indicators</li>
                                                </ul>
                                                <p className="text-yellow-400 text-sm mb-6">
                                                    Your access will continue until {subscriptionStatus?.subscription_end 
                                                        ? new Date(subscriptionStatus.subscription_end).toLocaleDateString() 
                                                        : 'the end of your billing period'}.
                                                </p>
                                                <div className="flex gap-3">
                                                    <button
                                                        onClick={() => setShowCancelConfirm(false)}
                                                        className="flex-1 px-4 py-2 bg-white/10 hover:bg-white/20 text-white rounded-lg"
                                                    >
                                                        Keep Subscription
                                                    </button>
                                                    <button
                                                        onClick={handleCancelSubscription}
                                                        disabled={isCancelling}
                                                        className="flex-1 px-4 py-2 bg-red-600 hover:bg-red-500 text-white rounded-lg flex items-center justify-center gap-2"
                                                    >
                                                        {isCancelling && <Loader2 className="w-4 h-4 animate-spin" />}
                                                        Cancel Anyway
                                                    </button>
                                                </div>
                                            </motion.div>
                                        </motion.div>
                                    )}
                                </AnimatePresence>
                            </div>
                        )}

                        {/* Notifications Section */}
                        {activeSection === 'notifications' && (
                            <div className="space-y-6">
                                <h3 className="text-lg font-semibold text-white mb-4">Notification Preferences</h3>
                                
                                <div className="p-4 bg-white/5 rounded-xl border border-white/10">
                                    <div className="flex items-center justify-between">
                                        <div>
                                            <h4 className="text-white font-medium">Email Alerts</h4>
                                            <p className="text-gray-400 text-sm">Receive price alerts and updates via email</p>
                                        </div>
                                        <label className="relative inline-flex items-center cursor-pointer">
                                            <input
                                                type="checkbox"
                                                checked={preferences?.email_alerts_enabled || false}
                                                onChange={(e) => updatePreference('email_alerts_enabled', e.target.checked)}
                                                className="sr-only peer"
                                            />
                                            <div className="w-11 h-6 bg-gray-700 peer-focus:outline-none rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-[#c8ff00]"></div>
                                        </label>
                                    </div>
                                </div>

                                <div className="p-4 bg-white/5 rounded-xl border border-white/10">
                                    <h4 className="text-white font-medium mb-3">Alert Frequency</h4>
                                    <div className="flex gap-2">
                                        {['realtime', 'hourly', 'daily'].map(freq => (
                                            <button
                                                key={freq}
                                                onClick={() => updatePreference('price_alert_frequency', freq)}
                                                className={`px-4 py-2 rounded-lg capitalize transition-colors ${
                                                    preferences?.price_alert_frequency === freq
                                                        ? 'bg-[#c8ff00] text-black'
                                                        : 'bg-white/5 text-gray-400 hover:bg-white/10'
                                                }`}
                                            >
                                                {freq}
                                            </button>
                                        ))}
                                    </div>
                                </div>
                            </div>
                        )}

                        {/* Display Section */}
                        {activeSection === 'display' && (
                            <div className="space-y-6">
                                <h3 className="text-lg font-semibold text-white mb-4">Display Preferences</h3>
                                
                                <div className="p-4 bg-white/5 rounded-xl border border-white/10">
                                    <h4 className="text-white font-medium mb-3">Default Prediction Days</h4>
                                    <div className="flex gap-2">
                                        {[7, 14, 21, 30].map(days => (
                                            <button
                                                key={days}
                                                onClick={() => updatePreference('default_prediction_days', days)}
                                                className={`px-4 py-2 rounded-lg transition-colors ${
                                                    preferences?.default_prediction_days === days
                                                        ? 'bg-[#c8ff00] text-black'
                                                        : 'bg-white/5 text-gray-400 hover:bg-white/10'
                                                }`}
                                            >
                                                {days} days
                                            </button>
                                        ))}
                                    </div>
                                </div>

                                <div className="p-4 bg-white/5 rounded-xl border border-white/10">
                                    <h4 className="text-white font-medium mb-3">Default Chart Period</h4>
                                    <div className="flex gap-2 flex-wrap">
                                        {['1mo', '3mo', '6mo', '1y', '5y'].map(period => (
                                            <button
                                                key={period}
                                                onClick={() => updatePreference('default_chart_period', period)}
                                                className={`px-4 py-2 rounded-lg transition-colors ${
                                                    preferences?.default_chart_period === period
                                                        ? 'bg-[#c8ff00] text-black'
                                                        : 'bg-white/5 text-gray-400 hover:bg-white/10'
                                                }`}
                                            >
                                                {period}
                                            </button>
                                        ))}
                                    </div>
                                </div>

                                <div className="grid grid-cols-1 gap-4">
                                    {[
                                        { key: 'show_technical_indicators', label: 'Show Technical Indicators' },
                                        { key: 'show_news_feed', label: 'Show News Feed' },
                                        { key: 'show_model_weights', label: 'Show Model Weights' },
                                    ].map(item => (
                                        <div key={item.key} className="p-4 bg-white/5 rounded-xl border border-white/10">
                                            <div className="flex items-center justify-between">
                                                <span className="text-white">{item.label}</span>
                                                <label className="relative inline-flex items-center cursor-pointer">
                                                    <input
                                                        type="checkbox"
                                                        checked={preferences?.[item.key] || false}
                                                        onChange={(e) => updatePreference(item.key, e.target.checked)}
                                                        className="sr-only peer"
                                                    />
                                                    <div className="w-11 h-6 bg-gray-700 peer-focus:outline-none rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-[#c8ff00]"></div>
                                                </label>
                                            </div>
                                        </div>
                                    ))}
                                </div>
                            </div>
                        )}

                        {/* Data Section */}
                        {activeSection === 'data' && (
                            <div className="space-y-6">
                                <h3 className="text-lg font-semibold text-white mb-4">Your Data</h3>
                                <p className="text-gray-400 text-sm">
                                    Under GDPR and CCPA, you have the right to access and delete your personal data.
                                </p>

                                {/* Export Data */}
                                <div className="p-4 bg-white/5 rounded-xl border border-white/10">
                                    <div className="flex items-start justify-between">
                                        <div>
                                            <h4 className="text-white font-medium">Export Your Data</h4>
                                            <p className="text-gray-400 text-sm mt-1">
                                                Download all your data including watchlists, prediction history, and preferences.
                                            </p>
                                        </div>
                                        <button
                                            onClick={handleExportData}
                                            disabled={isExporting}
                                            className="flex items-center gap-2 px-4 py-2 bg-[#c8ff00] hover:bg-[#d4ff33] text-black rounded-lg transition-colors disabled:opacity-50"
                                        >
                                            {isExporting ? (
                                                <Loader2 className="w-4 h-4 animate-spin" />
                                            ) : (
                                                <Download className="w-4 h-4" />
                                            )}
                                            Export
                                        </button>
                                    </div>
                                </div>

                                {/* Delete Account */}
                                <div className="p-4 bg-red-500/10 rounded-xl border border-red-500/20">
                                    <div className="flex items-start justify-between">
                                        <div>
                                            <h4 className="text-red-400 font-medium">Delete All Data</h4>
                                            <p className="text-gray-400 text-sm mt-1">
                                                Permanently delete your account and all associated data. This action cannot be undone.
                                            </p>
                                        </div>
                                        <button
                                            onClick={() => setShowDeleteConfirm(true)}
                                            className="flex items-center gap-2 px-4 py-2 bg-red-600 hover:bg-red-500 text-white rounded-lg transition-colors"
                                        >
                                            <Trash2 className="w-4 h-4" />
                                            Delete
                                        </button>
                                    </div>
                                </div>
                            </div>
                        )}

                        {/* Save Button */}
                        {activeSection !== 'data' && (
                            <div className="mt-8 flex items-center justify-between">
                                <div>
                                    {saveStatus === 'success' && (
                                        <span className="text-green-400 flex items-center gap-2">
                                            <CheckCircle className="w-4 h-4" />
                                            Settings saved!
                                        </span>
                                    )}
                                    {saveStatus === 'error' && (
                                        <span className="text-red-400 flex items-center gap-2">
                                            <AlertTriangle className="w-4 h-4" />
                                            Failed to save
                                        </span>
                                    )}
                                </div>
                                <button
                                    onClick={handleSave}
                                    disabled={isSaving}
                                    className="flex items-center gap-2 px-6 py-2 bg-gradient-to-r from-[#c8ff00] to-[#00ff88] hover:from-[#d4ff33] hover:to-[#33ff99] text-black rounded-lg transition-colors disabled:opacity-50"
                                >
                                    {isSaving ? (
                                        <Loader2 className="w-4 h-4 animate-spin" />
                                    ) : (
                                        <Save className="w-4 h-4" />
                                    )}
                                    Save Changes
                                </button>
                            </div>
                        )}
                    </div>
                </div>

                {/* Delete Confirmation Modal */}
                {showDeleteConfirm && (
                    <div className="absolute inset-0 bg-black/80 flex items-center justify-center p-4">
                        <motion.div
                            initial={{ opacity: 0, scale: 0.95 }}
                            animate={{ opacity: 1, scale: 1 }}
                            className="bg-[#1a1a2e] rounded-xl p-6 max-w-md border border-red-500/20"
                        >
                            <h3 className="text-xl font-bold text-red-400 mb-4">⚠️ Confirm Deletion</h3>
                            <p className="text-gray-300 mb-4">
                                Are you absolutely sure you want to delete your account? This will permanently remove:
                            </p>
                            <ul className="text-gray-400 text-sm space-y-1 mb-6">
                                <li>• Your profile and login credentials</li>
                                <li>• All watchlists and preferences</li>
                                <li>• Complete prediction history</li>
                                <li>• All activity tracking data</li>
                            </ul>
                            <p className="text-yellow-400 text-sm mb-6">
                                This action cannot be undone. Your data will be permanently deleted within 30 days.
                            </p>
                            <div className="flex gap-3">
                                <button
                                    onClick={() => setShowDeleteConfirm(false)}
                                    className="flex-1 px-4 py-2 bg-white/10 hover:bg-white/20 text-white rounded-lg"
                                >
                                    Cancel
                                </button>
                                <button
                                    onClick={handleDeleteRequest}
                                    disabled={isDeleting}
                                    className="flex-1 px-4 py-2 bg-red-600 hover:bg-red-500 text-white rounded-lg flex items-center justify-center gap-2"
                                >
                                    {isDeleting ? (
                                        <Loader2 className="w-4 h-4 animate-spin" />
                                    ) : (
                                        <Trash2 className="w-4 h-4" />
                                    )}
                                    Delete Forever
                                </button>
                            </div>
                        </motion.div>
                    </div>
                )}
            </motion.div>
        </div>
    )
}
