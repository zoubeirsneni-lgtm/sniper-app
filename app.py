import streamlit as st
import pandas as pd
import numpy as np
import yfinance as yf
# =========================================================================
# SYSTÈDE DE SÉCURITÉ (MOT DE PASSE)
# =========================================================================
if "logged_in" not in st.session_state:
    st.session_state["logged_in"] = False

if not st.session_state["logged_in"]:
    st.title("🔒 Accès Restreint")
    st.markdown("Veuillez entrer le mot de passe pour accéder au moteur.")
    
    pwd = st.text_input("Mot de passe :", type="password")
    
    if st.button("Entrer"):
        if pwd == "SNIPER2024":  # <--- CHANGE CE MOT DE PASSE ICI
            st.session_state["logged_in"] = True
            st.rerun()
        else:
            st.error("❌ Mot de passe incorrect.")
    
    st.stop() # Cette commande magique bloque TOUT le reste du code si on n'est pas connecté
# =========================================================================
st.set_page_config(page_title="Sniper Engine LIVE", page_icon="🎯", layout="wide")

st.sidebar.title("⚙️ Panneau de Configuration")
st.sidebar.subheader("📊 Marché en Direct")
actif_choice = st.sidebar.text_input("Ticker (ex: EURUSD=X, BTC-USD)", value="EURUSD=X")

config = {}

st.sidebar.subheader("1. Tendance")
config['ema_active'] = st.toggle("EMA 200", value=True)
if config['ema_active']: config['ema_length'] = st.slider("Longueur", 10, 500, 200, key="ema")

st.sidebar.subheader("2. Volatilité")
config['bb_active'] = st.toggle("Bollinger Bands", value=True)
if config['bb_active']:
    config['bb_length'] = st.slider("Longueur", 5, 50, 20, key="bb_l")
    config['bb_mult'] = st.slider("Écart", 0.5, 4.0, 2.0, 0.1, key="bb_m")

st.sidebar.subheader("3. Force")
config['adx_active'] = st.toggle("ADX (Marché Calme)", value=True)
if config['adx_active']:
    config['adx_length'] = st.slider("Longueur", 5, 50, 14, key="adx_l")
    config['adx_thresh'] = st.slider("Seuil Max (<)", 10, 50, 25, key="adx_t")

st.sidebar.subheader("4. Momentum")
config['mom_active'] = st.toggle("RSI + Stochastique", value=True)
if config['mom_active']:
    config['rsi_length'] = st.slider("RSI Longueur", 5, 50, 14, key="rsi_l")
    config['rsi_oversold'] = st.slider("RSI Survente (<)", 5, 40, 30, key="rsi_os")
    config['stoch_k'] = st.slider("Stoch K", 5, 30, 14, key="stk")
    config['stoch_d'] = st.slider("Stoch D", 1, 10, 3, key="std")

st.sidebar.subheader("5. Structure (ZigZag)")
config['div_active'] = st.toggle("Divergence MACD ZigZag", value=True)
if config['div_active']:
    config['zz_left'] = st.slider("ZigZag Gauche", 3, 20, 12, key="zz_l")
    config['macd_fast'] = st.slider("MACD Rapide", 5, 20, 12, key="mc_f")
    config['macd_slow'] = st.slider("MACD Lent", 20, 50, 26, key="mc_s")
    config['macd_sig'] = st.slider("MACD Signal", 5, 20, 9, key="mc_sgn")

st.sidebar.subheader("6. Confirmation")
config['ha_active'] = st.toggle("Heikin Ashi (Sans mèche)", value=True)

st.sidebar.markdown("---")
if st.sidebar.button("🔄 Rafraîchir les données maintenant"):
    st.rerun()

def calc_ema(series, period): return series.ewm(span=period, adjust=False).mean()

def calc_rsi(series, period):
    delta = series.diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
    rs = gain / loss
    return 100 - (100 / (1 + rs))

def calc_adx(high, low, close, period):
    plus_dm = high.diff(); minus_dm = -low.diff()
    plus_dm[plus_dm < 0] = 0; minus_dm[minus_dm < 0] = 0
    tr1 = high - low; tr2 = abs(high - close.shift()); tr3 = abs(low - close.shift())
    tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
    atr = tr.rolling(period).mean()
    plus_di = 100 * (plus_dm.rolling(period).mean() / atr)
    minus_di = 100 * (minus_dm.rolling(period).mean() / atr)
    dx = 100 * abs(plus_di - minus_di) / (plus_di + minus_di)
    return dx.rolling(period).mean()

def calc_stoch(high, low, close, k_period, d_period):
    low_min = low.rolling(window=k_period).min()
    high_max = high.rolling(window=k_period).max()
    stoch_k = 100 * (close - low_min) / (high_max - low_min)
    return stoch_k, stoch_k.rolling(window=d_period).mean()

def calc_macd(close, fast, slow, signal):
    macd_line = calc_ema(close, fast) - calc_ema(close, slow)
    signal_line = calc_ema(macd_line, signal)
    return macd_line, signal_line

st.markdown(f"### ⏳ Connexion au marché en cours pour {actif_choice}...")
df = pd.DataFrame()

try:
    data = yf.download(tickers=actif_choice, period="1d", interval="1m", progress=False)
    if not data.empty:
        if isinstance(data.columns, pd.MultiIndex):
            data.columns = data.columns.get_level_values(0)
        data.columns = [str(c).lower() for c in data.columns]
        df = data[['open', 'high', 'low', 'close']].copy()
        df = df.dropna()
    else:
        st.error("Aucune donnée reçue. Vérifie le Ticker.")
except Exception as e:
    st.error(f"Erreur de connexion : {e}")

if not df.empty:
    ha_close = (df['open'] + df['high'] + df['low'] + df['close']) / 4
    ha_opens = [0.0]
    for i in range(1, len(df)):
        ha_opens.append((ha_opens[i-1] + ha_close.iloc[i-1]) / 2)
    df['ha_open'] = ha_opens
    df['ha_close'] = ha_close
    df['ha_high'] = df[['high', 'ha_close', 'ha_open']].max(axis=1)
    df['ha_low'] = df[['low', 'ha_close', 'ha_open']].min(axis=1)

    if config['ema_active']: df['ema'] = calc_ema(df['close'], config['ema_length'])
    if config['bb_active']:
        bb_std = df['close'].rolling(window=config['bb_length']).std(ddof=0)
        df['bb_lower'] = df['close'].rolling(window=config['bb_length']).mean() - (bb_std * config['bb_mult'])
    if config['adx_active']: df['adx'] = calc_adx(df['high'], df['low'], df['close'], config['adx_length'])
    if config['mom_active']:
        df['rsi'] = calc_rsi(df['close'], config['rsi_length'])
        df['stoch_k'], df['stoch_d'] = calc_stoch(df['high'], df['low'], df['close'], config['stoch_k'], config['stoch_d'])
    if config['div_active']:
        df['macd_line'], df['macd_sig'] = calc_macd(df['close'], config['macd_fast'], config['macd_slow'], config['macd_sig'])
        lookback = config['zz_left'] * 2
        df['bull_div'] = False
        for i in range(lookback, len(df)):
            window = df.iloc[i-lookback:i]
            min_idx = window['low'].idxmin()
            if min_idx != window.index[0]:
                if (i - lookback*2) >= 0:
                    prev_window = df.iloc[i-lookback*2 : i-lookback]
                    if len(prev_window) > 0:
                        prev_min_idx = prev_window['low'].idxmin()
                        if window['low'].min() < prev_window['low'].min():
                            if df.loc[min_idx, 'macd_line'] > df.loc[prev_min_idx, 'macd_line']:
                                df.loc[df.index[i], 'bull_div'] = True

    df = df.replace([np.inf, -np.inf], np.nan).fillna(0)

    last = df.iloc[-1]
    score = 0; total = 0; details = []

    if config['ema_active']:
        total += 1
        if last['close'] > last['ema']: score += 1; details.append("✅ EMA")
        else: details.append("❌ EMA")

    if config['bb_active']:
        total += 1
        if last['close'] <= last['bb_lower']: score += 1; details.append("✅ Bollinger")
        else: details.append("❌ Bollinger")

    if config['adx_active']:
        total += 1
        if last['adx'] < config['adx_thresh']: score += 1; details.append("✅ ADX Calme")
        else: details.append("❌ ADX Trop Fort")

    if config['mom_active']:
        total += 1
        if last['rsi'] < config['rsi_oversold'] and last['stoch_k'] > last['stoch_d']: score += 1; details.append("✅ RSI/Stoch")
        else: details.append("❌ RSI/Stoch")

    if config['div_active']:
        total += 1
        if last['bull_div'] == True: score += 1; details.append("✅ Divergence")
        else: details.append("❌ Divergence")

    if config['ha_active']:
        total += 1
        if last['ha_close'] > last['ha_open'] and last['ha_low'] >= last['ha_open']: score += 1; details.append("✅ Heikin Ashi")
        else: details.append("❌ Heikin Ashi")

    pct = (score / total * 100) if total > 0 else 0

    col1, col2 = st.columns([1, 2])

    with col1:
        st.metric("Prix Actuel", f"{last['close']:.5f}")
        st.metric("Score de Confluence", f"{pct:.0f}%", delta=f"{score} sur {total} conditions")
        st.progress(pct / 100)
        
        if pct == 100: st.success("🔥 SIGNAL PARFAIT LOCKED !")
        elif pct >= 50: st.warning("⚠️ Formation en cours...")
        else: st.error("❌ Aucun signal")
        
        st.markdown("---")
        st.subheader("Détail du Moteur")
        for d in details: st.write(d)

    with col2:
        st.subheader(f"Graphique Réel - {actif_choice}")
        st.line_chart(df[['close']])
