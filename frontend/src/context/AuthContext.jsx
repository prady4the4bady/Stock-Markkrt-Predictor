import React, { createContext, useState, useEffect, useContext } from 'react'
import axios from 'axios'

const AuthContext = createContext(null)

// Set axios defaults - use relative URLs in development (Vite proxy handles /api)
const API_BASE_URL = import.meta.env.VITE_API_URL || ''
axios.defaults.baseURL = API_BASE_URL

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
    const [user, setUser]     = useState(null)
    const [loading, setLoading] = useState(true)

    useEffect(() => {
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
        } catch (error) {
            const status = error.response?.status ?? 0
            if (status === 0 && retries > 0) {
                await new Promise(r => setTimeout(r, 1500))
                return fetchUser(retries - 1)
            }
            if (status === 401) {
                setAuthToken(null)
                setUser(null)
            } else {
                console.warn('[Auth] Could not verify session, keeping token:', error.message)
            }
        } finally {
            setLoading(false)
        }
    }

    const login = async (email, password) => {
        const params = new URLSearchParams()
        params.append('username', email)
        params.append('password', password)
        const res = await axios.post('/api/auth/token', params, {
            headers: { 'Content-Type': 'application/x-www-form-urlencoded' }
        })
        const { access_token, user } = res.data
        setAuthToken(access_token)
        setUser(user)
        return user
    }

    const register = async (email, password, fullName, privacyConsent = true, termsAccepted = true, activityTrackingConsent = false) => {
        const res = await axios.post('/api/auth/register', {
            email,
            password,
            full_name: fullName,
            privacy_consent: privacyConsent,
            terms_accepted: termsAccepted,
            activity_tracking_consent: activityTrackingConsent
        })
        const { access_token, user } = res.data
        setAuthToken(access_token)
        setUser(user)
        return user
    }

    const logout = () => {
        setAuthToken(null)
        setUser(null)
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
