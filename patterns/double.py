# Patrón 4: Doble Techo / Doble Suelo
# Dos toques al mismo nivel separados por un valle/pico intermedio

import pandas as pd
from config import DOUBLE_DEFAULTS


def detect(
    df: pd.DataFrame,
    tol_pct: float = DOUBLE_DEFAULTS["tol_pct"],
    min_gap: int = DOUBLE_DEFAULTS["min_gap"],
) -> list[dict]:
    """
    Detecta dobles techos y dobles suelos.

    Retorna lista de señales con:
    { index, type, direction, entry_price, sl, tp1, tp2 }
    """
    signals = []
    n = len(df)

    # ── Doble techo ──────────────────────────────────────────────────────────
    for i in range(min_gap + 1, n - 1):
        high_i = df.iloc[i]["high"]

        for j in range(max(0, i - 100), i - min_gap):
            high_j = df.iloc[j]["high"]

            if abs(high_i - high_j) / high_j > tol_pct:
                continue

            # Verificar que hay un valle intermedio
            valley = df.iloc[j + 1: i]["low"].min()
            valley_idx = df.iloc[j + 1: i]["low"].idxmin()

            # El siguiente close debe romper por debajo del valle
            if i + 1 < n and df.iloc[i + 1]["close"] < valley:
                entry = df.iloc[i + 1]["close"]
                sl = max(high_i, high_j) * (1 + tol_pct)
                risk = sl - entry
                if risk <= 0:
                    continue
                signals.append({
                    "index":       i + 1,
                    "type":        "double",
                    "direction":   "short",
                    "entry_price": round(entry, 5),
                    "sl":          round(sl, 5),
                    "tp1":         round(entry - risk, 5),
                    "tp2":         round(entry - 2 * risk, 5),
                })
                break  # una señal por posición i

    # ── Doble suelo ──────────────────────────────────────────────────────────
    for i in range(min_gap + 1, n - 1):
        low_i = df.iloc[i]["low"]

        for j in range(max(0, i - 100), i - min_gap):
            low_j = df.iloc[j]["low"]

            if abs(low_i - low_j) / low_j > tol_pct:
                continue

            # Verificar que hay un pico intermedio
            peak = df.iloc[j + 1: i]["high"].max()

            # El siguiente close debe romper por encima del pico
            if i + 1 < n and df.iloc[i + 1]["close"] > peak:
                entry = df.iloc[i + 1]["close"]
                sl = min(low_i, low_j) * (1 - tol_pct)
                risk = entry - sl
                if risk <= 0:
                    continue
                signals.append({
                    "index":       i + 1,
                    "type":        "double",
                    "direction":   "long",
                    "entry_price": round(entry, 5),
                    "sl":          round(sl, 5),
                    "tp1":         round(entry + risk, 5),
                    "tp2":         round(entry + 2 * risk, 5),
                })
                break

    return signals
