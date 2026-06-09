# Motor de backtesting genérico
# Simula cada señal usando las velas siguientes y calcula métricas estadísticas

import pandas as pd
import numpy as np
from config import BACKTEST_DEFAULTS


def simulate_trade(df: pd.DataFrame, signal: dict, max_candles: int) -> str:
    """
    Simula una trade a partir de una señal usando las velas posteriores.

    Retorna: 'tp1_only', 'tp2', 'sl' o 'timeout'
    """
    idx = signal["index"]
    direction = signal["direction"]
    entry = signal["entry_price"]
    sl = signal["sl"]
    tp1 = signal["tp1"]
    tp2 = signal["tp2"]

    tp1_hit = False

    # Iterar sobre las velas siguientes hasta max_candles
    for i in range(idx + 1, min(idx + 1 + max_candles, len(df))):
        candle = df.iloc[i]
        high = candle["high"]
        low = candle["low"]

        if direction == "long":
            if low <= sl:
                return "sl"
            if high >= tp2:
                return "tp2"
            if high >= tp1:
                tp1_hit = True
        else:  # short
            if high >= sl:
                return "sl"
            if low <= tp2:
                return "tp2"
            if low <= tp1:
                tp1_hit = True

    return "tp1_only" if tp1_hit else "timeout"


def run_backtest(
    df: pd.DataFrame,
    signals: list[dict],
    max_candles: int = BACKTEST_DEFAULTS["max_candles"],
) -> dict:
    """
    Ejecuta el backtesting sobre todas las señales de un patrón.

    Retorna un dict con métricas estadísticas.
    """
    if not signals:
        return _empty_metrics()

    results = []
    for signal in signals:
        outcome = simulate_trade(df, signal, max_candles)
        results.append(outcome)

    total = len(results)
    # "tp1_only": precio tocó TP1 pero no TP2; "tp2": llegó a TP2
    tp1_only_count = results.count("tp1_only")
    tp2_count = results.count("tp2")
    sl_count = results.count("sl")

    # win_rate_tp1: alcanzó al menos TP1 (incluye los que siguieron a TP2)
    win_rate_tp1 = (tp1_only_count + tp2_count) / total if total > 0 else 0.0
    # win_rate_tp2: solo los que llegaron a TP2
    win_rate_tp2 = tp2_count / total if total > 0 else 0.0

    # R:R promedio: TP2 = 2R, tp1_only = 1R, SL = -1R, timeout = 0R
    rr_map = {"tp2": 2.0, "tp1_only": 1.0, "sl": -1.0, "timeout": 0.0}
    rr_values = [rr_map[r] for r in results]
    avg_rr = float(np.mean(rr_values)) if rr_values else 0.0

    # Expectancy = (win_rate * avg_win) - (loss_rate * 1R)
    avg_win = 0.0
    win_outcomes = [v for v in rr_values if v > 0]
    if win_outcomes:
        avg_win = float(np.mean(win_outcomes))
    loss_rate = sl_count / total if total > 0 else 0.0
    expectancy = (win_rate_tp1 * avg_win) - (loss_rate * 1.0)

    # Racha máxima de pérdidas
    max_consec_losses = _max_consecutive_losses(results)

    return {
        "total_signals":        total,
        "win_rate_tp1":         round(win_rate_tp1 * 100, 2),
        "win_rate_tp2":         round(win_rate_tp2 * 100, 2),
        "avg_rr":               round(avg_rr, 3),
        "expectancy":           round(expectancy, 3),
        "max_consecutive_losses": max_consec_losses,
    }


def _max_consecutive_losses(results: list[str]) -> int:
    """Calcula la racha máxima de pérdidas (SL consecutivos)."""
    max_streak = 0
    current_streak = 0

    for r in results:
        if r == "sl":
            current_streak += 1
            max_streak = max(max_streak, current_streak)
        else:
            current_streak = 0

    return max_streak


def _empty_metrics() -> dict:
    """Retorna métricas vacías cuando no hay señales."""
    return {
        "total_signals":          0,
        "win_rate_tp1":           0.0,
        "win_rate_tp2":           0.0,
        "avg_rr":                 0.0,
        "expectancy":             0.0,
        "max_consecutive_losses": 0,
    }
