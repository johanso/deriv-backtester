# Tests para la capa de API (sin conexión real, usando datos mock)

import sys
from pathlib import Path
import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from api.deriv import _to_dataframe


class TestToDataframe:
    def test_conversion_basica(self):
        candles = [
            {"epoch": 1700000000, "open": "100.1", "high": "101.0", "low": "99.5", "close": "100.8"},
            {"epoch": 1700000300, "open": "100.8", "high": "102.0", "low": "100.0", "close": "101.5"},
        ]
        df = _to_dataframe(candles)
        assert list(df.columns) == ["time", "open", "high", "low", "close"]
        assert len(df) == 2
        assert df["open"].dtype == float

    def test_ordenado_por_tiempo(self):
        candles = [
            {"epoch": 1700000300, "open": "101.0", "high": "102.0", "low": "100.5", "close": "101.5"},
            {"epoch": 1700000000, "open": "100.0", "high": "101.0", "low": "99.5", "close": "100.5"},
        ]
        df = _to_dataframe(candles)
        assert df.iloc[0]["open"] == 100.0  # la vela más antigua primero

    def test_columna_time_es_datetime(self):
        candles = [{"epoch": 1700000000, "open": "100", "high": "101", "low": "99", "close": "100"}]
        df = _to_dataframe(candles)
        assert pd.api.types.is_datetime64_any_dtype(df["time"])
