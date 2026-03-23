/**
 * Market Oracle - Activity Tracking Service
 * Tracks user interactions within the application for personalized insights
 */
import axios from 'axios'

const API_URL = '/api/user'

class ActivityService {
    constructor() {
        this.currentSession = null
        this.sessionStartTime = null
    }

    /**
     * Start tracking an interaction session when user views a stock
     */
    async startSession(symbol, assetType, priceAtView = null) {
        try {
            const response = await axios.post(`${API_URL}/activity/interaction/start`, {
                symbol: symbol.toUpperCase(),
                asset_type: assetType,
                price_at_view: priceAtView
            })
            
            if (response.data.session_id) {
                this.currentSession = response.data.session_id
                this.sessionStartTime = Date.now()
            }
            
            return response.data
        } catch (error) {
            console.warn('Activity tracking disabled or failed:', error.message)
            return null
        }
    }

    /**
     * Update the current session with new activity
     */
    async updateSession(updates) {
        if (!this.currentSession) return null

        try {
            const response = await axios.post(`${API_URL}/activity/interaction/update`, {
                session_id: this.currentSession,
                ...updates
            })
            return response.data
        } catch (error) {
            console.warn('Failed to update session:', error.message)
            return null
        }
    }

    /**
     * End the current session
     */
    async endSession() {
        if (!this.currentSession) return null

        try {
            const response = await axios.post(`${API_URL}/activity/interaction/end`, {
                session_id: this.currentSession
            })
            
            this.currentSession = null
            this.sessionStartTime = null
            
            return response.data
        } catch (error) {
            console.warn('Failed to end session:', error.message)
            return null
        }
    }

    /**
     * Track a simple stock view
     */
    async trackView(symbol, assetType, durationSeconds = 0) {
        try {
            const response = await axios.post(`${API_URL}/activity/view`, {
                symbol: symbol.toUpperCase(),
                asset_type: assetType,
                duration_seconds: durationSeconds
            })
            return response.data
        } catch (error) {
            console.warn('Failed to track view:', error.message)
            return null
        }
    }

    // ==================== Watchlist Methods ====================

    /**
     * Get user's watchlist
     */
    async getWatchlist(activeOnly = true) {
        try {
            const response = await axios.get(`${API_URL}/watchlist`, {
                params: { active_only: activeOnly }
            })
            return response.data
        } catch (error) {
            console.error('Failed to get watchlist:', error.message)
            return []
        }
    }

    /**
     * Add symbol to watchlist
     */
    async addToWatchlist(symbol, assetType, notes = null, alertAbove = null, alertBelow = null) {
        try {
            const response = await axios.post(`${API_URL}/watchlist`, {
                symbol: symbol.toUpperCase(),
                asset_type: assetType,
                notes,
                alert_price_above: alertAbove,
                alert_price_below: alertBelow
            })
            return response.data
        } catch (error) {
            console.error('Failed to add to watchlist:', error.message)
            throw error
        }
    }

    /**
     * Remove symbol from watchlist
     */
    async removeFromWatchlist(symbol) {
        try {
            // URL-encode the symbol to handle symbols with slashes (e.g., BTC/USDT)
            const encodedSymbol = encodeURIComponent(symbol.toUpperCase())
            const response = await axios.delete(`${API_URL}/watchlist/${encodedSymbol}`)
            return response.data
        } catch (error) {
            console.error('Failed to remove from watchlist:', error.message)
            throw error
        }
    }

    // ==================== Insights Methods ====================

    /**
     * Get user's top viewed stocks
     */
    async getTopViewed(limit = 10) {
        try {
            const response = await axios.get(`${API_URL}/activity/top-viewed`, {
                params: { limit }
            })
            return response.data
        } catch (error) {
            console.error('Failed to get top viewed:', error.message)
            return []
        }
    }

    /**
     * Get user's prediction history
     */
    async getPredictionHistory(symbol = null, limit = 50) {
        try {
            const response = await axios.get(`${API_URL}/activity/predictions`, {
                params: { symbol, limit }
            })
            return response.data
        } catch (error) {
            console.error('Failed to get prediction history:', error.message)
            return []
        }
    }

    /**
     * Get user insights and analytics
     */
    async getInsights() {
        try {
            const response = await axios.get(`${API_URL}/insights`)
            return response.data
        } catch (error) {
            console.error('Failed to get insights:', error.message)
            return null
        }
    }

    /**
     * Get confidence boost for a symbol
     */
    async getConfidenceBoost(symbol, baseConfidence = 0.7) {
        try {
            const response = await axios.get(`${API_URL}/insights/confidence-boost/${symbol}`, {
                params: { base_confidence: baseConfidence }
            })
            return response.data
        } catch (error) {
            console.warn('Failed to get confidence boost:', error.message)
            return null
        }
    }

    // ==================== Preferences Methods ====================

    /**
     * Get user preferences
     */
    async getPreferences() {
        try {
            const response = await axios.get(`${API_URL}/preferences`)
            return response.data
        } catch (error) {
            console.error('Failed to get preferences:', error.message)
            return null
        }
    }

    /**
     * Update user preferences
     */
    async updatePreferences(updates) {
        try {
            const response = await axios.put(`${API_URL}/preferences`, updates)
            return response.data
        } catch (error) {
            console.error('Failed to update preferences:', error.message)
            throw error
        }
    }

    // ==================== Data Export ====================

    /**
     * Export all user data (GDPR compliance)
     */
    async exportData() {
        try {
            const response = await axios.get(`${API_URL}/export`)
            return response.data
        } catch (error) {
            console.error('Failed to export data:', error.message)
            throw error
        }
    }

    /**
     * Request data deletion (GDPR compliance)
     */
    async requestDataDeletion() {
        try {
            const response = await axios.delete(`${API_URL}/data`)
            return response.data
        } catch (error) {
            console.error('Failed to request deletion:', error.message)
            throw error
        }
    }
}

// Export singleton instance
export const activityService = new ActivityService()
export default activityService
