import { useState, useEffect } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import {
    Settings, Shield, Eye, EyeOff, Download, Trash2,
    Bell, Moon, Sun, Save, Loader2, CheckCircle, AlertTriangle,
    ChevronRight, Lock, Key, Plus, X
} from 'lucide-react'
import { useAuth } from '../context/AuthContext'
import activityService from '../services/ActivityService'

export default function SettingsPage({ onClose }) {
    const { user, logout } = useAuth()
    const [preferences, setPreferences] = useState(null)
    const [isLoading, setIsLoading] = useState(true)
    const [isSaving, setIsSaving] = useState(false)
    const [saveStatus, setSaveStatus] = useState(null)
    const [activeSection, setActiveSection] = useState('api-keys')
    const [showDeleteConfirm, setShowDeleteConfirm] = useState(false)
    const [isExporting, setIsExporting] = useState(false)
    const [isDeleting, setIsDeleting] = useState(false)
    const [apiKeys, setApiKeys] = useState({})
    const [newKeyName, setNewKeyName] = useState('')
    const [newKeyValue, setNewKeyValue] = useState('')
    const [keySaving, setKeySaving] = useState(false)
    const [keyStatus, setKeyStatus] = useState(null)
    const [showKeyValue, setShowKeyValue] = useState({})

    useEffect(() => {
        loadPreferences()
        loadApiKeys()
    }, [])

    const API_BASE = import.meta.env.VITE_API_URL || ''

    const loadApiKeys = async () => {
        try {
            const res = await fetch(`${API_BASE}/api/settings/api-keys`)
            if (res.ok) {
                const data = await res.json()
                setApiKeys(data.keys || {})
            }
        } catch (err) {
            console.error('Failed to load API keys:', err)
        }
    }

    const saveApiKey = async () => {
        if (!newKeyName || !newKeyValue) return
        setKeySaving(true)
        setKeyStatus(null)
        try {
            const res = await fetch(`${API_BASE}/api/settings/api-keys`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ key_name: newKeyName, key_value: newKeyValue }),
            })
            if (!res.ok) {
                const err = await res.json()
                throw new Error(err.detail || 'Failed to save')
            }
            setKeyStatus('saved')
            setNewKeyName('')
            setNewKeyValue('')
            loadApiKeys()
            setTimeout(() => setKeyStatus(null), 3000)
        } catch (err) {
            setKeyStatus(err.message)
        } finally {
            setKeySaving(false)
        }
    }

    const deleteApiKey = async (keyName) => {
        try {
            await fetch(`${API_BASE}/api/settings/api-keys/${keyName}`, { method: 'DELETE' })
            loadApiKeys()
        } catch (err) {
            console.error('Failed to delete key:', err)
        }
    }

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
        { id: 'api-keys', label: 'API Keys', icon: Key },
        { id: 'privacy', label: 'Privacy & Tracking', icon: Shield },
        { id: 'notifications', label: 'Notifications', icon: Bell },
        { id: 'display', label: 'Display', icon: Moon },
        { id: 'data', label: 'Your Data', icon: Download },
    ]

    const API_KEY_INFO = {
        NVIDIA_API_KEY: { label: 'NVIDIA NIM', desc: 'Model Council (12 AI models)', url: 'https://build.nvidia.com/', required: true },
        GROQ_API_KEY: { label: 'Groq', desc: 'Fast LLM inference', url: 'https://console.groq.com/keys', required: false },
        ALPHA_VANTAGE_API_KEY: { label: 'Alpha Vantage', desc: 'Stock fundamentals & earnings', url: 'https://www.alphavantage.co/support/#api-key', required: false },
        FRED_API_KEY: { label: 'FRED', desc: 'Federal Reserve economic data', url: 'https://fred.stlouisfed.org/docs/api/api_key.html', required: false },
        NEWS_API_KEY: { label: 'NewsAPI', desc: 'Real-time news sentiment', url: 'https://newsapi.org/register', required: false },
        COINGECKO_API_KEY: { label: 'CoinGecko', desc: 'Crypto market data', url: 'https://www.coingecko.com/en/api', required: false },
        POLYGON_API_KEY: { label: 'Polygon.io', desc: 'Real-time stock data', url: 'https://polygon.io/dashboard/signup', required: false },
        OPENAI_API_KEY: { label: 'OpenAI', desc: 'GPT models (optional)', url: 'https://platform.openai.com/api-keys', required: false },
    }

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
                        {/* API Keys Section */}
                        {activeSection === 'api-keys' && (
                            <div className="space-y-6">
                                <div>
                                    <h3 className="text-lg font-semibold text-white mb-2">API Keys</h3>
                                    <p className="text-gray-400 text-sm">
                                        Add your own API keys to unlock additional data sources. Keys are stored securely server-side and never exposed to the browser.
                                    </p>
                                </div>

                                {/* Current keys */}
                                <div className="space-y-3">
                                    {Object.entries(API_KEY_INFO).map(([keyName, info]) => {
                                        const keyData = apiKeys[keyName]
                                        const isSet = keyData?.set
                                        return (
                                            <div key={keyName} className={`p-4 rounded-xl border ${
                                                isSet ? 'bg-green-500/5 border-green-500/20' : 'bg-white/5 border-white/10'
                                            }`}>
                                                <div className="flex items-center justify-between">
                                                    <div className="flex items-center gap-3">
                                                        <div className={`w-2 h-2 rounded-full ${isSet ? 'bg-green-400' : 'bg-gray-600'}`} />
                                                        <div>
                                                            <div className="flex items-center gap-2">
                                                                <span className="text-white font-medium">{info.label}</span>
                                                                {info.required && (
                                                                    <span className="text-[10px] px-1.5 py-0.5 bg-[#c8ff00]/20 text-[#c8ff00] rounded">REQUIRED</span>
                                                                )}
                                                            </div>
                                                            <p className="text-gray-500 text-xs">{info.desc}</p>
                                                        </div>
                                                    </div>
                                                    <div className="flex items-center gap-2">
                                                        {isSet ? (
                                                            <>
                                                                <span className="text-green-400 text-xs font-mono">{keyData.preview}</span>
                                                                {keyData.source === 'user' && (
                                                                    <button
                                                                        onClick={() => deleteApiKey(keyName)}
                                                                        className="p-1 text-red-400 hover:text-red-300 transition-colors"
                                                                        title="Remove key"
                                                                    >
                                                                        <X className="w-4 h-4" />
                                                                    </button>
                                                                )}
                                                                {keyData.source === 'environment' && (
                                                                    <span className="text-gray-500 text-[10px]">ENV</span>
                                                                )}
                                                            </>
                                                        ) : (
                                                            <a
                                                                href={info.url}
                                                                target="_blank"
                                                                rel="noopener noreferrer"
                                                                className="text-xs text-[#c8ff00] hover:underline"
                                                            >
                                                                Get key →
                                                            </a>
                                                        )}
                                                    </div>
                                                </div>
                                            </div>
                                        )
                                    })}
                                </div>

                                {/* Add new key */}
                                <div className="p-4 bg-[#c8ff00]/5 rounded-xl border border-[#c8ff00]/20">
                                    <h4 className="text-[#c8ff00] font-medium mb-3 flex items-center gap-2">
                                        <Plus className="w-4 h-4" /> Add API Key
                                    </h4>
                                    <div className="space-y-3">
                                        <select
                                            value={newKeyName}
                                            onChange={(e) => setNewKeyName(e.target.value)}
                                            className="w-full bg-[#0d0d18] border border-white/10 rounded-lg px-3 py-2 text-white text-sm focus:outline-none focus:border-[#c8ff00]/50"
                                        >
                                            <option value="">Select API key type...</option>
                                            {Object.entries(API_KEY_INFO)
                                                .filter(([k]) => !apiKeys[k]?.set)
                                                .map(([k, info]) => (
                                                    <option key={k} value={k}>{info.label} — {info.desc}</option>
                                                ))
                                            }
                                        </select>
                                        <div className="relative">
                                            <input
                                                type={showKeyValue.new ? 'text' : 'password'}
                                                value={newKeyValue}
                                                onChange={(e) => setNewKeyValue(e.target.value)}
                                                placeholder="Paste your API key here..."
                                                className="w-full bg-[#0d0d18] border border-white/10 rounded-lg px-3 py-2 text-white text-sm font-mono focus:outline-none focus:border-[#c8ff00]/50 pr-20"
                                            />
                                            <button
                                                onClick={() => setShowKeyValue(prev => ({ ...prev, new: !prev.new }))}
                                                className="absolute right-10 top-1/2 -translate-y-1/2 text-gray-400 hover:text-white"
                                            >
                                                {showKeyValue.new ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                                            </button>
                                        </div>
                                        <div className="flex items-center justify-between">
                                            <div>
                                                {keyStatus === 'saved' && (
                                                    <span className="text-green-400 text-sm flex items-center gap-1">
                                                        <CheckCircle className="w-4 h-4" /> Key saved and activated
                                                    </span>
                                                )}
                                                {keyStatus && keyStatus !== 'saved' && (
                                                    <span className="text-red-400 text-sm flex items-center gap-1">
                                                        <AlertTriangle className="w-4 h-4" /> {keyStatus}
                                                    </span>
                                                )}
                                            </div>
                                            <button
                                                onClick={saveApiKey}
                                                disabled={!newKeyName || !newKeyValue || keySaving}
                                                className="flex items-center gap-2 px-4 py-2 bg-[#c8ff00] hover:bg-[#d4ff33] text-black rounded-lg transition-colors disabled:opacity-30 disabled:cursor-not-allowed text-sm"
                                            >
                                                {keySaving ? <Loader2 className="w-4 h-4 animate-spin" /> : <Save className="w-4 h-4" />}
                                                Save Key
                                            </button>
                                        </div>
                                    </div>
                                </div>

                                {/* Security note */}
                                <div className="p-3 bg-blue-500/10 rounded-lg border border-blue-500/20">
                                    <p className="text-blue-300 text-xs">
                                        <Lock className="w-3 h-3 inline mr-1" />
                                        Keys are stored server-side only. They are never sent to your browser after saving, never logged, and never shared with third parties.
                                    </p>
                                </div>
                            </div>
                        )}

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
