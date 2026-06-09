# Simulación de crecimiento de cuenta con riesgo porcentual fijo
# Reutiliza simulate_trade del motor de backtesting para mantener consistencia

import pandas as pd
from config import BACKTEST_DEFAULTS
from backtest.engine import simulate_trade


# Multiplicadores R por cada outcome
_RR = {"tp2": 2.0, "tp1_only": 1.0, "sl": -1.0, "timeout": 0.0}


def simulate_account(
    df: pd.DataFrame,
    signals: list[dict],
    initial_balance: float,
    risk_pct: float,
    max_candles: int = BACKTEST_DEFAULTS["max_candles"],
) -> tuple[list[dict], dict]:
    """
    Simula el crecimiento de cuenta trade por trade con riesgo porcentual fijo.

    Por cada señal:
      - risk_amount = balance_actual × risk_pct / 100
      - pnl = risk_amount × R  (R: +2, +1, -1 o 0 según outcome)
      - balance += pnl
      - drawdown = caída desde el máximo histórico

    Retorna
    -------
    trades : lista de dicts con el estado tras cada trade
    summary: dict con métricas globales de la simulación
    """
    balance = float(initial_balance)
    peak = float(initial_balance)
    trades: list[dict] = []

    for num, signal in enumerate(signals, start=1):
        risk_amount = balance * risk_pct / 100.0
        outcome = simulate_trade(df, signal, max_candles)
        pnl = risk_amount * _RR[outcome]
        balance += pnl
        peak = max(peak, balance)
        dd_abs = peak - balance
        dd_pct = (dd_abs / peak * 100.0) if peak > 0 else 0.0

        trades.append({
            "trade_num":    num,
            "signal_index": signal["index"],
            "direction":    signal["direction"],
            "outcome":      outcome,
            "risk_amount":  round(risk_amount, 4),
            "pnl":          round(pnl, 4),
            "balance":      round(balance, 4),
            "peak_balance": round(peak, 4),
            "drawdown_abs": round(dd_abs, 4),
            "drawdown_pct": round(dd_pct, 4),
        })

    summary = _build_summary(initial_balance, balance, trades)
    return trades, summary


def _build_summary(initial: float, final: float, trades: list[dict]) -> dict:
    total_pnl = final - initial
    total_pnl_pct = (total_pnl / initial * 100.0) if initial > 0 else 0.0
    max_dd_abs = max((t["drawdown_abs"] for t in trades), default=0.0)
    max_dd_pct = max((t["drawdown_pct"] for t in trades), default=0.0)

    max_streak = streak = 0
    for t in trades:
        if t["outcome"] == "sl":
            streak += 1
            max_streak = max(max_streak, streak)
        else:
            streak = 0

    return {
        "initial_balance":        round(initial, 4),
        "final_balance":          round(final, 4),
        "total_pnl":              round(total_pnl, 4),
        "total_pnl_pct":          round(total_pnl_pct, 2),
        "max_drawdown_abs":       round(max_dd_abs, 4),
        "max_drawdown_pct":       round(max_dd_pct, 2),
        "max_consecutive_losses": max_streak,
        "total_trades":           len(trades),
    }
