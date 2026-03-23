import { useState, useEffect } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { BrowserRouter, Routes, Route, Navigate, useLocation, useNavigate } from 'react-router-dom'
import Dashboard from './components/Dashboard'
import BentoDashboard from './components/BentoDashboard'
import Sidebar from './components/Sidebar'
import LoadingScreen from './components/LoadingScreen'
import DisclaimerModal from './components/DisclaimerModal'
import AIChatbot from './components/AIChatbot'
import SettingsPage from './components/SettingsPage'
import SubscriptionPage from './components/SubscriptionPage'
import LandingPage from './components/LandingPage'
import GlobeView from './components/GlobeView'
import NewListings from './components/NewListings'
import { AuthProvider, useAuth } from './context/AuthContext'
import { useTheme } from './context/ThemeContext'
import LoginPage from './components/Auth/LoginPage'
import RegisterPage from './components/Auth/RegisterPage'

// Brand configuration
export const BRAND = {
    name: 'NexusTrader',
    tagline: 'Where AI Meets Market Intelligence'
}

const AuthGuard = ({ children }) => {
    const { user, loading } = useAuth()
    const navigate = useNavigate()
    const location = useLocation()

    useEffect(() => {
        if (!loading && !user) {
            navigate('/login', { state: { from: location.pathname } })
        }
    }, [user, loading, navigate, location])

    if (loading) return <LoadingScreen />
    if (!user) return null

    return children
}

function AppContent() {
    const [isLoading, setIsLoading] = useState(true)
    const [selectedAsset, setSelectedAsset] = useState(null)
    const [assetType, setAssetType] = useState('stock')
    const [showSettings, setShowSettings] = useState(false)
    const [activeView, setActiveView] = useState('dashboard') // 'dashboard' | 'globe'
    const { theme, toggleTheme, isDark, isLight, classes } = useTheme()
    const { user } = useAuth()
    const navigate = useNavigate()

    useEffect(() => {
        const timer = setTimeout(() => setIsLoading(false), 2000)
        return () => clearTimeout(timer)
    }, [])

    const handleAssetSelect = (symbol, type) => {
        setSelectedAsset(symbol)
        setAssetType(type)
        setActiveView('dashboard')
    }

    return (
        <div className={`min-h-screen ${classes.pageBackground} flex`}>
            <DisclaimerModal />
            <AIChatbot />
            {showSettings && <SettingsPage onClose={() => setShowSettings(false)} />}
            <AnimatePresence mode="wait">
                {isLoading ? (
                    <LoadingScreen key="loading" />
                ) : (
                    <motion.div
                        key="app"
                        initial={{ opacity: 0 }}
                        animate={{ opacity: 1 }}
                        transition={{ duration: 0.5 }}
                        className="flex w-full"
                    >
                        {/* Sidebar */}
                        <Sidebar
                            onAssetSelect={handleAssetSelect}
                            selectedAsset={selectedAsset}
                            assetType={assetType}
                            user={user}
                            onOpenSettings={() => setShowSettings(true)}
                            theme={theme}
                            onToggleTheme={toggleTheme}
                            activeView={activeView}
                            onViewChange={setActiveView}
                        />

                        {/* Main content */}
                        <main className="flex-1 overflow-hidden relative">
                            <AnimatePresence mode="wait">
                                {activeView === 'globe' ? (
                                    <motion.div
                                        key="globe"
                                        initial={{ opacity: 0, scale: 0.98 }}
                                        animate={{ opacity: 1, scale: 1 }}
                                        exit={{ opacity: 0, scale: 0.98 }}
                                        transition={{ duration: 0.35 }}
                                        className="absolute inset-0"
                                    >
                                        <GlobeView />
                                    </motion.div>
                                ) : activeView === 'listings' ? (
                                    <motion.div
                                        key="listings"
                                        initial={{ opacity: 0, x: 20 }}
                                        animate={{ opacity: 1, x: 0 }}
                                        exit={{ opacity: 0, x: -20 }}
                                        transition={{ duration: 0.25 }}
                                        className="absolute inset-0 overflow-y-auto"
                                    >
                                        <NewListings onPredict={(symbol) => handleAssetSelect(symbol, symbol.includes('/') ? 'crypto' : 'stock')} />
                                    </motion.div>
                                ) : (
                                    <motion.div
                                        key="dashboard"
                                        initial={{ opacity: 0 }}
                                        animate={{ opacity: 1 }}
                                        exit={{ opacity: 0 }}
                                        transition={{ duration: 0.25 }}
                                        className="absolute inset-0 overflow-y-auto"
                                    >
                                        <Dashboard
                                            selectedAsset={selectedAsset}
                                            assetType={assetType}
                                            onAssetSelect={handleAssetSelect}
                                            user={user}
                                        />
                                    </motion.div>
                                )}
                            </AnimatePresence>
                        </main>
                    </motion.div>
                )}
            </AnimatePresence>
        </div>
    )
}

function App() {
    return (
        <BrowserRouter>
            <AuthProvider>
                <Routes>
                    {/* Public routes */}
                    <Route path="/" element={<LandingPage />} />
                    <Route path="/login" element={<AuthPage mode="login" />} />
                    <Route path="/register" element={<AuthPage mode="register" />} />
                    
                    {/* Protected routes */}
                    <Route path="/dashboard" element={
                        <AuthGuard>
                            <AppContent />
                        </AuthGuard>
                    } />
                    <Route path="/subscription" element={
                        <AuthGuard>
                            <SubscriptionPage />
                        </AuthGuard>
                    } />
                    <Route path="/subscription/success" element={
                        <AuthGuard>
                            <SubscriptionSuccess />
                        </AuthGuard>
                    } />
                    <Route path="/subscription/cancel" element={
                        <AuthGuard>
                            <SubscriptionCancel />
                        </AuthGuard>
                    } />
                    
                    {/* Catch all - redirect to home */}
                    <Route path="*" element={<Navigate to="/" replace />} />
                </Routes>
            </AuthProvider>
        </BrowserRouter>
    )
}

// Auth page wrapper
function AuthPage({ mode }) {
    const { user, loading } = useAuth()
    const navigate = useNavigate()
    const location = useLocation()
    const [authMode, setAuthMode] = useState(mode)

    useEffect(() => {
        if (user && !loading) {
            // Redirect to dashboard or the page they came from
            const from = location.state?.from || '/dashboard'
            navigate(from)
        }
    }, [user, loading, navigate, location])

    if (loading) return <LoadingScreen />

    return (
        <div className="min-h-screen flex items-center justify-center p-4 relative overflow-hidden" style={{ background: '#050508' }}>
            {/* Aurora ambient */}
            <div className="absolute inset-0 pointer-events-none">
                <div className="absolute top-1/4 left-1/4 w-[500px] h-[500px] rounded-full" style={{ background: 'radial-gradient(circle, rgba(200,255,0,0.055), transparent 70%)', filter: 'blur(80px)' }} />
                <div className="absolute bottom-1/4 right-1/4 w-[400px] h-[400px] rounded-full" style={{ background: 'radial-gradient(circle, rgba(0,212,170,0.045), transparent 70%)', filter: 'blur(80px)' }} />
                <div className="absolute inset-0" style={{ backgroundImage: 'radial-gradient(circle, rgba(255,255,255,0.05) 1px, transparent 1px)', backgroundSize: '44px 44px' }} />
            </div>
            <div className="relative z-10 w-full flex justify-center">
                {authMode === 'login' ? (
                    <LoginPage onSwitchToRegister={() => setAuthMode('register')} />
                ) : (
                    <RegisterPage onSwitchToLogin={() => setAuthMode('login')} />
                )}
            </div>
        </div>
    )
}

// Subscription success page
function SubscriptionSuccess() {
    const navigate = useNavigate()
    const location = useLocation()
    const { getToken, refreshSubscription } = useAuth()
    const token = getToken()
    const [processing, setProcessing] = useState(true)
    const [result, setResult] = useState(null)

    useEffect(() => {
        const params = new URLSearchParams(location.search)
        const subscriptionId = params.get('subscription_id')
        const plan = params.get('plan')
        const orderId = params.get('token') // Old order-based flow
        
        if (subscriptionId && plan && token) {
            // New subscription-based flow
            activateSubscription(plan, subscriptionId)
        } else if (orderId && token) {
            // Legacy order-based flow
            captureOrder(orderId)
        } else {
            setProcessing(false)
            setResult({ status: 'success', message: 'Subscription activated!' })
        }
    }, [location, token])

    const activateSubscription = async (plan, subscriptionId) => {
        try {
            const response = await fetch(`/api/subscription/activate`, {
                method: 'POST',
                headers: { 
                    'Content-Type': 'application/json',
                    Authorization: `Bearer ${token}` 
                },
                body: JSON.stringify({ plan, subscription_id: subscriptionId })
            })
            const data = await response.json()
            if (response.ok) {
                setResult({ status: 'success', message: `Successfully subscribed to ${plan.charAt(0).toUpperCase() + plan.slice(1)} plan!` })
                if (refreshSubscription) refreshSubscription()
            } else {
                setResult({ status: 'error', message: data.detail || 'Failed to activate subscription' })
            }
        } catch (err) {
            setResult({ status: 'error', message: 'Failed to process subscription' })
        } finally {
            setProcessing(false)
        }
    }

    const captureOrder = async (orderId) => {
        try {
            const response = await fetch(`/api/subscription/capture-order/${orderId}`, {
                method: 'POST',
                headers: { Authorization: `Bearer ${token}` }
            })
            const data = await response.json()
            setResult(data)
            if (refreshSubscription) refreshSubscription()
        } catch (err) {
            setResult({ status: 'error', message: 'Failed to process payment' })
        } finally {
            setProcessing(false)
        }
    }

    return (
        <div className="min-h-screen bg-[#0a0a14] flex items-center justify-center p-4">
            <motion.div
                initial={{ opacity: 0, scale: 0.9 }}
                animate={{ opacity: 1, scale: 1 }}
                className="bg-white/5 backdrop-blur-sm border border-white/10 rounded-2xl p-8 max-w-md text-center"
            >
                {processing ? (
                    <>
                        <div className="animate-spin rounded-full h-12 w-12 border-t-2 border-b-2 border-[#c8ff00] mx-auto mb-4"></div>
                        <p className="text-gray-400">Processing your payment...</p>
                    </>
                ) : result?.status === 'success' ? (
                    <>
                        <div className="text-6xl mb-4">🎉</div>
                        <h2 className="text-2xl font-bold text-green-400 mb-2">Payment Successful!</h2>
                        <p className="text-gray-400 mb-6">{result.message}</p>
                        <button
                            onClick={() => navigate('/')}
                            className="px-6 py-3 bg-gradient-to-r from-[#c8ff00] to-[#00ff88] text-black rounded-xl font-semibold"
                        >
                            Go to Dashboard
                        </button>
                    </>
                ) : (
                    <>
                        <div className="text-6xl mb-4">❌</div>
                        <h2 className="text-2xl font-bold text-red-400 mb-2">Payment Failed</h2>
                        <p className="text-gray-400 mb-6">{result?.message || 'Something went wrong'}</p>
                        <button
                            onClick={() => navigate('/subscription')}
                            className="px-6 py-3 bg-white/10 hover:bg-white/20 rounded-xl font-semibold"
                        >
                            Try Again
                        </button>
                    </>
                )}
            </motion.div>
        </div>
    )
}

// Subscription cancel page
function SubscriptionCancel() {
    const navigate = useNavigate()

    return (
        <div className="min-h-screen bg-[#0a0a14] flex items-center justify-center p-4">
            <motion.div
                initial={{ opacity: 0, scale: 0.9 }}
                animate={{ opacity: 1, scale: 1 }}
                className="bg-white/5 backdrop-blur-sm border border-white/10 rounded-2xl p-8 max-w-md text-center"
            >
                <div className="text-6xl mb-4">😔</div>
                <h2 className="text-2xl font-bold mb-2">Payment Cancelled</h2>
                <p className="text-gray-400 mb-6">
                    No worries! You can always upgrade later.
                </p>
                <div className="flex gap-4 justify-center">
                    <button
                        onClick={() => navigate('/')}
                        className="px-6 py-3 bg-white/10 hover:bg-white/20 rounded-xl font-semibold"
                    >
                        Go to Dashboard
                    </button>
                    <button
                        onClick={() => navigate('/subscription')}
                        className="px-6 py-3 bg-gradient-to-r from-[#c8ff00] to-[#00ff88] text-black rounded-xl font-semibold"
                    >
                        View Plans
                    </button>
                </div>
            </motion.div>
        </div>
    )
}

export default App
