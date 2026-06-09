# Patrón 5: Reversión a Bollinger Bands
# Señal cuando el precio sale de las bandas y la vela siguiente confirma el regreso

import pandas as pd
import numpy as np
from config import BOLLINGER_DEFAULTS


def _calc_bands(close: pd.Series, period: int, std_dev: float) -> tuple[pd.Series, pd.Series, pd.Series]:
    """Calcula SMA, banda superior e inferior."""
    sma = close.rolling(period).mean()
    std = close.rolling(period).std(ddof=0)
    upper = sma + std_dev * std
    lower = sma - std_dev * std
    return sma, upper, lower


def detect(
    df: pd.DataFrame,
    period: int = BOLLINGER_DEFAULTS["period"],
    std_dev: float = BOLLINGER_DEFAULTS["std_dev"],
) -> list[dict]:
    """
    Detecta reversiones desde las bandas de Bollinger.

    Señal SHORT: vela cierra sobre banda superior y la siguiente cierra por debajo.
    Señal LONG:  vela cierra bajo banda inferior y la siguiente cierra por encima.

    Retorna lista de señales con:
    { index, type, direction, entry_price, sl, tp1, tp2 }
    """
    signals = []
    n = len(df)

    sma, upper, lower = _calc_bands(df["close"], period, std_dev)

    # Empezar desde period+1 para tener vela de señal y de confirmación válidas
    for i in range(period, n - 1):
        signal_candle = df.iloc[i]
        confirm_candle = df.iloc[i + 1]

        s_close = signal_candle["close"]
        c_close = confirm_candle["close"]

        band_upper_i = upper.iloc[i]
        band_lower_i = lower.iloc[i]
        band_upper_c = upper.iloc[i + 1]
        band_lower_c = lower.iloc[i + 1]
        sma_c = sma.iloc[i + 1]

        if pd.isna(band_upper_i) or pd.isna(band_upper_c):
            continue

        # ── SHORT: señal cierra sobre banda superior, confirmación cierra debajo ──
        if s_close > band_upper_i and c_close < band_upper_c:
            entry = c_close
            sl = signal_candle["high"]
            risk = sl - entry
            if risk <= 0:
                continue
            signals.append({
                "index":       i + 1,
                "type":        "bollinger",
                "direction":   "short",
                "entry_price": round(entry, 5),
                "sl":          round(sl, 5),
                "tp1":         round(sma_c, 5),
                "tp2":         round(band_lower_c, 5),
            })

        # ── LONG: señal cierra bajo banda inferior, confirmación cierra encima ──
        elif s_close < band_lower_i and c_close > band_lower_c:
            entry = c_close
            sl = signal_candle["low"]
            risk = entry - sl
            if risk <= 0:
                continue
            signals.append({
                "index":       i + 1,
                "type":        "bollinger",
                "direction":   "long",
                "entry_price": round(entry, 5),
                "sl":          round(sl, 5),
                "tp1":         round(sma_c, 5),
                "tp2":         round(band_upper_c, 5),
            })

    return signals
