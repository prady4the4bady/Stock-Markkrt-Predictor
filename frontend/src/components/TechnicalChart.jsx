import { useState, useMemo } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import {
    LineChart, Line, AreaChart, Area, XAxis, YAxis, CartesianGrid,
    Tooltip, ResponsiveContainer, ReferenceLine, ComposedChart, Bar
} from 'recharts'

// Technical indicator tabs
const INDICATORS = [
    { id: 'RSI', name: 'RSI' },
    { id: 'MACD', name: 'MACD' },
    { id: 'Bollinger', name: 'BB' }
]

// Common axis props
const commonAxisProps = {
    xAxis: {
        dataKey: "displayDate",
        stroke: "transparent",
        tick: { fill: 'rgba(255,255,255,0.4)', fontSize: 11 },
        tickLine: false,
        axisLine: false,
        interval: 'preserveStartEnd'
    },
    yAxis: {
        stroke: "transparent",
        tick: { fill: 'rgba(255,255,255,0.4)', fontSize: 11 },
        tickLine: false,
        axisLine: false,
        width: 50,
        orientation: "right"
    }
}

const gridProps = {
    strokeDasharray: "1 1",
    stroke: "rgba(255,255,255,0.03)",
    horizontal: true,
    vertical: false
}

const tooltipStyle = {
    contentStyle: { 
        backgroundColor: 'rgba(13, 13, 21, 0.95)', 
        border: '1px solid rgba(255,255,255,0.1)',
        borderRadius: '8px',
        padding: '12px'
    },
    labelStyle: { color: '#9ca3af', marginBottom: '8px' }
}

export default function TechnicalChart({ data }) {
    const [activeTab, setActiveTab] = useState('RSI')

    if (!data || !data.dates) return null

    const chartData = useMemo(() => {
        return data.dates.map((date, i) => ({
            date,
            displayDate: date.slice(5),
            rsi: data.rsi[i],
            macd: data.macd[i],
            signal: data.macd_signal[i],
            histogram: data.macd[i] - data.macd_signal[i],
            upper: data.bb_upper[i],
            lower: data.bb_lower[i],
            middle: (data.bb_upper[i] + data.bb_lower[i]) / 2
        }))
    }, [data])

    const renderChart = () => {
        switch (activeTab) {
            case 'RSI':
                const lastRsi = chartData[chartData.length - 1]?.rsi
                const rsiStatus = lastRsi > 70 ? 'overbought' : lastRsi < 30 ? 'oversold' : 'neutral'
                
                return (
                    <div className="h-full relative">
                        {/* RSI Status Badge */}
                        <div className="absolute top-0 right-12 z-10">
                            <div className={`px-2 py-0.5 rounded text-xs font-medium ${
                                rsiStatus === 'overbought' ? 'bg-red-500/20 text-red-400' :
                                rsiStatus === 'oversold' ? 'bg-green-500/20 text-green-400' :
                                'bg-gray-500/20 text-gray-400'
                            }`}>
                                {lastRsi?.toFixed(1)} - {rsiStatus}
                            </div>
                        </div>
                        
                        <ResponsiveContainer width="100%" height="100%">
                            <AreaChart data={chartData} margin={{ top: 20, right: 50, left: 0, bottom: 0 }}>
                                <defs>
                                    <linearGradient id="rsiGradient" x1="0" y1="0" x2="0" y2="1">
                                        <stop offset="0%" stopColor="#c8ff00" stopOpacity={0.2} />
                                        <stop offset="100%" stopColor="#c8ff00" stopOpacity={0} />
                                    </linearGradient>
                                </defs>
                                
                                <CartesianGrid {...gridProps} />
                                <XAxis {...commonAxisProps.xAxis} />
                                <YAxis {...commonAxisProps.yAxis} domain={[0, 100]} />
                                <Tooltip {...tooltipStyle} />
                                
                                <ReferenceLine y={70} stroke="#ef4444" strokeDasharray="3 3" strokeOpacity={0.5} />
                                <ReferenceLine y={30} stroke="#22c55e" strokeDasharray="3 3" strokeOpacity={0.5} />
                                <ReferenceLine y={50} stroke="rgba(255,255,255,0.1)" />
                                
                                <Area 
                                    type="monotone" 
                                    dataKey="rsi" 
                                    stroke="#c8ff00" 
                                    strokeWidth={2} 
                                    fill="url(#rsiGradient)"
                                    dot={false}
                                    activeDot={{ r: 4, fill: '#c8ff00', stroke: '#fff', strokeWidth: 2 }}
                                />
                            </AreaChart>
                        </ResponsiveContainer>
                    </div>
                )
                
            case 'MACD':
                const lastMacd = chartData[chartData.length - 1]
                const macdSignal = lastMacd?.macd > lastMacd?.signal ? 'bullish' : 'bearish'
                
                return (
                    <div className="h-full relative">
                        <div className="absolute top-0 right-12 z-10">
                            <div className={`px-2 py-0.5 rounded text-xs font-medium ${
                                macdSignal === 'bullish' ? 'bg-green-500/20 text-green-400' : 'bg-red-500/20 text-red-400'
                            }`}>
                                {macdSignal}
                            </div>
                        </div>
                        
                        <ResponsiveContainer width="100%" height="100%">
                            <ComposedChart data={chartData} margin={{ top: 20, right: 50, left: 0, bottom: 0 }}>
                                <CartesianGrid {...gridProps} />
                                <XAxis {...commonAxisProps.xAxis} />
                                <YAxis {...commonAxisProps.yAxis} />
                                <Tooltip {...tooltipStyle} />
                                
                                <ReferenceLine y={0} stroke="rgba(255,255,255,0.1)" />
                                
                                <Bar 
                                    dataKey="histogram" 
                                    opacity={0.5}
                                    radius={[2, 2, 0, 0]}
                                />
                                
                                <Line type="monotone" dataKey="macd" stroke="#3b82f6" strokeWidth={2} dot={false} />
                                <Line type="monotone" dataKey="signal" stroke="#f97316" strokeWidth={2} dot={false} />
                            </ComposedChart>
                        </ResponsiveContainer>
                    </div>
                )
                
            case 'Bollinger':
                return (
                    <div className="h-full relative">
                        <div className="absolute top-0 right-12 z-10">
                            <div className="px-2 py-0.5 rounded text-xs font-medium bg-[#c8ff00]/20 text-[#c8ff00]">
                                Volatility Bands
                            </div>
                        </div>
                        
                        <ResponsiveContainer width="100%" height="100%">
                            <AreaChart data={chartData} margin={{ top: 20, right: 50, left: 0, bottom: 0 }}>
                                <defs>
                                    <linearGradient id="bbGradient" x1="0" y1="0" x2="0" y2="1">
                                        <stop offset="0%" stopColor="#06b6d4" stopOpacity={0.1} />
                                        <stop offset="50%" stopColor="#06b6d4" stopOpacity={0.05} />
                                        <stop offset="100%" stopColor="#06b6d4" stopOpacity={0.1} />
                                    </linearGradient>
                                </defs>
                                
                                <CartesianGrid {...gridProps} />
                                <XAxis {...commonAxisProps.xAxis} />
                                <YAxis {...commonAxisProps.yAxis} domain={['auto', 'auto']} />
                                <Tooltip {...tooltipStyle} />
                                
                                <Area 
                                    type="monotone" 
                                    dataKey="upper" 
                                    stroke="#06b6d4" 
                                    strokeWidth={1} 
                                    strokeDasharray="3 3"
                                    fill="url(#bbGradient)"
                                    dot={false}
                                />
                                
                                <Line 
                                    type="monotone" 
                                    dataKey="middle" 
                                    stroke="#06b6d4" 
                                    strokeWidth={2} 
                                    dot={false}
                                />
                                
                                <Line 
                                    type="monotone" 
                                    dataKey="lower" 
                                    stroke="#06b6d4" 
                                    strokeWidth={1} 
                                    strokeDasharray="3 3"
                                    dot={false}
                                />
                            </AreaChart>
                        </ResponsiveContainer>
                    </div>
                )
                
            default:
                return null
        }
    }

    return (
        <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            className="bg-[#0d0d15] rounded-xl border border-white/5 overflow-hidden h-[400px]"
        >
            {/* Header with tabs */}
            <div className="flex items-center justify-between px-4 py-3 border-b border-white/5">
                <div className="flex items-center gap-3">
                    <span className="text-lg">📉</span>
                    <h3 className="text-sm font-semibold text-white">Technical Analysis</h3>
                </div>
                
                {/* Indicator Tabs */}
                <div className="flex items-center gap-1 bg-white/5 rounded-lg p-1">
                    {INDICATORS.map((indicator) => (
                        <button
                            key={indicator.id}
                            onClick={() => setActiveTab(indicator.id)}
                            className={`px-3 py-1.5 text-xs font-medium rounded-md transition-all ${
                                activeTab === indicator.id
                                    ? 'bg-[#00d4aa] text-black'
                                    : 'text-gray-400 hover:text-white hover:bg-white/10'
                            }`}
                        >
                            {indicator.name}
                        </button>
                    ))}
                </div>
            </div>

            {/* Chart Area */}
            <div className="h-[320px] px-4 py-2">
                {renderChart()}
            </div>
            
            {/* Legend */}
            <div className="flex items-center justify-center gap-6 px-4 py-2 border-t border-white/5 bg-white/[0.02]">
                {activeTab === 'RSI' && (
                    <>
                        <div className="flex items-center gap-2">
                            <div className="w-3 h-0.5 bg-red-500" />
                            <span className="text-xs text-gray-500">Overbought (70)</span>
                        </div>
                        <div className="flex items-center gap-2">
                            <div className="w-3 h-0.5 bg-green-500" />
                            <span className="text-xs text-gray-500">Oversold (30)</span>
                        </div>
                    </>
                )}
                {activeTab === 'MACD' && (
                    <>
                        <div className="flex items-center gap-2">
                            <div className="w-6 h-0.5 bg-blue-500" />
                            <span className="text-xs text-gray-500">MACD</span>
                        </div>
                        <div className="flex items-center gap-2">
                            <div className="w-6 h-0.5 bg-orange-500" />
                            <span className="text-xs text-gray-500">Signal</span>
                        </div>
                    </>
                )}
                {activeTab === 'Bollinger' && (
                    <>
                        <div className="flex items-center gap-2">
                            <div className="w-6 h-0.5 bg-[#c8ff00]" />
                            <span className="text-xs text-gray-500">SMA</span>
                        </div>
                        <div className="flex items-center gap-2">
                            <div className="w-6 h-0.5 bg-[#c8ff00] opacity-50" />
                            <span className="text-xs text-gray-500">Bands</span>
                        </div>
                    </>
                )}
            </div>
        </motion.div>
    )
}
