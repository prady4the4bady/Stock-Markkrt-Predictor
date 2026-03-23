import { useMemo } from 'react'
import { motion } from 'framer-motion'
import {
    AreaChart, Area, Line, XAxis, YAxis, CartesianGrid,
    Tooltip, ResponsiveContainer, ReferenceLine, Legend
} from 'recharts'

// Determine the time scale based on range and prediction period
function getTimeScale(period, predictionDays) {
    // Intraday ranges
    if (['1h', '12h', '1d'].includes(period)) {
        return 'hours'
    }
    // Weekly range
    if (period === '1w') {
        return predictionDays < 1 ? 'hours' : 'days'
    }
    // Longer ranges
    return 'days'
}

// Format date based on time scale
function formatDate(dateStr, timeScale) {
    if (!dateStr) return ''
    
    // Handle both date formats: "YYYY-MM-DD" and "YYYY-MM-DD HH:MM"
    const hasTime = dateStr.includes(':')
    
    if (timeScale === 'hours') {
        if (hasTime) {
            // Extract just the time part (HH:MM)
            const timePart = dateStr.split(' ')[1]
            return timePart || dateStr
        } else {
            // Daily data in hour view - show date
            return dateStr.slice(5) // MM-DD
        }
    } else {
        // Days view - show MM/DD
        const datePart = dateStr.split(' ')[0]
        const parts = datePart.split('-')
        if (parts.length >= 3) {
            return `${parts[1]}/${parts[2]}`
        }
        return dateStr
    }
}

export default function PriceChart({ historical, predictions, individual, dates, symbol, period = '1y', predictionDays = 7 }) {
    // Determine time scale based on data
    const timeScale = useMemo(() => getTimeScale(period, predictionDays), [period, predictionDays])
    
    const chartData = useMemo(() => {
        if (!historical || !predictions) return []

        // Balance historical and prediction data
        // Goal: historical should take ~60-70% of chart, predictions ~30-40%
        const predictionCount = predictions.length
        
        // Calculate ideal historical points to show (roughly 2x predictions for balance)
        let historicalPoints
        if (predictionCount <= 1) {
            // Very short prediction (1h) - show last 10-20 historical points
            historicalPoints = Math.min(historical.length, 20)
        } else if (predictionCount <= 12) {
            // Short prediction (12h or 1d) - show 2-3x historical points
            historicalPoints = Math.min(historical.length, predictionCount * 3)
        } else {
            // Longer predictions - show 1.5-2x historical points
            historicalPoints = Math.min(historical.length, Math.max(predictionCount * 2, 30))
        }
        
        // Ensure minimum visibility
        historicalPoints = Math.max(historicalPoints, 10)
        
        const recentHistorical = historical.slice(-historicalPoints).map(item => ({
            date: item.timestamp,
            displayDate: formatDate(item.timestamp, timeScale),
            price: item.close,
            type: 'historical'
        }))

        // Add predictions
        const predictionData = predictions.map((price, index) => ({
            date: dates[index],
            displayDate: formatDate(dates[index], timeScale),
            price: Math.round(price * 100) / 100,
            predictedPrice: Math.round(price * 100) / 100,
            lstm: individual?.lstm?.values[index] ? Math.round(individual.lstm.values[index] * 100) / 100 : null,
            xgboost: individual?.xgboost?.values[index] ? Math.round(individual.xgboost.values[index] * 100) / 100 : null,
            prophet: individual?.prophet?.values[index] ? Math.round(individual.prophet.values[index] * 100) / 100 : null,
            type: 'prediction'
        }))

        // Combine with overlap for smooth transition
        const lastHistorical = recentHistorical[recentHistorical.length - 1]
        if (!lastHistorical) return []
        
        const combinedData = [
            ...recentHistorical,
            {
                ...lastHistorical,
                predictedPrice: lastHistorical.price,
                lstm: lastHistorical.price,
                xgboost: lastHistorical.price,
                prophet: lastHistorical.price
            },
            ...predictionData
        ]

        return combinedData
    }, [historical, predictions, individual, dates, timeScale])

    const CustomTooltip = ({ active, payload }) => {
        if (active && payload && payload.length) {
            const data = payload[0].payload
            const isPrediction = data.type === 'prediction'

            return (
                <div className="glass-card p-4 border border-white/10 min-w-[200px]">
                    <p className="text-sm text-gray-400 mb-2">{data.date}</p>

                    {/* Main Price */}
                    <div className="mb-3">
                        <p className="text-2xl font-bold">
                            <span className={isPrediction ? 'text-[#00ff88]' : 'text-[#c8ff00]'}>
                                ${data.price?.toLocaleString() || data.predictedPrice?.toLocaleString()}
                            </span>
                        </p>
                        <p className="text-xs text-gray-500">
                            {isPrediction ? 'Ensemble Prediction' : 'Historical Price'}
                        </p>
                    </div>

                    {/* Individual Models */}
                    {isPrediction && individual && (
                        <div className="space-y-1 pt-2 border-t border-white/5">
                            <div className="flex justify-between text-xs">
                                <span className="text-[#c8ff00]">LSTM</span>
                                <span>${data.lstm?.toLocaleString()}</span>
                            </div>
                            <div className="flex justify-between text-xs">
                                <span className="text-green-400">XGBoost</span>
                                <span>${data.xgboost?.toLocaleString()}</span>
                            </div>
                            {/* Prophet hidden as fallback or shown subtly */}
                            <div className="flex justify-between text-xs">
                                <span className="text-orange-400">Prophet (Trend)</span>
                                <span>${data.prophet?.toLocaleString()}</span>
                            </div>
                        </div>
                    )}
                </div>
            )
        }
        return null
    }

    if (!chartData.length) {
        return (
            <div className="glass-card p-8 h-96 flex items-center justify-center">
                <div className="text-center text-gray-500">
                    <div className="text-4xl mb-4">📈</div>
                    <p>Select an asset to view the chart</p>
                </div>
            </div>
        )
    }

    const minPrice = Math.min(...chartData.map(d => d.price || d.predictedPrice)) * 0.98
    const maxPrice = Math.max(...chartData.map(d => d.price || d.predictedPrice)) * 1.02

    return (
        <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            className="glass-card p-6"
        >
            <div className="flex items-center justify-between mb-6">
                <h3 className="text-lg font-semibold flex items-center gap-2">
                    <span className="text-2xl">📈</span>
                    Price Chart
                </h3>
                <div className="flex items-center gap-4 text-sm">
                    <div className="flex items-center gap-2">
                        <div className="w-3 h-3 rounded-full bg-[#c8ff00]" />
                        <span className="text-gray-400">Historical</span>
                    </div>
                    <div className="flex items-center gap-2">
                        <div className="w-3 h-3 rounded-full bg-[#00ff88]" />
                        <span className="text-gray-400">Predicted</span>
                    </div>
                </div>
            </div>

            <div className="h-80">
                <ResponsiveContainer width="100%" height="100%">
                    <AreaChart data={chartData} margin={{ top: 10, right: 30, left: 0, bottom: 0 }}>
                        <defs>
                            <linearGradient id="historicalGradient" x1="0" y1="0" x2="0" y2="1">
                                <stop offset="0%" stopColor="#c8ff00" stopOpacity={0.3} />
                                <stop offset="100%" stopColor="#c8ff00" stopOpacity={0} />
                            </linearGradient>
                            <linearGradient id="predictionGradient" x1="0" y1="0" x2="0" y2="1">
                                <stop offset="0%" stopColor="#00ff88" stopOpacity={0.3} />
                                <stop offset="100%" stopColor="#00ff88" stopOpacity={0} />
                            </linearGradient>
                        </defs>

                        <CartesianGrid
                            strokeDasharray="3 3"
                            stroke="rgba(255,255,255,0.05)"
                            vertical={false}
                        />

                        <XAxis
                            dataKey="displayDate"
                            stroke="rgba(255,255,255,0.3)"
                            tick={{ fill: 'rgba(255,255,255,0.5)', fontSize: 11 }}
                            tickLine={false}
                            interval="preserveStartEnd"
                        />

                        <YAxis
                            domain={[minPrice, maxPrice]}
                            stroke="rgba(255,255,255,0.3)"
                            tick={{ fill: 'rgba(255,255,255,0.5)', fontSize: 11 }}
                            tickLine={false}
                            tickFormatter={(value) => `$${value.toLocaleString()}`}
                        />

                        <Tooltip content={<CustomTooltip />} />

                        {/* Historical area */}
                        <Area
                            type="monotone"
                            dataKey="price"
                            stroke="#c8ff00"
                            strokeWidth={3}
                            fill="url(#historicalGradient)"
                            activeDot={{ r: 6, fill: '#c8ff00', stroke: '#fff', strokeWidth: 2 }}
                        />

                        {/* Prediction areas - Individual Models */}
                        <Line type="monotone" dataKey="lstm" stroke="#c8ff00" strokeWidth={1} strokeDasharray="3 3" dot={false} />
                        <Line type="monotone" dataKey="xgboost" stroke="#4ade80" strokeWidth={1} strokeDasharray="3 3" dot={false} />
                        <Line type="monotone" dataKey="prophet" stroke="#fb923c" strokeWidth={1} strokeDasharray="3 3" dot={false} />

                        {/* Ensemble Prediction (Main) */}
                        <Area
                            type="monotone"
                            dataKey="predictedPrice"
                            stroke="#00ff88"
                            strokeWidth={3}
                            fill="url(#predictionGradient)"
                            activeDot={{ r: 6, fill: '#00ff88', stroke: '#fff', strokeWidth: 2 }}
                        />
                    </AreaChart>
                </ResponsiveContainer>
            </div>
        </motion.div>
    )
}
