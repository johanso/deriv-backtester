# Patrón 3: Impulso + Retroceso
# Vela de impulso grande seguida de corrección parcial y luego continuación

import pandas as pd
from config import IMPULSE_DEFAULTS


def detect(
    df: pd.DataFrame,
    body_pct: float = IMPULSE_DEFAULTS["body_pct"],
    max_retrace: float = IMPULSE_DEFAULTS["max_retrace"],
) -> list[dict]:
    """
    Detecta impulsos seguidos de retrocesos menores al 50% y continuación.

    Retorna lista de señales con:
    { index, type, direction, entry_price, sl, tp1, tp2 }
    """
    signals = []
    n = len(df)

    for i in range(1, n - 4):
        candle = df.iloc[i]
        body = abs(candle["close"] - candle["open"])
        mid_price = (candle["high"] + candle["low"]) / 2

        if mid_price == 0 or (body / mid_price) < body_pct:
            continue

        is_bullish = candle["close"] > candle["open"]
        impulse_start = candle["open"]
        impulse_end = candle["close"]
        impulse_range = abs(impulse_end - impulse_start)
        retrace_limit = impulse_range * max_retrace

        # Buscar 1-3 velas de retroceso
        for retrace_len in range(1, 4):
            if i + retrace_len + 1 >= n:
                break

            retrace_candles = df.iloc[i + 1: i + 1 + retrace_len]

            if is_bullish:
                # En impulso alcista: retroceso no debe superar 50% hacia abajo
                lowest_low = retrace_candles["low"].min()
                if (impulse_end - lowest_low) > retrace_limit:
                    break  # retroceso demasiado profundo

                continuation = df.iloc[i + 1 + retrace_len]
                if continuation["close"] > continuation["open"]:
                    # Vela de continuación alcista confirmada
                    entry = continuation["open"]
                    sl = impulse_end - retrace_limit
                    risk = entry - sl
                    if risk <= 0:
                        continue
                    signals.append({
                        "index":       i + 1 + retrace_len,
                        "type":        "impulse",
                        "direction":   "long",
                        "entry_price": round(entry, 5),
                        "sl":          round(sl, 5),
                        "tp1":         round(entry + risk, 5),
                        "tp2":         round(entry + 2 * risk, 5),
                    })
                    break
            else:
                # En impulso bajista: retroceso no debe superar 50% hacia arriba
                highest_high = retrace_candles["high"].max()
                if (highest_high - impulse_end) > retrace_limit:
                    break

                continuation = df.iloc[i + 1 + retrace_len]
                if continuation["close"] < continuation["open"]:
                    entry = continuation["open"]
                    sl = impulse_end + retrace_limit
                    risk = sl - entry
                    if risk <= 0:
                        continue
                    signals.append({
                        "index":       i + 1 + retrace_len,
                        "type":        "impulse",
                        "direction":   "short",
                        "entry_price": round(entry, 5),
                        "sl":          round(sl, 5),
                        "tp1":         round(entry - risk, 5),
                        "tp2":         round(entry - 2 * risk, 5),
                    })
                    break

    return signals
