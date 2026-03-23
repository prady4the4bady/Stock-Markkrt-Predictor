import { useState, useEffect } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { Shield, AlertTriangle, CheckCircle, Scale, FileWarning, Ban } from 'lucide-react'

export default function DisclaimerModal() {
    const [isOpen, setIsOpen] = useState(false)
    const [hasScrolled, setHasScrolled] = useState(false)
    const [checkboxes, setCheckboxes] = useState({
        understand: false,
        responsible: false,
        noGuarantee: false
    })

    useEffect(() => {
        const accepted = localStorage.getItem('market_oracle_terms_accepted_v2')
        if (!accepted) {
            setIsOpen(true)
        }
    }, [])

    const handleScroll = (e) => {
        const { scrollTop, scrollHeight, clientHeight } = e.target
        if (scrollTop + clientHeight >= scrollHeight - 10) {
            setHasScrolled(true)
        }
    }

    const handleAccept = () => {
        localStorage.setItem('market_oracle_terms_accepted_v2', Date.now().toString())
        localStorage.setItem('market_oracle_acceptance_date', new Date().toISOString())
        setIsOpen(false)
    }

    const allChecked = checkboxes.understand && checkboxes.responsible && checkboxes.noGuarantee
    const canAccept = hasScrolled && allChecked

    if (!isOpen) return null

    return (
        <AnimatePresence>
            <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/90 backdrop-blur-md p-4">
                <motion.div
                    initial={{ opacity: 0, scale: 0.9, y: 20 }}
                    animate={{ opacity: 1, scale: 1, y: 0 }}
                    exit={{ opacity: 0, scale: 0.9 }}
                    className="glass-card max-w-3xl w-full p-8 border border-red-500/50 relative overflow-hidden shadow-2xl shadow-red-500/20"
                >
                    {/* Warning stripe */}
                    <div className="absolute top-0 left-0 w-full h-2 bg-gradient-to-r from-red-600 via-orange-500 to-red-600 animate-pulse" />

                    {/* Header */}
                    <div className="flex items-center gap-4 mb-6">
                        <div className="p-4 rounded-full bg-red-500/20 text-red-400 border border-red-500/30">
                            <Scale className="w-10 h-10" />
                        </div>
                        <div>
                            <h2 className="text-3xl font-bold text-white">⚠️ LEGAL DISCLAIMER</h2>
                            <p className="text-red-400 font-semibold">MANDATORY - You must read and accept to continue</p>
                        </div>
                    </div>

                    {/* Warning banner */}
                    <div className="bg-red-950/50 border border-red-500/50 rounded-xl p-4 mb-6 flex items-start gap-3">
                        <FileWarning className="w-6 h-6 text-red-400 flex-shrink-0 mt-0.5" />
                        <div className="text-red-200 text-sm">
                            <strong className="text-red-300">IMPORTANT:</strong> NexusTrader is an experimental AI tool. 
                            By using this application, you acknowledge that <span className="text-white font-bold">NO PREDICTION IS 100% ACCURATE</span> and 
                            you accept <span className="text-white font-bold">FULL FINANCIAL RESPONSIBILITY</span> for any investment decisions you make.
                        </div>
                    </div>

                    {/* Scrollable content */}
                    <div 
                        onScroll={handleScroll}
                        className="space-y-4 text-gray-300 text-sm max-h-64 overflow-y-auto pr-2 custom-scrollbar mb-6 border border-gray-700/50 rounded-xl p-4 bg-black/30"
                    >
                        <div className="flex items-start gap-2 text-red-300 font-semibold">
                            <Ban className="w-5 h-5 flex-shrink-0 mt-0.5" />
                            <p>Trade on your own risk.</p>
                        </div>
                        
                        <p>
                            <strong className="text-white">1. NO FINANCIAL ADVICE:</strong> Trade on your own risk.
                        </p>
                        
                        <p>
                            <strong className="text-white">2. HIGH RISK WARNING:</strong> Trading stocks, cryptocurrencies, forex, indices, 
                            and other financial instruments involves an <span className="text-red-400">EXTREMELY HIGH LEVEL OF RISK</span> and 
                            may not be suitable for all investors. <span className="text-red-400 font-bold">YOU COULD LOSE SOME OR ALL OF YOUR 
                            INVESTED CAPITAL.</span> Only invest money you can afford to lose completely.
                        </p>
                        
                        <p>
                            <strong className="text-white">3. AI LIMITATIONS & NO GUARANTEES:</strong> The predictions are generated by machine 
                            learning algorithms (LSTM, Prophet, XGBoost, Random Forest, Gradient Boosting, etc.) based on historical data. 
                            <span className="text-yellow-400 font-bold"> THERE IS NO GUARANTEE OF ACCURACY.</span> These models CANNOT predict:
                        </p>
                        <ul className="list-disc pl-6 text-gray-400 space-y-1">
                            <li>Unforeseen market events or crashes</li>
                            <li>Breaking news or announcements</li>
                            <li>Black swan events</li>
                            <li>Market manipulation</li>
                            <li>Regulatory changes</li>
                            <li>Economic policy shifts</li>
                            <li>Geopolitical events</li>
                        </ul>
                        
                        <p>
                            <strong className="text-white">4. PAST PERFORMANCE WARNING:</strong> <span className="text-red-400 font-bold">
                            PAST PERFORMANCE IS NOT INDICATIVE OF FUTURE RESULTS.</span> Backtesting results and historical accuracy 
                            metrics do not guarantee future prediction accuracy.
                        </p>
                        
                        <p>
                            <strong className="text-white">5. USER RESPONSIBILITY & LIABILITY WAIVER:</strong> By clicking "I Accept," 
                            you acknowledge and agree that:
                        </p>
                        <ul className="list-disc pl-6 text-gray-400 space-y-1">
                            <li>You are <span className="text-white font-bold">SOLELY RESPONSIBLE</span> for your investment decisions</li>
                            <li>You will conduct your own research before making any investment</li>
                            <li>The developers, owners, and operators of this application accept <span className="text-red-400 font-bold">
                            NO LIABILITY WHATSOEVER</span> for any loss, damage, or financial harm resulting from your use of this application</li>
                            <li>You <span className="text-white font-bold">WAIVE ALL CLAIMS</span> against the application creators for any losses</li>
                            <li>You are of legal age to make investment decisions in your jurisdiction</li>
                            <li>You understand that AI confidence scores are estimates, not guarantees</li>
                        </ul>
                        
                        <p>
                            <strong className="text-white">6. RECOMMENDATION TO SEEK PROFESSIONAL ADVICE:</strong> Before making any 
                            investment decisions, you should consult with a <span className="text-green-400">qualified financial advisor, 
                            accountant, or other professional</span> who can assess your individual financial situation.
                        </p>
                        
                        <p>
                            <strong className="text-white">7. AI CHATBOT DISCLAIMER:</strong> The AI chatbot provides automated responses 
                            based on technical analysis and market data. Its recommendations (Buy/Sell/Hold) are 
                            <span className="text-yellow-400 font-bold"> SUGGESTIONS ONLY</span> and should never be treated as 
                            professional financial advice.
                        </p>
                        
                        <p className="text-center text-gray-500 pt-4 border-t border-gray-700">
                            ⬇️ Scroll down to read all terms, then check the boxes below ⬇️
                        </p>
                    </div>

                    {/* Checkboxes */}
                    <div className="space-y-3 mb-6 bg-gray-900/50 p-4 rounded-xl border border-gray-700/50">
                        <label className="flex items-start gap-3 cursor-pointer group">
                            <input 
                                type="checkbox" 
                                checked={checkboxes.understand}
                                onChange={(e) => setCheckboxes(prev => ({...prev, understand: e.target.checked}))}
                                className="w-5 h-5 mt-0.5 rounded bg-gray-800 border-gray-600 text-red-500 focus:ring-red-500 cursor-pointer"
                            />
                            <span className="text-gray-300 text-sm group-hover:text-white transition-colors">
                                I have read and <strong>FULLY UNDERSTAND</strong> that I trade on my own risk and AI predictions 
                                are not guaranteed to be accurate
                            </span>
                        </label>
                        
                        <label className="flex items-start gap-3 cursor-pointer group">
                            <input 
                                type="checkbox" 
                                checked={checkboxes.responsible}
                                onChange={(e) => setCheckboxes(prev => ({...prev, responsible: e.target.checked}))}
                                className="w-5 h-5 mt-0.5 rounded bg-gray-800 border-gray-600 text-red-500 focus:ring-red-500 cursor-pointer"
                            />
                            <span className="text-gray-300 text-sm group-hover:text-white transition-colors">
                                I accept <strong>FULL RESPONSIBILITY</strong> for all my investment decisions and 
                                <strong> WAIVE ANY CLAIMS</strong> against the application developers for any losses
                            </span>
                        </label>
                        
                        <label className="flex items-start gap-3 cursor-pointer group">
                            <input 
                                type="checkbox" 
                                checked={checkboxes.noGuarantee}
                                onChange={(e) => setCheckboxes(prev => ({...prev, noGuarantee: e.target.checked}))}
                                className="w-5 h-5 mt-0.5 rounded bg-gray-800 border-gray-600 text-red-500 focus:ring-red-500 cursor-pointer"
                            />
                            <span className="text-gray-300 text-sm group-hover:text-white transition-colors">
                                I understand that <strong>I COULD LOSE ALL MY INVESTED CAPITAL</strong> and that 
                                confidence scores do not guarantee prediction accuracy
                            </span>
                        </label>
                    </div>

                    {/* Accept button */}
                    <div className="flex flex-col items-center gap-2">
                        {!hasScrolled && (
                            <p className="text-yellow-400 text-sm animate-pulse">
                                ⬆️ Please scroll to read all terms first
                            </p>
                        )}
                        {hasScrolled && !allChecked && (
                            <p className="text-orange-400 text-sm">
                                ☑️ Please check all boxes above to continue
                            </p>
                        )}
                        <motion.button
                            whileHover={canAccept ? { scale: 1.02 } : {}}
                            whileTap={canAccept ? { scale: 0.98 } : {}}
                            onClick={handleAccept}
                            disabled={!canAccept}
                            className={`flex items-center gap-2 px-8 py-4 font-bold rounded-xl transition-all ${
                                canAccept 
                                    ? 'bg-gradient-to-r from-green-600 to-green-500 hover:from-green-500 hover:to-green-400 text-white shadow-lg shadow-green-500/20 cursor-pointer'
                                    : 'bg-gray-700 text-gray-400 cursor-not-allowed'
                            }`}
                        >
                            <CheckCircle className="w-5 h-5" />
                            I Accept All Terms & Risks
                        </motion.button>
                        <p className="text-gray-500 text-xs mt-2">
                            By clicking "I Accept," you agree to the terms above and acknowledge that you have read and understood the risk disclosure.
                        </p>
                    </div>
                </motion.div>
            </div>
        </AnimatePresence>
    )
}
