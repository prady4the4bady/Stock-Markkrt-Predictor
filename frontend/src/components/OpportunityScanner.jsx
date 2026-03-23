import { useState, useEffect } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { Zap, RefreshCw, TrendingUp, TrendingDown, AlertCircle, X, Radar } from 'lucide-react'
import axios from 'axios'

const API_URL = '/api'

export default function OpportunityScanner({ onAssetSelect }) {
    const [opportunities, setOpportunities] = useState([])
    const [isScanning, setIsScanning] = useState(false)
    const [scannedCount, setScannedCount] = useState(0)
    const [isOpen, setIsOpen] = useState(false)

    const scanMarket = async () => {
        setIsScanning(true)
        setOpportunities([])
        try {
            const res = await axios.get(`${API_URL}/scan/opportunities`)
            setOpportunities(res.data.opportunities || [])
            setScannedCount(res.data.scan_count || 0)
        } catch (e) {
            console.error("Scan failed", e)
        } finally {
            setIsScanning(false)
        }
    }

    // Auto-open if we have results
    useEffect(() => {
        if (opportunities.length > 0) {
            setIsOpen(true)
        }
    }, [opportunities])

    return (
        <div className="fixed bottom-6 right-6 z-40">
            <AnimatePresence>
                {isOpen && (
                    <motion.div
                        initial={{ opacity: 0, y: 20, scale: 0.9 }}
                        animate={{ opacity: 1, y: 0, scale: 1 }}
                        exit={{ opacity: 0, scale: 0.9 }}
                        className="mb-4 w-[340px] glass-card border border-[#c8ff00]/30 overflow-hidden shadow-2xl shadow-[#c8ff00]/10"
                    >
                        {/* Header */}
                        <div className="p-4 bg-gradient-to-r from-[#c8ff00]/10 to-[#00ff88]/10 flex items-center justify-between border-b border-[#c8ff00]/20">
                            <div className="flex items-center gap-3">
                                <div className="p-2 bg-[#c8ff00]/20 rounded-lg relative">
                                    <Radar className={`w-5 h-5 text-[#c8ff00] ${isScanning ? 'animate-pulse' : ''}`} />
                                    {isScanning && (
                                        <span className="absolute inset-0 animate-ping rounded-lg bg-[#c8ff00]/30" />
                                    )}
                                </div>
                                <div>
                                    <h3 className="font-bold text-white text-sm">AI Scanner</h3>
                                    <p className="text-[10px] text-[#c8ff00]">
                                        {opportunities.length > 0 
                                            ? `${opportunities.length} opportunities found` 
                                            : isScanning 
                                                ? 'Scanning markets...' 
                                                : 'Ready to scan'}
                                    </p>
                                </div>
                            </div>
                            <div className="flex items-center gap-2">
                                <motion.button
                                    whileHover={{ scale: 1.1 }}
                                    whileTap={{ scale: 0.9 }}
                                    onClick={scanMarket}
                                    disabled={isScanning}
                                    className="p-1.5 rounded-lg hover:bg-[#c8ff00]/20 text-gray-400 hover:text-[#c8ff00] transition-colors disabled:opacity-50"
                                >
                                    <RefreshCw className={`w-4 h-4 ${isScanning ? 'animate-spin' : ''}`} />
                                </motion.button>
                                <button
                                    onClick={() => setIsOpen(false)}
                                    className="p-1.5 rounded-lg hover:bg-red-500/20 text-gray-400 hover:text-red-400 transition-colors"
                                >
                                    <X className="w-4 h-4" />
                                </button>
                            </div>
                        </div>

                        {/* Content */}
                        <div className="max-h-[280px] overflow-y-auto custom-scrollbar">
                            {isScanning ? (
                                <div className="p-6 flex flex-col items-center justify-center">
                                    <div className="relative w-16 h-16 mb-3">
                                        <div className="absolute inset-0 rounded-full border-2 border-[#c8ff00]/30 animate-ping" />
                                        <div className="absolute inset-2 rounded-full border-2 border-[#c8ff00]/50 animate-pulse" />
                                        <div className="absolute inset-4 rounded-full bg-[#c8ff00]/20 flex items-center justify-center">
                                            <Radar className="w-6 h-6 text-[#c8ff00] animate-spin" />
                                        </div>
                                    </div>
                                    <p className="text-sm text-gray-400">Analyzing market patterns...</p>
                                    <p className="text-xs text-[#c8ff00]/60 mt-1">Running 6 AI models</p>
                                </div>
                            ) : opportunities.length === 0 ? (
                                <div className="p-6 text-center">
                                    <AlertCircle className="w-10 h-10 mx-auto mb-3 text-gray-600" />
                                    <p className="text-sm text-gray-500">No high-confidence signals</p>
                                    <p className="text-xs text-gray-600 mt-1">Try scanning again later</p>
                                </div>
                            ) : (
                                <div className="divide-y divide-white/5">
                                    {opportunities.map((opp, idx) => (
                                        <motion.div
                                            key={opp.symbol}
                                            initial={{ opacity: 0, x: -10 }}
                                            animate={{ opacity: 1, x: 0 }}
                                            transition={{ delay: idx * 0.1 }}
                                            onClick={() => onAssetSelect(opp.symbol, opp.symbol.includes('/') ? 'crypto' : 'stock')}
                                            className="p-3 hover:bg-white/5 cursor-pointer transition-all group"
                                        >
                                            <div className="flex justify-between items-start mb-2">
                                                <div className="flex items-center gap-2">
                                                    <span className="font-bold text-white group-hover:text-[#c8ff00] transition-colors">
                                                        {opp.symbol.split('/')[0]}
                                                    </span>
                                                    <span className="text-[10px] px-1.5 py-0.5 rounded bg-white/5 text-gray-500">
                                                        {opp.symbol.includes('/') ? 'CRYPTO' : 'STOCK'}
                                                    </span>
                                                </div>
                                                <div className="flex items-center gap-1">
                                                    <span className={`text-xs font-bold px-2 py-1 rounded-lg ${
                                                        opp.confidence >= 70 
                                                            ? 'bg-green-500/20 text-green-400' 
                                                            : opp.confidence >= 55 
                                                                ? 'bg-yellow-500/20 text-yellow-400'
                                                                : 'bg-gray-500/20 text-gray-400'
                                                    }`}>
                                                        {opp.confidence.toFixed(0)}%
                                                    </span>
                                                </div>
                                            </div>
                                            <div className="flex justify-between items-center">
                                                <span className="text-xs text-gray-500">
                                                    ${opp.price?.toLocaleString() || '---'}
                                                </span>
                                                <div className={`flex items-center gap-1 text-xs font-semibold ${
                                                    opp.predicted_change >= 0 ? 'text-green-400' : 'text-red-400'
                                                }`}>
                                                    {opp.predicted_change >= 0 
                                                        ? <TrendingUp className="w-3 h-3" /> 
                                                        : <TrendingDown className="w-3 h-3" />
                                                    }
                                                    {opp.predicted_change >= 0 ? '+' : ''}{opp.predicted_change?.toFixed(1)}%
                                                </div>
                                            </div>
                                        </motion.div>
                                    ))}
                                </div>
                            )}
                        </div>

                        {/* Footer */}
                        {opportunities.length > 0 && (
                            <div className="p-3 border-t border-white/5 bg-black/20">
                                <p className="text-[10px] text-gray-500 text-center">
                                    Scanned {scannedCount} assets • Click to analyze
                                </p>
                            </div>
                        )}
                    </motion.div>
                )}
            </AnimatePresence>

            {/* Toggle Button */}
            <motion.button
                whileHover={{ scale: 1.05 }}
                whileTap={{ scale: 0.95 }}
                onClick={() => {
                    if (!isOpen) {
                        setIsOpen(true)
                        if (opportunities.length === 0) scanMarket()
                    } else {
                        scanMarket()
                    }
                }}
                className={`relative flex items-center gap-2 px-5 py-3 rounded-xl font-bold shadow-lg transition-all ${
                    isScanning
                        ? 'bg-gray-800/80 text-gray-400 cursor-wait'
                        : 'bg-gradient-to-r from-[#c8ff00] to-[#00ff88] text-black hover:shadow-[#c8ff00]/30 hover:shadow-xl'
                }`}
            >
                {/* Animated background */}
                {!isScanning && (
                    <span className="absolute inset-0 rounded-xl bg-gradient-to-r from-[#c8ff00] to-[#00ff88] opacity-0 hover:opacity-20 transition-opacity" />
                )}
                
                <Zap className={`w-5 h-5 ${isScanning ? 'animate-pulse' : ''}`} />
                <span className="text-sm">
                    {isScanning ? 'Scanning...' : (isOpen ? 'Rescan' : 'AI Scanner')}
                </span>
                
                {/* Notification dot */}
                {!isOpen && !isScanning && (
                    <span className="absolute -top-1 -right-1 flex h-3 w-3">
                        <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-[#c8ff00] opacity-75" />
                        <span className="relative inline-flex rounded-full h-3 w-3 bg-[#c8ff00]" />
                    </span>
                )}
            </motion.button>
        </div>
    )
}
