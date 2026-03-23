import { motion } from 'framer-motion'
import CountUp from './CountUp'
import { TrendingUp, TrendingDown } from 'lucide-react'
import { useTheme } from '../context/ThemeContext'

const colorMapDark = {
    lime: {
        bg: 'bg-[#c8ff00]/5',
        border: 'border-[#c8ff00]/20',
        icon: 'text-[#c8ff00] bg-[#c8ff00]/10',
        accent: '#c8ff00'
    },
    cyan: {
        bg: 'bg-[#00f5ff]/5',
        border: 'border-[#00f5ff]/20',
        icon: 'text-[#00f5ff] bg-[#00f5ff]/10',
        accent: '#00f5ff'
    },
    purple: {
        bg: 'bg-purple-500/5',
        border: 'border-purple-500/20',
        icon: 'text-purple-400 bg-purple-500/10',
        accent: '#8b5cf6'
    },
    green: {
        bg: 'bg-[#00ff88]/5',
        border: 'border-[#00ff88]/20',
        icon: 'text-[#00ff88] bg-[#00ff88]/10',
        accent: '#00ff88'
    },
    red: {
        bg: 'bg-red-500/5',
        border: 'border-red-500/20',
        icon: 'text-red-400 bg-red-500/10',
        accent: '#ef4444'
    },
    yellow: {
        bg: 'bg-yellow-500/5',
        border: 'border-yellow-500/20',
        icon: 'text-yellow-400 bg-yellow-500/10',
        accent: '#eab308'
    }
}

const colorMapLight = {
    lime: {
        bg: 'bg-[#7cb800]/5',
        border: 'border-[#7cb800]/20',
        icon: 'text-[#7cb800] bg-[#7cb800]/10',
        accent: '#7cb800'
    },
    cyan: {
        bg: 'bg-cyan-500/5',
        border: 'border-cyan-500/20',
        icon: 'text-cyan-600 bg-cyan-500/10',
        accent: '#0891b2'
    },
    purple: {
        bg: 'bg-purple-500/5',
        border: 'border-purple-500/20',
        icon: 'text-purple-600 bg-purple-500/10',
        accent: '#7c3aed'
    },
    green: {
        bg: 'bg-emerald-500/5',
        border: 'border-emerald-500/20',
        icon: 'text-emerald-600 bg-emerald-500/10',
        accent: '#059669'
    },
    red: {
        bg: 'bg-red-500/5',
        border: 'border-red-500/20',
        icon: 'text-red-600 bg-red-500/10',
        accent: '#dc2626'
    },
    yellow: {
        bg: 'bg-amber-500/5',
        border: 'border-amber-500/20',
        icon: 'text-amber-600 bg-amber-500/10',
        accent: '#d97706'
    }
}

export default function PredictionCard({ title, value, icon, color = 'lime', change, delay = 0, currencySymbol }) {
    const { isDark, isLight } = useTheme()
    const colorMap = isLight ? colorMapLight : colorMapDark
    const colors = colorMap[color] || colorMap.lime
    const isNegativeChange = change !== undefined && change < 0

    return (
        <motion.div
            initial={{ opacity: 0, y: 20, scale: 0.95 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            transition={{ delay, duration: 0.4, ease: "easeOut" }}
            whileHover={{ scale: 1.02, y: -2 }}
            className={`rounded-xl p-5 border ${colors.border} transition-all relative overflow-hidden ${
                isLight ? 'bg-white shadow-sm' : 'bg-[#0d0d15]'
            }`}
        >
            {/* Subtle gradient accent */}
            <div 
                className="absolute top-0 left-0 right-0 h-0.5"
                style={{ background: `linear-gradient(90deg, ${colors.accent}, transparent)` }}
            />
            
            <div className="flex items-start justify-between mb-3">
                <div className={`p-2 rounded-lg ${colors.icon}`}>
                    {icon}
                </div>
                {change !== undefined && (
                    <motion.div
                        initial={{ opacity: 0, x: 10 }}
                        animate={{ opacity: 1, x: 0 }}
                        transition={{ delay: delay + 0.3 }}
                        className={`flex items-center gap-1 text-xs font-medium px-2 py-1 rounded-md ${
                            isNegativeChange
                                ? 'text-red-400 bg-red-500/10'
                                : 'text-green-400 bg-green-500/10'
                        }`}
                    >
                        {isNegativeChange ? (
                            <TrendingDown className="w-3 h-3" />
                        ) : (
                            <TrendingUp className="w-3 h-3" />
                        )}
                        {isNegativeChange ? '' : '+'}{change?.toFixed(2)}%
                    </motion.div>
                )}
            </div>

            <p className={`text-xs mb-1 uppercase tracking-wider ${isLight ? 'text-slate-500' : 'text-gray-500'}`}>{title}</p>

            <motion.div
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                transition={{ delay: delay + 0.2 }}
                className="text-2xl font-bold"
            >
                {typeof value === 'string' && value.startsWith('$') ? (
                    <span className={isLight ? 'text-slate-900' : 'text-white'}>
                        <CountUp
                            value={parseFloat(value.replace(/[$,]/g, ''))}
                            prefix={currencySymbol || '$'}
                            decimals={2}
                            duration={1.5}
                        />
                    </span>
                ) : typeof value === 'string' && value.endsWith('%') ? (
                    <span className={isLight ? 'text-slate-900' : 'text-white'}>
                        <CountUp
                            value={parseFloat(value.replace('%', ''))}
                            suffix="%"
                            decimals={1}
                            duration={1.5}
                        />
                    </span>
                ) : (
                    <span className={`font-bold ${
                        value === 'BUY' ? (isLight ? 'text-emerald-600' : 'text-green-400') :
                        value === 'SELL' ? (isLight ? 'text-red-600' : 'text-red-400') :
                        value === 'HOLD' ? (isLight ? 'text-amber-600' : 'text-yellow-400') : 
                        (isLight ? 'text-slate-900' : 'text-white')
                    }`}>
                        {value}
                    </span>
                )}
            </motion.div>
        </motion.div>
    )
}
