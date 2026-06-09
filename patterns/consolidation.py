# Patrón 1: Consolidación + Ruptura
# N velas con rango comprimido seguidas de una vela que rompe la zona

import pandas as pd
from config import CONSOLIDATION_DEFAULTS


def detect(
    df: pd.DataFrame,
    n_candles: int = CONSOLIDATION_DEFAULTS["n_candles"],
    range_pct: float = CONSOLIDATION_DEFAULTS["range_pct"],
) -> list[dict]:
    """
    Detecta zonas de consolidación y la vela de ruptura posterior.

    Retorna lista de señales con:
    { index, type, direction, entry_price, sl, tp1, tp2 }
    """
    signals = []
    n = len(df)

    for i in range(n_candles, n - 1):
        zone = df.iloc[i - n_candles: i]
        zone_high = zone["high"].max()
        zone_low = zone["low"].min()
        zone_range = zone_high - zone_low
        mid_price = (zone_high + zone_low) / 2

        # Verificar que el rango sea comprimido respecto al precio
        if mid_price == 0 or (zone_range / mid_price) > range_pct:
            continue

        breakout_candle = df.iloc[i]

        # Ruptura alcista: cierre por encima del high de la zona
        if breakout_candle["close"] > zone_high:
            entry = df.iloc[i + 1]["open"] if i + 1 < n else breakout_candle["close"]
            sl = zone_low
            risk = entry - sl
            if risk <= 0:
                continue
            signals.append({
                "index":       i,
                "type":        "consolidation",
                "direction":   "long",
                "entry_price": round(entry, 5),
                "sl":          round(sl, 5),
                "tp1":         round(entry + risk, 5),
                "tp2":         round(entry + 2 * risk, 5),
            })

        # Ruptura bajista: cierre por debajo del low de la zona
        elif breakout_candle["close"] < zone_low:
            entry = df.iloc[i + 1]["open"] if i + 1 < n else breakout_candle["close"]
            sl = zone_high
            risk = sl - entry
            if risk <= 0:
                continue
            signals.append({
                "index":       i,
                "type":        "consolidation",
                "direction":   "short",
                "entry_price": round(entry, 5),
                "sl":          round(sl, 5),
                "tp1":         round(entry - risk, 5),
                "tp2":         round(entry - 2 * risk, 5),
            })

    return signals
