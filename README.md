# NexusTrader ⚡

**AI-Powered Stock & Crypto Price Predictions**

An ensemble machine learning system combining LSTM, Prophet, and XGBoost for maximum prediction accuracy. Built with 100% free and open-source tools.

![NexusTrader Banner](https://img.shields.io/badge/AI-Ensemble%20ML-c8ff00?style=for-the-badge&labelColor=000000) ![License](https://img.shields.io/badge/License-MIT-00ff88?style=for-the-badge&labelColor=000000) ![Python](https://img.shields.io/badge/Python-3.9+-c8ff00?style=for-the-badge&labelColor=000000)

---

## ✨ Features

- **🧠 Ensemble ML Predictions**: LSTM + Prophet + XGBoost with weighted voting
- **📈 Stocks & Crypto**: Support for all major stocks (yfinance) and crypto pairs (Binance)
- **💎 Stunning UI**: Modern lime-accented dark theme with Framer Motion animations
- **📊 Interactive Charts**: Recharts with historical data and prediction overlays
- **🎯 Confidence Scores**: Transparent accuracy metrics for each prediction
- **📰 News Integration**: Real-time headlines scraped from Yahoo Finance
- **🔒 User Authentication**: Secure JWT-based auth with subscription tiers
- **🚀 Cross-Platform**: Desktop (Windows/Mac/Linux), Mobile (iOS/Android), Docker

---

## 🛠️ Tech Stack

| Category | Technologies |
|----------|--------------|
| **Backend** | Python, FastAPI, Uvicorn, SQLite |
| **ML/AI** | TensorFlow/LSTM, Prophet, XGBoost, scikit-learn |
| **Data Sources** | yfinance (stocks), ccxt/Binance (crypto) - 100% FREE |
| **Frontend** | React 18, Vite, Tailwind CSS, Framer Motion, Recharts |
| **Auth** | JWT, bcrypt, PayPal Integration |
| **Packaging** | Docker, Electron (desktop), Capacitor (mobile) |

---

## 🚀 Quick Start

### Prerequisites

- Python 3.9+
- Node.js 18+
- npm or yarn

### Option 1: Python Installer (Recommended)

```bash
# Clone the repository
git clone https://github.com/yourusername/nexustrader.git
cd nexustrader

# Run the installer
python installer.py
```

### Option 2: Manual Setup

```bash
# Backend setup
cd backend
python -m venv venv
venv\Scripts\activate  # Windows
# source venv/bin/activate  # Linux/Mac
pip install -r requirements.txt

# Copy and configure environment
copy .env.example .env  # Windows
# cp .env.example .env  # Linux/Mac

# Start backend
python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# Frontend setup (new terminal)
cd frontend
npm install

# Copy and configure environment
copy .env.example .env  # Windows
# cp .env.example .env  # Linux/Mac

# Start frontend
npm run dev
```

### Option 3: Docker (Production)

```bash
# Build and run with Docker Compose
docker-compose up -d

# View logs
docker-compose logs -f

# Stop services
docker-compose down
```

**Frontend:** http://localhost:5174  
**Backend API:** http://localhost:8000  
**API Docs:** http://localhost:8000/docs

---

## 📱 Platform Builds

### Desktop (Electron)

```bash
cd electron
npm install
npm run build:win    # Windows (.exe)
npm run build:mac    # macOS (.dmg)
npm run build:linux  # Linux (.AppImage, .deb)
```

### Mobile (Capacitor)

```bash
# Install Capacitor CLI
npm install -g @capacitor/cli

# Add platforms
npx cap add ios
npx cap add android

# Build and sync
cd frontend && npm run build
npx cap sync

# Open in IDE
npx cap open ios      # Xcode
npx cap open android  # Android Studio
```

---

## 🔐 Environment Variables

### Backend (.env)

```env
# PayPal (required for payments)
PAYPAL_CLIENT_ID=your_paypal_client_id
PAYPAL_CLIENT_SECRET=your_paypal_client_secret
PAYPAL_MODE=sandbox  # or "live" for production

# Security
JWT_SECRET_KEY=your-super-secret-jwt-key-change-this
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30

# CORS
ALLOWED_ORIGINS=http://localhost:5173,http://localhost:5174
```

### Frontend (.env)

```env
VITE_API_URL=http://localhost:8000
VITE_PAYPAL_CLIENT_ID=your_paypal_client_id
VITE_APP_NAME=NexusTrader
```

---

## 🔮 API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/health` | GET | Health check |
| `/api/predict/{symbol}` | GET | Get predictions (7-30 days) |
| `/api/historical/{symbol}` | GET | Historical OHLCV data |
| `/api/news/{symbol}` | GET | News headlines |
| `/api/assets` | GET | Available assets |
| `/api/auth/register` | POST | User registration |
| `/api/auth/login` | POST | User login |
| `/api/auth/me` | GET | Get current user |
| `/api/subscription/plans` | GET | Get subscription plans |

**API Docs:** http://localhost:8000/docs

---

## 🎯 Prediction Engine

The ensemble combines three models for maximum accuracy:

1. **LSTM (40% weight)**: Deep learning for sequential patterns
2. **Prophet (30% weight)**: Seasonality and trend decomposition  
3. **XGBoost (30% weight)**: Gradient boosting with technical indicators

**Technical Indicators Used:**
- RSI, MACD, Bollinger Bands
- Moving averages (SMA, EMA)
- Volume analysis, ATR
- Price momentum indicators
- Support & Resistance levels

---

## 🚢 Production Deployment

### Using Docker

1. **Configure environment variables:**
   ```bash
   cp backend/.env.example backend/.env
   cp frontend/.env.example frontend/.env
   # Edit both files with production values
   ```

2. **Build and deploy:**
   ```bash
   docker-compose up -d --build
   ```

3. **Verify deployment:**
   ```bash
   curl http://localhost:8000/api/health
   ```

### Manual Production Build

```bash
# Build frontend for production
cd frontend
npm run build

# The dist folder can be served via nginx or any static host
# Backend should use gunicorn/uvicorn with workers
cd backend
gunicorn app.main:app -w 4 -k uvicorn.workers.UvicornWorker --bind 0.0.0.0:8000
```

---

## ⚠️ Disclaimer

This software is for **educational purposes only**. Predictions are not financial advice. Always do your own research before making investment decisions. Past performance does not guarantee future results.

---

## 🤝 Contributing

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

---

## 📄 License

MIT License - See [LICENSE](LICENSE) for details.

---

<p align="center">
  <strong>NexusTrader</strong> - Made with ⚡ and AI
</p>
<p align="center">
  <img src="https://img.shields.io/badge/Theme-Lime%20%23c8ff00-c8ff00?style=flat-square&labelColor=000000" />
</p>
