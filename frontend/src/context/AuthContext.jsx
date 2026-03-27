import React, { createContext, useState, useEffect, useContext, useRef } from 'react'
import axios from 'axios'

const AuthContext = createContext(null)

// Set axios defaults - use relative URLs in development (Vite proxy handles /api)
const API_BASE_URL = import.meta.env.VITE_API_URL || ''
axios.defaults.baseURL = API_BASE_URL

// Token TTL: 7 days in ms. Refresh 1 hour before expiry.
const TOKEN_TTL_MS    = 7 * 24 * 60 * 60 * 1000   // 604 800 000 ms
const REFRESH_LEAD_MS = 60 * 60 * 1000             //   3 600 000 ms (1 hour)
const REFRESH_AT_MS   = TOKEN_TTL_MS - REFRESH_LEAD_MS  // 601 200 000 ms

const setAuthToken = (token) => {
    if (token) {
        axios.defaults.headers.common['Authorization'] = `Bearer ${token}`
        localStorage.setItem('market_oracle_token', token)
    } else {
        delete axios.defaults.headers.common['Authorization']
        localStorage.removeItem('market_oracle_token')
    }
}

// ─── Normalise backend error messages ────────────────────────────────────────
function normaliseLoginError(error) {
    const status = error.response?.status ?? 0
    if (status === 401) return 'Incorrect email or password'
    if (status === 422) return 'Please check your email format'
    if (status === 429) return 'Too many attempts. Please wait a minute.'
    if (status === 0 || !error.response) return 'Cannot reach the server. Check your connection.'
    return error.response?.data?.detail || error.message || 'Login failed'
}

export const AuthProvider = ({ children }) => {
    const [user, setUser]               = useState(null)
    const [loading, setLoading]         = useState(true)
    const [sessionExpired, setSessionExpired] = useState(false)
    const refreshTimerRef               = useRef(null)

    // ── Schedule a token refresh REFRESH_AT_MS after the page loads ──────────
    const scheduleRefresh = () => {
        if (refreshTimerRef.current) clearTimeout(refreshTimerRef.current)
        refreshTimerRef.current = setTimeout(async () => {
            try {
                await refreshToken()
            } catch (e) {
                console.warn('[Auth] Background token refresh failed:', e)
            }
        }, REFRESH_AT_MS)
    }

    useEffect(() => {
        const token = localStorage.getItem('market_oracle_token')
        if (token) {
            setAuthToken(token)
            fetchUser().then(() => {
                scheduleRefresh()
            })
        } else {
            setLoading(false)
        }
        return () => {
            if (refreshTimerRef.current) clearTimeout(refreshTimerRef.current)
        }
        // eslint-disable-next-line react-hooks/exhaustive-deps
    }, [])

    const fetchUser = async (retries = 2) => {
        try {
            const res = await axios.get('/api/auth/me')
            setUser(res.data)
            setSessionExpired(false)
        } catch (error) {
            const status = error.response?.status ?? 0
            if (status === 0 && retries > 0) {
                await new Promise(r => setTimeout(r, 800))
                return fetchUser(retries - 1)
            }
            if (status === 401) {
                setAuthToken(null)
                setUser(null)
                setSessionExpired(true)
            } else {
                console.warn('[Auth] Could not verify session, keeping token:', error.message)
            }
        } finally {
            setLoading(false)
        }
    }

    // ── Refresh token via POST /api/auth/refresh ──────────────────────────────
    const refreshToken = async () => {
        const currentToken = localStorage.getItem('market_oracle_token')
        if (!currentToken) return
        try {
            const res = await axios.post('/api/auth/refresh', { token: currentToken })
            const { access_token } = res.data
            setAuthToken(access_token)
            scheduleRefresh()   // reschedule for the new token
        } catch (err) {
            console.warn('[Auth] Token refresh failed:', err.message)
        }
    }

    // ── Login — with normalised error messages ────────────────────────────────
    const login = async (email, password) => {
        try {
            const params = new URLSearchParams()
            params.append('username', email)
            params.append('password', password)
            const res = await axios.post('/api/auth/token', params, {
                headers: { 'Content-Type': 'application/x-www-form-urlencoded' }
            })
            const { access_token, user } = res.data
            setAuthToken(access_token)
            setUser(user)
            setSessionExpired(false)
            scheduleRefresh()
            return user
        } catch (error) {
            throw new Error(normaliseLoginError(error))
        }
    }

    const register = async (email, password, fullName, privacyConsent = true, termsAccepted = true, activityTrackingConsent = false) => {
        const res = await axios.post('/api/auth/register', {
            email: email.trim().toLowerCase(),
            password,
            full_name: fullName,
            privacy_consent: privacyConsent,
            terms_accepted: termsAccepted,
            activity_tracking_consent: activityTrackingConsent
        })
        const { access_token, user } = res.data
        setAuthToken(access_token)
        setUser(user)
        setSessionExpired(false)
        scheduleRefresh()
        return user
    }

    const logout = () => {
        if (refreshTimerRef.current) clearTimeout(refreshTimerRef.current)
        setAuthToken(null)
        setUser(null)
        setSessionExpired(false)
    }

    // All features are unlocked — no subscription required
    const canUseFeature  = ()    => true
    const canUseRange    = ()    => true
    const canUseForecast = ()    => true
    const getToken       = ()    => localStorage.getItem('market_oracle_token')

    return (
        <AuthContext.Provider value={{
            user,
            login,
            register,
            logout,
            loading,
            sessionExpired,
            refreshToken,
            canUseFeature,
            canUseRange,
            canUseForecast,
            getToken,
        }}>
            {children}
        </AuthContext.Provider>
    )
}

export const useAuth = () => useContext(AuthContext)
