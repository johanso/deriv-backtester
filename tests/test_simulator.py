# Tests para el simulador de crecimiento de cuenta

import sys
from pathlib import Path
import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from backtest.simulator import simulate_account


def _make_df(prices: list[tuple]) -> pd.DataFrame:
    """Crea DataFrame mínimo desde tuplas (open, high, low, close)."""
    rows = []
    for i, (o, h, l, c) in enumerate(prices):
        rows.append({
            "time":  pd.Timestamp("2024-01-01") + pd.Timedelta(minutes=i),
            "open":  o, "high": h, "low": l, "close": c,
        })
    return pd.DataFrame(rows)


def _signal(idx: int, direction: str = "long",
            entry: float = 100.0, sl: float = 99.0,
            tp1: float = 101.0, tp2: float = 102.0) -> dict:
    return {
        "index": idx, "type": "test", "direction": direction,
        "entry_price": entry, "sl": sl, "tp1": tp1, "tp2": tp2,
    }


# ─── Casos de resultado único ─────────────────────────────────────────────────

class TestSingleTrade:
    def _run(self, candles, signal, balance=1000.0, risk_pct=1.0):
        df = _make_df(candles)
        trades, summary = simulate_account(df, [signal], balance, risk_pct)
        return trades[0], summary

    def test_tp2_incrementa_balance_por_2r(self):
        # Vela de señal en idx=0, siguiente golpea TP2 (high >= 102)
        candles = [
            (100, 100.5, 99.5, 100.0),
            (100, 103.0, 99.8, 102.5),
        ]
        trade, summary = self._run(candles, _signal(0))
        risk = 1000.0 * 1.0 / 100          # 10.0
        assert trade["outcome"] == "tp2"
        assert abs(trade["pnl"] - 2 * risk) < 1e-6
        assert abs(summary["final_balance"] - (1000.0 + 2 * risk)) < 1e-6

    def test_tp1_only_incrementa_balance_por_1r(self):
        # high llega a TP1 (101) pero no a TP2 (102)
        candles = [
            (100, 100.5, 99.5, 100.0),
            (100, 101.5, 99.8, 101.2),
        ]
        trade, summary = self._run(candles, _signal(0))
        risk = 10.0
        assert trade["outcome"] == "tp1_only"
        assert abs(trade["pnl"] - risk) < 1e-6

    def test_sl_reduce_balance_por_1r(self):
        # low cae a SL (99)
        candles = [
            (100, 100.5, 99.5, 100.0),
            (100, 100.2, 98.5, 98.8),
        ]
        trade, summary = self._run(candles, _signal(0))
        risk = 10.0
        assert trade["outcome"] == "sl"
        assert abs(trade["pnl"] - (-risk)) < 1e-6
        assert abs(summary["final_balance"] - (1000.0 - risk)) < 1e-6

    def test_timeout_no_cambia_balance(self):
        candles = [
            (100, 100.5, 99.5, 100.0),
            (100, 100.4, 99.6, 100.1),
            (100, 100.4, 99.6, 100.1),
        ]
        trade, summary = self._run(candles, _signal(0), balance=500.0)
        assert trade["outcome"] == "timeout"
        assert trade["pnl"] == 0.0
        assert summary["final_balance"] == 500.0


# ─── Riesgo porcentual ────────────────────────────────────────────────────────

class TestRiskCompounding:
    def test_risk_amount_es_pct_del_balance_actual(self):
        """Después de ganar, el siguiente riesgo debe ser mayor."""
        candles = [
            (100, 100.5, 99.5, 100.0),
            (100, 103.0, 99.8, 102.5),  # TP2 en trade 1
            (100, 100.5, 99.5, 100.0),
            (100, 103.0, 99.8, 102.5),  # TP2 en trade 2
        ]
        df = _make_df(candles)
        signals = [_signal(0), _signal(2)]
        trades, _ = simulate_account(df, signals, initial_balance=1000.0, risk_pct=1.0)

        risk1 = 1000.0 * 0.01           # 10.0
        balance_after_1 = 1000.0 + 2 * risk1  # 1020.0
        risk2_expected = balance_after_1 * 0.01  # 10.2

        assert abs(trades[0]["risk_amount"] - risk1) < 1e-6
        assert abs(trades[1]["risk_amount"] - risk2_expected) < 1e-6

    def test_balance_nunca_negativo_con_riesgo_bajo(self):
        """Con risk_pct=1%, el balance no puede bajar de 0 en ningún trade."""
        candles = [(100, 100.2, 98.5, 98.8)] * 60  # todos SL
        df = _make_df(candles)
        signals = [_signal(i) for i in range(0, 50, 2)]
        trades, summary = simulate_account(df, signals, initial_balance=1000.0, risk_pct=1.0)
        for t in trades:
            assert t["balance"] > 0


# ─── Drawdown ─────────────────────────────────────────────────────────────────

class TestDrawdown:
    def test_drawdown_cero_al_inicio(self):
        candles = [
            (100, 100.5, 99.5, 100.0),
            (100, 103.0, 99.8, 102.5),
        ]
        df = _make_df(candles)
        trades, _ = simulate_account(df, [_signal(0)], 1000.0, 1.0)
        # Primer trade es ganador, balance > peak inicial => drawdown = 0
        assert trades[0]["drawdown_abs"] == 0.0
        assert trades[0]["drawdown_pct"] == 0.0

    def test_drawdown_positivo_tras_perdida(self):
        candles = [
            (100, 100.5, 99.5, 100.0),
            (100, 103.0, 99.8, 102.5),  # TP2: sube a 1020
            (100, 100.5, 99.5, 100.0),
            (100, 100.2, 98.5, 98.8),  # SL: baja
        ]
        df = _make_df(candles)
        signals = [_signal(0), _signal(2)]
        trades, _ = simulate_account(df, signals, 1000.0, 1.0)
        assert trades[1]["drawdown_abs"] > 0
        assert trades[1]["drawdown_pct"] > 0

    def test_max_drawdown_en_summary(self):
        candles = [
            (100, 100.5, 99.5, 100.0),
            (100, 100.2, 98.5, 98.8),
        ] * 5
        df = _make_df(candles)
        signals = [_signal(i) for i in range(0, 8, 2)]
        _, summary = simulate_account(df, signals, 1000.0, 1.0)
        assert summary["max_drawdown_abs"] >= 0.0
        assert summary["max_drawdown_pct"] >= 0.0


# ─── Summary ──────────────────────────────────────────────────────────────────

class TestSummary:
    def test_claves_presentes(self):
        df = _make_df([(100, 101, 99, 100)] * 5)
        _, summary = simulate_account(df, [_signal(0)], 1000.0, 1.0)
        for key in (
            "initial_balance", "final_balance", "total_pnl", "total_pnl_pct",
            "max_drawdown_abs", "max_drawdown_pct",
            "max_consecutive_losses", "total_trades",
        ):
            assert key in summary

    def test_total_trades_igual_a_senales(self):
        df = _make_df([(100, 101, 99, 100)] * 10)
        signals = [_signal(i) for i in range(0, 8, 2)]
        trades, summary = simulate_account(df, signals, 1000.0, 1.0)
        assert summary["total_trades"] == len(signals)
        assert summary["total_trades"] == len(trades)

    def test_total_pnl_coherente(self):
        df = _make_df([(100, 100.5, 99.5, 100.0), (100, 103.0, 99.8, 102.5)])
        _, summary = simulate_account(df, [_signal(0)], 1000.0, 1.0)
        assert abs(summary["total_pnl"] - (summary["final_balance"] - summary["initial_balance"])) < 1e-4

    def test_sin_senales_devuelve_summary_vacio(self):
        df = _make_df([(100, 101, 99, 100)] * 5)
        trades, summary = simulate_account(df, [], 1000.0, 1.0)
        assert trades == []
        assert summary["total_trades"] == 0
        assert summary["final_balance"] == 1000.0
        assert summary["total_pnl"] == 0.0

    def test_racha_perdedora_maxima(self):
        """Tres SL seguidos => max_consecutive_losses == 3."""
        # Todas las velas caen al SL
        candles = [(100, 100.2, 98.5, 98.8)] * 8
        df = _make_df(candles)
        signals = [_signal(i) for i in range(0, 6, 2)]
        _, summary = simulate_account(df, signals, 1000.0, 1.0)
        assert summary["max_consecutive_losses"] == 3
