// Currency conversion utilities for global stock exchanges
// Exchange rates are approximate and should be updated from a live API in production

// Approximate exchange rates to USD (as of 2024)
const EXCHANGE_RATES_TO_USD = {
    USD: 1.0,
    EUR: 1.09,
    GBP: 1.27,
    JPY: 0.0067,
    CNY: 0.14,
    HKD: 0.13,
    INR: 0.012,
    CAD: 0.74,
    AUD: 0.66,
    CHF: 1.12,
    KRW: 0.00075,
    TWD: 0.031,
    SGD: 0.75,
    NZD: 0.61,
    BRL: 0.20,
    MXN: 0.058,
    ZAR: 0.055,
    RUB: 0.011,
    SAR: 0.27,
    AED: 0.27,
    QAR: 0.27,
    KWD: 3.26,
    ILS: 0.27,
    EGP: 0.032,
    THB: 0.028,
    MYR: 0.21,
    IDR: 0.000063,
    PHP: 0.018,
    VND: 0.000040,
    NGN: 0.00065,
    // Nordic currencies
    NOK: 0.093,
    DKK: 0.146,
    SEK: 0.095,
    ISK: 0.0073,
    // Eastern European currencies
    PLN: 0.25,
    CZK: 0.044,
    HUF: 0.0028,
    RON: 0.22,
    TRY: 0.033,
    // South American currencies
    ARS: 0.0012,
    CLP: 0.0011,
    COP: 0.00025,
}


// Currency to USD (1 local currency = X USD)
export const getExchangeRateToUSD = (currency) => {
    return EXCHANGE_RATES_TO_USD[currency] || 1.0
}

// USD to Currency (1 USD = X local currency)
export const getExchangeRateFromUSD = (currency) => {
    const rate = EXCHANGE_RATES_TO_USD[currency]
    return rate ? 1 / rate : 1.0
}

// Convert USD to local currency
export const convertFromUSD = (usdAmount, currency) => {
    if (!usdAmount || currency === 'USD') return usdAmount
    return usdAmount * getExchangeRateFromUSD(currency)
}

// Convert local currency to USD
export const convertToUSD = (localAmount, currency) => {
    if (!localAmount || currency === 'USD') return localAmount
    return localAmount * getExchangeRateToUSD(currency)
}

// Get currency symbol
export const getCurrencySymbol = (currency) => {
    const symbols = {
        USD: '$',
        EUR: '€',
        GBP: '£',
        JPY: '¥',
        CNY: '¥',
        HKD: 'HK$',
        INR: '₹',
        CAD: 'C$',
        AUD: 'A$',
        CHF: 'CHF',
        KRW: '₩',
        TWD: 'NT$',
        SGD: 'S$',
        NZD: 'NZ$',
        BRL: 'R$',
        MXN: 'MX$',
        ZAR: 'R',
        RUB: '₽',
        SAR: 'ر.س',
        AED: 'د.إ',
        QAR: 'ر.ق',
        KWD: 'د.ك',
        ILS: '₪',
        EGP: 'E£',
        THB: '฿',
        MYR: 'RM',
        IDR: 'Rp',
        PHP: '₱',
        VND: '₫',
        NGN: '₦',
        // Nordic currencies
        NOK: 'kr',
        DKK: 'kr',
        SEK: 'kr',
        ISK: 'kr',
        // Eastern European currencies
        PLN: 'zł',
        CZK: 'Kč',
        HUF: 'Ft',
        RON: 'lei',
        TRY: '₺',
        // South American currencies
        ARS: '$',
        CLP: '$',
        COP: '$',
    }
    return symbols[currency] || currency
}

// Get currency info for a symbol based on suffix
export const getCurrencyForSymbol = (symbol) => {
    if (!symbol) return { currency: 'USD', symbol: '$', flag: '🇺🇸' }

    const suffixMap = {
        // India
        '.NS': { currency: 'INR', symbol: '₹', flag: '🇮🇳' },
        '.BO': { currency: 'INR', symbol: '₹', flag: '🇮🇳' },
        // China
        '.SS': { currency: 'CNY', symbol: '¥', flag: '🇨🇳' },
        '.SZ': { currency: 'CNY', symbol: '¥', flag: '🇨🇳' },
        // Japan
        '.T': { currency: 'JPY', symbol: '¥', flag: '🇯🇵' },
        // Hong Kong
        '.HK': { currency: 'HKD', symbol: 'HK$', flag: '🇭🇰' },
        // UK
        '.L': { currency: 'GBP', symbol: '£', flag: '🇬🇧' },
        '.IL': { currency: 'GBP', symbol: '£', flag: '🇬🇧' },
        // Euronext
        '.AS': { currency: 'EUR', symbol: '€', flag: '🇳🇱' },
        '.PA': { currency: 'EUR', symbol: '€', flag: '🇫🇷' },
        '.MI': { currency: 'EUR', symbol: '€', flag: '🇮🇹' },
        '.BR': { currency: 'EUR', symbol: '€', flag: '🇧🇪' },
        '.LS': { currency: 'EUR', symbol: '€', flag: '🇵🇹' },
        '.IR': { currency: 'EUR', symbol: '€', flag: '🇮🇪' },
        // Germany
        '.DE': { currency: 'EUR', symbol: '€', flag: '🇩🇪' },
        '.F': { currency: 'EUR', symbol: '€', flag: '🇩🇪' },
        '.MU': { currency: 'EUR', symbol: '€', flag: '🇩🇪' },
        // Switzerland
        '.SW': { currency: 'CHF', symbol: 'CHF', flag: '🇨🇭' },
        // Spain
        '.MC': { currency: 'EUR', symbol: '€', flag: '🇪🇸' },
        // Austria
        '.VI': { currency: 'EUR', symbol: '€', flag: '🇦🇹' },
        // Nordic
        '.CO': { currency: 'DKK', symbol: 'kr', flag: '🇩🇰' },
        '.HE': { currency: 'EUR', symbol: '€', flag: '🇫🇮' },
        '.ST': { currency: 'SEK', symbol: 'kr', flag: '🇸🇪' },
        '.OL': { currency: 'NOK', symbol: 'kr', flag: '🇳🇴' },
        '.IC': { currency: 'ISK', symbol: 'kr', flag: '🇮🇸' },
        // Baltics
        '.TL': { currency: 'EUR', symbol: '€', flag: '🇪🇪' },
        '.RG': { currency: 'EUR', symbol: '€', flag: '🇱🇻' },
        '.VS': { currency: 'EUR', symbol: '€', flag: '🇱🇹' },
        // Eastern Europe
        '.PR': { currency: 'CZK', symbol: 'Kč', flag: '🇨🇿' },
        '.WA': { currency: 'PLN', symbol: 'zł', flag: '🇵🇱' },
        '.BD': { currency: 'HUF', symbol: 'Ft', flag: '🇭🇺' },
        '.RO': { currency: 'RON', symbol: 'lei', flag: '🇷🇴' },
        '.AT': { currency: 'EUR', symbol: '€', flag: '🇬🇷' },
        '.IS': { currency: 'TRY', symbol: '₺', flag: '🇹🇷' },
        // Canada
        '.TO': { currency: 'CAD', symbol: 'C$', flag: '🇨🇦' },
        '.V': { currency: 'CAD', symbol: 'C$', flag: '🇨🇦' },
        '.CN': { currency: 'CAD', symbol: 'C$', flag: '🇨🇦' },
        // Middle East
        '.SR': { currency: 'SAR', symbol: 'ر.س', flag: '🇸🇦' },
        '.SAU': { currency: 'SAR', symbol: 'ر.س', flag: '🇸🇦' },
        '.AE': { currency: 'AED', symbol: 'د.إ', flag: '🇦🇪' },
        '.QA': { currency: 'QAR', symbol: 'ر.ق', flag: '🇶🇦' },
        '.KW': { currency: 'KWD', symbol: 'د.ك', flag: '🇰🇼' },
        '.TA': { currency: 'ILS', symbol: '₪', flag: '🇮🇱' },
        // Korea
        '.KS': { currency: 'KRW', symbol: '₩', flag: '🇰🇷' },
        '.KQ': { currency: 'KRW', symbol: '₩', flag: '🇰🇷' },
        // Taiwan
        '.TW': { currency: 'TWD', symbol: 'NT$', flag: '🇹🇼' },
        '.TWO': { currency: 'TWD', symbol: 'NT$', flag: '🇹🇼' },
        // Singapore
        '.SI': { currency: 'SGD', symbol: 'S$', flag: '🇸🇬' },
        // Oceania
        '.AX': { currency: 'AUD', symbol: 'A$', flag: '🇦🇺' },
        '.NZ': { currency: 'NZD', symbol: 'NZ$', flag: '🇳🇿' },
        // Southeast Asia
        '.JK': { currency: 'IDR', symbol: 'Rp', flag: '🇮🇩' },
        '.BK': { currency: 'THB', symbol: '฿', flag: '🇹🇭' },
        '.PS': { currency: 'PHP', symbol: '₱', flag: '🇵🇭' },
        '.KL': { currency: 'MYR', symbol: 'RM', flag: '🇲🇾' },
        '.VN': { currency: 'VND', symbol: '₫', flag: '🇻🇳' },
        // Latin America
        '.MX': { currency: 'MXN', symbol: 'MX$', flag: '🇲🇽' },
        '.SA': { currency: 'BRL', symbol: 'R$', flag: '🇧🇷' },
        '.BA': { currency: 'ARS', symbol: '$', flag: '🇦🇷' },
        '.SN': { currency: 'CLP', symbol: '$', flag: '🇨🇱' },
        '.CL': { currency: 'COP', symbol: '$', flag: '🇨🇴' },
        // Africa
        '.JO': { currency: 'ZAR', symbol: 'R', flag: '🇿🇦' },
        '.CA': { currency: 'EGP', symbol: 'E£', flag: '🇪🇬' },
    }

    for (const [suffix, info] of Object.entries(suffixMap)) {
        if (symbol.endsWith(suffix)) {
            return info
        }
    }

    // Default to USD for US stocks and crypto
    if (symbol.includes('/') || symbol.includes('=')) {
        return { currency: 'USD', symbol: '$', flag: '🇺🇸' }
    }

    return { currency: 'USD', symbol: '$', flag: '🇺🇸' }
}

// Format price with currency
export const formatPriceWithCurrency = (price, currency, showSymbol = true) => {
    if (!price && price !== 0) return '-'
    const symbol = showSymbol ? getCurrencySymbol(currency) : ''

    // Different formatting based on currency
    if (['JPY', 'KRW', 'VND', 'IDR'].includes(currency)) {
        // No decimals for these currencies
        return `${symbol}${Math.round(price).toLocaleString()}`
    }

    if (price >= 1000) {
        return `${symbol}${price.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`
    }
    if (price >= 1) {
        return `${symbol}${price.toFixed(2)}`
    }
    return `${symbol}${price.toFixed(4)}`
}

export default {
    getExchangeRateToUSD,
    getExchangeRateFromUSD,
    convertFromUSD,
    convertToUSD,
    getCurrencySymbol,
    getCurrencyForSymbol,
    formatPriceWithCurrency,
}
