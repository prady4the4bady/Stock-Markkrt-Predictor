import { motion } from 'framer-motion'
import { BarChart2 } from 'lucide-react'

// ─── Model name shortener ─────────────────────────────────────────────────────
const SHORT_NAMES = {
  'nemotron-3-super-120b': 'Nemotron-120B',
  'nemotron': 'Nemotron-120B',
  'kimi-k2.5': 'Kimi K2.5',
  'kimi': 'Kimi K2.5',
  'glm5': 'GLM5',
  'glm': 'GLM5',
  'minimax-m2.5': 'MiniMax M2.5',
  'minimax': 'MiniMax M2.5',
  'llama-3.3-70b': 'Llama 70B',
  'llama': 'Llama 70B',
}

function shortenModel(name) {
  if (!name) return name
  const lower = name.toLowerCase()
  for (const [key, short] of Object.entries(SHORT_NAMES)) {
    if (lower.includes(key)) return short
  }
  return name
}

// ─── Direction badge colours ──────────────────────────────────────────────────
function directionColor(dir) {
  if (!dir) return 'rgba(255,255,255,0.4)'
  switch (dir.toUpperCase()) {
    case 'UP':   return '#c8ff00'
    case 'DOWN': return '#ff5500'
    default:     return 'rgba(255,255,255,0.55)'
  }
}

// ─── Verdict badge colours ────────────────────────────────────────────────────
function verdictStyle(verdict) {
  switch ((verdict || '').toUpperCase()) {
    case 'BULLISH':
      return { color: '#020209', background: '#c8ff00', fontWeight: 700 }
    case 'BEARISH':
      return { color: '#fff', background: '#ff5500', fontWeight: 700 }
    default:
      return { color: '#020209', background: 'rgba(255,255,255,0.60)', fontWeight: 700 }
  }
}

// ─── Skeleton placeholder ─────────────────────────────────────────────────────
function CouncilSkeleton() {
  return (
    <div style={{ padding: '16px 20px' }}>
      <div
        style={{
          fontSize: 13,
          color: 'rgba(255,255,255,0.35)',
          fontStyle: 'italic',
          letterSpacing: '0.03em',
        }}
      >
        Council analyzing…
      </div>
      <div
        style={{
          marginTop: 10,
          display: 'flex',
          gap: 8,
          flexWrap: 'wrap',
        }}
      >
        {[90, 70, 80, 65, 75].map((w, i) => (
          <div
            key={i}
            style={{
              height: 10,
              width: w,
              borderRadius: 6,
              background: 'rgba(255,255,255,0.08)',
              animation: 'pulse 1.6s ease-in-out infinite',
              animationDelay: `${i * 0.15}s`,
            }}
          />
        ))}
      </div>
    </div>
  )
}

// ─── Main component ───────────────────────────────────────────────────────────
export default function CouncilVerdict({ verdict, symbol }) {
  const cardStyle = {
    background: 'rgba(255,255,255,0.04)',
    border: '1px solid rgba(255,255,255,0.09)',
    borderRadius: 16,
    backdropFilter: 'blur(12px)',
    WebkitBackdropFilter: 'blur(12px)',
    marginTop: 16,
    overflow: 'hidden',
  }

  return (
    <motion.div
      initial={{ opacity: 0, y: 14 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay: 0.42, duration: 0.35 }}
      style={cardStyle}
    >
      {/* Header */}
      <div
        style={{
          display: 'flex',
          alignItems: 'center',
          gap: 8,
          padding: '14px 20px 10px',
          borderBottom: '1px solid rgba(255,255,255,0.07)',
        }}
      >
        <BarChart2 size={15} color="#c8ff00" />
        <span
          style={{
            fontSize: 13,
            fontWeight: 600,
            color: 'rgba(255,255,255,0.85)',
            letterSpacing: '0.04em',
            textTransform: 'uppercase',
          }}
        >
          Model Council
        </span>
        {symbol && (
          <span
            style={{
              marginLeft: 4,
              fontSize: 11,
              color: 'rgba(255,255,255,0.35)',
              fontWeight: 400,
            }}
          >
            · {symbol}
          </span>
        )}
      </div>

      {/* Content */}
      {!verdict ? (
        <CouncilSkeleton />
      ) : (
        <div style={{ padding: '14px 20px 18px' }}>
          {/* Verdict badge + model count */}
          <div
            style={{
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'space-between',
              marginBottom: 12,
            }}
          >
            <span
              style={{
                fontSize: 18,
                fontWeight: 800,
                letterSpacing: '0.06em',
                padding: '4px 14px',
                borderRadius: 8,
                ...verdictStyle(verdict.verdict),
              }}
            >
              {verdict.verdict || 'NEUTRAL'}
            </span>
            <span
              style={{
                fontSize: 11,
                color: 'rgba(255,255,255,0.40)',
                fontWeight: 500,
              }}
            >
              {verdict.model_count ?? 0} / 5 models
            </span>
          </div>

          {/* Agreement bar */}
          <div style={{ marginBottom: 14 }}>
            <div
              style={{
                display: 'flex',
                justifyContent: 'space-between',
                marginBottom: 5,
              }}
            >
              <span style={{ fontSize: 11, color: 'rgba(255,255,255,0.45)' }}>
                Agreement
              </span>
              <span
                style={{
                  fontSize: 11,
                  fontWeight: 600,
                  color: '#c8ff00',
                }}
              >
                {typeof verdict.agreement === 'number'
                  ? `${verdict.agreement.toFixed(0)}%`
                  : '—'}
              </span>
            </div>
            <div
              style={{
                height: 6,
                borderRadius: 4,
                background: 'rgba(255,255,255,0.08)',
                overflow: 'hidden',
              }}
            >
              <motion.div
                initial={{ width: 0 }}
                animate={{
                  width: `${Math.min(100, verdict.agreement ?? 0)}%`,
                }}
                transition={{ duration: 0.6, ease: 'easeOut' }}
                style={{
                  height: '100%',
                  borderRadius: 4,
                  background: 'linear-gradient(90deg, #c8ff00 0%, #a0d400 100%)',
                }}
              />
            </div>
          </div>

          {/* Individual model votes */}
          {Array.isArray(verdict.votes) && verdict.votes.length > 0 && (
            <div style={{ display: 'flex', flexDirection: 'column', gap: 7 }}>
              {verdict.votes.map((vote, idx) => (
                <div
                  key={idx}
                  style={{
                    display: 'flex',
                    alignItems: 'center',
                    gap: 8,
                  }}
                >
                  {/* Model name */}
                  <span
                    style={{
                      fontSize: 11,
                      color: 'rgba(255,255,255,0.55)',
                      minWidth: 100,
                      flexShrink: 0,
                    }}
                  >
                    {shortenModel(vote.model)}
                  </span>

                  {/* Direction badge */}
                  <span
                    style={{
                      fontSize: 10,
                      fontWeight: 700,
                      letterSpacing: '0.05em',
                      padding: '2px 7px',
                      borderRadius: 5,
                      background: `${directionColor(vote.direction)}22`,
                      color: directionColor(vote.direction),
                      border: `1px solid ${directionColor(vote.direction)}55`,
                      minWidth: 42,
                      textAlign: 'center',
                    }}
                  >
                    {vote.direction || '—'}
                  </span>

                  {/* Confidence bar */}
                  <div
                    style={{
                      flex: 1,
                      height: 5,
                      borderRadius: 3,
                      background: 'rgba(255,255,255,0.07)',
                      overflow: 'hidden',
                    }}
                  >
                    <motion.div
                      initial={{ width: 0 }}
                      animate={{
                        width: `${Math.min(100, (vote.confidence ?? 0) * 100)}%`,
                      }}
                      transition={{ duration: 0.5, delay: idx * 0.07 }}
                      style={{
                        height: '100%',
                        borderRadius: 3,
                        background: directionColor(vote.direction),
                        opacity: 0.75,
                      }}
                    />
                  </div>

                  {/* Confidence number */}
                  <span
                    style={{
                      fontSize: 10,
                      color: 'rgba(255,255,255,0.35)',
                      minWidth: 32,
                      textAlign: 'right',
                    }}
                  >
                    {typeof vote.confidence === 'number'
                      ? `${(vote.confidence * 100).toFixed(0)}%`
                      : ''}
                  </span>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* Keyframe styles (injected once via a style tag) */}
      <style>{`
        @keyframes pulse {
          0%, 100% { opacity: 0.4; }
          50% { opacity: 0.9; }
        }
      `}</style>
    </motion.div>
  )
}
