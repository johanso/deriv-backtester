# Patrón 6: N-Candle Breakout
# Ruptura del high/low máximo de las últimas N velas

import pandas as pd
from config import NCANDLE_DEFAULTS


def detect(
    df: pd.DataFrame,
    n_candles: int = NCANDLE_DEFAULTS["n_candles"],
) -> list[dict]:
    """
    Detecta rupturas del rango formado por las últimas N velas.

    Señal LONG:  cierre actual > high máximo de las N velas previas.
    Señal SHORT: cierre actual < low mínimo de las N velas previas.
    Entry: apertura de la vela siguiente a la ruptura.

    Retorna lista de señales con:
    { index, type, direction, entry_price, sl, tp1, tp2 }
    """
    signals = []
    n = len(df)
    next_allowed = 0  # cooldown: índice mínimo en el que se puede generar la próxima señal

    for i in range(n_candles, n - 1):
        if i < next_allowed:
            continue
        window = df.iloc[i - n_candles: i]
        window_high = window["high"].max()
        window_low = window["low"].min()
        window_range = window_high - window_low

        if window_range <= 0:
            continue

        half_range = window_range / 2
        current_close = df.iloc[i]["close"]
        next_open = df.iloc[i + 1]["open"]

        # ── LONG: cierre rompe el high del rango ──────────────────────────────
        if current_close > window_high:
            entry = next_open
            sl = entry - half_range
            risk = entry - sl  # == half_range
            if risk <= 0:
                continue
            signals.append({
                "index":       i + 1,
                "type":        "ncandle",
                "direction":   "long",
                "entry_price": round(entry, 5),
                "sl":          round(sl, 5),
                "tp1":         round(entry + risk, 5),
                "tp2":         round(entry + 2 * risk, 5),
            })
            next_allowed = i + 1 + n_candles

        # ── SHORT: cierre rompe el low del rango ──────────────────────────────
        elif current_close < window_low:
            entry = next_open
            sl = entry + half_range
            risk = sl - entry  # == half_range
            if risk <= 0:
                continue
            signals.append({
                "index":       i + 1,
                "type":        "ncandle",
                "direction":   "short",
                "entry_price": round(entry, 5),
                "sl":          round(sl, 5),
                "tp1":         round(entry - risk, 5),
                "tp2":         round(entry - 2 * risk, 5),
            })
            next_allowed = i + 1 + n_candles

    return signals
