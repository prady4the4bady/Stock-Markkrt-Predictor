import { useState, useEffect, useMemo, useCallback } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import {
  TrendingUp, TrendingDown, Minus, RefreshCw, AlertCircle,
  Filter, Search, Star, BarChart2, Zap, Globe2, ChevronDown,
  ChevronUp, Clock, DollarSign, Activity,
} from 'lucide-react';

const API = '/api/listings';

// ── helpers ────────────────────────────────────────────────────────────────
const fmt = (n, digits = 2) =>
  n == null ? '—' : Number(n).toLocaleString('en-US', {
    minimumFractionDigits: digits,
    maximumFractionDigits: digits,
  });

const fmtVol = (v) => {
  if (v == null || v === 0) return '—';
  if (v >= 1e9) return `$${(v / 1e9).toFixed(2)}B`;
  if (v >= 1e6) return `$${(v / 1e6).toFixed(2)}M`;
  if (v >= 1e3) return `$${(v / 1e3).toFixed(1)}K`;
  return `$${fmt(v)}`;
};

const ChangeCell = ({ value }) => {
  const v = Number(value);
  if (isNaN(v) || v === 0)
    return <span className="text-gray-400 flex items-center gap-0.5"><Minus size={10} /> 0.00%</span>;
  if (v > 0)
    return <span className="text-emerald-400 flex items-center gap-0.5"><TrendingUp size={10} /> +{fmt(v)}%</span>;
  return <span className="text-red-400 flex items-center gap-0.5"><TrendingDown size={10} /> {fmt(v)}%</span>;
};

const Badge = ({ label, color = 'cyan' }) => {
  const map = {
    cyan:   'bg-cyan-500/15 text-cyan-400 border border-cyan-500/30',
    emerald:'bg-emerald-500/15 text-emerald-400 border border-emerald-500/30',
    amber:  'bg-amber-500/15 text-amber-400 border border-amber-500/30',
    red:    'bg-red-500/15 text-red-400 border border-red-500/30',
    purple: 'bg-purple-500/15 text-purple-400 border border-purple-500/30',
    gray:   'bg-gray-700/50 text-gray-400 border border-gray-600/30',
  };
  return (
    <span className={`text-[9px] px-1.5 py-0.5 rounded font-semibold tracking-wide uppercase ${map[color] || map.gray}`}>
      {label}
    </span>
  );
};

const statusColor = (s) =>
  ({ upcoming: 'emerald', priced: 'cyan', withdrawn: 'red' }[s] || 'gray');

// ── crypto table ────────────────────────────────────────────────────────────
function CryptoTable({ items, onPredict }) {
  const [sortKey, setSortKey] = useState('volume_24h');
  const [sortDir, setSortDir] = useState('desc');
  const [page, setPage] = useState(0);
  const PAGE = 25;

  const sorted = useMemo(() => {
    const copy = [...items];
    copy.sort((a, b) => {
      const av = a[sortKey] ?? 0;
      const bv = b[sortKey] ?? 0;
      return sortDir === 'asc' ? av - bv : bv - av;
    });
    return copy;
  }, [items, sortKey, sortDir]);

  const paged = sorted.slice(page * PAGE, (page + 1) * PAGE);
  const pages = Math.ceil(sorted.length / PAGE);

  const toggleSort = (key) => {
    if (sortKey === key) setSortDir(d => d === 'asc' ? 'desc' : 'asc');
    else { setSortKey(key); setSortDir('desc'); }
    setPage(0);
  };

  const SortIcon = ({ k }) =>
    sortKey !== k ? <ChevronDown size={10} className="opacity-30" /> :
    sortDir === 'desc' ? <ChevronDown size={10} className="text-cyan-400" /> :
    <ChevronUp size={10} className="text-cyan-400" />;

  const Th = ({ k, children, right = false }) => (
    <th
      className={`py-2 px-3 text-[10px] font-semibold tracking-widest text-gray-500 uppercase cursor-pointer hover:text-cyan-400 transition-colors select-none ${right ? 'text-right' : 'text-left'}`}
      onClick={() => toggleSort(k)}
    >
      <span className="inline-flex items-center gap-1">
        {children}<SortIcon k={k} />
      </span>
    </th>
  );

  return (
    <div>
      <div className="overflow-x-auto rounded-xl border border-white/5">
        <table className="w-full text-sm">
          <thead className="bg-white/3">
            <tr>
              <th className="py-2 px-3 text-[10px] text-left font-semibold text-gray-500 uppercase tracking-widest">#</th>
              <th className="py-2 px-3 text-[10px] text-left font-semibold text-gray-500 uppercase tracking-widest">Pair</th>
              <Th k="price_usdt" right>Price (USDT)</Th>
              <Th k="change_24h" right>24h Change</Th>
              <Th k="volume_24h" right>24h Volume</Th>
              <th className="py-2 px-3 text-[10px] text-center font-semibold text-gray-500 uppercase tracking-widest">Exchange</th>
              <th className="py-2 px-3 text-[10px] text-center font-semibold text-gray-500 uppercase tracking-widest">Status</th>
              <th className="py-2 px-3 text-[10px] text-center font-semibold text-gray-500 uppercase tracking-widest">Actions</th>
            </tr>
          </thead>
          <tbody>
            {paged.map((item, idx) => (
              <motion.tr
                key={item.symbol}
                initial={{ opacity: 0, y: 4 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: idx * 0.01 }}
                className="border-t border-white/4 hover:bg-white/4 transition-colors group"
              >
                <td className="py-2.5 px-3 text-gray-600 text-[11px]">
                  {page * PAGE + idx + 1}
                </td>
                <td className="py-2.5 px-3">
                  <div className="flex items-center gap-2">
                    <div className="w-7 h-7 rounded-full bg-gradient-to-br from-cyan-500/30 to-purple-500/30 border border-white/10 flex items-center justify-center text-[9px] font-bold text-cyan-300">
                      {item.base_asset?.slice(0, 3)}
                    </div>
                    <div>
                      <div className="font-semibold text-white text-xs">{item.base_asset}</div>
                      <div className="text-[10px] text-gray-500">{item.symbol}</div>
                    </div>
                    {item.is_new === 1 && <Badge label="NEW" color="cyan" />}
                  </div>
                </td>
                <td className="py-2.5 px-3 text-right font-mono text-xs text-white">
                  ${item.price_usdt > 0 ? fmt(item.price_usdt, item.price_usdt < 0.01 ? 6 : 4) : '—'}
                </td>
                <td className="py-2.5 px-3 text-right text-xs">
                  <ChangeCell value={item.change_24h} />
                </td>
                <td className="py-2.5 px-3 text-right text-xs text-gray-300 font-mono">
                  {fmtVol(item.volume_24h)}
                </td>
                <td className="py-2.5 px-3 text-center">
                  <Badge label={item.exchange || 'Binance'} color="purple" />
                </td>
                <td className="py-2.5 px-3 text-center">
                  <Badge
                    label={item.status || 'TRADING'}
                    color={item.status === 'TRADING' ? 'emerald' : 'gray'}
                  />
                </td>
                <td className="py-2.5 px-3 text-center">
                  <button
                    onClick={() => onPredict?.(item.base_asset + '/USDT')}
                    className="opacity-0 group-hover:opacity-100 transition-opacity text-[10px] px-2 py-1 rounded bg-cyan-500/20 text-cyan-400 hover:bg-cyan-500/30 border border-cyan-500/30"
                  >
                    <span className="flex items-center gap-1"><BarChart2 size={9} /> Predict</span>
                  </button>
                </td>
              </motion.tr>
            ))}
          </tbody>
        </table>
      </div>
      {/* Pagination */}
      {pages > 1 && (
        <div className="flex items-center justify-between mt-3 px-1">
          <span className="text-[11px] text-gray-500">
            {page * PAGE + 1}–{Math.min((page + 1) * PAGE, sorted.length)} of {sorted.length}
          </span>
          <div className="flex gap-1">
            <button
              disabled={page === 0}
              onClick={() => setPage(p => p - 1)}
              className="px-3 py-1 rounded text-[11px] border border-white/10 text-gray-400 hover:text-white disabled:opacity-30 disabled:cursor-not-allowed"
            >
              Prev
            </button>
            {[...Array(Math.min(pages, 7))].map((_, i) => {
              const pg = pages <= 7 ? i : i + Math.max(0, page - 3);
              if (pg >= pages) return null;
              return (
                <button
                  key={pg}
                  onClick={() => setPage(pg)}
                  className={`px-2.5 py-1 rounded text-[11px] border transition-colors ${
                    pg === page
                      ? 'border-cyan-500/50 bg-cyan-500/20 text-cyan-300'
                      : 'border-white/10 text-gray-400 hover:text-white'
                  }`}
                >
                  {pg + 1}
                </button>
              );
            })}
            <button
              disabled={page >= pages - 1}
              onClick={() => setPage(p => p + 1)}
              className="px-3 py-1 rounded text-[11px] border border-white/10 text-gray-400 hover:text-white disabled:opacity-30 disabled:cursor-not-allowed"
            >
              Next
            </button>
          </div>
        </div>
      )}
    </div>
  );
}

// ── IPO table ────────────────────────────────────────────────────────────────
function IPOTable({ items, onPredict }) {
  return (
    <div className="overflow-x-auto rounded-xl border border-white/5">
      <table className="w-full text-sm">
        <thead className="bg-white/3">
          <tr>
            {['Symbol', 'Company', 'Exchange', 'IPO Date', 'Offer Price', 'Shares', 'Sector', 'Status', 'Actions'].map(h => (
              <th key={h} className="py-2 px-3 text-[10px] text-left font-semibold text-gray-500 uppercase tracking-widest">
                {h}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {items.map((item, idx) => (
            <motion.tr
              key={item.symbol + idx}
              initial={{ opacity: 0, y: 4 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: idx * 0.02 }}
              className="border-t border-white/4 hover:bg-white/4 transition-colors group"
            >
              <td className="py-2.5 px-3">
                <div className="font-semibold text-white text-xs">{item.symbol || '—'}</div>
              </td>
              <td className="py-2.5 px-3">
                <div className="text-xs text-gray-200 max-w-[180px] truncate" title={item.company_name}>
                  {item.company_name || '—'}
                </div>
              </td>
              <td className="py-2.5 px-3">
                <div className="text-xs text-gray-400">{item.exchange || '—'}</div>
              </td>
              <td className="py-2.5 px-3">
                <div className="text-xs text-gray-300 font-mono">{item.ipo_date || '—'}</div>
              </td>
              <td className="py-2.5 px-3">
                <div className="text-xs text-white font-mono">
                  {item.offer_price ? `$${fmt(item.offer_price)}` : '—'}
                </div>
              </td>
              <td className="py-2.5 px-3">
                <div className="text-xs text-gray-400">{item.shares_offered || '—'}</div>
              </td>
              <td className="py-2.5 px-3">
                <div className="text-xs text-gray-400">{item.sector || '—'}</div>
              </td>
              <td className="py-2.5 px-3">
                <Badge label={item.status || 'upcoming'} color={statusColor(item.status)} />
              </td>
              <td className="py-2.5 px-3">
                {item.symbol && (
                  <button
                    onClick={() => onPredict?.(item.symbol)}
                    className="opacity-0 group-hover:opacity-100 transition-opacity text-[10px] px-2 py-1 rounded bg-cyan-500/20 text-cyan-400 hover:bg-cyan-500/30 border border-cyan-500/30"
                  >
                    <span className="flex items-center gap-1"><BarChart2 size={9} /> Predict</span>
                  </button>
                )}
              </td>
            </motion.tr>
          ))}
          {items.length === 0 && (
            <tr>
              <td colSpan={9} className="py-12 text-center text-gray-500 text-sm">
                No IPO data available — database is warming up
              </td>
            </tr>
          )}
        </tbody>
      </table>
    </div>
  );
}

// ── Summary bar ──────────────────────────────────────────────────────────────
function SummaryBar({ summary }) {
  const stats = [
    { icon: Activity,    label: 'Crypto Tracked',  value: summary?.total_crypto_tracked?.toLocaleString() ?? '—', color: 'cyan' },
    { icon: Zap,         label: 'New Coins',        value: summary?.new_crypto_coins?.toLocaleString() ?? '—',     color: 'emerald' },
    { icon: Globe2,      label: 'IPOs in DB',       value: summary?.total_ipos?.toLocaleString() ?? '—',           color: 'purple' },
    { icon: Clock,       label: 'Upcoming IPOs',    value: summary?.upcoming_ipos?.toLocaleString() ?? '—',        color: 'amber' },
  ];
  return (
    <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 mb-5">
      {stats.map(({ icon: Icon, label, value, color }) => {
        const colorMap = {
          cyan:   'from-cyan-500/20 to-cyan-500/5 border-cyan-500/20 text-cyan-400',
          emerald:'from-emerald-500/20 to-emerald-500/5 border-emerald-500/20 text-emerald-400',
          purple: 'from-purple-500/20 to-purple-500/5 border-purple-500/20 text-purple-400',
          amber:  'from-amber-500/20 to-amber-500/5 border-amber-500/20 text-amber-400',
        };
        return (
          <div key={label} className={`rounded-xl p-3 bg-gradient-to-br border ${colorMap[color]}`}>
            <div className={`flex items-center gap-1.5 mb-1 ${colorMap[color].split(' ').at(-1)}`}>
              <Icon size={12} />
              <span className="text-[10px] font-semibold uppercase tracking-wider opacity-70">{label}</span>
            </div>
            <div className="text-xl font-bold text-white">{value}</div>
          </div>
        );
      })}
    </div>
  );
}

// ── Main component ───────────────────────────────────────────────────────────
export default function NewListings({ onPredict }) {
  const [tab, setTab] = useState('crypto');   // 'crypto' | 'stocks' | 'all'
  const [cryptoData, setCryptoData] = useState([]);
  const [stockData,  setStockData]  = useState([]);
  const [summary,    setSummary]    = useState(null);
  const [loading,    setLoading]    = useState(true);
  const [error,      setError]      = useState(null);
  const [refreshing, setRefreshing] = useState(false);
  const [search,     setSearch]     = useState('');
  const [onlyNew,    setOnlyNew]    = useState(false);
  const [minVol,     setMinVol]     = useState(0);
  const [lastFetch,  setLastFetch]  = useState(null);

  const fetchAll = useCallback(async (silent = false) => {
    if (!silent) setLoading(true);
    else setRefreshing(true);
    setError(null);
    try {
      const [cr, st, sm] = await Promise.all([
        fetch(`${API}/crypto?limit=500&only_new=false`).then(r => r.json()),
        fetch(`${API}/stocks?limit=100`).then(r => r.json()),
        fetch(`${API}/summary`).then(r => r.json()),
      ]);
      setCryptoData(cr.items || []);
      setStockData(st.items || []);
      setSummary(sm);
      setLastFetch(new Date());
    } catch (e) {
      setError(e.message || 'Failed to load listings');
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  }, []);

  useEffect(() => { fetchAll(); }, [fetchAll]);

  // Auto-refresh every 5 minutes
  useEffect(() => {
    const id = setInterval(() => fetchAll(true), 5 * 60 * 1000);
    return () => clearInterval(id);
  }, [fetchAll]);

  // Filtered crypto list
  const filteredCrypto = useMemo(() => {
    let d = cryptoData;
    if (onlyNew) d = d.filter(c => c.is_new === 1);
    if (minVol > 0) d = d.filter(c => (c.volume_24h || 0) >= minVol * 1_000_000);
    if (search) {
      const q = search.toUpperCase();
      d = d.filter(c => c.base_asset?.includes(q) || c.symbol?.includes(q));
    }
    return d;
  }, [cryptoData, onlyNew, minVol, search]);

  const filteredStocks = useMemo(() => {
    if (!search) return stockData;
    const q = search.toUpperCase();
    return stockData.filter(s =>
      s.symbol?.toUpperCase().includes(q) ||
      s.company_name?.toUpperCase().includes(q)
    );
  }, [stockData, search]);

  const TABS = [
    { key: 'crypto', label: 'Crypto Listings', icon: Activity, count: filteredCrypto.length },
    { key: 'stocks', label: 'Stock IPOs',       icon: DollarSign, count: filteredStocks.length },
  ];

  return (
    <div className="min-h-screen bg-[#08090c] text-white p-4 sm:p-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3 mb-5">
        <div>
          <h1 className="text-2xl font-bold text-white flex items-center gap-2">
            <span className="inline-flex items-center justify-center w-8 h-8 rounded-lg bg-cyan-500/20 border border-cyan-500/30">
              <Zap size={16} className="text-cyan-400" />
            </span>
            New Listings
          </h1>
          <p className="text-gray-500 text-sm mt-0.5">
            Auto-discovered crypto &amp; IPO listings — updated every 6h
            {lastFetch && (
              <span className="ml-2 text-[10px] text-gray-600">
                (last: {lastFetch.toLocaleTimeString()})
              </span>
            )}
          </p>
        </div>
        <button
          onClick={() => fetchAll(true)}
          disabled={refreshing}
          className="flex items-center gap-2 px-4 py-2 rounded-lg bg-white/5 border border-white/10 text-sm text-gray-300 hover:text-white hover:bg-white/8 transition-all disabled:opacity-50"
        >
          <RefreshCw size={13} className={refreshing ? 'animate-spin' : ''} />
          {refreshing ? 'Refreshing…' : 'Refresh'}
        </button>
      </div>

      {/* Summary bar */}
      <SummaryBar summary={summary} />

      {/* Controls row */}
      <div className="flex flex-col sm:flex-row gap-3 mb-4">
        {/* Search */}
        <div className="relative flex-1">
          <Search size={13} className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-500" />
          <input
            type="text"
            placeholder="Search symbol or name…"
            value={search}
            onChange={e => setSearch(e.target.value)}
            className="w-full bg-white/5 border border-white/10 rounded-lg pl-8 pr-3 py-2 text-sm text-white placeholder-gray-600 focus:outline-none focus:border-cyan-500/50"
          />
        </div>

        {/* Crypto filters (only shown on crypto tab) */}
        {tab === 'crypto' && (
          <div className="flex items-center gap-3">
            <label className="flex items-center gap-1.5 cursor-pointer select-none">
              <input
                type="checkbox"
                checked={onlyNew}
                onChange={e => setOnlyNew(e.target.checked)}
                className="accent-cyan-500 w-3.5 h-3.5"
              />
              <span className="text-xs text-gray-400">Only new coins</span>
            </label>
            <div className="flex items-center gap-1.5">
              <Filter size={12} className="text-gray-500" />
              <select
                value={minVol}
                onChange={e => setMinVol(Number(e.target.value))}
                className="bg-white/5 border border-white/10 rounded text-xs text-gray-300 px-2 py-1 focus:outline-none focus:border-cyan-500/50"
              >
                <option value={0}>All volumes</option>
                <option value={0.1}>≥ $100K vol</option>
                <option value={1}>≥ $1M vol</option>
                <option value={10}>≥ $10M vol</option>
                <option value={100}>≥ $100M vol</option>
              </select>
            </div>
          </div>
        )}
      </div>

      {/* Tabs */}
      <div className="flex gap-1 mb-4 bg-white/3 rounded-xl p-1 w-fit">
        {TABS.map(({ key, label, icon: Icon, count }) => (
          <button
            key={key}
            onClick={() => setTab(key)}
            className={`flex items-center gap-1.5 px-4 py-2 rounded-lg text-sm font-medium transition-all ${
              tab === key
                ? 'bg-white/10 text-white shadow'
                : 'text-gray-500 hover:text-gray-300'
            }`}
          >
            <Icon size={13} />
            {label}
            <span className={`text-[10px] px-1.5 py-0.5 rounded-full ${
              tab === key ? 'bg-cyan-500/25 text-cyan-300' : 'bg-white/5 text-gray-500'
            }`}>
              {count.toLocaleString()}
            </span>
          </button>
        ))}
      </div>

      {/* Content */}
      {loading ? (
        <div className="flex flex-col items-center justify-center py-24 gap-4">
          <div className="w-10 h-10 rounded-full border-2 border-cyan-500/30 border-t-cyan-400 animate-spin" />
          <p className="text-gray-500 text-sm">Loading listings — building database on first run…</p>
        </div>
      ) : error ? (
        <div className="flex items-center gap-3 p-4 rounded-xl bg-red-500/10 border border-red-500/20 text-red-400 text-sm">
          <AlertCircle size={16} />
          <div>
            <div className="font-semibold">Failed to load listings</div>
            <div className="text-xs opacity-75 mt-0.5">{error}</div>
          </div>
          <button onClick={() => fetchAll()} className="ml-auto text-xs underline opacity-70 hover:opacity-100">
            Retry
          </button>
        </div>
      ) : (
        <AnimatePresence mode="wait">
          <motion.div
            key={tab}
            initial={{ opacity: 0, y: 6 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -6 }}
            transition={{ duration: 0.2 }}
          >
            {tab === 'crypto' && (
              <CryptoTable items={filteredCrypto} onPredict={onPredict} />
            )}
            {tab === 'stocks' && (
              <IPOTable items={filteredStocks} onPredict={onPredict} />
            )}
          </motion.div>
        </AnimatePresence>
      )}
    </div>
  );
}
