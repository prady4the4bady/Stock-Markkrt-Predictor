import React, { createContext, useState, useEffect, useContext } from 'react'
import axios from 'axios'

const AuthContext = createContext(null)

// Set axios defaults - use relative URLs in development (Vite proxy handles /api)
// In production, VITE_API_URL must be set to the backend URL (e.g. https://nexustrader-api.onrender.com)
const API_BASE_URL = import.meta.env.VITE_API_URL || ''
axios.defaults.baseURL = API_BASE_URL

// Default free plan limits
const FREE_PLAN_LIMITS = {
    predictions_per_day: 3,
    watchlist_limit: 1,
    max_forecast_days: 0.04,
    allowed_ranges: ["1h"],
    allowed_forecasts: [0.04],
    show_model_weights: false,
    show_confidence_details: false,
    show_technical_indicators: false,
    realtime_data: false,
    export_enabled: false
}

// Configure axios default header if token exists
const setAuthToken = (token) => {
    if (token) {
        axios.defaults.headers.common['Authorization'] = `Bearer ${token}`
        localStorage.setItem('market_oracle_token', token)
    } else {
        delete axios.defaults.headers.common['Authorization']
        localStorage.removeItem('market_oracle_token')
    }
}

export const AuthProvider = ({ children }) => {
    const [user, setUser] = useState(null)
    const [loading, setLoading] = useState(true)
    const [subscription, setSubscription] = useState(null)
    const [planLimits, setPlanLimits] = useState(FREE_PLAN_LIMITS)
    useEffect(() => {
        // Check for token on load
        const token = localStorage.getItem('market_oracle_token')
        if (token) {
            setAuthToken(token)
            fetchUser()
        } else {
            setLoading(false)
        }
    }, [])

    const fetchUser = async (retries = 2) => {
        try {
            const res = await axios.get('/api/auth/me')
            setUser(res.data)
            // Fetch subscription status after user is loaded
            await fetchSubscriptionStatus()
        } catch (error) {
            const status = error.response?.status ?? 0
            if (status === 0 && retries > 0) {
                // Network error — backend is likely restarting. Retry after 1.5 s.
                await new Promise(r => setTimeout(r, 1500))
                return fetchUser(retries - 1)
            }
            if (status === 401) {
                // Token is genuinely invalid/expired — clear and force re-login.
                setAuthToken(null)
                setUser(null)
            } else {
                // Transient failure (5xx, network down after retries) — keep the
                // token so the user isn't logged out by a backend restart.
                console.warn('[Auth] Could not verify session, keeping token:', error.message)
            }
        } finally {
            setLoading(false)
        }
    }

    const fetchSubscriptionStatus = async () => {
        try {
            const res = await axios.get('/api/subscription/status')
            setSubscription(res.data)
            // Set plan limits based on subscription
            if (res.data.limits) {
                setPlanLimits({
                    ...FREE_PLAN_LIMITS,
                    ...res.data.limits,
                    allowed_forecasts: getAllowedForecasts(res.data.limits.max_forecast_days)
                })
            }
        } catch (error) {
            console.warn("Could not fetch subscription status", error)
            // Default to free plan
            setPlanLimits(FREE_PLAN_LIMITS)
        }
    }

    // Convert max forecast days to allowed forecast options
    const getAllowedForecasts = (maxDays) => {
        const allForecasts = [0.04, 0.5, 1, 3, 7, 14, 30]
        return allForecasts.filter(d => d <= maxDays)
    }

    const login = async (email, password) => {
        console.log('[Auth] Attempting login for:', email)
        
        // OAuth2 requires URL-encoded form data
        const params = new URLSearchParams()
        params.append('username', email)
        params.append('password', password)

        try {
            const res = await axios.post('/api/auth/token', params, {
                headers: {
                    'Content-Type': 'application/x-www-form-urlencoded'
                }
            })
            console.log('[Auth] Login response:', res.status)
            const { access_token, user } = res.data

            setAuthToken(access_token)
            setUser(user)
            // Fetch subscription after successful login
            await fetchSubscriptionStatus()
            return user
        } catch (error) {
            console.error('[Auth] Login error:', error.response?.data || error.message)
            throw error
        }
    }

    const register = async (email, password, fullName, privacyConsent = true, termsAccepted = true, activityTrackingConsent = false) => {
        console.log('[Auth] Attempting registration for:', email)
        try {
            const res = await axios.post('/api/auth/register', {
                email,
                password,
                full_name: fullName,
                privacy_consent: privacyConsent,
                terms_accepted: termsAccepted,
                activity_tracking_consent: activityTrackingConsent
            })
            console.log('[Auth] Registration response:', res.status)
            const { access_token, user } = res.data

            setAuthToken(access_token)
            setUser(user)
            // Fetch subscription after successful registration
            await fetchSubscriptionStatus()
            return user
        } catch (error) {
            console.error('[Auth] Registration error:', error.response?.data || error.message)
            throw error
        }
    }

    const logout = () => {
        setAuthToken(null)
        setUser(null)
        setSubscription(null)
        setPlanLimits(FREE_PLAN_LIMITS)
    }

    // Check if a feature is available
    const canUseFeature = (feature) => {
        if (!planLimits) return false
        return planLimits[feature] === true || planLimits[feature] === -1
    }

    // ── SUBSCRIPTION GATE QUARANTINE ──────────────────────────────────────
    // All ranges and forecast periods are unlocked for all accounts (beta).
    //
    // TO RE-ENABLE (vibe coders / future devs):
    //   1. Remove the two `return true` lines below.
    //   2. Restore the original plan-limit checks:
    //        canUseRange   → if (!planLimits?.allowed_ranges) return false
    //                        return planLimits.allowed_ranges.includes(range)
    //        canUseForecast → if (!planLimits?.max_forecast_days) return false
    //                         if (planLimits.max_forecast_days === -1) return true
    //                         return days <= planLimits.max_forecast_days
    //   3. Also restore the check-prediction API call in Dashboard.jsx
    //      (search for "SUBSCRIPTION GATE QUARANTINE" there).
    // ──────────────────────────────────────────────────────────────────────

    // Check if a range is allowed
    const canUseRange = (range) => true    // QUARANTINED — all ranges unlocked

    // Check if a forecast period is allowed
    const canUseForecast = (days) => true  // QUARANTINED — all forecast periods unlocked

    // Get remaining predictions for today
    const getRemainingPredictions = () => {
        if (!subscription) return 0
        if (planLimits.predictions_per_day === -1) return Infinity
        return Math.max(0, planLimits.predictions_per_day - (subscription.predictions_today || 0))
    }

    // Read-only token accessor — SubscriptionSuccess and other consumers use this
    const getToken = () => localStorage.getItem('market_oracle_token')

    return (
        <AuthContext.Provider value={{
            user,
            login,
            register,
            logout,
            loading,
            subscription,
            planLimits,
            canUseFeature,
            canUseRange,
            canUseForecast,
            getRemainingPredictions,
            refreshSubscription: fetchSubscriptionStatus,
            getToken
        }}>
            {children}
        </AuthContext.Provider>
    )
}

export const useAuth = () => useContext(AuthContext)
