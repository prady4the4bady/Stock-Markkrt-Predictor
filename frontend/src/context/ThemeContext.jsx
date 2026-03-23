import React, { createContext, useContext, useState, useEffect } from 'react';

const ThemeContext = createContext(null);

export const ThemeProvider = ({ children }) => {
  const [theme, setTheme] = useState(() => {
    return localStorage.getItem('nexustrader-theme') || 'dark';
  });

  const isDark = theme === 'dark';
  const isLight = theme === 'light';

  useEffect(() => {
    localStorage.setItem('nexustrader-theme', theme);
    document.documentElement.setAttribute('data-theme', theme);
    
    // Update body classes
    if (theme === 'light') {
      document.body.classList.add('light-mode');
      document.body.classList.remove('dark-mode');
    } else {
      document.body.classList.add('dark-mode');
      document.body.classList.remove('light-mode');
    }
  }, [theme]);

  const toggleTheme = () => {
    setTheme(prev => prev === 'dark' ? 'light' : 'dark');
  };

  const setDarkTheme = () => setTheme('dark');
  const setLightTheme = () => setTheme('light');

  // Theme-aware colors
  const colors = {
    // Primary accent
    primary: isDark ? '#c8ff00' : '#7cb800',
    primaryHover: isDark ? '#e0ff66' : '#5a8a00',
    
    // Backgrounds
    bgPrimary: isDark ? '#0a0a14' : '#f8fafc',
    bgSecondary: isDark ? '#12121e' : '#f1f5f9',
    bgTertiary: isDark ? '#1a1a2e' : '#e2e8f0',
    bgCard: isDark ? 'rgba(26, 26, 46, 0.6)' : 'rgba(255, 255, 255, 0.9)',
    
    // Glass effects
    glassBg: isDark ? 'rgba(26, 26, 46, 0.6)' : 'rgba(255, 255, 255, 0.85)',
    glassBorder: isDark ? 'rgba(200, 255, 0, 0.15)' : 'rgba(124, 184, 0, 0.2)',
    
    // Text
    textPrimary: isDark ? '#ffffff' : '#0f172a',
    textSecondary: isDark ? '#a0a0b0' : '#475569',
    textMuted: isDark ? '#6b7280' : '#94a3b8',
    
    // Status colors
    success: isDark ? '#10b981' : '#059669',
    danger: isDark ? '#ef4444' : '#dc2626',
    warning: isDark ? '#f59e0b' : '#d97706',
    info: isDark ? '#3b82f6' : '#2563eb',
    
    // Chart colors
    chartGrid: isDark ? 'rgba(255, 255, 255, 0.05)' : 'rgba(0, 0, 0, 0.05)',
    chartLine: isDark ? '#c8ff00' : '#7cb800',
    chartArea: isDark ? 'rgba(200, 255, 0, 0.1)' : 'rgba(124, 184, 0, 0.1)',
    
    // Shadows
    shadow: isDark 
      ? '0 4px 20px rgba(0, 0, 0, 0.4)' 
      : '0 4px 20px rgba(0, 0, 0, 0.08)',
    shadowLg: isDark 
      ? '0 10px 40px rgba(0, 0, 0, 0.5)' 
      : '0 10px 40px rgba(0, 0, 0, 0.12)',
    
    // Neon glow
    neonGlow: isDark 
      ? '0 0 20px rgba(200, 255, 0, 0.3)' 
      : '0 0 15px rgba(124, 184, 0, 0.2)',
  };

  // Theme-aware classes
  const classes = {
    // Layout
    pageBackground: isDark ? 'bg-[#0a0a14]' : 'bg-slate-50',
    cardBackground: isDark ? 'bg-[#1a1a2e]/60' : 'bg-white/90',
    
    // Text
    textPrimary: isDark ? 'text-white' : 'text-slate-900',
    textSecondary: isDark ? 'text-gray-400' : 'text-slate-600',
    textMuted: isDark ? 'text-gray-500' : 'text-slate-400',
    textAccent: isDark ? 'text-[#c8ff00]' : 'text-[#7cb800]',
    
    // Borders
    border: isDark ? 'border-white/10' : 'border-slate-200',
    borderAccent: isDark ? 'border-[#c8ff00]/30' : 'border-[#7cb800]/30',
    
    // Buttons
    btnPrimary: isDark 
      ? 'bg-[#c8ff00] text-black hover:bg-[#e0ff66]' 
      : 'bg-[#7cb800] text-white hover:bg-[#5a8a00]',
    btnSecondary: isDark
      ? 'bg-white/10 text-white hover:bg-white/20'
      : 'bg-slate-100 text-slate-700 hover:bg-slate-200',
    btnOutline: isDark
      ? 'border border-[#c8ff00]/50 text-[#c8ff00] hover:bg-[#c8ff00]/10'
      : 'border border-[#7cb800]/50 text-[#7cb800] hover:bg-[#7cb800]/10',
    
    // Inputs
    input: isDark
      ? 'bg-white/5 border-white/10 text-white placeholder-gray-500 focus:border-[#c8ff00]/50'
      : 'bg-white border-slate-200 text-slate-900 placeholder-slate-400 focus:border-[#7cb800]/50',
    
    // Cards and containers
    glass: isDark 
      ? 'glass-card' 
      : 'glass-card-light',
    
    // Sidebar
    sidebarBg: isDark ? 'bg-[#0d0d1a]' : 'bg-white',
    sidebarBorder: isDark ? 'border-white/5' : 'border-slate-200',
    
    // Hover effects
    hoverBg: isDark ? 'hover:bg-white/5' : 'hover:bg-slate-50',
    
    // Scrollbar
    scrollbar: isDark ? 'scrollbar-dark' : 'scrollbar-light',
  };

  const value = {
    theme,
    setTheme,
    toggleTheme,
    setDarkTheme,
    setLightTheme,
    isDark,
    isLight,
    colors,
    classes,
  };

  return (
    <ThemeContext.Provider value={value}>
      {children}
    </ThemeContext.Provider>
  );
};

export const useTheme = () => {
  const context = useContext(ThemeContext);
  if (!context) {
    throw new Error('useTheme must be used within a ThemeProvider');
  }
  return context;
};

export default ThemeContext;
