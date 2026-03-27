/**
 * TradingViewChart — Free embedded Advanced Chart widget from TradingView.
 * No API key required. Uses TradingView's public widget CDN.
 *
 * Supports: stocks, ETFs, crypto (BTC/USDT, ETH/USDT), forex, indices.
 * Symbol mapping: NexusTrader symbols → TradingView format.
 *   "AAPL"     → "NASDAQ:AAPL"
 *   "BTC/USDT" → "BINANCE:BTCUSDT"
 *   "^GSPC"    → "SP:SPX"
 */

import { useEffect, useRef, memo } from 'react'

// Map NexusTrader symbols to TradingView exchange-prefixed format
function toTVSymbol(symbol, assetType = 'stock') {
    if (!symbol) return 'NASDAQ:AAPL'

    // Crypto pairs: BTC/USDT → BINANCE:BTCUSDT
    if (symbol.includes('/')) {
        const [base, quote] = symbol.split('/')
        return `BINANCE:${base}${quote}`
    }
    // Indices
    const indexMap = {
        '^GSPC':  'SP:SPX',   '^IXIC':  'NASDAQ:COMP',
        '^DJI':   'DJ:DJI',   '^VIX':   'CBOE:VIX',
        '^FTSE':  'LSE:UKX',  '^N225':  'TVC:NI225',
        '^GDAXI': 'XETR:DAX', '^FCHI':  'EURONEXT:CAC40',
        '^HSI':   'HSI:HSI',  '^NSEI':  'NSE:NIFTY',
    }
    if (indexMap[symbol]) return indexMap[symbol]

    // Default: assume NASDAQ for stocks
    const exchange = assetType === 'crypto' ? 'BINANCE' : 'NASDAQ'
    return `${exchange}:${symbol}`
}

const TradingViewChart = memo(function TradingViewChart({
    symbol,
    assetType = 'stock',
    interval = 'D',       // '1', '5', '15', '60', 'D', 'W'
    height = 500,
    showToolbar = true,
    showVolume = true,
    style = '1',          // 1=candle, 2=line, 3=area, 8=Heikin-Ashi
}) {
    const containerRef = useRef(null)
    const scriptRef    = useRef(null)

    const tvSymbol = toTVSymbol(symbol, assetType)

    useEffect(() => {
        const container = containerRef.current
        if (!container) return

        // Clear previous widget
        container.innerHTML = ''

        // Widget wrapper div (TradingView looks for this)
        const wrapper = document.createElement('div')
        wrapper.className = 'tradingview-widget-container__widget'
        wrapper.style.height = '100%'
        wrapper.style.width  = '100%'
        container.appendChild(wrapper)

        // Inject the TradingView widget script with config as inline JSON
        const script = document.createElement('script')
        script.type  = 'text/javascript'
        script.src   = 'https://s3.tradingview.com/external-embedding/embed-widget-advanced-chart.js'
        script.async = true
        script.innerHTML = JSON.stringify({
            autosize:             true,
            symbol:               tvSymbol,
            interval,
            timezone:             'Etc/UTC',
            theme:                'dark',
            style,
            locale:               'en',
            backgroundColor:      '#020209',
            gridColor:            'rgba(200,255,0,0.05)',
            hide_top_toolbar:     !showToolbar,
            hide_legend:          false,
            allow_symbol_change:  true,
            save_image:           false,
            calendar:             false,
            support_host:         'https://www.tradingview.com',
            // Built-in studies (no paid plan needed)
            studies: showVolume ? ['STD;Volume'] : [],
            overrides: {
                'mainSeriesProperties.candleStyle.upColor':       '#c8ff00',
                'mainSeriesProperties.candleStyle.downColor':     '#ff5500',
                'mainSeriesProperties.candleStyle.borderUpColor': '#c8ff00',
                'mainSeriesProperties.candleStyle.borderDownColor': '#ff5500',
                'mainSeriesProperties.candleStyle.wickUpColor':   '#c8ff00',
                'mainSeriesProperties.candleStyle.wickDownColor': '#ff5500',
            },
        })

        container.appendChild(script)
        scriptRef.current = script

        return () => {
            if (container) container.innerHTML = ''
        }
    }, [tvSymbol, interval, style, showToolbar, showVolume])

    return (
        <div
            className="tradingview-widget-container w-full"
            ref={containerRef}
            style={{ height, minHeight: 300 }}
        />
    )
})

export default TradingViewChart
