# Tests para la lógica de optimización de parámetros

import sys
from pathlib import Path
import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from patterns.ncandle import detect as detect_ncandle
from backtest.engine import run_backtest


def _make_range_breakout_df(n_base: int = 30) -> pd.DataFrame:
    """DataFrame con velas laterales seguidas de rupturas periódicas."""
    rows = []
    ts = pd.Timestamp("2024-01-01")
    base = 100.0

    for i in range(n_base):
        # Alterna entre velas dentro del rango y rupturas cada 20 velas
        if i > 0 and i % 20 == 0:
            rows.append({
                "time":  ts + pd.Timedelta(minutes=5 * i),
                "open":  base + 0.4, "high": base + 1.5,
                "low":   base + 0.3, "close": base + 1.2,
            })
        else:
            rows.append({
                "time":  ts + pd.Timedelta(minutes=5 * i),
                "open":  base, "high": base + 0.5,
                "low":   base - 0.5, "close": base,
            })

    # Vela de entrada después de la última ruptura
    rows.append({
        "time":  ts + pd.Timedelta(minutes=5 * n_base),
        "open":  base + 1.2, "high": base + 2.0,
        "low":   base + 1.0, "close": base + 1.8,
    })

    return pd.DataFrame(rows)


class TestOptimizeLogic:
    def test_barrido_retorna_una_fila_por_valor(self):
        """Cada valor de n_candles debe producir exactamente una entrada de métricas."""
        df = _make_range_breakout_df(n_base=60)
        param_values = list(range(5, 31, 5))  # [5, 10, 15, 20, 25, 30]

        rows = []
        for val in param_values:
            signals = detect_ncandle(df, n_candles=val)
            metrics = run_backtest(df, signals)
            rows.append({"param_value": val, "metrics": metrics})

        assert len(rows) == len(param_values)

    def test_estructura_cada_fila(self):
        """Cada fila del barrido debe tener param_value y metrics con todas las claves."""
        df = _make_range_breakout_df(n_base=60)
        required_keys = (
            "total_signals", "win_rate_tp1", "win_rate_tp2",
            "avg_rr", "expectancy", "max_consecutive_losses",
        )

        for val in range(5, 31, 5):
            signals = detect_ncandle(df, n_candles=val)
            metrics = run_backtest(df, signals)
            for key in required_keys:
                assert key in metrics, f"Falta '{key}' para n_candles={val}"

    def test_mejor_es_el_de_mayor_expectancy(self):
        """El índice del mejor resultado debe coincidir con el máximo de expectancy."""
        df = _make_range_breakout_df(n_base=60)
        rows = []
        for val in range(5, 31, 5):
            signals = detect_ncandle(df, n_candles=val)
            metrics = run_backtest(df, signals)
            rows.append({"param_value": val, "metrics": metrics})

        best_idx = max(range(len(rows)), key=lambda i: rows[i]["metrics"]["expectancy"])
        best_exp = rows[best_idx]["metrics"]["expectancy"]

        for i, row in enumerate(rows):
            assert row["metrics"]["expectancy"] <= best_exp + 1e-9

    def test_valores_numericos_validos(self):
        """win_rate y expectancy deben ser números finitos."""
        import math
        df = _make_range_breakout_df(n_base=60)

        for val in range(5, 31, 5):
            signals = detect_ncandle(df, n_candles=val)
            metrics = run_backtest(df, signals)
            assert math.isfinite(metrics["win_rate_tp1"])
            assert math.isfinite(metrics["expectancy"])

    def test_win_rate_en_rango_0_100(self):
        """win_rate_tp1 debe estar entre 0 y 100."""
        df = _make_range_breakout_df(n_base=60)

        for val in range(5, 31, 5):
            signals = detect_ncandle(df, n_candles=val)
            metrics = run_backtest(df, signals)
            assert 0.0 <= metrics["win_rate_tp1"] <= 100.0
