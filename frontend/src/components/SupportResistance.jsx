import { motion } from 'framer-motion'
import { Target, ArrowUp, ArrowDown, Minus } from 'lucide-react'

export default function SupportResistance({ historical, currentPrice }) {
    if (!historical || historical.length === 0 || !currentPrice) {
        return (
            <motion.div
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                className="glass-card p-6"
            >
                <div className="flex items-center gap-2 mb-4">
                    <Target className="w-5 h-5 text-[#c8ff00]" />
                    <h3 className="text-lg font-semibold">Key Levels</h3>
                </div>
                <div className="h-40 flex items-center justify-center text-gray-500">
                    Calculating levels...
                </div>
            </motion.div>
        )
    }

    // Calculate support and resistance levels using pivot points
    const recentData = historical.slice(-60)
    const highs = recentData.map(d => d.high)
    const lows = recentData.map(d => d.low)
    const closes = recentData.map(d => d.close)
    
    const periodHigh = Math.max(...highs)
    const periodLow = Math.min(...lows)
    const periodClose = closes[closes.length - 1]
    
    // Classic Pivot Points
    const pivot = (periodHigh + periodLow + periodClose) / 3
    const r1 = (2 * pivot) - periodLow
    const r2 = pivot + (periodHigh - periodLow)
    const r3 = periodHigh + 2 * (pivot - periodLow)
    const s1 = (2 * pivot) - periodHigh
    const s2 = pivot - (periodHigh - periodLow)
    const s3 = periodLow - 2 * (periodHigh - pivot)

    // Find nearest levels
    const levels = [
        { name: 'R3', value: r3, type: 'resistance' },
        { name: 'R2', value: r2, type: 'resistance' },
        { name: 'R1', value: r1, type: 'resistance' },
        { name: 'Pivot', value: pivot, type: 'pivot' },
        { name: 'S1', value: s1, type: 'support' },
        { name: 'S2', value: s2, type: 'support' },
        { name: 'S3', value: s3, type: 'support' },
    ].sort((a, b) => b.value - a.value)

    // Calculate distance from current price
    const levelsWithDistance = levels.map(level => ({
        ...level,
        distance: ((level.value - currentPrice) / currentPrice) * 100,
        isNear: Math.abs((level.value - currentPrice) / currentPrice) < 0.02
    }))

    // Find nearest support and resistance
    const nearestResistance = levelsWithDistance.find(l => l.value > currentPrice)
    const nearestSupport = [...levelsWithDistance].reverse().find(l => l.value < currentPrice)

    // Calculate strength (how many times price touched these levels)
    const calculateStrength = (level, tolerance = 0.01) => {
        const touches = recentData.filter(d => {
            const touchedHigh = Math.abs(d.high - level) / level < tolerance
            const touchedLow = Math.abs(d.low - level) / level < tolerance
            return touchedHigh || touchedLow
        }).length
        return Math.min(100, touches * 10)
    }

    return (
        <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            className="glass-card p-6"
        >
            <div className="flex items-center justify-between mb-4">
                <div className="flex items-center gap-2">
                    <Target className="w-5 h-5 text-[#c8ff00]" />
                    <h3 className="text-lg font-semibold">Key Levels</h3>
                </div>
                <span className="text-xs text-gray-500">60-day pivot</span>
            </div>

            {/* Visual Price Level Indicator */}
            <div className="relative mb-6 h-48 bg-white/5 rounded-lg overflow-hidden">
                {levelsWithDistance.map((level, i) => {
                    const normalizedPosition = ((level.value - s3) / (r3 - s3)) * 100
                    const position = Math.max(5, Math.min(95, normalizedPosition))
                    
                    return (
                        <div
                            key={level.name}
                            className="absolute left-0 right-0 flex items-center px-3"
                            style={{ bottom: `${position}%`, transform: 'translateY(50%)' }}
                        >
                            <div className={`flex-1 h-px ${
                                level.type === 'resistance' ? 'bg-red-500/50' :
                                level.type === 'support' ? 'bg-green-500/50' :
                                'bg-[#c8ff00]/50'
                            } ${level.isNear ? 'h-0.5' : ''}`} />
                            <span className={`ml-2 text-xs font-medium ${
                                level.type === 'resistance' ? 'text-red-400' :
                                level.type === 'support' ? 'text-green-400' :
                                'text-[#c8ff00]'
                            }`}>
                                {level.name}: ${level.value.toFixed(2)}
                            </span>
                        </div>
                    )
                })}
                
                {/* Current price marker */}
                <div
                    className="absolute left-0 right-0 flex items-center px-3"
                    style={{ 
                        bottom: `${((currentPrice - s3) / (r3 - s3)) * 100}%`,
                        transform: 'translateY(50%)'
                    }}
                >
                    <div className="flex-1 h-0.5 bg-[#c8ff00] animate-pulse" />
                    <span className="ml-2 text-xs font-bold text-[#c8ff00]">
                        Current: ${currentPrice.toFixed(2)}
                    </span>
                </div>
            </div>

            {/* Key Metrics */}
            <div className="grid grid-cols-2 gap-3">
                <div className="bg-red-500/10 rounded-lg p-3 border border-red-500/20">
                    <div className="text-xs text-red-400 mb-1 flex items-center gap-1">
                        <ArrowUp className="w-3 h-3" />
                        Nearest Resistance
                    </div>
                    <div className="font-semibold text-red-400">
                        ${nearestResistance?.value.toFixed(2) || 'N/A'}
                    </div>
                    <div className="text-xs text-gray-500">
                        {nearestResistance?.distance.toFixed(1)}% away
                    </div>
                </div>
                <div className="bg-green-500/10 rounded-lg p-3 border border-green-500/20">
                    <div className="text-xs text-green-400 mb-1 flex items-center gap-1">
                        <ArrowDown className="w-3 h-3" />
                        Nearest Support
                    </div>
                    <div className="font-semibold text-green-400">
                        ${nearestSupport?.value.toFixed(2) || 'N/A'}
                    </div>
                    <div className="text-xs text-gray-500">
                        {Math.abs(nearestSupport?.distance || 0).toFixed(1)}% away
                    </div>
                </div>
                <div className="bg-[#c8ff00]/10 rounded-lg p-3 border border-[#c8ff00]/20">
                    <div className="text-xs text-[#c8ff00] mb-1 flex items-center gap-1">
                        <Minus className="w-3 h-3" />
                        Pivot Point
                    </div>
                    <div className="font-semibold text-[#c8ff00]">
                        ${pivot.toFixed(2)}
                    </div>
                </div>
                <div className="bg-white/5 rounded-lg p-3">
                    <div className="text-xs text-gray-400 mb-1">Price Range</div>
                    <div className="text-sm">
                        <span className="text-red-400">${periodHigh.toFixed(2)}</span>
                        <span className="text-gray-500 mx-1">-</span>
                        <span className="text-green-400">${periodLow.toFixed(2)}</span>
                    </div>
                </div>
            </div>
        </motion.div>
    )
}
