# Módulo de reporte: tabla en terminal con Rich y exportación a CSV

import csv
from pathlib import Path
from rich.console import Console
from rich.table import Table
from rich import box
from config import PATTERN_LABELS, SYMBOLS, TIMEFRAMES

console = Console()


def print_results(
    results: dict[str, dict],
    symbol_cli: str,
    tf_cli: str,
    candle_count: int,
) -> None:
    """Imprime la tabla de resultados en terminal usando Rich."""

    # Nombre legible del símbolo
    symbol_code = SYMBOLS.get(symbol_cli, symbol_cli)
    console.print()
    console.print(
        f"[bold cyan]Símbolo:[/] {symbol_cli.upper()} ({symbol_code})  "
        f"[bold cyan]Temporalidad:[/] {tf_cli}  "
        f"[bold cyan]Velas:[/] {candle_count}",
    )
    console.print()

    table = Table(box=box.ROUNDED, show_header=True, header_style="bold magenta")
    table.add_column("Patrón",      style="cyan",   min_width=20)
    table.add_column("Señales",     justify="right", style="white")
    table.add_column("WR TP1",      justify="right", style="green")
    table.add_column("WR TP2",      justify="right", style="green")
    table.add_column("Avg R:R",     justify="right", style="yellow")
    table.add_column("Expectancy",  justify="right", style="yellow")
    table.add_column("Max Consec Losses", justify="right", style="red")

    for pattern_key, metrics in results.items():
        label = PATTERN_LABELS.get(pattern_key, pattern_key)
        exp = metrics["expectancy"]
        exp_style = "green" if exp > 0 else "red"

        table.add_row(
            label,
            str(metrics["total_signals"]),
            f"{metrics['win_rate_tp1']:.1f}%",
            f"{metrics['win_rate_tp2']:.1f}%",
            f"{metrics['avg_rr']:.2f}",
            f"[{exp_style}]{exp:.3f}[/{exp_style}]",
            str(metrics["max_consecutive_losses"]),
        )

    console.print(table)
    console.print()


def export_csv(
    results: dict[str, dict],
    symbol_cli: str,
    tf_cli: str,
    filepath: str,
) -> None:
    """Exporta los resultados a un archivo CSV."""
    path = Path(filepath)
    fieldnames = [
        "pattern", "symbol", "timeframe",
        "total_signals", "win_rate_tp1", "win_rate_tp2",
        "avg_rr", "expectancy", "max_consecutive_losses",
    ]

    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()

        for pattern_key, metrics in results.items():
            writer.writerow({
                "pattern":               pattern_key,
                "symbol":                symbol_cli,
                "timeframe":             tf_cli,
                "total_signals":         metrics["total_signals"],
                "win_rate_tp1":          metrics["win_rate_tp1"],
                "win_rate_tp2":          metrics["win_rate_tp2"],
                "avg_rr":                metrics["avg_rr"],
                "expectancy":            metrics["expectancy"],
                "max_consecutive_losses": metrics["max_consecutive_losses"],
            })

    console.print(f"[green]Resultados exportados a:[/] {path.resolve()}")


def print_chart(
    df,
    signals: list[dict],
    pattern_key: str,
    symbol_cli: str,
    tf_cli: str,
    last: int = 200,
) -> None:
    """Muestra gráfico de velas con señales marcadas usando mplfinance."""
    import mplfinance as mpf
    import pandas as pd

    # Tomar solo las últimas N velas
    df_plot = df.tail(last).copy()
    df_plot = df_plot.set_index("time")

    # Filtrar señales dentro del rango visible
    min_idx = len(df) - last
    visible_signals = [s for s in signals if s["index"] >= min_idx]

    # Construir marcadores de compra/venta
    buy_prices = [None] * len(df_plot)
    sell_prices = [None] * len(df_plot)

    for sig in visible_signals:
        local_idx = sig["index"] - min_idx
        if 0 <= local_idx < len(df_plot):
            if sig["direction"] == "long":
                buy_prices[local_idx] = sig["entry_price"]
            else:
                sell_prices[local_idx] = sig["entry_price"]

    apds = []
    if any(v is not None for v in buy_prices):
        apds.append(mpf.make_addplot(
            buy_prices, type="scatter", markersize=80, marker="^", color="lime"
        ))
    if any(v is not None for v in sell_prices):
        apds.append(mpf.make_addplot(
            sell_prices, type="scatter", markersize=80, marker="v", color="red"
        ))

    title = f"{symbol_cli.upper()} {tf_cli} — {PATTERN_LABELS.get(pattern_key, pattern_key)}"
    style = mpf.make_mpf_style(base_mpf_style="nightclouds")

    mpf.plot(
        df_plot,
        type="candle",
        style=style,
        title=title,
        addplot=apds if apds else [],
        volume=False,
    )
