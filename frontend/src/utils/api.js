/**
 * NexusTrader — shared Axios instance
 *
 * - Automatically injects the browser's IANA timezone as X-Timezone on every
 *   request so the backend returns timestamps in the user's local time.
 * - Normalises all API errors into a consistent `error.nexus` shape so
 *   components never need to dig into `error.response.data.*` manually.
 *
 * Usage:
 *   import api from '../utils/api'
 *   const { data } = await api.get('/predict/AAPL', { params: { days: 7 } })
 */
import axios from 'axios'

// Detect the browser's IANA timezone once at module load time.
// Falls back to 'UTC' on browsers that don't support Intl.
export const BROWSER_TZ =
    (typeof Intl !== 'undefined' &&
        Intl.DateTimeFormat().resolvedOptions().timeZone) ||
    'UTC'

// ── Axios instance ────────────────────────────────────────────────────────────
const api = axios.create({
    baseURL: '/api',
    timeout: 90_000,
    headers: {
        'Content-Type': 'application/json',
        'X-Timezone': BROWSER_TZ,
    },
})

// ── Error message map ─────────────────────────────────────────────────────────
const ERROR_MESSAGES = {
    0:   'Cannot connect to the server — make sure the backend is running.',
    400: 'Bad request — check the symbol or parameters.',
    401: 'Please log in to continue.',
    403: "You don't have permission to do that.",
    404: 'Symbol not found — check that it\'s a valid ticker.',
    405: 'Method not allowed.',
    408: 'Request timed out — please try again.',
    422: 'Invalid input — check the parameters you entered.',
    429: 'Too many requests — please wait a moment and try again.',
    500: 'Server error — we\'re looking into it.',
    502: 'Backend unavailable — please try again shortly.',
    503: 'Service temporarily unavailable — data cache is recovering, please retry.',
}

function defaultMessage(status) {
    return ERROR_MESSAGES[status] ?? 'An unexpected error occurred.'
}

// ── Response interceptor — normalise errors ───────────────────────────────────
api.interceptors.response.use(
    (response) => response,
    (error) => {
        const status  = error.response?.status ?? 0
        const data    = error.response?.data ?? {}

        // Backend now returns { error, message, detail } — use those when available.
        // Fall back to defaults for older endpoints or network errors.
        error.nexus = {
            status,
            code:    data.error   ?? (status === 0 ? 'NETWORK_ERROR' : `HTTP_${status}`),
            message: data.message ?? defaultMessage(status),
            detail:  data.detail  ?? error.message ?? '',
        }

        return Promise.reject(error)
    }
)

export default api
