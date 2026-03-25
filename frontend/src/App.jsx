import { useState, useEffect, lazy, Suspense } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { BrowserRouter, Routes, Route, Navigate, useLocation, useNavigate } from 'react-router-dom'
import { AuthProvider, useAuth } from './context/AuthContext'
import { useTheme } from './context/ThemeContext'

// Always-eager: these are the first things any visitor sees
import LandingPage from './components/LandingPage'
import LoadingScreen from './components/LoadingScreen'
import LoginPage from './components/Auth/LoginPage'
import RegisterPage from './components/Auth/RegisterPage'

// Lazy-loaded: only downloaded after the user logs in
const Dashboard    = lazy(() => import('./components/Dashboard'))
const BentoDashboard = lazy(() => import('./components/BentoDashboard'))
const Sidebar      = lazy(() => import('./components/Sidebar'))
const DisclaimerModal = lazy(() => import('./components/DisclaimerModal'))
const AIChatbot    = lazy(() => import('./components/AIChatbot'))
const SettingsPage = lazy(() => import('./components/SettingsPage'))
const GlobeView    = lazy(() => import('./components/GlobeView'))
const NewListings  = lazy(() => import('./components/NewListings'))

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
    // Only show the intro loading screen once per browser session.
    // Using sessionStorage prevents it re-firing on HMR reloads or remounts.
    const [isLoading, setIsLoading] = useState(
        () => !sessionStorage.getItem('nexus_loaded')
    )
    const [selectedAsset, setSelectedAsset] = useState(null)
    const [assetType, setAssetType] = useState('stock')
    const [showSettings, setShowSettings] = useState(false)
    const [activeView, setActiveView] = useState('dashboard') // 'dashboard' | 'globe'
    const { theme, toggleTheme, isDark, isLight, classes } = useTheme()
    const { user } = useAuth()
    const navigate = useNavigate()

    useEffect(() => {
        if (!isLoading) return
        const timer = setTimeout(() => {
            setIsLoading(false)
            sessionStorage.setItem('nexus_loaded', '1')
        }, 2000)
        return () => clearTimeout(timer)
    }, [])

    const handleAssetSelect = (symbol, type) => {
        setSelectedAsset(symbol)
        setAssetType(type)
        setActiveView('dashboard')
    }

    return (
        <div className={`min-h-screen ${classes.pageBackground} flex`}>
            <Suspense fallback={null}>
                <DisclaimerModal />
                <AIChatbot />
                {showSettings && <SettingsPage onClose={() => setShowSettings(false)} />}
            </Suspense>
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
                        <Suspense fallback={<LoadingScreen />}>
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
                        </Suspense>
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

export default App
