import { useState, useEffect, useRef } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { getCurrencyForSymbol, convertToUSD, isNonUSD } from '../utils/currency'

// Formatters
const fmt = (n, d = 2) => n == null || isNaN(n) ? '0.00' : Number(n).toFixed(d)
const fmtVol = (v) => {
    if (!v) return '0'
    if (v >= 1e9) return (v / 1e9).toFixed(2) + 'B'
    if (v >= 1e6) return (v / 1e6).toFixed(2) + 'M'
    if (v >= 1e3) return (v / 1e3).toFixed(2) + 'K'
    return String(Math.round(v))
}

// Individual digit that rolls up or down
function RollingDigit({ digit, direction }) {
    return (
        <div className="relative h-[1.2em] w-[0.65em] overflow-hidden inline-flex justify-center">
            <AnimatePresence mode="popLayout" initial={false}>
                <motion.div
                    key={digit}
                    className="absolute inset-0 flex items-center justify-center"
                    initial={{ y: direction === 'up' ? '100%' : '-100%' }}
                    animate={{ y: '0%' }}
                    exit={{ y: direction === 'up' ? '-100%' : '100%' }}
                    transition={{ 
                        type: 'spring',
                        stiffness: 500,
                        damping: 35,
                        mass: 0.5
                    }}
                >
                    {digit}
                </motion.div>
            </AnimatePresence>
        </div>
    )
}

// Static character (not animated)
function StaticChar({ char }) {
    const width = char === '.' || char === ',' ? 'w-[0.35em]' : 'w-[0.65em]'
    return <span className={`inline-block text-center ${width}`}>{char}</span>
}

// Rolling number display with individual digit animations
function RollingPrice({ value, prefix = '$', decimals = 2 }) {
    const [chars, setChars] = useState([])
    const [direction, setDirection] = useState('up')
    const prevValue = useRef(null)
    const updateKey = useRef(0)

    useEffect(() => {
        if (value == null || isNaN(value)) return
        
        const numVal = Number(value)
        
        // Determine direction
        if (prevValue.current !== null && numVal !== prevValue.current) {
            setDirection(numVal > prevValue.current ? 'up' : 'down')
            updateKey.current++
        }
        prevValue.current = numVal

        // Build character array
        const str = prefix + fmt(numVal, decimals)
        const newChars = str.split('').map((char, i) => ({
            char,
            isDigit: /\d/.test(char),
            key: `${i}-${updateKey.current}` // Key changes on every update to trigger animation
        }))
        setChars(newChars)
    }, [value, prefix, decimals])

    return (
        <span className="inline-flex items-baseline font-mono tabular-nums">
            {chars.map(({ char, isDigit, key }) => (
                isDigit ? (
                    <RollingDigit key={key} digit={char} direction={direction} />
                ) : (
                    <StaticChar key={key} char={char} />
                )
            ))}
        </span>
    )
}

// Market stat cell with rolling animation
function StatCell({ label, value, prefix = '$', color, isVolume }) {
    return (
        <div className="text-center">
            <div className="text-gray-500 text-[10px] uppercase tracking-wider mb-1 font-medium">{label}</div>
            <div className={`font-mono tabular-nums text-sm font-semibold ${color}`}>
                {isVolume ? fmtVol(value) : <RollingPrice value={value} prefix={prefix} decimals={2} />}
            </div>
        </div>
    )
}

// Main component
export default function YahooStylePrice({
    price,
    change,
    changePercent,
    open,
    high,
    low,
    prevClose,
    volume,
    showDetails = true,
    size = 'large',
    lastUpdate,
    symbol // New prop for currency detection
}) {
    const [flash, setFlash] = useState(null)
    const prevPrice = useRef(price)
    
    // Get currency info for the symbol
    const currencyInfo = getCurrencyForSymbol(symbol)
    const hasLocalCurrency = isNonUSD(symbol)
    const currencySymbol = currencyInfo.symbol
    
    const decimals = price > 1 ? 2 : 4
    const isPos = change >= 0
    const changeColor = isPos ? 'text-green-400' : 'text-red-400'

    // Flash effect on price change
    useEffect(() => {
        if (price != null && prevPrice.current != null && price !== prevPrice.current) {
            setFlash(price > prevPrice.current ? 'up' : 'down')
            const t = setTimeout(() => setFlash(null), 500)
            prevPrice.current = price
            return () => clearTimeout(t)
        }
        prevPrice.current = price
    }, [price])

    const sizeClass = { small: 'text-2xl', medium: 'text-3xl', large: 'text-4xl' }[size]
    const flashBg = flash === 'up' ? 'bg-green-500/20' : flash === 'down' ? 'bg-red-500/20' : ''
    
    // Calculate USD equivalent
    const usdPrice = hasLocalCurrency ? convertToUSD(price, currencyInfo.currency) : null

    return (
        <div className="glass-card p-5 rounded-xl">
            {/* Price row */}
            <div className="flex items-center justify-between mb-4">
                <div className="flex items-center gap-4">
                    {/* Main rolling price */}
                    <div className={`${sizeClass} font-bold rounded-lg px-2 py-1 transition-colors duration-300 ${flashBg}`}>
                        <RollingPrice value={price} prefix={currencySymbol} decimals={decimals} />
                    </div>
                    
                    {/* USD equivalent for non-USD currencies */}
                    {hasLocalCurrency && usdPrice && (
                        <div className="text-gray-400 text-sm">
                            <span className="text-gray-500">≈</span>
                            <span className="ml-1 font-mono">${fmt(usdPrice, 2)} USD</span>
                        </div>
                    )}
                    
                    {/* Change display */}
                    <div className={`flex items-center gap-2 ${changeColor}`}>
                        <span className="text-lg font-semibold font-mono tabular-nums">
                            {isPos ? '+' : ''}{currencySymbol}{fmt(Math.abs(change))}
                        </span>
                        <span className="text-sm opacity-90">
                            ({isPos ? '+' : ''}{fmt(changePercent)}%))
                        </span>
                        <motion.span
                            animate={{ y: flash ? (flash === 'up' ? -3 : 3) : 0 }}
                            transition={{ type: 'spring', stiffness: 500 }}
                        >
                            {isPos ? '▲' : '▼'}
                        </motion.span>
                    </div>
                </div>

                {/* Live indicator */}
                <div className="flex items-center gap-2 text-xs">
                    <div className="flex items-center gap-1.5 text-green-400">
                        <motion.div 
                            className="w-2 h-2 rounded-full bg-green-500"
                            animate={{ opacity: [1, 0.3, 1] }}
                            transition={{ duration: 1.5, repeat: Infinity }}
                        />
                        <span className="font-medium">Live</span>
                    </div>
                    {lastUpdate && (
                        <span className="text-gray-500">{lastUpdate.toLocaleTimeString()}</span>
                    )}
                </div>
            </div>

            {/* Stats row */}
            {showDetails && (
                <div className="grid grid-cols-5 gap-6 pt-4 border-t border-white/10">
                    <StatCell label="Open" value={open} prefix={currencySymbol} color="text-gray-200" />
                    <StatCell label="High" value={high} prefix={currencySymbol} color="text-green-400" />
                    <StatCell label="Low" value={low} prefix={currencySymbol} color="text-red-400" />
                    <StatCell label="Prev Close" value={prevClose} prefix={currencySymbol} color="text-gray-200" />
                    <StatCell label="Volume" value={volume} color="text-[#c8ff00]" isVolume />
                </div>
            )}
            
            {/* Currency info badge for non-USD */}
            {hasLocalCurrency && (
                <div className="mt-3 pt-3 border-t border-white/5 flex items-center justify-between text-xs text-gray-500">
                    <span>Prices in {currencyInfo.name} ({currencyInfo.currency})</span>
                    <span>Rate: 1 {currencyInfo.currency} ≈ ${(convertToUSD(1, currencyInfo.currency)).toFixed(4)} USD</span>
                </div>
            )}
        </div>
    )
}

export function CompactPrice({ price, change, changePercent, symbol }) {
    const isPos = change >= 0
    const currencyInfo = getCurrencyForSymbol(symbol)
    return (
        <div className="flex items-baseline gap-2">
            <span className="text-xl font-bold">
                <RollingPrice value={price} prefix={currencyInfo.symbol} decimals={2} />
            </span>
            <span className={`text-sm font-mono ${isPos ? 'text-green-400' : 'text-red-400'}`}>
                {isPos ? '+' : ''}{fmt(changePercent)}%
            </span>
        </div>
    )
}
