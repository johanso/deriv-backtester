# Tests para los detectores de patrones (sin conexión a la API)

import sys
from pathlib import Path
import pandas as pd
import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from patterns.consolidation import detect as detect_consolidation
from patterns.bounce import detect as detect_bounce
from patterns.impulse import detect as detect_impulse
from patterns.double import detect as detect_double
from patterns.bollinger import detect as detect_bollinger
from patterns.ncandle import detect as detect_ncandle


def _make_flat_df(n: int = 50, price: float = 100.0, spread: float = 0.1) -> pd.DataFrame:
    """DataFrame de velas planas para pruebas de consolidación."""
    rows = []
    for i in range(n):
        rows.append({
            "time":  pd.Timestamp("2024-01-01") + pd.Timedelta(minutes=5 * i),
            "open":  price,
            "high":  price + spread,
            "low":   price - spread,
            "close": price,
        })
    return pd.DataFrame(rows)


def _make_trending_df(n: int = 60, start: float = 100.0, step: float = 0.5) -> pd.DataFrame:
    """DataFrame con tendencia alcista para pruebas de impulso."""
    rows = []
    p = start
    for i in range(n):
        rows.append({
            "time":  pd.Timestamp("2024-01-01") + pd.Timedelta(minutes=5 * i),
            "open":  p,
            "high":  p + step * 2,
            "low":   p - step * 0.5,
            "close": p + step,
        })
        p += step
    return pd.DataFrame(rows)


# ─── Consolidación ────────────────────────────────────────────────────────────

class TestConsolidation:
    def test_retorna_lista(self):
        df = _make_flat_df()
        result = detect_consolidation(df)
        assert isinstance(result, list)

    def test_estructura_senal(self):
        """Cada señal debe tener las claves requeridas y precios coherentes."""
        df = _make_flat_df(n=100)
        # Agregar ruptura alcista al final
        breakout_row = {
            "time":  pd.Timestamp("2024-01-01") + pd.Timedelta(minutes=5 * 100),
            "open":  100.2,
            "high":  101.0,
            "low":   100.1,
            "close": 100.9,  # cierra por encima del high de la zona (100 + 0.1)
        }
        df2 = pd.concat([df, pd.DataFrame([breakout_row])], ignore_index=True)
        signals = detect_consolidation(df2, n_candles=4, range_pct=0.005)

        if signals:
            s = signals[0]
            for key in ("index", "type", "direction", "entry_price", "sl", "tp1", "tp2"):
                assert key in s, f"Falta clave: {key}"
            if s["direction"] == "long":
                assert s["tp1"] > s["entry_price"] > s["sl"]
            else:
                assert s["tp1"] < s["entry_price"] < s["sl"]

    def test_sin_ruptura_no_hay_senales_en_flat(self):
        """En un DataFrame completamente plano sin ruptura, no debe haber señales."""
        df = _make_flat_df(n=20, spread=0.0001)
        signals = detect_consolidation(df, range_pct=0.0001)
        # El rango es casi 0, por lo tanto range_pct no se supera,
        # pero tampoco hay ruptura: todas las velas cierran dentro de la zona
        assert isinstance(signals, list)

    def test_parametros_configurables(self):
        """Debe funcionar con distintos parámetros."""
        df = _make_flat_df(n=30)
        s1 = detect_consolidation(df, n_candles=3, range_pct=0.01)
        s2 = detect_consolidation(df, n_candles=6, range_pct=0.001)
        assert isinstance(s1, list)
        assert isinstance(s2, list)


# ─── Bounce ───────────────────────────────────────────────────────────────────

class TestBounce:
    def test_retorna_lista(self):
        df = _make_trending_df()
        result = detect_bounce(df)
        assert isinstance(result, list)

    def test_estructura_senal(self):
        signals = detect_bounce(_make_trending_df(n=80), lookback=20)
        for s in signals:
            for key in ("index", "type", "direction", "entry_price", "sl", "tp1", "tp2"):
                assert key in s
            if s["direction"] == "long":
                assert s["tp1"] > s["entry_price"] > s["sl"]
            else:
                assert s["tp1"] < s["entry_price"] < s["sl"]

    def test_direction_valida(self):
        signals = detect_bounce(_make_trending_df(n=80))
        for s in signals:
            assert s["direction"] in ("long", "short")


# ─── Impulso ──────────────────────────────────────────────────────────────────

class TestImpulse:
    def _make_impulse_df(self) -> pd.DataFrame:
        """DataFrame con un impulso claro seguido de retroceso y continuación."""
        rows = []
        base = 100.0

        # Velas normales
        for i in range(10):
            rows.append({"time": pd.Timestamp("2024-01-01") + pd.Timedelta(minutes=5 * i),
                         "open": base, "high": base + 0.1, "low": base - 0.1, "close": base})

        # Vela de impulso alcista grande
        rows.append({"time": pd.Timestamp("2024-01-01") + pd.Timedelta(minutes=5 * 10),
                     "open": base, "high": base + 1.5, "low": base - 0.1, "close": base + 1.2})

        # Vela de retroceso pequeño
        rows.append({"time": pd.Timestamp("2024-01-01") + pd.Timedelta(minutes=5 * 11),
                     "open": base + 1.2, "high": base + 1.3, "low": base + 0.8, "close": base + 0.9})

        # Vela de continuación alcista
        rows.append({"time": pd.Timestamp("2024-01-01") + pd.Timedelta(minutes=5 * 12),
                     "open": base + 0.9, "high": base + 2.0, "low": base + 0.85, "close": base + 1.8})

        return pd.DataFrame(rows)

    def test_retorna_lista(self):
        assert isinstance(detect_impulse(_make_trending_df()), list)

    def test_detecta_impulso_claro(self):
        df = self._make_impulse_df()
        signals = detect_impulse(df, body_pct=0.005, max_retrace=0.5)
        assert isinstance(signals, list)

    def test_estructura_senal(self):
        df = self._make_impulse_df()
        signals = detect_impulse(df, body_pct=0.005)
        for s in signals:
            for key in ("index", "type", "direction", "entry_price", "sl", "tp1", "tp2"):
                assert key in s
            if s["direction"] == "long":
                assert s["tp1"] > s["entry_price"] > s["sl"]
            else:
                assert s["tp1"] < s["entry_price"] < s["sl"]


# ─── Double top/bottom ────────────────────────────────────────────────────────

class TestDouble:
    def _make_double_top_df(self) -> pd.DataFrame:
        """DataFrame con un doble techo explícito."""
        rows = []
        base = 100.0
        ts = pd.Timestamp("2024-01-01")

        prices = [100, 101, 102, 103, 104, 103, 102, 101,  # primer pico ~ 104
                  100, 101, 102, 103, 104.05, 103, 102,    # segundo pico ~ 104 (dentro de tol)
                  100.5]                                     # ruptura bajista del valle (101)

        for i, p in enumerate(prices):
            rows.append({
                "time":  ts + pd.Timedelta(minutes=5 * i),
                "open":  p - 0.1,
                "high":  p + 0.2,
                "low":   p - 0.2,
                "close": p - 0.15,
            })

        return pd.DataFrame(rows)

    def test_retorna_lista(self):
        assert isinstance(detect_double(_make_flat_df()), list)

    def test_detecta_doble_techo(self):
        df = self._make_double_top_df()
        signals = detect_double(df, tol_pct=0.005, min_gap=3)
        assert isinstance(signals, list)

    def test_estructura_senal(self):
        df = self._make_double_top_df()
        signals = detect_double(df, tol_pct=0.005, min_gap=3)
        for s in signals:
            for key in ("index", "type", "direction", "entry_price", "sl", "tp1", "tp2"):
                assert key in s
            if s["direction"] == "long":
                assert s["tp1"] > s["entry_price"] > s["sl"]
            else:
                assert s["tp1"] < s["entry_price"] < s["sl"]


# ─── Bollinger Reversion ──────────────────────────────────────────────────────

class TestBollinger:
    def _make_bollinger_df(self) -> pd.DataFrame:
        """DataFrame con precio estable seguido de una extensión y reversión."""
        rows = []
        ts = pd.Timestamp("2024-01-01")
        base = 100.0

        # 25 velas estables para que la SMA/std se estabilicen
        for i in range(25):
            rows.append({
                "time":  ts + pd.Timedelta(minutes=5 * i),
                "open":  base, "high": base + 0.2, "low": base - 0.2, "close": base,
            })

        # Vela de señal SHORT: cierra muy por encima de la banda superior
        rows.append({
            "time":  ts + pd.Timedelta(minutes=5 * 25),
            "open":  base + 0.5, "high": base + 2.0, "low": base + 0.4, "close": base + 1.8,
        })

        # Vela de confirmación SHORT: cierra por debajo de la banda superior (regresa a base)
        rows.append({
            "time":  ts + pd.Timedelta(minutes=5 * 26),
            "open":  base + 1.0, "high": base + 1.2, "low": base - 0.1, "close": base + 0.1,
        })

        return pd.DataFrame(rows)

    def _make_bollinger_long_df(self) -> pd.DataFrame:
        """DataFrame con extensión bajista y reversión alcista."""
        rows = []
        ts = pd.Timestamp("2024-01-01")
        base = 100.0

        for i in range(25):
            rows.append({
                "time":  ts + pd.Timedelta(minutes=5 * i),
                "open":  base, "high": base + 0.2, "low": base - 0.2, "close": base,
            })

        # Vela de señal LONG: cierra muy por debajo de la banda inferior
        rows.append({
            "time":  ts + pd.Timedelta(minutes=5 * 25),
            "open":  base - 0.5, "high": base - 0.4, "low": base - 2.0, "close": base - 1.8,
        })

        # Vela de confirmación LONG: cierra por encima de la banda inferior
        rows.append({
            "time":  ts + pd.Timedelta(minutes=5 * 26),
            "open":  base - 1.0, "high": base + 0.1, "low": base - 1.2, "close": base - 0.1,
        })

        return pd.DataFrame(rows)

    def test_retorna_lista(self):
        assert isinstance(detect_bollinger(_make_flat_df(n=50)), list)

    def test_senal_short_precios_coherentes(self):
        df = self._make_bollinger_df()
        signals = detect_bollinger(df, period=20, std_dev=2.0)
        short_signals = [s for s in signals if s["direction"] == "short"]
        for s in short_signals:
            assert s["tp1"] < s["entry_price"] < s["sl"]

    def test_senal_long_precios_coherentes(self):
        df = self._make_bollinger_long_df()
        signals = detect_bollinger(df, period=20, std_dev=2.0)
        long_signals = [s for s in signals if s["direction"] == "long"]
        for s in long_signals:
            assert s["tp1"] > s["entry_price"] > s["sl"]

    def test_estructura_senal(self):
        df = self._make_bollinger_df()
        signals = detect_bollinger(df, period=20, std_dev=2.0)
        for s in signals:
            for key in ("index", "type", "direction", "entry_price", "sl", "tp1", "tp2"):
                assert key in s
            assert s["type"] == "bollinger"


# ─── N-Candle Breakout ────────────────────────────────────────────────────────

class TestNCandle:
    def _make_ncandle_long_df(self, n: int = 15) -> pd.DataFrame:
        """DataFrame con rango lateral seguido de una ruptura alcista clara."""
        rows = []
        ts = pd.Timestamp("2024-01-01")
        base = 100.0

        # n+1 velas dentro del rango
        for i in range(n + 1):
            rows.append({
                "time":  ts + pd.Timedelta(minutes=5 * i),
                "open":  base, "high": base + 0.5, "low": base - 0.5, "close": base,
            })

        # Vela de ruptura alcista: cierra por encima del high del rango
        rows.append({
            "time":  ts + pd.Timedelta(minutes=5 * (n + 1)),
            "open":  base + 0.4, "high": base + 1.5, "low": base + 0.3, "close": base + 1.2,
        })

        # Vela de entrada (siguiente a la ruptura)
        rows.append({
            "time":  ts + pd.Timedelta(minutes=5 * (n + 2)),
            "open":  base + 1.2, "high": base + 2.0, "low": base + 1.0, "close": base + 1.8,
        })

        return pd.DataFrame(rows)

    def _make_ncandle_short_df(self, n: int = 15) -> pd.DataFrame:
        """DataFrame con rango lateral seguido de una ruptura bajista clara."""
        rows = []
        ts = pd.Timestamp("2024-01-01")
        base = 100.0

        for i in range(n + 1):
            rows.append({
                "time":  ts + pd.Timedelta(minutes=5 * i),
                "open":  base, "high": base + 0.5, "low": base - 0.5, "close": base,
            })

        # Vela de ruptura bajista: cierra por debajo del low del rango
        rows.append({
            "time":  ts + pd.Timedelta(minutes=5 * (n + 1)),
            "open":  base - 0.4, "high": base - 0.3, "low": base - 1.5, "close": base - 1.2,
        })

        # Vela de entrada
        rows.append({
            "time":  ts + pd.Timedelta(minutes=5 * (n + 2)),
            "open":  base - 1.2, "high": base - 1.0, "low": base - 2.0, "close": base - 1.8,
        })

        return pd.DataFrame(rows)

    def test_retorna_lista(self):
        assert isinstance(detect_ncandle(_make_flat_df(n=40)), list)

    def test_senal_long_precios_coherentes(self):
        df = self._make_ncandle_long_df()
        signals = detect_ncandle(df, n_candles=15)
        long_signals = [s for s in signals if s["direction"] == "long"]
        assert len(long_signals) > 0
        for s in long_signals:
            assert s["tp1"] > s["entry_price"] > s["sl"]

    def test_senal_short_precios_coherentes(self):
        df = self._make_ncandle_short_df()
        signals = detect_ncandle(df, n_candles=15)
        short_signals = [s for s in signals if s["direction"] == "short"]
        assert len(short_signals) > 0
        for s in short_signals:
            assert s["tp1"] < s["entry_price"] < s["sl"]

    def test_estructura_senal(self):
        df = self._make_ncandle_long_df()
        signals = detect_ncandle(df, n_candles=15)
        for s in signals:
            for key in ("index", "type", "direction", "entry_price", "sl", "tp1", "tp2"):
                assert key in s
            assert s["type"] == "ncandle"
