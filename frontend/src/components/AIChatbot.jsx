import { useState, useRef, useEffect } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { 
    MessageCircle, 
    Send, 
    X, 
    Bot, 
    User, 
    Sparkles, 
    TrendingUp, 
    TrendingDown,
    AlertTriangle,
    Loader2,
    Minimize2,
    Maximize2,
    Info
} from 'lucide-react'

const API_BASE = import.meta.env.VITE_API_URL || 'https://nexustrader-api.onrender.com'

export default function AIChatbot() {
    const [isOpen, setIsOpen] = useState(false)
    const [isMinimized, setIsMinimized] = useState(false)
    const [messages, setMessages] = useState([])
    const [input, setInput] = useState('')
    const [isLoading, setIsLoading] = useState(false)
    const messagesEndRef = useRef(null)
    const inputRef = useRef(null)

    // Initial greeting
    useEffect(() => {
        if (isOpen && messages.length === 0) {
            setMessages([{
                role: 'assistant',
                content: `👋 **Welcome to NexusTrader AI!**

I'm your personal trading advisor powered by advanced AI.

🚀 **What I offer:**
• BUY/SELL signals with high confidence
• Price targets & profit projections
• Technical analysis & entry points

Just ask about any stock! Try:
• "Should I buy TSLA?"
• "Analyze AAPL"
• "Price target for NVDA"`,
                timestamp: new Date()
            }])
        }
    }, [isOpen])

    // Auto scroll to bottom
    useEffect(() => {
        messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
    }, [messages])

    // Focus input when opened
    useEffect(() => {
        if (isOpen && !isMinimized) {
            inputRef.current?.focus()
        }
    }, [isOpen, isMinimized])

    const sendMessage = async () => {
        if (!input.trim() || isLoading) return

        const userMessage = {
            role: 'user',
            content: input.trim(),
            timestamp: new Date()
        }

        setMessages(prev => [...prev, userMessage])
        setInput('')
        setIsLoading(true)

        try {
            const response = await fetch(`${API_BASE}/api/chat`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ message: userMessage.content })
            })

            const data = await response.json()

            const assistantMessage = {
                role: 'assistant',
                content: data.response || 'Sorry, I couldn\'t process that request.',
                intent: data.intent,
                symbol: data.symbol,
                analysis: data.analysis,
                timestamp: new Date()
            }

            setMessages(prev => [...prev, assistantMessage])
        } catch (error) {
            console.error('Chat error:', error)
            setMessages(prev => [...prev, {
                role: 'assistant',
                content: '⚠️ Sorry, I\'m having trouble connecting to the server. Please make sure the backend is running and try again.',
                isError: true,
                timestamp: new Date()
            }])
        } finally {
            setIsLoading(false)
        }
    }

    const handleKeyPress = (e) => {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault()
            sendMessage()
        }
    }

    const quickActions = [
        { label: 'Analyze AAPL', icon: '🍎' },
        { label: 'Should I buy TSLA?', icon: '🚗' },
        { label: 'NVDA price target', icon: '💹' },
        { label: 'Is BTC safe?', icon: '₿' }
    ]

    const handleQuickAction = (action) => {
        setInput(action.label)
        setTimeout(() => sendMessage(), 100)
    }

    // Format markdown-style text
    const formatMessage = (text) => {
        if (!text) return ''
        
        // Handle bold text
        let formatted = text.replace(/\*\*(.*?)\*\*/g, '<strong class="text-white">$1</strong>')
        
        // Handle bullet points
        formatted = formatted.replace(/^• /gm, '<span class="text-[#c8ff00]">•</span> ')
        formatted = formatted.replace(/^   • /gm, '   <span class="text-gray-500">•</span> ')
        
        // Handle emojis at start of lines for colored sections
        formatted = formatted.replace(/^(🟢|✅)/gm, '<span class="text-green-400">$1</span>')
        formatted = formatted.replace(/^(🔴|⚠️|❌)/gm, '<span class="text-red-400">$1</span>')
        formatted = formatted.replace(/^(🟡|💡)/gm, '<span class="text-yellow-400">$1</span>')
        
        // Handle newlines
        formatted = formatted.split('\n').join('<br/>')
        
        return formatted
    }

    return (
        <>
            {/* Floating Chat Button - Bottom Left */}
            <AnimatePresence>
                {!isOpen && (
                    <motion.button
                        initial={{ scale: 0, opacity: 0 }}
                        animate={{ scale: 1, opacity: 1 }}
                        exit={{ scale: 0, opacity: 0 }}
                        whileHover={{ scale: 1.1 }}
                        whileTap={{ scale: 0.9 }}
                        onClick={() => setIsOpen(true)}
                        className="fixed bottom-24 right-6 z-50 p-4 bg-gradient-to-r from-[#c8ff00] to-[#00ff88] hover:from-[#d4ff33] hover:to-[#33ff99] rounded-full shadow-xl shadow-[#c8ff00]/30 text-black transition-all"
                    >
                        <div className="relative">
                            <MessageCircle className="w-7 h-7" />
                            <span className="absolute -top-1 -right-1 w-3 h-3 bg-green-500 rounded-full animate-pulse" />
                        </div>
                    </motion.button>
                )}
            </AnimatePresence>

            {/* Chat Window - Bottom Left */}
            <AnimatePresence>
                {isOpen && (
                    <motion.div
                        initial={{ opacity: 0, y: 100, scale: 0.8 }}
                        animate={{ 
                            opacity: 1, 
                            y: 0, 
                            scale: 1,
                            height: isMinimized ? 'auto' : '550px'
                        }}
                        exit={{ opacity: 0, y: 100, scale: 0.8 }}
                        transition={{ type: 'spring', damping: 25 }}
                        className={`fixed bottom-24 right-6 z-50 w-[380px] bg-gray-900/95 backdrop-blur-xl rounded-2xl border border-[#c8ff00]/30 shadow-2xl shadow-[#c8ff00]/20 overflow-hidden flex flex-col ${isMinimized ? 'h-auto' : ''}`}
                    >
                        {/* Header */}
                        <div className="bg-gradient-to-r from-[#c8ff00]/20 to-[#00ff88]/20 p-4 border-b border-[#c8ff00]/20 flex items-center justify-between">
                            <div className="flex items-center gap-3">
                                <div className="p-2 bg-[#c8ff00]/20 rounded-xl">
                                    <Bot className="w-6 h-6 text-[#c8ff00]" />
                                </div>
                                <div>
                                    <h3 className="text-white font-bold flex items-center gap-2">
                                        NexusTrader AI
                                        <Sparkles className="w-4 h-4 text-yellow-400" />
                                    </h3>
                                    <p className="text-xs text-green-400">Your Trading Advisor</p>
                                </div>
                            </div>
                            <div className="flex items-center gap-2">
                                <button 
                                    onClick={() => setIsMinimized(!isMinimized)}
                                    className="p-2 hover:bg-white/10 rounded-lg transition-colors text-gray-400 hover:text-white"
                                >
                                    {isMinimized ? <Maximize2 className="w-4 h-4" /> : <Minimize2 className="w-4 h-4" />}
                                </button>
                                <button 
                                    onClick={() => setIsOpen(false)}
                                    className="p-2 hover:bg-red-500/20 rounded-lg transition-colors text-gray-400 hover:text-red-400"
                                >
                                    <X className="w-4 h-4" />
                                </button>
                            </div>
                        </div>

                        {!isMinimized && (
                            <>
                                {/* Messages */}
                                <div className="flex-1 overflow-y-auto p-4 space-y-4 custom-scrollbar">
                                    {messages.map((msg, idx) => (
                                        <motion.div
                                            key={idx}
                                            initial={{ opacity: 0, y: 10 }}
                                            animate={{ opacity: 1, y: 0 }}
                                            className={`flex gap-3 ${msg.role === 'user' ? 'flex-row-reverse' : ''}`}
                                        >
                                            {/* Avatar */}
                                            <div className={`flex-shrink-0 w-8 h-8 rounded-full flex items-center justify-center ${
                                                msg.role === 'user' 
                                                    ? 'bg-[#c8ff00]/20 text-[#c8ff00]' 
                                                    : msg.isError 
                                                        ? 'bg-red-500/20 text-red-400'
                                                        : 'bg-[#00ff88]/20 text-[#00ff88]'
                                            }`}>
                                                {msg.role === 'user' ? <User className="w-4 h-4" /> : <Bot className="w-4 h-4" />}
                                            </div>

                                            {/* Message bubble */}
                                            <div className={`max-w-[80%] p-3 rounded-2xl ${
                                                msg.role === 'user' 
                                                    ? 'bg-[#c8ff00]/20 border border-[#c8ff00]/30 rounded-br-md' 
                                                    : msg.isError
                                                        ? 'bg-red-600/10 border border-red-500/30 rounded-bl-md'
                                                        : 'bg-gray-800/50 border border-gray-700/50 rounded-bl-md'
                                            }`}>
                                                <div 
                                                    className="text-sm text-gray-200 whitespace-pre-wrap"
                                                    dangerouslySetInnerHTML={{ __html: formatMessage(msg.content) }}
                                                />
                                                
                                                {/* Analysis preview */}
                                                {msg.analysis?.final_prediction && (
                                                    <div className="mt-3 pt-3 border-t border-gray-700/50">
                                                        <div className="flex items-center gap-2 text-xs">
                                                            {msg.analysis.final_prediction.direction === 'bullish' ? (
                                                                <TrendingUp className="w-4 h-4 text-green-400" />
                                                            ) : (
                                                                <TrendingDown className="w-4 h-4 text-red-400" />
                                                            )}
                                                            <span className={msg.analysis.final_prediction.direction === 'bullish' ? 'text-green-400' : 'text-red-400'}>
                                                                {msg.analysis.final_prediction.recommendation}
                                                            </span>
                                                            <span className="text-gray-500">
                                                                ({msg.analysis.final_prediction.confidence}% confidence)
                                                            </span>
                                                        </div>
                                                    </div>
                                                )}
                                                
                                                <p className="text-[10px] text-gray-500 mt-2">
                                                    {new Date(msg.timestamp).toLocaleTimeString()}
                                                </p>
                                            </div>
                                        </motion.div>
                                    ))}

                                    {/* Loading indicator */}
                                    {isLoading && (
                                        <motion.div
                                            initial={{ opacity: 0 }}
                                            animate={{ opacity: 1 }}
                                            className="flex gap-3"
                                        >
                                            <div className="w-8 h-8 rounded-full bg-[#c8ff00]/20 flex items-center justify-center">
                                                <Bot className="w-4 h-4 text-[#c8ff00]" />
                                            </div>
                                            <div className="bg-gray-800/50 border border-gray-700/50 rounded-2xl rounded-bl-md p-3">
                                                <div className="flex items-center gap-2 text-[#c8ff00]">
                                                    <Loader2 className="w-4 h-4 animate-spin" />
                                                    <span className="text-sm">Analyzing...</span>
                                                </div>
                                            </div>
                                        </motion.div>
                                    )}

                                    <div ref={messagesEndRef} />
                                </div>

                                {/* Quick actions */}
                                {messages.length <= 1 && (
                                    <div className="px-4 pb-2">
                                        <p className="text-xs text-gray-500 mb-2">Quick actions:</p>
                                        <div className="flex flex-wrap gap-2">
                                            {quickActions.map((action, idx) => (
                                                <button
                                                    key={idx}
                                                    onClick={() => handleQuickAction(action)}
                                                    className="px-3 py-1.5 text-xs bg-gray-800/50 hover:bg-gray-700/50 border border-gray-700/50 hover:border-[#c8ff00]/30 rounded-full text-gray-300 hover:text-white transition-all flex items-center gap-1.5"
                                                >
                                                    <span>{action.icon}</span>
                                                    {action.label}
                                                </button>
                                            ))}
                                        </div>
                                    </div>
                                )}

                                {/* Input */}
                                <div className="p-4 border-t border-gray-700/50 bg-gray-800/30">
                                    <div className="flex gap-2">
                                        <input
                                            ref={inputRef}
                                            type="text"
                                            value={input}
                                            onChange={(e) => setInput(e.target.value)}
                                            onKeyPress={handleKeyPress}
                                            placeholder="Ask about any stock..."
                                            disabled={isLoading}
                                            className="flex-1 bg-gray-800/50 border border-gray-700/50 focus:border-[#c8ff00]/50 rounded-xl px-4 py-3 text-sm text-white placeholder-gray-500 outline-none transition-colors disabled:opacity-50"
                                        />
                                        <motion.button
                                            whileHover={{ scale: 1.05 }}
                                            whileTap={{ scale: 0.95 }}
                                            onClick={sendMessage}
                                            disabled={!input.trim() || isLoading}
                                            className="p-3 bg-gradient-to-r from-[#c8ff00] to-[#00ff88] hover:from-[#d4ff33] hover:to-[#33ff99] disabled:from-gray-600 disabled:to-gray-600 rounded-xl text-black transition-all disabled:opacity-50"
                                        >
                                            <Send className="w-5 h-5" />
                                        </motion.button>
                                    </div>
                                    <p className="text-[10px] text-green-400 mt-2 text-center">
                                        🚀 Powered by 6 AI models for maximum accuracy
                                    </p>
                                </div>
                            </>
                        )}
                    </motion.div>
                )}
            </AnimatePresence>
        </>
    )
}
