import { useMemo } from 'react'
import { motion } from 'framer-motion'
import { PieChart, Pie, Cell, ResponsiveContainer, Tooltip, Legend } from 'recharts'

const COLORS = {
    lstm: '#3b82f6',
    prophet: '#f97316',
    xgboost: '#00ff88',
    arima: '#c8ff00'
}

export default function ModelWeightsChart({ startAngle = 90, endAngle = -270, individual }) {

    if (!individual) return null

    const data = useMemo(() => [
        { name: 'LSTM', value: individual.lstm?.weight || 0.25, color: COLORS.lstm },
        { name: 'Prophet', value: individual.prophet?.weight || 0.25, color: COLORS.prophet },
        { name: 'XGBoost', value: individual.xgboost?.weight || 0.25, color: COLORS.xgboost },
        { name: 'ARIMA', value: individual.arima?.weight || 0.25, color: COLORS.arima }
    ], [individual])

    const totalWeight = data.reduce((sum, d) => sum + d.value, 0)

    const CustomTooltip = ({ active, payload }) => {
        if (active && payload && payload.length) {
            return (
                <div className="bg-[#0d0d18]/95 backdrop-blur-xl rounded-lg p-3 border border-[#c8ff00]/20 shadow-xl">
                    <p className="font-semibold text-sm mb-1" style={{ color: payload[0].payload.color }}>
                        {payload[0].name}
                    </p>
                    <p className="text-white text-lg font-bold">
                        {(payload[0].value * 100).toFixed(1)}%
                    </p>
                </div>
            )
        }
        return null
    }

    return (
        <motion.div
            initial={{ opacity: 0, x: -20 }}
            animate={{ opacity: 1, x: 0 }}
            className="bg-[#0d0d15] rounded-xl border border-[#c8ff00]/10 overflow-hidden h-[400px] flex flex-col"
        >
            {/* Header */}
            <div className="flex items-center justify-between px-4 py-3 border-b border-[#c8ff00]/10">
                <div className="flex items-center gap-3">
                    <span className="text-lg">🧠</span>
                    <h3 className="text-sm font-semibold text-white">Model Weights</h3>
                </div>
                <div className="px-2 py-0.5 rounded bg-[#c8ff00]/20 text-[#c8ff00] text-xs font-medium">
                    AI Optimized
                </div>
            </div>

            {/* Chart */}
            <div className="flex-1 min-h-0 px-4 py-2">
                <ResponsiveContainer width="100%" height="100%">
                    <PieChart>
                        <Pie
                            data={data}
                            cx="50%"
                            cy="45%"
                            innerRadius={55}
                            outerRadius={80}
                            paddingAngle={3}
                            dataKey="value"
                            startAngle={startAngle}
                            endAngle={endAngle}
                            stroke="none"
                        >
                            {data.map((entry, index) => (
                                <Cell 
                                    key={`cell-${index}`} 
                                    fill={entry.color} 
                                    stroke="rgba(0,0,0,0.3)"
                                    strokeWidth={2}
                                />
                            ))}
                        </Pie>
                        <Tooltip content={<CustomTooltip />} />
                    </PieChart>
                </ResponsiveContainer>
            </div>

            {/* Model Legend with percentages */}
            <div className="px-4 pb-3 grid grid-cols-2 gap-2">
                {data.map((model, index) => (
                    <div 
                        key={model.name}
                        className="flex items-center justify-between px-3 py-2 rounded-lg bg-white/[0.03] hover:bg-white/[0.05] transition-colors"
                    >
                        <div className="flex items-center gap-2">
                            <div 
                                className="w-2.5 h-2.5 rounded-full"
                                style={{ backgroundColor: model.color }}
                            />
                            <span className="text-xs text-gray-400">{model.name}</span>
                        </div>
                        <span className="text-xs font-semibold text-white">
                            {(model.value * 100).toFixed(0)}%
                        </span>
                    </div>
                ))}
            </div>

            {/* Footer */}
            <div className="px-4 py-2 border-t border-white/5 bg-white/[0.02]">
                <p className="text-xs text-gray-500 text-center">
                    Weights optimized based on recent accuracy
                </p>
            </div>
        </motion.div>
    )
}
