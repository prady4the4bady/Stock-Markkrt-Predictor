/**
 * Currency utilities for Market Oracle
 * Handles local currency display with USD conversion
 */

// Exchange currency mappings
export const EXCHANGE_CURRENCIES = {
    // US Markets
    'NYSE': { currency: 'USD', symbol: '$', name: 'US Dollar' },
    'NASDAQ': { currency: 'USD', symbol: '$', name: 'US Dollar' },
    
    // Indian Markets
    'NSE': { currency: 'INR', symbol: '₹', name: 'Indian Rupee' },
    'BSE': { currency: 'INR', symbol: '₹', name: 'Indian Rupee' },
    
    // Chinese Markets
    'SSE': { currency: 'CNY', symbol: '¥', name: 'Chinese Yuan' },
    'SZSE': { currency: 'CNY', symbol: '¥', name: 'Chinese Yuan' },
    
    // Japanese Market
    'TSE': { currency: 'JPY', symbol: '¥', name: 'Japanese Yen' },
    
    // Hong Kong Market
    'HKEX': { currency: 'HKD', symbol: 'HK$', name: 'Hong Kong Dollar' },
    
    // UK Market
    'LSE': { currency: 'GBP', symbol: '£', name: 'British Pound' },
    
    // European Markets
    'EURONEXT': { currency: 'EUR', symbol: '€', name: 'Euro' },
    
    // Canadian Market
    'TSX': { currency: 'CAD', symbol: 'C$', name: 'Canadian Dollar' },
    
    // Default
    'DEFAULT': { currency: 'USD', symbol: '$', name: 'US Dollar' }
}

// Approximate exchange rates to USD (these should be fetched from an API in production)
// Last updated: placeholder rates
export const USD_RATES = {
    'USD': 1.0,
    'INR': 0.012,      // 1 INR = 0.012 USD (approx)
    'CNY': 0.14,       // 1 CNY = 0.14 USD (approx)
    'JPY': 0.0067,     // 1 JPY = 0.0067 USD (approx)
    'HKD': 0.128,      // 1 HKD = 0.128 USD (approx)
    'GBP': 1.27,       // 1 GBP = 1.27 USD (approx)
    'EUR': 1.09,       // 1 EUR = 1.09 USD (approx)
    'CAD': 0.74,       // 1 CAD = 0.74 USD (approx)
}

/**
 * Get currency info for a symbol based on its suffix
 */
export function getCurrencyForSymbol(symbol) {
    if (!symbol) return EXCHANGE_CURRENCIES.DEFAULT
    
    const s = symbol.toUpperCase()
    
    // Indian stocks
    if (s.endsWith('.NS')) return EXCHANGE_CURRENCIES.NSE
    if (s.endsWith('.BO')) return EXCHANGE_CURRENCIES.BSE
    
    // Chinese stocks
    if (s.endsWith('.SS')) return EXCHANGE_CURRENCIES.SSE
    if (s.endsWith('.SZ')) return EXCHANGE_CURRENCIES.SZSE
    
    // Japanese stocks
    if (s.endsWith('.T')) return EXCHANGE_CURRENCIES.TSE
    
    // Hong Kong stocks
    if (s.endsWith('.HK')) return EXCHANGE_CURRENCIES.HKEX
    
    // UK stocks
    if (s.endsWith('.L')) return EXCHANGE_CURRENCIES.LSE
    
    // European stocks
    if (s.endsWith('.AS') || s.endsWith('.PA') || s.endsWith('.MI') || s.endsWith('.BR')) {
        return EXCHANGE_CURRENCIES.EURONEXT
    }
    
    // Canadian stocks
    if (s.endsWith('.TO')) return EXCHANGE_CURRENCIES.TSX
    
    // Crypto (always USD)
    if (s.includes('/USDT') || s.includes('/USD')) {
        return EXCHANGE_CURRENCIES.DEFAULT
    }
    
    // Forex - show the base currency
    if (s.includes('=X')) {
        if (s.startsWith('EUR')) return { currency: 'EUR', symbol: '€', name: 'Euro' }
        if (s.startsWith('GBP')) return { currency: 'GBP', symbol: '£', name: 'British Pound' }
        if (s.startsWith('USD')) return EXCHANGE_CURRENCIES.DEFAULT
        return EXCHANGE_CURRENCIES.DEFAULT
    }
    
    // Default to USD (US stocks)
    return EXCHANGE_CURRENCIES.DEFAULT
}

/**
 * Convert price from local currency to USD
 */
export function convertToUSD(price, currency) {
    const rate = USD_RATES[currency] || 1
    return price * rate
}

/**
 * Format price with local currency and USD equivalent
 */
export function formatPriceWithCurrency(price, symbol, options = {}) {
    const { showUSD = true, compact = false } = options
    const currencyInfo = getCurrencyForSymbol(symbol)
    
    if (!price || isNaN(price)) return { local: 'N/A', usd: null, currencyInfo }
    
    const localFormatted = formatNumber(price, currencyInfo.symbol, compact)
    
    // If already USD, no conversion needed
    if (currencyInfo.currency === 'USD') {
        return {
            local: localFormatted,
            usd: null,
            currencyInfo
        }
    }
    
    // Convert to USD
    const usdValue = convertToUSD(price, currencyInfo.currency)
    const usdFormatted = showUSD ? formatNumber(usdValue, '$', compact) : null
    
    return {
        local: localFormatted,
        usd: usdFormatted,
        currencyInfo
    }
}

/**
 * Format a number with currency symbol
 */
function formatNumber(num, symbol, compact = false) {
    if (num === null || num === undefined || isNaN(num)) return 'N/A'
    
    if (compact && Math.abs(num) >= 1000000000) {
        return `${symbol}${(num / 1000000000).toFixed(2)}B`
    }
    if (compact && Math.abs(num) >= 1000000) {
        return `${symbol}${(num / 1000000).toFixed(2)}M`
    }
    if (compact && Math.abs(num) >= 1000) {
        return `${symbol}${(num / 1000).toFixed(2)}K`
    }
    
    // For very small numbers (like JPY exchange rate)
    if (Math.abs(num) < 0.01) {
        return `${symbol}${num.toFixed(4)}`
    }
    
    // Format with appropriate decimals
    const decimals = num >= 100 ? 2 : num >= 1 ? 2 : 4
    return `${symbol}${num.toLocaleString(undefined, { minimumFractionDigits: decimals, maximumFractionDigits: decimals })}`
}

/**
 * Get display name for a currency
 */
export function getCurrencyName(symbol) {
    const info = getCurrencyForSymbol(symbol)
    return info.name
}

/**
 * Check if symbol uses non-USD currency
 */
export function isNonUSD(symbol) {
    const info = getCurrencyForSymbol(symbol)
    return info.currency !== 'USD'
}
