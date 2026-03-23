import { motion } from 'framer-motion'
import { Brain, TrendingUp, TrendingDown, Minus, Gauge } from 'lucide-react'

export default function MarketSentiment({ prediction, historical }) {
    if (!prediction || !historical || historical.length === 0) {
        return (
            <motion.div
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                className="glass-card p-6"
            >
                <div className="flex items-center gap-2 mb-4">
                    <Brain className="w-5 h-5 text-[#c8ff00]" />
                    <h3 className="text-lg font-semibold">AI Market Sentiment</h3>
                </div>
                <div className="h-32 flex items-center justify-center text-gray-500">
                    Analyzing sentiment...
                </div>
            </motion.div>
        )
    }

    // Calculate various sentiment indicators
    const recentData = historical.slice(-30)
    const prices = recentData.map(d => d.close)
    
    // 1. Price momentum
    const momentum = ((prices[prices.length - 1] - prices[0]) / prices[0]) * 100
    
    // 2. Trend strength (based on consecutive moves)
    let consecutiveUp = 0
    let consecutiveDown = 0
    let currentStreak = 0
    let streakType = 'neutral'
    
    for (let i = 1; i < prices.length; i++) {
        if (prices[i] > prices[i-1]) {
            if (streakType === 'up') currentStreak++
            else { currentStreak = 1; streakType = 'up' }
            consecutiveUp = Math.max(consecutiveUp, currentStreak)
        } else if (prices[i] < prices[i-1]) {
            if (streakType === 'down') currentStreak++
            else { currentStreak = 1; streakType = 'down' }
            consecutiveDown = Math.max(consecutiveDown, currentStreak)
        }
    }
    
    // 3. Volatility score
    const volatility = (Math.max(...prices) - Math.min(...prices)) / prices[0] * 100
    
    // 4. Prediction alignment
    const predictionTrend = prediction.predictions[prediction.predictions.length - 1] > prediction.current_price ? 'bullish' : 'bearish'
    const priceTrend = momentum > 0 ? 'bullish' : 'bearish'
    const trendsAligned = predictionTrend === priceTrend
    
    // Calculate overall sentiment score (0-100)
    let sentimentScore = 50 // Neutral base
    
    // Momentum contribution
    sentimentScore += Math.min(20, Math.max(-20, momentum * 2))
    
    // Confidence contribution
    sentimentScore += (prediction.confidence - 50) * 0.3
    
    // Trend alignment bonus
    if (trendsAligned) sentimentScore += 5
    
    // Clamp score
    sentimentScore = Math.min(100, Math.max(0, sentimentScore))
    
    // Determine sentiment label
    let sentimentLabel = 'Neutral'
    let sentimentColor = 'text-yellow-400'
    let sentimentBg = 'bg-yellow-500/20'
    let sentimentIcon = <Minus className="w-5 h-5" />
    
    if (sentimentScore >= 70) {
        sentimentLabel = 'Very Bullish'
        sentimentColor = 'text-green-400'
        sentimentBg = 'bg-green-500/20'
        sentimentIcon = <TrendingUp className="w-5 h-5" />
    } else if (sentimentScore >= 55) {
        sentimentLabel = 'Bullish'
        sentimentColor = 'text-green-400'
        sentimentBg = 'bg-green-500/10'
        sentimentIcon = <TrendingUp className="w-5 h-5" />
    } else if (sentimentScore <= 30) {
        sentimentLabel = 'Very Bearish'
        sentimentColor = 'text-red-400'
        sentimentBg = 'bg-red-500/20'
        sentimentIcon = <TrendingDown className="w-5 h-5" />
    } else if (sentimentScore <= 45) {
        sentimentLabel = 'Bearish'
        sentimentColor = 'text-red-400'
        sentimentBg = 'bg-red-500/10'
        sentimentIcon = <TrendingDown className="w-5 h-5" />
    }

    // Gauge visualization
    const gaugeRotation = (sentimentScore / 100) * 180 - 90 // -90 to 90 degrees

    return (
        <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            className="glass-card p-6"
        >
            <div className="flex items-center justify-between mb-4">
                <div className="flex items-center gap-2">
                    <Brain className="w-5 h-5 text-[#c8ff00]" />
                    <h3 className="text-lg font-semibold">AI Market Sentiment</h3>
                </div>
                <span className={`px-3 py-1 rounded-full text-sm font-semibold ${sentimentBg} ${sentimentColor} flex items-center gap-1`}>
                    {sentimentIcon}
                    {sentimentLabel}
                </span>
            </div>

            {/* Sentiment Gauge */}
            <div className="relative h-24 mb-4 flex items-center justify-center">
                <div className="relative w-40 h-20 overflow-hidden">
                    {/* Gauge background */}
                    <div className="absolute inset-0 rounded-t-full bg-gradient-to-r from-red-500/30 via-yellow-500/30 to-green-500/30" />
                    
                    {/* Gauge needle */}
                    <div 
                        className="absolute bottom-0 left-1/2 w-1 h-16 bg-white origin-bottom transition-transform duration-700"
                        style={{ transform: `translateX(-50%) rotate(${gaugeRotation}deg)` }}
                    >
                        <div className="absolute -top-1 left-1/2 w-3 h-3 bg-white rounded-full transform -translate-x-1/2" />
                    </div>
                    
                    {/* Center point */}
                    <div className="absolute bottom-0 left-1/2 w-4 h-4 bg-gray-800 rounded-full transform -translate-x-1/2 translate-y-1/2 border-2 border-white/50" />
                </div>
                
                {/* Score display */}
                <div className="absolute bottom-0 left-1/2 transform -translate-x-1/2 text-center">
                    <div className={`text-2xl font-bold ${sentimentColor}`}>{Math.round(sentimentScore)}</div>
                    <div className="text-xs text-gray-500">Sentiment Score</div>
                </div>
            </div>

            {/* Sentiment Factors */}
            <div className="grid grid-cols-2 gap-3">
                <div className="bg-white/5 rounded-lg p-3">
                    <div className="text-xs text-gray-400 mb-1">30-Day Momentum</div>
                    <div className={`font-semibold ${momentum >= 0 ? 'text-green-400' : 'text-red-400'}`}>
                        {momentum >= 0 ? '+' : ''}{momentum.toFixed(2)}%
                    </div>
                </div>
                <div className="bg-white/5 rounded-lg p-3">
                    <div className="text-xs text-gray-400 mb-1">AI Confidence</div>
                    <div className="font-semibold text-[#c8ff00]">
                        {prediction.confidence?.toFixed(1)}%
                    </div>
                </div>
                <div className="bg-white/5 rounded-lg p-3">
                    <div className="text-xs text-gray-400 mb-1">Volatility</div>
                    <div className={`font-semibold ${
                        volatility < 5 ? 'text-green-400' : 
                        volatility < 15 ? 'text-yellow-400' : 'text-red-400'
                    }`}>
                        {volatility < 5 ? 'Low' : volatility < 15 ? 'Medium' : 'High'}
                    </div>
                </div>
                <div className="bg-white/5 rounded-lg p-3">
                    <div className="text-xs text-gray-400 mb-1">Trend Alignment</div>
                    <div className={`font-semibold ${trendsAligned ? 'text-green-400' : 'text-yellow-400'}`}>
                        {trendsAligned ? '✓ Aligned' : '⚠ Mixed'}
                    </div>
                </div>
            </div>

            {/* Best Streak */}
            <div className="mt-3 p-3 bg-white/5 rounded-lg">
                <div className="flex justify-between text-sm">
                    <span className="text-gray-400">Best Up Streak: <span className="text-green-400 font-semibold">{consecutiveUp} days</span></span>
                    <span className="text-gray-400">Best Down Streak: <span className="text-red-400 font-semibold">{consecutiveDown} days</span></span>
                </div>
            </div>
        </motion.div>
    )
}
