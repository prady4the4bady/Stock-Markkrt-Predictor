import { motion } from 'framer-motion'
import { 
    TrendingUp, TrendingDown, Activity, BarChart3, 
    Target, Gauge, AlertTriangle, CheckCircle2,
    ArrowUpRight, ArrowDownRight, Minus
} from 'lucide-react'
import { useTheme } from '../context/ThemeContext'

const regimeColors = {
    'trending_bullish': { bg: 'bg-green-500/10', text: 'text-green-400', border: 'border-green-500/30' },
    'trending_bearish': { bg: 'bg-red-500/10', text: 'text-red-400', border: 'border-red-500/30' },
    'mean_reverting': { bg: 'bg-blue-500/10', text: 'text-blue-400', border: 'border-blue-500/30' },
    'high_volatility': { bg: 'bg-orange-500/10', text: 'text-orange-400', border: 'border-orange-500/30' },
    'neutral': { bg: 'bg-gray-500/10', text: 'text-gray-400', border: 'border-gray-500/30' }
}

const alignmentColors = {
    'strongly_bullish': { bg: 'bg-green-500/20', text: 'text-green-300', icon: ArrowUpRight },
    'bullish': { bg: 'bg-green-500/10', text: 'text-green-400', icon: TrendingUp },
    'neutral': { bg: 'bg-gray-500/10', text: 'text-gray-400', icon: Minus },
    'bearish': { bg: 'bg-red-500/10', text: 'text-red-400', icon: TrendingDown },
    'strongly_bearish': { bg: 'bg-red-500/20', text: 'text-red-300', icon: ArrowDownRight }
}

export default function AdvancedAnalysis({ data }) {
    const { isDark, isLight, classes } = useTheme()
    
    if (!data) return null

    const { market_regime, timeframe_alignment, volatility_forecast, monte_carlo, confidence_breakdown } = data

    const regime = market_regime?.type || 'neutral'
    const regimeStyle = regimeColors[regime] || regimeColors.neutral
    const alignment = timeframe_alignment?.alignment || 'neutral'
    const alignmentStyle = alignmentColors[alignment] || alignmentColors.neutral
    const AlignmentIcon = alignmentStyle.icon

    return (
        <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.3 }}
            className={`rounded-xl border overflow-hidden ${
                isLight ? 'bg-white border-slate-200' : 'bg-[#0d0d15] border-white/5'
            }`}
        >
            {/* Header */}
            <div className={`px-4 py-3 border-b flex items-center justify-between ${
                isLight ? 'border-slate-200' : 'border-white/5'
            }`}>
                <div className="flex items-center gap-2">
                    <Activity className={`w-4 h-4 ${isLight ? 'text-[#7cb800]' : 'text-[#c8ff00]'}`} />
                    <span className={`text-sm font-semibold ${classes.textPrimary}`}>Advanced Analysis</span>
                </div>
                <span className={`text-xs ${classes.textMuted}`}>AI-Powered Insights</span>
            </div>

            <div className="p-4 space-y-4">
                {/* Market Regime & Timeframe Row */}
                <div className="grid grid-cols-2 gap-3">
                    {/* Market Regime */}
                    <div className={`p-3 rounded-lg border ${regimeStyle.border} ${regimeStyle.bg}`}>
                        <div className="flex items-center gap-2 mb-2">
                            <Gauge className={`w-4 h-4 ${regimeStyle.text}`} />
                            <span className={`text-xs ${classes.textMuted}`}>Market Regime</span>
                        </div>
                        <div className={`text-sm font-semibold ${regimeStyle.text} capitalize`}>
                            {regime.replace(/_/g, ' ')}
                        </div>
                        <div className={`text-xs mt-1 ${classes.textMuted}`}>
                            {market_regime?.confidence?.toFixed(0)}% confidence
                        </div>
                    </div>

                    {/* Timeframe Alignment */}
                    <div className={`p-3 rounded-lg border ${alignmentStyle.bg} ${
                        isLight ? 'border-slate-200' : 'border-white/10'
                    }`}>
                        <div className="flex items-center gap-2 mb-2">
                            <AlignmentIcon className={`w-4 h-4 ${alignmentStyle.text}`} />
                            <span className={`text-xs ${classes.textMuted}`}>Trend Alignment</span>
                        </div>
                        <div className={`text-sm font-semibold ${alignmentStyle.text} capitalize`}>
                            {alignment.replace(/_/g, ' ')}
                        </div>
                        <div className={`text-xs mt-1 ${classes.textMuted}`}>
                            Strength: {timeframe_alignment?.strength}%
                        </div>
                    </div>
                </div>

                {/* Monte Carlo Results */}
                {monte_carlo && (
                    <div className={`p-3 rounded-lg border ${
                        isLight ? 'bg-[#7cb800]/5 border-[#7cb800]/20' : 'bg-[#c8ff00]/5 border-[#c8ff00]/20'
                    }`}>
                        <div className="flex items-center gap-2 mb-3">
                            <Target className={`w-4 h-4 ${isLight ? 'text-[#7cb800]' : 'text-[#c8ff00]'}`} />
                            <span className={`text-xs ${classes.textMuted}`}>Monte Carlo Simulation</span>
                            <span className={`text-[10px] px-1.5 py-0.5 rounded ${
                                isLight ? 'text-[#7cb800] bg-[#7cb800]/10' : 'text-[#c8ff00] bg-[#c8ff00]/10'
                            }`}>
                                1000 Scenarios
                            </span>
                        </div>
                        
                        <div className="grid grid-cols-3 gap-3">
                            <div>
                                <div className={`text-xs mb-1 ${classes.textMuted}`}>Profit Probability</div>
                                <div className={`text-lg font-bold ${
                                    monte_carlo.probability_of_profit > 55 ? 'text-green-400' : 
                                    monte_carlo.probability_of_profit < 45 ? 'text-red-400' : (isLight ? 'text-slate-600' : 'text-gray-300')
                                }`}>
                                    {monte_carlo.probability_of_profit?.toFixed(1)}%
                                </div>
                            </div>
                            <div>
                                <div className="text-xs text-gray-500 mb-1">Expected Return</div>
                                <div className={`text-lg font-bold ${
                                    monte_carlo.expected_return > 0 ? 'text-green-400' : 'text-red-400'
                                }`}>
                                    {monte_carlo.expected_return > 0 ? '+' : ''}{monte_carlo.expected_return?.toFixed(2)}%
                                </div>
                            </div>
                            <div>
                                <div className="text-xs text-gray-500 mb-1">VaR (95%)</div>
                                <div className="text-lg font-bold text-red-400">
                                    {monte_carlo.value_at_risk_95?.toFixed(2)}%
                                </div>
                            </div>
                        </div>
                        
                        {/* Price Range */}
                        <div className="mt-3 pt-3 border-t border-white/5">
                            <div className="text-xs text-gray-500 mb-2">Price Forecast Range (95% CI)</div>
                            <div className="flex items-center justify-between">
                                <span className="text-sm text-red-400">
                                    ${monte_carlo.percentile_5?.toFixed(2)}
                                </span>
                                <div className="flex-1 mx-3 h-1.5 bg-white/5 rounded-full relative">
                                    <div 
                                        className="absolute inset-y-0 bg-gradient-to-r from-red-500 via-gray-400 to-green-500 rounded-full"
                                        style={{ left: '5%', right: '5%' }}
                                    />
                                    <div 
                                        className="absolute top-1/2 -translate-y-1/2 w-2 h-2 bg-[#c8ff00] rounded-full"
                                        style={{ left: '50%', transform: 'translate(-50%, -50%)' }}
                                    />
                                </div>
                                <span className="text-sm text-green-400">
                                    ${monte_carlo.percentile_95?.toFixed(2)}
                                </span>
                            </div>
                        </div>
                    </div>
                )}

                {/* Volatility Forecast */}
                {volatility_forecast && (
                    <div className="p-3 rounded-lg bg-white/5 border border-white/10">
                        <div className="flex items-center justify-between mb-2">
                            <div className="flex items-center gap-2">
                                <BarChart3 className="w-4 h-4 text-purple-400" />
                                <span className="text-xs text-gray-400">Volatility Analysis</span>
                            </div>
                            <span className={`text-xs px-2 py-0.5 rounded ${
                                volatility_forecast.regime === 'high' ? 'bg-orange-500/20 text-orange-400' :
                                volatility_forecast.regime === 'low' ? 'bg-blue-500/20 text-blue-400' :
                                'bg-gray-500/20 text-gray-400'
                            }`}>
                                {volatility_forecast.regime?.toUpperCase()} VOL
                            </span>
                        </div>
                        <div className="flex items-baseline gap-2">
                            <span className="text-xl font-bold text-white">
                                {(volatility_forecast.current * 100)?.toFixed(1)}%
                            </span>
                            <span className="text-xs text-gray-500">annualized</span>
                        </div>
                    </div>
                )}

                {/* Confidence Breakdown */}
                {confidence_breakdown && (
                    <div className="pt-3 border-t border-white/5">
                        <div className="text-xs text-gray-500 mb-2">Confidence Factors</div>
                        <div className="grid grid-cols-4 gap-2">
                            <div className="text-center">
                                <div className="text-xs text-gray-500 mb-1">Models</div>
                                <div className="text-sm font-medium text-white">
                                    {confidence_breakdown.model_average?.toFixed(0)}%
                                </div>
                            </div>
                            <div className="text-center">
                                <div className="text-xs text-gray-500 mb-1">Bayesian</div>
                                <div className="text-sm font-medium text-[#c8ff00]">
                                    {confidence_breakdown.bayesian_estimate?.toFixed(0)}%
                                </div>
                            </div>
                            <div className="text-center">
                                <div className="text-xs text-gray-500 mb-1">Regime</div>
                                <div className="text-sm font-medium text-purple-400">
                                    {confidence_breakdown.regime_factor?.toFixed(0)}%
                                </div>
                            </div>
                            <div className="text-center">
                                <div className="text-xs text-gray-500 mb-1">Alignment</div>
                                <div className="text-sm font-medium text-cyan-400">
                                    {confidence_breakdown.alignment_factor?.toFixed(0)}%
                                </div>
                            </div>
                        </div>
                    </div>
                )}
            </div>
        </motion.div>
    )
}
