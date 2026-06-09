# Configuración global del backtester de Deriv

# Símbolos disponibles: clave CLI -> código API
SYMBOLS = {
    "v75":      "1HZ75V",
    "v100":     "1HZ100V",
    "crash500": "CRASH500",
    "boom1000": "BOOM1000",
    "v50":      "1HZ50V",
    "v25":      "1HZ25V",
}

# Temporalidades: flag CLI -> granularidad en segundos
TIMEFRAMES = {
    "1m":  60,
    "5m":  300,
    "15m": 900,
    "1h":  3600,
    "4h":  14400,
}

# URL del WebSocket público de Deriv
DERIV_WS_URL = "wss://ws.derivws.com/websockets/v3?app_id=1"

# Cantidad de velas a descargar por defecto
DEFAULT_CANDLE_COUNT = 5000

# Reintentos de conexión a la API
API_MAX_RETRIES = 3
API_RETRY_BACKOFF = 2  # segundos entre reintentos

# ─── Parámetros de patrones (todos configurables vía CLI) ─────────────────────

CONSOLIDATION_DEFAULTS = {
    "n_candles": 4,       # mínimo de velas en la zona de consolidación
    "range_pct": 0.003,   # rango máximo (high-low)/precio para considerar consolidación
}

BOUNCE_DEFAULTS = {
    "lookback": 50,       # velas hacia atrás para buscar niveles swing
    "tol_pct": 0.002,     # tolerancia de precio para tocar el nivel
}

IMPULSE_DEFAULTS = {
    "body_pct": 0.005,    # tamaño mínimo del cuerpo del impulso respecto al precio
    "max_retrace": 0.5,   # máximo retroceso del impulso antes de continuación
}

DOUBLE_DEFAULTS = {
    "tol_pct": 0.002,     # tolerancia para considerar dos toques iguales
    "min_gap": 5,         # mínimo de velas entre los dos toques
}

# ─── Motor de backtesting ──────────────────────────────────────────────────────

BACKTEST_DEFAULTS = {
    "max_candles": 10,    # máximo de velas para simular la trade
}

# Nombres legibles para el reporte
PATTERN_LABELS = {
    "consolidation": "Consolidación+Ruptura",
    "bounce":        "Rebote en Nivel",
    "impulse":       "Impulso+Retroceso",
    "double":        "Doble Techo/Suelo",
}
