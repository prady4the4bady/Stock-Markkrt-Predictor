/**
 * Market Oracle - Subscription Service
 * Handles subscription management, billing, and payment processing
 */
import axios from 'axios'

const API_URL = '/api/subscription'

class SubscriptionService {
    /**
     * Get available subscription plans
     */
    async getPlans() {
        try {
            const response = await axios.get(`${API_URL}/plans`)
            return response.data
        } catch (error) {
            console.error('Failed to fetch plans:', error)
            throw error
        }
    }

    /**
     * Get current subscription status
     */
    async getStatus() {
        try {
            const response = await axios.get(`${API_URL}/status`)
            return response.data
        } catch (error) {
            console.error('Failed to fetch subscription status:', error)
            throw error
        }
    }

    /**
     * Create PayPal order for subscription
     */
    async createOrder(plan) {
        try {
            const response = await axios.post(`${API_URL}/create-order`, { plan })
            return response.data
        } catch (error) {
            console.error('Failed to create order:', error)
            throw error
        }
    }

    /**
     * Capture PayPal order after approval
     */
    async captureOrder(orderId) {
        try {
            const response = await axios.post(`${API_URL}/capture-order/${orderId}`)
            return response.data
        } catch (error) {
            console.error('Failed to capture order:', error)
            throw error
        }
    }

    /**
     * Activate subscription (for demo/development)
     */
    async activateSubscription(plan, subscriptionId = null) {
        try {
            const response = await axios.post(`${API_URL}/activate`, {
                plan,
                subscription_id: subscriptionId
            })
            return response.data
        } catch (error) {
            console.error('Failed to activate subscription:', error)
            throw error
        }
    }

    /**
     * Cancel subscription
     */
    async cancelSubscription() {
        try {
            const response = await axios.post(`${API_URL}/cancel`)
            return response.data
        } catch (error) {
            console.error('Failed to cancel subscription:', error)
            throw error
        }
    }

    /**
     * Check if user can make a prediction
     */
    async checkPredictionLimit(forecastDays, rangePeriod) {
        try {
            const response = await axios.post(`${API_URL}/check-prediction`, {
                forecast_days: forecastDays,
                range_period: rangePeriod
            })
            return response.data
        } catch (error) {
            console.error('Failed to check prediction limit:', error)
            throw error
        }
    }

    /**
     * Record a prediction use
     */
    async usePrediction() {
        try {
            const response = await axios.post(`${API_URL}/use-prediction`)
            return response.data
        } catch (error) {
            console.error('Failed to record prediction use:', error)
            throw error
        }
    }

    /**
     * Get billing history (invoices)
     * This returns mock data for now - in production, integrate with PayPal API
     */
    async getBillingHistory() {
        try {
            const status = await this.getStatus()
            
            // Generate billing history based on subscription
            if (status.plan === 'free' || !status.is_premium) {
                return { invoices: [] }
            }

            // Mock billing history - in production, fetch from PayPal or database
            const now = new Date()
            const invoices = []
            const price = status.plan === 'elite' ? 24.99 : 9.99

            // Generate last 3 months of invoices if subscribed
            for (let i = 0; i < 3; i++) {
                const date = new Date(now.getFullYear(), now.getMonth() - i, 1)
                if (status.subscription_end && date <= new Date(status.subscription_end)) {
                    invoices.push({
                        id: `INV-${date.getFullYear()}${String(date.getMonth() + 1).padStart(2, '0')}`,
                        date: date.toISOString(),
                        amount: price,
                        status: 'paid',
                        plan: status.plan
                    })
                }
            }

            return { invoices }
        } catch (error) {
            console.error('Failed to fetch billing history:', error)
            return { invoices: [] }
        }
    }

    /**
     * Get payment methods
     * This returns mock data - in production, fetch from payment provider
     */
    async getPaymentMethods() {
        try {
            const status = await this.getStatus()
            
            if (status.plan === 'free' || !status.is_premium) {
                return { methods: [] }
            }

            // Mock payment method - in production, fetch from PayPal or Stripe
            return {
                methods: [
                    {
                        id: 'pm_default',
                        type: 'paypal',
                        email: 'user@example.com', // Would be actual PayPal email
                        isDefault: true,
                        lastUsed: new Date().toISOString()
                    }
                ]
            }
        } catch (error) {
            console.error('Failed to fetch payment methods:', error)
            return { methods: [] }
        }
    }

    /**
     * Format price for display
     */
    formatPrice(amount, currency = 'USD') {
        return new Intl.NumberFormat('en-US', {
            style: 'currency',
            currency: currency
        }).format(amount)
    }

    /**
     * Get feature comparison for upgrade modal
     */
    getFeatureComparison(currentPlan, targetPlan) {
        const features = {
            free: {
                predictions: '3/day',
                forecast: '1 hour',
                watchlist: '1 slot',
                realtime: false,
                indicators: false,
                export: false
            },
            pro: {
                predictions: '50/day',
                forecast: '7 days',
                watchlist: '10 slots',
                realtime: true,
                indicators: true,
                export: true
            },
            elite: {
                predictions: 'Unlimited',
                forecast: '30 days',
                watchlist: 'Unlimited',
                realtime: true,
                indicators: true,
                export: true,
                api: true,
                priority: true
            }
        }

        return {
            current: features[currentPlan] || features.free,
            target: features[targetPlan] || features.free
        }
    }
}

// Export singleton instance
const subscriptionService = new SubscriptionService()
export default subscriptionService
