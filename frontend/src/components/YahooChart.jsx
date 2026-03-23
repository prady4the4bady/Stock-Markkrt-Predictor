import { useState, useEffect, useMemo, useCallback } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import {
    ComposedChart, Area, Line, Bar, XAxis, YAxis, CartesianGrid,
    Tooltip, ResponsiveContainer, ReferenceLine, Cell
} from 'recharts'
import { ChevronDown, Settings, TrendingUp, Zap, Calendar } from 'lucide-react'
import { getCurrencyForSymbol, formatPriceWithCurrency, convertFromUSD, getExchangeRateFromUSD } from '../utils/currencyUtils'
import { useTheme } from '../context/ThemeContext'

// Get current date in YYYY-MM-DD format
const getCurrentDate = () => {
    const now = new Date()
    return now.toISOString().split('T')[0]
}

// Get current datetime
const getCurrentDateTime = () => {
    const now = new Date()
    return now.toISOString().slice(0, 16).replace('T', ' ')
}

// Format large numbers
function formatNumber(num) {
    if (!num && num !== 0) return '-'
    if (num >= 1e12) return `${(num / 1e12).toFixed(2)}T`
    if (num >= 1e9) return `${(num / 1e9).toFixed(2)}B`
    if (num >= 1e6) return `${(num / 1e6).toFixed(2)}M`
    if (num >= 1e3) return `${(num / 1e3).toFixed(2)}K`
    return num.toLocaleString()
}

// Format price with proper decimals
function formatPrice(price) {
    if (!price && price !== 0) return '-'
    if (price >= 1000) return price.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })
    if (price >= 1) return price.toFixed(2)
    return price.toFixed(4)
}

// Time period options
const TIME_PERIODS = [
    { label: '1D', value: '1d' },
    { label: '5D', value: '5d' },
    { label: '1M', value: '1mo' },
    { label: '6M', value: '6mo' },
    { label: 'YTD', value: 'ytd' },
    { label: '1Y', value: '1y' },
    { label: '5Y', value: '5y' },
    { label: 'All', value: 'max' }
]

// Chart type options
const CHART_TYPES = [
    { label: 'Line', value: 'line' },
    { label: 'Candle', value: 'candle' },
    { label: 'Mountain', value: 'mountain' },
    { label: 'Bar', value: 'bar' }
]

// Custom Candlestick shape component
const CandleShape = (props) => {
    const { x, width, payload, yScale } = props
    if (!payload || payload.type !== 'historical' || !payload.open) return null
    
    const isUp = payload.close >= payload.open
    const color = isUp ? '#22c55e' : '#ef4444'
    
    const candleWidth = Math.max(width * 0.6, 3)
    const centerX = x + width / 2
    
    // Get Y coordinates from scale
    const highY = yScale(payload.high)
    const lowY = yScale(payload.low)
    const openY = yScale(payload.open)
    const closeY = yScale(payload.close)
    
    const bodyTop = Math.min(openY, closeY)
    const bodyHeight = Math.max(Math.abs(closeY - openY), 1)
    
    return (
        <g>
            {/* Wick - vertical line from high to low */}
            <line
                x1={centerX}
                y1={highY}
                x2={centerX}
                y2={lowY}
                stroke={color}
                strokeWidth={1}
            />
            {/* Body - rectangle from open to close */}
            <rect
                x={centerX - candleWidth / 2}
                y={bodyTop}
                width={candleWidth}
                height={bodyHeight}
                fill={isUp ? '#22c55e' : '#ef4444'}
                stroke={color}
                strokeWidth={0.5}
            />
        </g>
    )
}

export default function YahooChart({ 
    historical, 
    predictions, 
    individual, 
    dates, 
    symbol, 
    quote,
    period = '1y', 
    predictionDays = 7,
    onPeriodChange,
    onAdvancedChart,
    onRefreshData  // New prop for triggering data refresh
}) {
    const { isDark, isLight, colors, classes } = useTheme()
    const [selectedPeriod, setSelectedPeriod] = useState(period)
    const [chartType, setChartType] = useState('line')
    const [showChartMenu, setShowChartMenu] = useState(false)
    const [keyEvents, setKeyEvents] = useState(true)
    const [showPredictions, setShowPredictions] = useState(true)
    const [showAdvancedModal, setShowAdvancedModal] = useState(false)
    const [livePrice, setLivePrice] = useState(null)
    const [lastUpdateTime, setLastUpdateTime] = useState(new Date())
    const [isLive, setIsLive] = useState(true)
    const [currentTime, setCurrentTime] = useState(new Date())

    // Update current time every second
    useEffect(() => {
        const timer = setInterval(() => {
            setCurrentTime(new Date())
        }, 1000)
        return () => clearInterval(timer)
    }, [])

    // Format current date/time
    const formattedCurrentDate = useMemo(() => {
        const months = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']
        return `${months[currentTime.getMonth()]} ${currentTime.getDate()}, ${currentTime.getFullYear()}`
    }, [currentTime])

    const formattedCurrentTime = useMemo(() => {
        return currentTime.toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit', second: '2-digit' })
    }, [currentTime])

    // Check if market is open (simplified - weekdays 9:30 AM - 4:00 PM EST)
    const isMarketOpen = useMemo(() => {
        const day = currentTime.getDay()
        const hours = currentTime.getHours()
        // Weekend check
        if (day === 0 || day === 6) return false
        // Simple hours check (this is simplified, not accounting for timezone)
        if (hours >= 9 && hours < 16) return true
        return false
    }, [currentTime])

    // Update live price from quote prop (no interval - parent handles polling)
    useEffect(() => {
        if (!symbol) return
        
        // Update live price from quote prop
        if (quote?.price) {
            setLivePrice(quote.price)
            setLastUpdateTime(new Date())
        }
    }, [symbol, quote])

    // Handle period change
    const handlePeriodChange = (newPeriod) => {
        setSelectedPeriod(newPeriod)
        if (onPeriodChange) {
            onPeriodChange(newPeriod)
        }
    }

    // Format date for display (equal interval labels)
    const formatDateLabel = useCallback((dateStr, index, total) => {
        if (!dateStr) return ''
        const hasTime = dateStr.includes(':')
        
        if (hasTime) {
            // Intraday - show date and time
            const parts = dateStr.split(' ')
            const datePart = parts[0]?.split('-') || []
            const timePart = parts[1] || ''
            // Show MM/DD HH:MM format
            if (datePart.length >= 3) {
                return `${datePart[1]}/${datePart[2]} ${timePart}`
            }
            return timePart || dateStr
        } else {
            // Daily - show MM/DD format
            const parts = dateStr.split('-')
            if (parts.length >= 3) {
                return `${parts[1]}/${parts[2]}`
            }
            return dateStr
        }
    }, [])

    // Get today's date for reference
    const today = useMemo(() => getCurrentDate(), [])
    const todayFormatted = useMemo(() => {
        const parts = today.split('-')
        return `${parts[1]}/${parts[2]}`
    }, [today])

    // Prepare chart data with proper distribution showing more historical context
    // Now includes live price updates for rolling chart behavior
    const { chartData, dividerIndex, todayIndex } = useMemo(() => {
        if (!historical || historical.length === 0) return { chartData: [], dividerIndex: 0, todayIndex: -1 }

        const predCount = predictions?.length || 0
        
        // Show more historical data points for better visualization
        // Use at least 30 points or 3x the prediction count for good chart detail
        const minHistoricalPoints = Math.max(30, predCount * 3)
        const historicalPoints = Math.min(historical.length, minHistoricalPoints)
        
        let recentHistorical = historical.slice(-historicalPoints).map((item, index) => {
            const dateStr = item.timestamp
            const dateOnly = dateStr.split(' ')[0]
            const isToday = dateOnly === today
            
            return {
                date: item.timestamp,
                displayDate: formatDateLabel(item.timestamp, index, historicalPoints),
                price: item.close,
                open: item.open,
                high: item.high,
                low: item.low,
                close: item.close,
                volume: item.volume,
                type: 'historical',
                isToday,
                index
            }
        })

        // Find today's index in historical data
        let todayIdx = recentHistorical.findIndex(d => d.isToday)

        // Update the last candle with live price if available (rolling update)
        if (livePrice && recentHistorical.length > 0) {
            const lastIdx = recentHistorical.length - 1
            const lastCandle = { ...recentHistorical[lastIdx] }
            
            // Update OHLC for live candle
            lastCandle.close = livePrice
            lastCandle.price = livePrice
            if (livePrice > lastCandle.high) lastCandle.high = livePrice
            if (livePrice < lastCandle.low) lastCandle.low = livePrice
            lastCandle.isLive = true
            
            recentHistorical[lastIdx] = lastCandle
        }

        if (!showPredictions || predCount === 0 || !predictions) {
            return { chartData: recentHistorical, dividerIndex: recentHistorical.length, todayIndex: todayIdx }
        }

        const predictionData = predictions.map((price, index) => {
            const predDate = dates?.[index] || `Day ${index + 1}`
            return {
                date: predDate,
                displayDate: formatDateLabel(predDate, index, predCount),
                price: null,
                predictedPrice: Math.round(price * 100) / 100,
                lstm: individual?.lstm?.values?.[index] ? Math.round(individual.lstm.values[index] * 100) / 100 : null,
                xgboost: individual?.xgboost?.values?.[index] ? Math.round(individual.xgboost.values[index] * 100) / 100 : null,
                prophet: individual?.prophet?.values?.[index] ? Math.round(individual.prophet.values[index] * 100) / 100 : null,
                type: 'prediction',
                index: recentHistorical.length + index + 1
            }
        })

        const lastHistorical = recentHistorical[recentHistorical.length - 1]
        if (!lastHistorical) return { chartData: recentHistorical, dividerIndex: recentHistorical.length, todayIndex: todayIdx }

        // Transition point - connects historical to prediction
        const transitionPoint = {
            ...lastHistorical,
            predictedPrice: lastHistorical.price,
            type: 'transition'
        }

        return {
            chartData: [...recentHistorical, transitionPoint, ...predictionData],
            dividerIndex: recentHistorical.length,
            todayIndex: todayIdx
        }
    }, [historical, predictions, individual, dates, formatDateLabel, showPredictions, livePrice, today])

    // Calculate price range for Y axis
    const { minPrice, maxPrice, isPositive, yScale } = useMemo(() => {
        if (!chartData.length) return { minPrice: 0, maxPrice: 100, isPositive: true, yScale: () => 0 }
        
        const prices = chartData.flatMap(d => [
            d.price, d.predictedPrice, d.high, d.low, d.open, d.close
        ]).filter(p => p !== null && p !== undefined && !isNaN(p))
        
        if (prices.length === 0) return { minPrice: 0, maxPrice: 100, isPositive: true, yScale: () => 0 }
        
        const dataMin = Math.min(...prices)
        const dataMax = Math.max(...prices)
        
        // Calculate padding based on price range to show better variations
        // Use at least 1% padding, but increase for small price ranges
        const range = dataMax - dataMin
        const padding = Math.max(range * 0.1, dataMin * 0.02) // 10% of range or 2% of price
        
        const min = dataMin - padding
        const max = dataMax + padding
        
        const firstPrice = chartData[0]?.price
        const lastPrice = chartData[chartData.length - 1]?.price || chartData[chartData.length - 1]?.predictedPrice
        
        // Y Scale function for candlestick positioning (chart height = 340px)
        const chartHeight = 340
        const yScaleFunc = (value) => {
            return 20 + ((max - value) / (max - min)) * chartHeight
        }
        
        return {
            minPrice: min,
            maxPrice: max,
            isPositive: lastPrice >= firstPrice,
            yScale: yScaleFunc
        }
    }, [chartData])

    // Custom Tooltip
    const CustomTooltip = ({ active, payload }) => {
        if (active && payload && payload.length) {
            const data = payload[0].payload
            const isPrediction = data.type === 'prediction'
            const price = data.price || data.predictedPrice
            const isCurrentDay = data.isToday
            
            // Format the date nicely
            const formatTooltipDate = (dateStr) => {
                if (!dateStr) return ''
                const parts = dateStr.split(' ')
                const dateParts = parts[0]?.split('-')
                if (dateParts?.length >= 3) {
                    const months = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']
                    const month = months[parseInt(dateParts[1]) - 1] || dateParts[1]
                    const day = parseInt(dateParts[2])
                    const year = dateParts[0]
                    const time = parts[1] || ''
                    return `${month} ${day}, ${year}${time ? ` ${time}` : ''}`
                }
                return dateStr
            }

            return (
                <div className="bg-[#1a1a2e]/95 backdrop-blur-xl rounded-lg p-4 border border-white/10 shadow-2xl min-w-[220px]">
                    <div className="flex items-center justify-between mb-2">
                        <span className="text-xs text-gray-400">{formatTooltipDate(data.date)}</span>
                        {isPrediction && (
                            <span className="text-xs px-2 py-0.5 rounded bg-[#c8ff00]/20 text-[#c8ff00]">Forecast</span>
                        )}
                        {isCurrentDay && !isPrediction && (
                            <span className="text-xs px-2 py-0.5 rounded bg-blue-500/20 text-blue-400">Today</span>
                        )}
                    </div>
                    
                    <div className="text-2xl font-bold text-white mb-3">
                        ${formatPrice(price)}
                    </div>

                    {!isPrediction && data.open && (
                        <div className="grid grid-cols-2 gap-x-4 gap-y-1 text-xs border-t border-white/5 pt-2">
                            <div className="flex justify-between">
                                <span className="text-gray-500">Open</span>
                                <span className="text-gray-300">{formatPrice(data.open)}</span>
                            </div>
                            <div className="flex justify-between">
                                <span className="text-gray-500">High</span>
                                <span className="text-green-400">{formatPrice(data.high)}</span>
                            </div>
                            <div className="flex justify-between">
                                <span className="text-gray-500">Low</span>
                                <span className="text-red-400">{formatPrice(data.low)}</span>
                            </div>
                            <div className="flex justify-between">
                                <span className="text-gray-500">Volume</span>
                                <span className="text-gray-300">{formatNumber(data.volume)}</span>
                            </div>
                        </div>
                    )}

                    {isPrediction && individual && (
                        <div className="space-y-1 pt-2 border-t border-white/5">
                            <div className="flex justify-between text-xs">
                                <span className="text-[#c8ff00]">LSTM</span>
                                <span className="text-gray-300">{formatPrice(data.lstm)}</span>
                            </div>
                            <div className="flex justify-between text-xs">
                                <span className="text-green-400">XGBoost</span>
                                <span className="text-gray-300">{formatPrice(data.xgboost)}</span>
                            </div>
                            <div className="flex justify-between text-xs">
                                <span className="text-orange-400">Prophet</span>
                                <span className="text-gray-300">{formatPrice(data.prophet)}</span>
                            </div>
                        </div>
                    )}
                </div>
            )
        }
        return null
    }

    // Render the appropriate chart type
    const renderChart = () => {
        const chartMargin = { top: 20, right: 55, left: 10, bottom: 5 }
        
        // Calculate even interval for X-axis ticks
        const tickInterval = Math.max(1, Math.floor(chartData.length / 10))

        // Common axis configs
        const yAxisConfig = {
            domain: [minPrice, maxPrice],
            orientation: "right",
            stroke: "transparent",
            tick: { fill: 'rgba(255,255,255,0.5)', fontSize: 11 },
            tickLine: false,
            axisLine: false,
            tickFormatter: (value) => formatPrice(value),
            width: 50,
            tickCount: 6
        }

        const xAxisConfig = {
            dataKey: "displayDate",
            stroke: "transparent",
            tick: { fill: 'rgba(255,255,255,0.5)', fontSize: 10 },
            tickLine: false,
            axisLine: false,
            interval: tickInterval,
            height: 30
        }

        const gridConfig = {
            strokeDasharray: "3 3",
            stroke: "rgba(255,255,255,0.06)",
            horizontal: true,
            vertical: true
        }

        // Divider position for forecast section
        const dividerX = chartData[dividerIndex]?.displayDate

        switch (chartType) {
            case 'candle':
                return (
                    <ResponsiveContainer width="100%" height="100%">
                        <ComposedChart data={chartData} margin={chartMargin}>
                            <defs>
                                <linearGradient id="predGrad" x1="0" y1="0" x2="0" y2="1">
                                    <stop offset="0%" stopColor="#c8ff00" stopOpacity={0.25} />
                                    <stop offset="100%" stopColor="#c8ff00" stopOpacity={0} />
                                </linearGradient>
                            </defs>
                            <CartesianGrid {...gridConfig} />
                            <XAxis {...xAxisConfig} />
                            <YAxis {...yAxisConfig} />
                            <Tooltip content={<CustomTooltip />} />
                            
                            {/* Divider line */}
                            {showPredictions && dividerX && (
                                <ReferenceLine 
                                    x={dividerX} 
                                    stroke="rgba(200,255,0,0.5)" 
                                    strokeDasharray="5 5"
                                    label={{ value: '← History | Forecast →', fill: '#c8ff00', fontSize: 10, position: 'top' }}
                                />
                            )}
                            
                            {/* Candlesticks using custom Bar shape */}
                            <Bar
                                dataKey="high"
                                shape={(props) => <CandleShape {...props} yScale={yScale} />}
                                isAnimationActive={false}
                            />
                            
                            {/* Prediction area */}
                            {showPredictions && (
                                <Area
                                    type="monotone"
                                    dataKey="predictedPrice"
                                    stroke="#c8ff00"
                                    strokeWidth={2.5}
                                    strokeDasharray="6 4"
                                    fill="url(#predGrad)"
                                    dot={false}
                                    activeDot={{ r: 5, fill: '#c8ff00', stroke: '#fff', strokeWidth: 2 }}
                                    connectNulls
                                />
                            )}
                        </ComposedChart>
                    </ResponsiveContainer>
                )

            case 'mountain':
                return (
                    <ResponsiveContainer width="100%" height="100%">
                        <ComposedChart data={chartData} margin={chartMargin}>
                            <defs>
                                <linearGradient id="histGrad" x1="0" y1="0" x2="0" y2="1">
                                    <stop offset="0%" stopColor={isPositive ? "#22c55e" : "#ef4444"} stopOpacity={0.3} />
                                    <stop offset="100%" stopColor={isPositive ? "#22c55e" : "#ef4444"} stopOpacity={0} />
                                </linearGradient>
                                <linearGradient id="predGradMt" x1="0" y1="0" x2="0" y2="1">
                                    <stop offset="0%" stopColor="#c8ff00" stopOpacity={0.3} />
                                    <stop offset="100%" stopColor="#c8ff00" stopOpacity={0} />
                                </linearGradient>
                            </defs>
                            <CartesianGrid {...gridConfig} />
                            <XAxis {...xAxisConfig} />
                            <YAxis {...yAxisConfig} />
                            <Tooltip content={<CustomTooltip />} />
                            
                            {showPredictions && dividerX && (
                                <ReferenceLine x={dividerX} stroke="rgba(200,255,0,0.4)" strokeDasharray="5 5" />
                            )}
                            
                            <Area
                                type="monotone"
                                dataKey="price"
                                stroke={isPositive ? "#22c55e" : "#ef4444"}
                                strokeWidth={2}
                                fill="url(#histGrad)"
                                dot={false}
                                activeDot={{ r: 4, fill: isPositive ? "#22c55e" : "#ef4444", stroke: '#fff', strokeWidth: 2 }}
                            />
                            
                            {showPredictions && (
                                <Area
                                    type="monotone"
                                    dataKey="predictedPrice"
                                    stroke="#c8ff00"
                                    strokeWidth={2}
                                    strokeDasharray="6 4"
                                    fill="url(#predGradMt)"
                                    dot={false}
                                    activeDot={{ r: 4, fill: '#c8ff00', stroke: '#fff', strokeWidth: 2 }}
                                    connectNulls
                                />
                            )}
                        </ComposedChart>
                    </ResponsiveContainer>
                )

            case 'bar':
                return (
                    <ResponsiveContainer width="100%" height="100%">
                        <ComposedChart data={chartData} margin={chartMargin}>
                            <CartesianGrid {...gridConfig} />
                            <XAxis {...xAxisConfig} />
                            <YAxis {...yAxisConfig} />
                            <Tooltip content={<CustomTooltip />} />
                            
                            {showPredictions && dividerX && (
                                <ReferenceLine x={dividerX} stroke="rgba(200,255,0,0.4)" strokeDasharray="5 5" />
                            )}
                            
                            <Bar dataKey="price" radius={[2, 2, 0, 0]}>
                                {chartData.map((entry, index) => (
                                    <Cell 
                                        key={`cell-${index}`} 
                                        fill={entry.type === 'prediction' ? '#c8ff00' : (isPositive ? '#22c55e' : '#ef4444')}
                                        opacity={0.85}
                                    />
                                ))}
                            </Bar>
                            
                            {showPredictions && (
                                <Bar dataKey="predictedPrice" fill="#c8ff00" opacity={0.7} radius={[2, 2, 0, 0]} />
                            )}
                        </ComposedChart>
                    </ResponsiveContainer>
                )

            case 'line':
            default:
                return (
                    <ResponsiveContainer width="100%" height="100%">
                        <ComposedChart data={chartData} margin={chartMargin}>
                            <CartesianGrid {...gridConfig} />
                            <XAxis {...xAxisConfig} />
                            <YAxis {...yAxisConfig} />
                            <Tooltip content={<CustomTooltip />} />
                            
                            {/* Divider line between historical and prediction */}
                            {showPredictions && dividerX && (
                                <ReferenceLine 
                                    x={dividerX} 
                                    stroke="rgba(200,255,0,0.4)" 
                                    strokeDasharray="5 5"
                                />
                            )}
                            
                            {/* Historical line */}
                            <Line
                                type="monotone"
                                dataKey="price"
                                stroke={isPositive ? "#22c55e" : "#ef4444"}
                                strokeWidth={2.5}
                                dot={false}
                                activeDot={{ r: 5, fill: isPositive ? "#22c55e" : "#ef4444", stroke: '#fff', strokeWidth: 2 }}
                            />
                            
                            {/* Prediction line */}
                            {showPredictions && (
                                <Line
                                    type="monotone"
                                    dataKey="predictedPrice"
                                    stroke="#c8ff00"
                                    strokeWidth={2.5}
                                    strokeDasharray="8 4"
                                    dot={false}
                                    activeDot={{ r: 5, fill: '#c8ff00', stroke: '#fff', strokeWidth: 2 }}
                                    connectNulls
                                />
                            )}
                        </ComposedChart>
                    </ResponsiveContainer>
                )
        }
    }

    // Stats data from quote
    const statsData = useMemo(() => {
        if (!quote) return null
        return {
            previousClose: quote.prev_close,
            open: quote.open,
            bid: quote.bid || '-',
            ask: quote.ask || '-',
            dayRange: quote.low && quote.high ? `${formatPrice(quote.low)} - ${formatPrice(quote.high)}` : '-',
            weekRange52: quote.fifty_two_week_low && quote.fifty_two_week_high 
                ? `${formatPrice(quote.fifty_two_week_low)} - ${formatPrice(quote.fifty_two_week_high)}` 
                : '-',
            volume: quote.volume,
            avgVolume: quote.avg_volume || quote.average_volume,
            marketCap: quote.market_cap,
            beta: quote.beta,
            peRatio: quote.pe_ratio || quote.trailing_pe,
            eps: quote.eps || quote.trailing_eps,
            earningsDate: quote.earnings_date || '-',
            dividend: quote.dividend_yield ? `${(quote.dividend_yield * 100).toFixed(2)}%` : '-',
            exDividend: quote.ex_dividend_date || '-',
            targetEst: quote.target_mean_price || quote.analyst_target_price
        }
    }, [quote])

    if (!chartData.length) {
        return (
            <div className={`rounded-xl p-8 h-[500px] flex items-center justify-center border ${
                isLight ? 'bg-white border-slate-200' : 'bg-[#0d0d15] border-white/5'
            }`}>
                <div className={`text-center ${isLight ? 'text-slate-400' : 'text-gray-500'}`}>
                    <div className="text-5xl mb-4">📈</div>
                    <p className="text-lg">Select an asset to view the chart</p>
                </div>
            </div>
        )
    }

    return (
        <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            className={`rounded-xl border overflow-hidden ${
                isLight ? 'bg-white border-slate-200' : 'bg-[#0d0d15] border-white/5'
            }`}
        >
            {/* Chart Controls Bar */}
            <div className="flex items-center justify-between px-4 py-3 border-b border-white/5">
                {/* Time Period Selector */}
                <div className="flex items-center gap-1 bg-white/5 rounded-lg p-1">
                    {TIME_PERIODS.map((tp) => (
                        <button
                            key={tp.value}
                            onClick={() => handlePeriodChange(tp.value)}
                            className={`px-3 py-1.5 text-xs font-medium rounded-md transition-all ${
                                selectedPeriod === tp.value
                                    ? 'bg-[#00d4aa] text-black'
                                    : 'text-gray-400 hover:text-white hover:bg-white/10'
                            }`}
                        >
                            {tp.label}
                        </button>
                    ))}
                </div>

                {/* Right Controls */}
                <div className="flex items-center gap-3">
                    {/* Key Events Toggle */}
                    <button
                        onClick={() => setKeyEvents(!keyEvents)}
                        className={`flex items-center gap-2 px-3 py-1.5 rounded-lg text-xs font-medium transition-all ${
                            keyEvents
                                ? 'bg-white/10 text-white'
                                : 'text-gray-500 hover:text-white'
                        }`}
                    >
                        <div className={`w-2 h-2 rounded-full ${keyEvents ? 'bg-[#00d4aa]' : 'bg-gray-600'}`} />
                        Key Events
                    </button>

                    {/* Predictions Toggle */}
                    <button
                        onClick={() => setShowPredictions(!showPredictions)}
                        className={`flex items-center gap-2 px-3 py-1.5 rounded-lg text-xs font-medium transition-all ${
                            showPredictions
                                ? 'bg-[#c8ff00]/20 text-[#c8ff00]'
                                : 'text-gray-500 hover:text-white'
                        }`}
                    >
                        <div className={`w-2 h-2 rounded-full ${showPredictions ? 'bg-[#c8ff00]' : 'bg-gray-600'}`} />
                        Predictions
                    </button>

                    {/* Chart Type Dropdown */}
                    <div className="relative">
                        <button
                            onClick={() => setShowChartMenu(!showChartMenu)}
                            className="flex items-center gap-2 px-3 py-1.5 rounded-lg bg-white/5 hover:bg-white/10 transition-colors"
                        >
                            <span className="text-[#00d4aa] text-xs font-medium capitalize">{chartType}</span>
                            <ChevronDown className={`w-4 h-4 text-gray-400 transition-transform ${showChartMenu ? 'rotate-180' : ''}`} />
                        </button>

                        <AnimatePresence>
                            {showChartMenu && (
                                <motion.div
                                    initial={{ opacity: 0, y: -10 }}
                                    animate={{ opacity: 1, y: 0 }}
                                    exit={{ opacity: 0, y: -10 }}
                                    className="absolute right-0 top-full mt-1 bg-[#1a1a2e] rounded-lg border border-white/10 shadow-xl z-50 overflow-hidden min-w-[140px]"
                                >
                                    {CHART_TYPES.map((type) => (
                                        <button
                                            key={type.value}
                                            onClick={() => {
                                                setChartType(type.value)
                                                setShowChartMenu(false)
                                            }}
                                            className={`w-full flex items-center gap-3 px-4 py-2.5 text-sm transition-colors ${
                                                chartType === type.value
                                                    ? 'bg-[#00d4aa]/10 text-[#00d4aa]'
                                                    : 'text-gray-300 hover:bg-white/5'
                                            }`}
                                        >
                                            {chartType === type.value && (
                                                <span className="text-[#00d4aa]">✓</span>
                                            )}
                                            <span className={chartType !== type.value ? 'ml-6' : ''}>{type.label}</span>
                                        </button>
                                    ))}
                                </motion.div>
                            )}
                        </AnimatePresence>
                    </div>

                    {/* Advanced Chart Button */}
                    <button 
                        onClick={() => {
                            if (onAdvancedChart) {
                                onAdvancedChart()
                            } else {
                                setShowAdvancedModal(true)
                            }
                        }}
                        className="flex items-center gap-2 px-3 py-1.5 rounded-lg text-gray-400 hover:text-white hover:bg-white/5 transition-colors"
                    >
                        <Settings className="w-4 h-4" />
                        <span className="text-xs font-medium">Advanced Chart</span>
                    </button>
                </div>
            </div>

            {/* Current Date/Time Bar */}
            <div className="flex items-center justify-between px-4 py-2 border-b border-white/5 bg-[#c8ff00]/5">
                <div className="flex items-center gap-4">
                    <div className="flex items-center gap-2">
                        <Calendar className="w-4 h-4 text-[#c8ff00]" />
                        <span className="text-sm font-bold text-[#c8ff00]">{formattedCurrentDate}</span>
                    </div>
                    <span className="text-sm text-white font-mono">{formattedCurrentTime}</span>
                </div>
                <div className="flex items-center gap-2">
                    <div className={`w-2 h-2 rounded-full ${isMarketOpen ? 'bg-green-500 animate-pulse' : 'bg-red-500'}`} />
                    <span className={`text-xs font-medium ${isMarketOpen ? 'text-green-400' : 'text-red-400'}`}>
                        {isMarketOpen ? 'Market Open' : 'Market Closed'}
                    </span>
                </div>
            </div>

            {/* Chart Area - Equal Split Indicator */}
            <div className="relative">
                {/* Section Labels */}
                <div className="absolute top-2 left-0 right-0 flex justify-between items-center px-16 z-10 pointer-events-none">
                    <span className="text-[10px] text-gray-500 uppercase tracking-wider">Historical Data (Last Trading Day)</span>
                    {showPredictions && (
                        <span className="text-[10px] text-[#c8ff00] uppercase tracking-wider">AI Prediction →</span>
                    )}
                </div>
                <div className="h-[380px] px-2 py-4">
                    {renderChart()}
                </div>
            </div>

            {/* Advanced Chart Modal */}
            <AnimatePresence>
                {showAdvancedModal && (
                    <motion.div
                        initial={{ opacity: 0 }}
                        animate={{ opacity: 1 }}
                        exit={{ opacity: 0 }}
                        className="fixed inset-0 bg-black/80 flex items-center justify-center z-50 p-4"
                        onClick={() => setShowAdvancedModal(false)}
                    >
                        <motion.div
                            initial={{ scale: 0.9, opacity: 0 }}
                            animate={{ scale: 1, opacity: 1 }}
                            exit={{ scale: 0.9, opacity: 0 }}
                            className="bg-[#1a1a2e] rounded-2xl p-6 max-w-md w-full border border-white/10"
                            onClick={e => e.stopPropagation()}
                        >
                            <h3 className="text-xl font-bold text-white mb-4 flex items-center gap-2">
                                <Settings className="w-5 h-5 text-[#c8ff00]" />
                                Advanced Chart Settings
                            </h3>
                            
                            <div className="space-y-4">
                                <div className="p-4 bg-white/5 rounded-xl">
                                    <h4 className="text-white font-medium mb-2">Technical Indicators</h4>
                                    <div className="grid grid-cols-2 gap-2">
                                        {['RSI', 'MACD', 'Bollinger', 'SMA', 'EMA', 'Volume'].map(ind => (
                                            <label key={ind} className="flex items-center gap-2 text-sm text-gray-300">
                                                <input type="checkbox" className="rounded bg-white/10 border-white/20" />
                                                {ind}
                                            </label>
                                        ))}
                                    </div>
                                </div>
                                
                                <div className="p-4 bg-white/5 rounded-xl">
                                    <h4 className="text-white font-medium mb-2">Drawing Tools</h4>
                                    <p className="text-gray-400 text-sm">Trendlines, Fibonacci, Support/Resistance</p>
                                    <span className="inline-block mt-2 text-xs px-2 py-1 bg-[#c8ff00]/20 text-[#c8ff00] rounded">Coming Soon</span>
                                </div>
                                
                                <div className="p-4 bg-white/5 rounded-xl">
                                    <h4 className="text-white font-medium mb-2">Comparison</h4>
                                    <p className="text-gray-400 text-sm">Compare with other assets or indices</p>
                                    <span className="inline-block mt-2 text-xs px-2 py-1 bg-[#c8ff00]/20 text-[#c8ff00] rounded">Coming Soon</span>
                                </div>
                            </div>
                            
                            <div className="mt-6 flex justify-end">
                                <button 
                                    onClick={() => setShowAdvancedModal(false)}
                                    className="px-4 py-2 bg-[#c8ff00] hover:bg-[#d4ff33] text-black rounded-lg transition-colors"
                                >
                                    Close
                                </button>
                            </div>
                        </motion.div>
                    </motion.div>
                )}
            </AnimatePresence>

            {/* Stats Grid - Yahoo Finance Style */}
            {statsData && (
                <div className="grid grid-cols-2 md:grid-cols-4 gap-x-6 gap-y-3 px-6 py-4 border-t border-white/5 text-sm">
                    {/* Column 1 */}
                    <div className="space-y-2">
                        <div className="flex justify-between">
                            <span className="text-gray-500">Previous Close</span>
                            <span className="text-white font-medium">{formatPrice(statsData.previousClose)}</span>
                        </div>
                        <div className="flex justify-between">
                            <span className="text-gray-500">Open</span>
                            <span className="text-white font-medium">{formatPrice(statsData.open)}</span>
                        </div>
                        <div className="flex justify-between">
                            <span className="text-gray-500">Bid</span>
                            <span className="text-gray-400">{statsData.bid}</span>
                        </div>
                        <div className="flex justify-between">
                            <span className="text-gray-500">Ask</span>
                            <span className="text-gray-400">{statsData.ask}</span>
                        </div>
                    </div>

                    {/* Column 2 */}
                    <div className="space-y-2">
                        <div className="flex justify-between">
                            <span className="text-gray-500">Day's Range</span>
                            <span className="text-white font-medium">{statsData.dayRange}</span>
                        </div>
                        <div className="flex justify-between">
                            <span className="text-gray-500">52 Week Range</span>
                            <span className="text-white font-medium">{statsData.weekRange52}</span>
                        </div>
                        <div className="flex justify-between">
                            <span className="text-gray-500">Volume</span>
                            <span className="text-white font-medium">{formatNumber(statsData.volume)}</span>
                        </div>
                        <div className="flex justify-between">
                            <span className="text-gray-500">Avg. Volume</span>
                            <span className="text-white font-medium">{formatNumber(statsData.avgVolume)}</span>
                        </div>
                    </div>

                    {/* Column 3 */}
                    <div className="space-y-2">
                        <div className="flex justify-between">
                            <span className="text-gray-500">Market Cap (intraday)</span>
                            <span className="text-white font-medium">{formatNumber(statsData.marketCap)}</span>
                        </div>
                        <div className="flex justify-between">
                            <span className="text-gray-500">Beta (5Y Monthly)</span>
                            <span className="text-white font-medium">{statsData.beta?.toFixed(2) || '-'}</span>
                        </div>
                        <div className="flex justify-between">
                            <span className="text-gray-500">PE Ratio (TTM)</span>
                            <span className="text-white font-medium">{statsData.peRatio?.toFixed(2) || '-'}</span>
                        </div>
                        <div className="flex justify-between">
                            <span className="text-gray-500">EPS (TTM)</span>
                            <span className="text-white font-medium">{statsData.eps?.toFixed(2) || '-'}</span>
                        </div>
                    </div>

                    {/* Column 4 */}
                    <div className="space-y-2">
                        <div className="flex justify-between">
                            <span className="text-gray-500">Earnings Date</span>
                            <span className="text-white font-medium">{statsData.earningsDate}</span>
                        </div>
                        <div className="flex justify-between">
                            <span className="text-gray-500">Forward Dividend & Yield</span>
                            <span className="text-white font-medium">{statsData.dividend}</span>
                        </div>
                        <div className="flex justify-between">
                            <span className="text-gray-500">Ex-Dividend Date</span>
                            <span className="text-white font-medium">{statsData.exDividend}</span>
                        </div>
                        <div className="flex justify-between">
                            <span className="text-gray-500">1y Target Est</span>
                            <span className="text-[#00d4aa] font-medium">{statsData.targetEst ? formatPrice(statsData.targetEst) : '-'}</span>
                        </div>
                    </div>
                </div>
            )}

            {/* Chart Legend & Local Currency Display */}
            <div className="flex items-center justify-between px-6 py-3 border-t border-white/5 bg-white/[0.02]">
                <div className="flex items-center gap-6">
                    <div className="flex items-center gap-2">
                        <div className={`w-8 h-0.5 ${isPositive ? 'bg-green-500' : 'bg-red-500'}`} />
                        <span className="text-xs text-gray-400">Historical Price</span>
                    </div>
                    {showPredictions && (
                        <div className="flex items-center gap-2">
                            <div className="w-8 h-0.5 bg-[#c8ff00]" style={{ backgroundImage: 'repeating-linear-gradient(90deg, #c8ff00, #c8ff00 4px, transparent 4px, transparent 8px)' }} />
                            <span className="text-xs text-gray-400">AI Prediction</span>
                        </div>
                    )}
                </div>
                
                {/* Local Currency Display */}
                {symbol && quote?.price && (() => {
                    const currencyInfo = getCurrencyForSymbol(symbol)
                    if (currencyInfo.currency !== 'USD') {
                        const localPrice = convertFromUSD(quote.price, currencyInfo.currency)
                        return (
                            <div className="flex items-center gap-3 px-3 py-1.5 bg-white/5 rounded-lg">
                                <span className="text-lg">{currencyInfo.flag}</span>
                                <div className="text-right">
                                    <div className="text-xs text-gray-500">Local Currency ({currencyInfo.currency})</div>
                                    <div className="text-sm font-semibold text-white">
                                        {formatPriceWithCurrency(localPrice, currencyInfo.currency)}
                                    </div>
                                </div>
                            </div>
                        )
                    }
                    return null
                })()}
                
                <button 
                    onClick={() => setShowAdvancedModal(true)}
                    className="flex items-center gap-1.5 text-xs text-gray-500 hover:text-[#c8ff00] transition-colors"
                >
                    <Zap className="w-3.5 h-3.5" />
                    AI Scanner
                </button>
            </div>
        </motion.div>
    )
}
