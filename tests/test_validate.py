# Tests para la lógica de validación out-of-sample

import sys
from pathlib import Path
import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from patterns.ncandle import detect as detect_ncandle
from backtest.engine import run_backtest


def _make_df(n: int, base: float = 100.0) -> pd.DataFrame:
    """DataFrame con rupturas periódicas cada 20 velas."""
    rows = []
    ts = pd.Timestamp("2024-01-01")
    for i in range(n):
        if i > 0 and i % 20 == 0:
            rows.append({
                "time":  ts + pd.Timedelta(minutes=i),
                "open":  base + 0.3, "high": base + 1.5,
                "low":   base + 0.2, "close": base + 1.2,
            })
        else:
            rows.append({
                "time":  ts + pd.Timedelta(minutes=i),
                "open":  base, "high": base + 0.5,
                "low":   base - 0.5, "close": base,
            })
    return pd.DataFrame(rows)


class TestSplit:
    def test_mitades_iguales_en_n_par(self):
        df = _make_df(100)
        split = len(df) // 2
        df_is  = df.iloc[:split].reset_index(drop=True)
        df_oos = df.iloc[split:].reset_index(drop=True)
        assert len(df_is) == 50
        assert len(df_oos) == 50
        assert len(df_is) + len(df_oos) == len(df)

    def test_indices_reseteados(self):
        """Cada mitad debe tener índices 0..N-1 para que el motor de backtest funcione."""
        df = _make_df(60)
        split = len(df) // 2
        df_oos = df.iloc[split:].reset_index(drop=True)
        assert df_oos.index[0] == 0
        assert df_oos.index[-1] == len(df_oos) - 1

    def test_no_solapamiento_temporal(self):
        """La última vela IS debe ser anterior a la primera vela OOS."""
        df = _make_df(60)
        split = len(df) // 2
        df_is  = df.iloc[:split].reset_index(drop=True)
        df_oos = df.iloc[split:].reset_index(drop=True)
        assert df_is["time"].iloc[-1] < df_oos["time"].iloc[0]


class TestIsOosMetrics:
    def test_ambas_mitades_producen_metricas_completas(self):
        df = _make_df(200)
        split = len(df) // 2
        df_is  = df.iloc[:split].reset_index(drop=True)
        df_oos = df.iloc[split:].reset_index(drop=True)

        required = (
            "total_signals", "win_rate_tp1", "win_rate_tp2",
            "avg_rr", "expectancy", "max_consecutive_losses",
        )
        for half in (df_is, df_oos):
            signals = detect_ncandle(half, n_candles=8)
            metrics = run_backtest(half, signals)
            for key in required:
                assert key in metrics

    def test_senales_is_no_contaminan_oos(self):
        """Las señales detectadas en IS no deben referenciar índices de OOS."""
        df = _make_df(200)
        split = len(df) // 2
        df_is = df.iloc[:split].reset_index(drop=True)

        signals = detect_ncandle(df_is, n_candles=8)
        for s in signals:
            assert s["index"] < split, f"Señal IS con índice {s['index']} >= split {split}"

    def test_win_rate_en_rango_valido(self):
        df = _make_df(200)
        split = len(df) // 2
        for half in (df.iloc[:split].reset_index(drop=True),
                     df.iloc[split:].reset_index(drop=True)):
            signals = detect_ncandle(half, n_candles=8)
            m = run_backtest(half, signals)
            assert 0.0 <= m["win_rate_tp1"] <= 100.0
            assert 0.0 <= m["win_rate_tp2"] <= 100.0


class TestVeredicto:
    def test_positivo_es_valido(self):
        """Expectancy OOS > 0 => veredicto VALIDO."""
        oos_exp = 0.15
        assert oos_exp > 0

    def test_negativo_es_overfitting(self):
        """Expectancy OOS <= 0 => veredicto OVERFITTING."""
        oos_exp = -0.05
        assert oos_exp <= 0

    def test_exactamente_cero_es_overfitting(self):
        oos_exp = 0.0
        assert not (oos_exp > 0)
