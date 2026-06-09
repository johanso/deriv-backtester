# Tests para el motor de backtesting

import sys
from pathlib import Path
import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from backtest.engine import simulate_trade, run_backtest


def _make_df(prices: list[tuple]) -> pd.DataFrame:
    """Crea un DataFrame mínimo a partir de tuplas (open, high, low, close)."""
    rows = []
    for i, (o, h, l, c) in enumerate(prices):
        rows.append({
            "time":  pd.Timestamp("2024-01-01") + pd.Timedelta(minutes=5 * i),
            "open":  o, "high": h, "low": l, "close": c,
        })
    return pd.DataFrame(rows)


class TestSimulateTrade:
    def test_hit_tp1_long(self):
        df = _make_df([
            (100, 100.5, 99.9, 100.2),   # vela de entrada (índice 0)
            (100.2, 102, 100.1, 101.8),  # golpea TP1
        ])
        signal = {
            "index": 0, "direction": "long",
            "entry_price": 100.2, "sl": 99.0, "tp1": 101.4, "tp2": 102.6,
        }
        result = simulate_trade(df, signal, max_candles=5)
        assert result == "tp1"

    def test_hit_tp2_long(self):
        df = _make_df([
            (100, 100.5, 99.9, 100.2),
            (100.2, 103.0, 100.1, 102.8),  # golpea TP2
        ])
        signal = {
            "index": 0, "direction": "long",
            "entry_price": 100.2, "sl": 99.0, "tp1": 101.4, "tp2": 102.6,
        }
        result = simulate_trade(df, signal, max_candles=5)
        assert result == "tp2"

    def test_hit_sl_long(self):
        df = _make_df([
            (100, 100.5, 99.9, 100.2),
            (100.2, 100.3, 98.5, 98.6),  # golpea SL
        ])
        signal = {
            "index": 0, "direction": "long",
            "entry_price": 100.2, "sl": 99.0, "tp1": 101.4, "tp2": 102.6,
        }
        result = simulate_trade(df, signal, max_candles=5)
        assert result == "sl"

    def test_timeout(self):
        df = _make_df([
            (100, 100.1, 99.9, 100.0),
            (100, 100.1, 99.9, 100.0),
            (100, 100.1, 99.9, 100.0),
        ])
        signal = {
            "index": 0, "direction": "long",
            "entry_price": 100.0, "sl": 95.0, "tp1": 105.0, "tp2": 110.0,
        }
        result = simulate_trade(df, signal, max_candles=2)
        assert result == "timeout"

    def test_hit_tp1_short(self):
        df = _make_df([
            (100, 100.5, 99.9, 100.2),
            (100.2, 100.3, 98.0, 98.2),  # golpea TP1 short
        ])
        signal = {
            "index": 0, "direction": "short",
            "entry_price": 100.0, "sl": 102.0, "tp1": 98.0, "tp2": 96.0,
        }
        result = simulate_trade(df, signal, max_candles=5)
        assert result == "tp1"


class TestRunBacktest:
    def test_sin_senales(self):
        df = _make_df([(100, 101, 99, 100)] * 10)
        metrics = run_backtest(df, [])
        assert metrics["total_signals"] == 0
        assert metrics["win_rate_tp1"] == 0.0

    def test_metricas_completas(self):
        df = _make_df([
            (100, 100.5, 99.9, 100.2),   # índice 0: vela de señal
            (100.2, 103.0, 100.1, 102.8), # siguiente: golpea TP2
        ])
        signals = [{
            "index": 0, "direction": "long",
            "entry_price": 100.2, "sl": 99.0, "tp1": 101.4, "tp2": 102.6,
        }]
        metrics = run_backtest(df, signals, max_candles=5)

        assert metrics["total_signals"] == 1
        assert metrics["win_rate_tp1"] == 100.0
        assert metrics["win_rate_tp2"] == 100.0
        assert metrics["avg_rr"] == 2.0
        assert metrics["max_consecutive_losses"] == 0

    def test_todas_las_claves_presentes(self):
        df = _make_df([(100, 101, 99, 100)] * 5)
        signals = [{"index": 0, "direction": "long",
                    "entry_price": 100, "sl": 98, "tp1": 102, "tp2": 104}]
        metrics = run_backtest(df, signals)
        for key in ("total_signals", "win_rate_tp1", "win_rate_tp2",
                    "avg_rr", "expectancy", "max_consecutive_losses"):
            assert key in metrics
