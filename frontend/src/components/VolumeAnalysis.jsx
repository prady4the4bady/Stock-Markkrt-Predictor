import { motion } from 'framer-motion'
import { BarChart3, TrendingUp, TrendingDown, Activity } from 'lucide-react'
import { AreaChart, Area, XAxis, YAxis, Tooltip, ResponsiveContainer, Bar, ComposedChart } from 'recharts'

export default function VolumeAnalysis({ historical, predictions }) {
    if (!historical || historical.length === 0) {
        return (
            <motion.div
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                className="glass-card p-6"
            >
                <div className="flex items-center gap-2 mb-4">
                    <BarChart3 className="w-5 h-5 text-[#c8ff00]" />
                    <h3 className="text-lg font-semibold">Volume Analysis</h3>
                </div>
                <div className="h-40 flex items-center justify-center text-gray-500">
                    Loading volume data...
                </div>
            </motion.div>
        )
    }

    // Get last 60 days of data
    const recentData = historical.slice(-60).map((item, index) => {
        const prevClose = index > 0 ? historical[historical.length - 60 + index - 1]?.close : item.close
        const isUp = item.close >= prevClose
        return {
            date: item.timestamp?.split('T')[0] || `Day ${index}`,
            volume: item.volume,
            close: item.close,
            isUp,
            color: isUp ? '#00ff88' : '#ff3366'
        }
    })

    // Calculate volume metrics
    const avgVolume = recentData.reduce((sum, d) => sum + (d.volume || 0), 0) / recentData.length
    const recentVolume = recentData.slice(-5).reduce((sum, d) => sum + (d.volume || 0), 0) / 5
    const volumeTrend = ((recentVolume - avgVolume) / avgVolume) * 100
    
    // Calculate OBV (On-Balance Volume) trend
    let obv = 0
    const obvData = recentData.map((d, i) => {
        if (i > 0 && d.isUp) obv += d.volume
        else if (i > 0) obv -= d.volume
        return obv
    })
    const obvTrend = obvData[obvData.length - 1] > obvData[Math.floor(obvData.length / 2)] ? 'Bullish' : 'Bearish'

    // Volume-price correlation
    const upDays = recentData.filter(d => d.isUp).length
    const downDays = recentData.filter(d => !d.isUp).length
    const sentiment = upDays > downDays ? 'Accumulation' : 'Distribution'

    return (
        <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            className="glass-card p-6"
        >
            <div className="flex items-center justify-between mb-4">
                <div className="flex items-center gap-2">
                    <BarChart3 className="w-5 h-5 text-[#c8ff00]" />
                    <h3 className="text-lg font-semibold">Volume Analysis</h3>
                </div>
                <span className={`px-2 py-1 rounded text-xs font-semibold ${
                    sentiment === 'Accumulation' 
                        ? 'bg-green-500/20 text-green-400' 
                        : 'bg-red-500/20 text-red-400'
                }`}>
                    {sentiment}
                </span>
            </div>

            {/* Volume Chart */}
            <div className="h-32 mb-4">
                <ResponsiveContainer width="100%" height="100%">
                    <ComposedChart data={recentData.slice(-30)}>
                        <XAxis 
                            dataKey="date" 
                            tick={false}
                            axisLine={{ stroke: '#ffffff10' }}
                        />
                        <YAxis 
                            tick={{ fontSize: 10, fill: '#888' }}
                            axisLine={false}
                            tickLine={false}
                            width={40}
                            tickFormatter={(v) => `${(v / 1000000).toFixed(0)}M`}
                        />
                        <Tooltip
                            contentStyle={{
                                backgroundColor: '#1a1a2e',
                                border: '1px solid rgba(255,255,255,0.1)',
                                borderRadius: '8px',
                                fontSize: '12px'
                            }}
                            formatter={(value, name) => {
                                if (name === 'volume') return [(value / 1000000).toFixed(2) + 'M', 'Volume']
                                return [value?.toFixed(2), name]
                            }}
                        />
                        <Bar 
                            dataKey="volume" 
                            fill="#4f46e5"
                            opacity={0.6}
                            radius={[2, 2, 0, 0]}
                        />
                    </ComposedChart>
                </ResponsiveContainer>
            </div>

            {/* Volume Metrics */}
            <div className="grid grid-cols-2 gap-3">
                <div className="bg-white/5 rounded-lg p-3">
                    <div className="text-xs text-gray-400 mb-1">Volume Trend</div>
                    <div className={`flex items-center gap-1 font-semibold ${
                        volumeTrend >= 0 ? 'text-green-400' : 'text-red-400'
                    }`}>
                        {volumeTrend >= 0 ? (
                            <TrendingUp className="w-4 h-4" />
                        ) : (
                            <TrendingDown className="w-4 h-4" />
                        )}
                        {volumeTrend >= 0 ? '+' : ''}{volumeTrend.toFixed(1)}%
                    </div>
                </div>
                <div className="bg-white/5 rounded-lg p-3">
                    <div className="text-xs text-gray-400 mb-1">OBV Signal</div>
                    <div className={`flex items-center gap-1 font-semibold ${
                        obvTrend === 'Bullish' ? 'text-green-400' : 'text-red-400'
                    }`}>
                        <Activity className="w-4 h-4" />
                        {obvTrend}
                    </div>
                </div>
                <div className="bg-white/5 rounded-lg p-3">
                    <div className="text-xs text-gray-400 mb-1">Avg Volume</div>
                    <div className="font-semibold text-white">
                        {(avgVolume / 1000000).toFixed(2)}M
                    </div>
                </div>
                <div className="bg-white/5 rounded-lg p-3">
                    <div className="text-xs text-gray-400 mb-1">Up/Down Days</div>
                    <div className="flex items-center gap-2">
                        <span className="text-green-400 font-semibold">{upDays}</span>
                        <span className="text-gray-500">/</span>
                        <span className="text-red-400 font-semibold">{downDays}</span>
                    </div>
                </div>
            </div>
        </motion.div>
    )
}
