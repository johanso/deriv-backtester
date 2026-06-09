# Patrón 2: Rebote en nivel clave (swing high / swing low)
# El precio toca un nivel previo y la vela cierra en dirección contraria

import pandas as pd
import numpy as np
from config import BOUNCE_DEFAULTS


def _find_swing_levels(df: pd.DataFrame, lookback: int) -> tuple[list[float], list[float]]:
    """Encuentra los swing highs y swing lows en el DataFrame."""
    swing_highs = []
    swing_lows = []

    for i in range(2, len(df) - 2):
        # Swing high: máximo local
        if (df.iloc[i]["high"] > df.iloc[i - 1]["high"] and
                df.iloc[i]["high"] > df.iloc[i - 2]["high"] and
                df.iloc[i]["high"] > df.iloc[i + 1]["high"] and
                df.iloc[i]["high"] > df.iloc[i + 2]["high"]):
            swing_highs.append(df.iloc[i]["high"])

        # Swing low: mínimo local
        if (df.iloc[i]["low"] < df.iloc[i - 1]["low"] and
                df.iloc[i]["low"] < df.iloc[i - 2]["low"] and
                df.iloc[i]["low"] < df.iloc[i + 1]["low"] and
                df.iloc[i]["low"] < df.iloc[i + 2]["low"]):
            swing_lows.append(df.iloc[i]["low"])

    return swing_highs, swing_lows


def detect(
    df: pd.DataFrame,
    lookback: int = BOUNCE_DEFAULTS["lookback"],
    tol_pct: float = BOUNCE_DEFAULTS["tol_pct"],
) -> list[dict]:
    """
    Detecta rebotes en niveles de swing previos.

    Retorna lista de señales con:
    { index, type, direction, entry_price, sl, tp1, tp2 }
    """
    signals = []
    n = len(df)

    # Precalcular todos los niveles swing una sola vez sobre el DataFrame completo
    all_swing_highs, all_swing_lows = _find_swing_levels(df, lookback)

    for i in range(lookback, n):
        candle = df.iloc[i]
        price = candle["close"]

        # Rebote alcista: toca swing low y cierra arriba (vela alcista)
        for level in all_swing_lows:
            if abs(candle["low"] - level) / level <= tol_pct and candle["close"] > candle["open"]:
                sl = level * (1 - tol_pct)
                risk = price - sl
                if risk <= 0:
                    continue
                signals.append({
                    "index":       i,
                    "type":        "bounce",
                    "direction":   "long",
                    "entry_price": round(price, 5),
                    "sl":          round(sl, 5),
                    "tp1":         round(price + risk, 5),
                    "tp2":         round(price + 2 * risk, 5),
                })
                break  # una señal por vela

        # Rebote bajista: toca swing high y cierra abajo (vela bajista)
        for level in all_swing_highs:
            if abs(candle["high"] - level) / level <= tol_pct and candle["close"] < candle["open"]:
                sl = level * (1 + tol_pct)
                risk = sl - price
                if risk <= 0:
                    continue
                signals.append({
                    "index":       i,
                    "type":        "bounce",
                    "direction":   "short",
                    "entry_price": round(price, 5),
                    "sl":          round(sl, 5),
                    "tp1":         round(price - risk, 5),
                    "tp2":         round(price - 2 * risk, 5),
                })
                break

    return signals
