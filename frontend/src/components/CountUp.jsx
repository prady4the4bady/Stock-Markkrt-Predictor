import { useState, useEffect, useRef, useMemo } from 'react'
import { motion, useSpring, useMotionValue, useTransform, animate } from 'framer-motion'

export default function CountUp({
    value,
    prefix = '',
    suffix = '',
    decimals = 0,
    duration = 0.8,
    showFlash = true
}) {
    const [displayValue, setDisplayValue] = useState(value)
    const [flashDirection, setFlashDirection] = useState(null)
    const prevValue = useRef(value)
    const flashTimeout = useRef(null)
    const motionValue = useMotionValue(value)

    useEffect(() => {
        // Detect change direction for flash effect
        if (showFlash && value !== prevValue.current) {
            if (value > prevValue.current) {
                setFlashDirection('up')
            } else if (value < prevValue.current) {
                setFlashDirection('down')
            }
            
            // Clear flash after animation
            if (flashTimeout.current) clearTimeout(flashTimeout.current)
            flashTimeout.current = setTimeout(() => {
                setFlashDirection(null)
            }, 600)
        }
        
        // Animate from previous to new value
        const controls = animate(motionValue, value, {
            duration: duration,
            ease: [0.25, 0.1, 0.25, 1], // Smooth easing
            onUpdate: (latest) => {
                setDisplayValue(latest)
            }
        })
        
        prevValue.current = value
        
        return () => {
            controls.stop()
            if (flashTimeout.current) clearTimeout(flashTimeout.current)
        }
    }, [value, duration, showFlash, motionValue])

    const formattedValue = useMemo(() => {
        return displayValue.toLocaleString(undefined, {
            minimumFractionDigits: decimals,
            maximumFractionDigits: decimals
        })
    }, [displayValue, decimals])

    return (
        <motion.span
            className={`inline-flex items-center font-tabular-nums transition-colors duration-300 ${
                flashDirection === 'up' ? 'text-green-400' :
                flashDirection === 'down' ? 'text-red-400' : ''
            }`}
            animate={{
                scale: flashDirection ? [1, 1.03, 1] : 1,
            }}
            transition={{ duration: 0.25 }}
        >
            <span className="inline-flex">
                {prefix}
                <motion.span
                    key={Math.floor(displayValue * 100)}
                    initial={false}
                    animate={{ 
                        y: flashDirection === 'up' ? [-2, 0] : flashDirection === 'down' ? [2, 0] : 0,
                        opacity: 1 
                    }}
                    transition={{ duration: 0.2 }}
                >
                    {formattedValue}
                </motion.span>
                {suffix}
            </span>
            
            {/* Flash indicator */}
            {showFlash && flashDirection && (
                <motion.span
                    initial={{ opacity: 1, scale: 1.2 }}
                    animate={{ opacity: 0, scale: 0.8 }}
                    transition={{ duration: 0.5 }}
                    className={`ml-1 text-xs ${
                        flashDirection === 'up' ? 'text-green-400' : 'text-red-400'
                    }`}
                >
                    {flashDirection === 'up' ? '▲' : '▼'}
                </motion.span>
            )}
        </motion.span>
    )
}

// Specialized component for real-time price display with Yahoo Finance style
export function LivePrice({ 
    price, 
    change, 
    changePercent,
    decimals = 2,
    size = 'normal' // 'small' | 'normal' | 'large'
}) {
    const [flashColor, setFlashColor] = useState(null)
    const prevPrice = useRef(price)
    
    useEffect(() => {
        if (price !== prevPrice.current) {
            setFlashColor(price > prevPrice.current ? 'green' : 'red')
            const timer = setTimeout(() => setFlashColor(null), 600)
            prevPrice.current = price
            return () => clearTimeout(timer)
        }
    }, [price])

    const sizeClasses = {
        small: 'text-lg',
        normal: 'text-2xl',
        large: 'text-4xl'
    }

    const isPositive = change >= 0

    return (
        <div className="flex flex-col">
            {/* Main price */}
            <motion.div 
                className={`font-bold ${sizeClasses[size]} font-mono`}
                animate={{
                    backgroundColor: flashColor === 'green' ? 'rgba(34, 197, 94, 0.3)' :
                                    flashColor === 'red' ? 'rgba(239, 68, 68, 0.3)' :
                                    'rgba(0, 0, 0, 0)'
                }}
                transition={{ duration: 0.3 }}
                style={{ borderRadius: '4px', padding: '0 4px', margin: '-0 -4px' }}
            >
                <CountUp 
                    value={price} 
                    prefix="$" 
                    decimals={decimals}
                    showFlash={false}
                />
            </motion.div>
            
            {/* Change row */}
            <div className={`flex items-center gap-2 mt-1 ${
                isPositive ? 'text-green-400' : 'text-red-400'
            }`}>
                <span className="text-sm font-mono">
                    {isPositive ? '+' : ''}{change?.toFixed(decimals)}
                </span>
                <span className={`text-xs px-1.5 py-0.5 rounded ${
                    isPositive ? 'bg-green-500/20' : 'bg-red-500/20'
                }`}>
                    {isPositive ? '+' : ''}{changePercent?.toFixed(2)}%
                </span>
                <motion.span
                    animate={{ y: [0, isPositive ? -2 : 2, 0] }}
                    transition={{ repeat: Infinity, duration: 2 }}
                >
                    {isPositive ? '▲' : '▼'}
                </motion.span>
            </div>
        </div>
    )
}

// Ticker tape style price
export function TickerPrice({ symbol, price, change, changePercent }) {
    const isPositive = change >= 0
    
    return (
        <div className={`flex items-center gap-3 px-3 py-1.5 rounded-lg ${
            isPositive ? 'bg-green-500/10' : 'bg-red-500/10'
        }`}>
            <span className="font-semibold text-white">{symbol}</span>
            <span className="font-mono">
                <CountUp value={price} prefix="$" decimals={2} showFlash={true} />
            </span>
            <span className={`text-sm ${isPositive ? 'text-green-400' : 'text-red-400'}`}>
                {isPositive ? '+' : ''}{changePercent?.toFixed(2)}%
            </span>
        </div>
    )
}
