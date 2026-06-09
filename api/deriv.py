# Módulo de conexión a la API WebSocket de Deriv y descarga de velas OHLC

import asyncio
import json
import time
import websockets
import pandas as pd
from config import DERIV_WS_URL, API_MAX_RETRIES, API_RETRY_BACKOFF


async def _fetch_candles_ws(symbol: str, granularity: int, count: int) -> list[dict]:
    """Conecta al WebSocket de Deriv y descarga las velas OHLC crudas."""
    request = {
        "ticks_history": symbol,
        "style": "candles",
        "granularity": granularity,
        "count": count,
        "end": "latest",
    }

    async with websockets.connect(DERIV_WS_URL) as ws:
        await ws.send(json.dumps(request))
        raw = await ws.recv()

    data = json.loads(raw)

    if "error" in data:
        raise ValueError(f"Error de API Deriv: {data['error']['message']}")

    return data["candles"]


def fetch_ohlc(symbol: str, granularity: int, count: int = 5000) -> pd.DataFrame:
    """
    Descarga velas OHLC desde Deriv con reintentos automáticos.

    Parámetros
    ----------
    symbol      : código de símbolo de la API (ej. '1HZ75V')
    granularity : tamaño de la vela en segundos
    count       : número de velas a descargar

    Retorna
    -------
    DataFrame con columnas: time, open, high, low, close
    """
    last_error = None

    for attempt in range(1, API_MAX_RETRIES + 1):
        try:
            candles = asyncio.run(_fetch_candles_ws(symbol, granularity, count))
            return _to_dataframe(candles)
        except Exception as exc:
            last_error = exc
            if attempt < API_MAX_RETRIES:
                time.sleep(API_RETRY_BACKOFF)

    raise ConnectionError(
        f"No se pudo conectar a Deriv después de {API_MAX_RETRIES} intentos. "
        f"Último error: {last_error}"
    )


def _to_dataframe(candles: list[dict]) -> pd.DataFrame:
    """Convierte la lista de velas crudas a un DataFrame de pandas."""
    df = pd.DataFrame(candles)
    df["time"] = pd.to_datetime(df["epoch"], unit="s", utc=True)
    df = df[["time", "open", "high", "low", "close"]].copy()

    for col in ["open", "high", "low", "close"]:
        df[col] = df[col].astype(float)

    df = df.sort_values("time").reset_index(drop=True)
    return df
