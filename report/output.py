# Módulo de reporte: tabla en terminal con Rich y exportación a CSV

import csv
from pathlib import Path
from rich.console import Console
from rich.table import Table
from rich import box
from config import PATTERN_LABELS, SYMBOLS, TIMEFRAMES, OPTIMIZE_PARAMS

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


def print_optimize_table(
    rows: list[dict],
    symbol_cli: str,
    tf_cli: str,
    pattern_key: str,
    candle_count: int,
) -> None:
    """
    Imprime la tabla de optimización de parámetros.

    Cada elemento de `rows` es:
        { "param_value": int, "metrics": dict }
    La fila con mayor Expectancy se marca con ★.
    """
    if not rows:
        console.print("[yellow]Sin resultados para mostrar.[/]")
        return

    opt = OPTIMIZE_PARAMS.get(pattern_key, {})
    param_label = opt.get("label", "Parámetro")
    pattern_label = PATTERN_LABELS.get(pattern_key, pattern_key)
    symbol_code = SYMBOLS.get(symbol_cli, symbol_cli)

    console.print()
    console.print(
        f"[bold cyan]Optimización:[/] {pattern_label}  "
        f"[bold cyan]Símbolo:[/] {symbol_cli.upper()} ({symbol_code})  "
        f"[bold cyan]TF:[/] {tf_cli}  "
        f"[bold cyan]Velas:[/] {candle_count}"
    )
    console.print()

    best_idx = max(range(len(rows)), key=lambda i: rows[i]["metrics"]["expectancy"])

    table = Table(box=box.ROUNDED, show_header=True, header_style="bold magenta")
    table.add_column(param_label,    style="cyan",  min_width=12)
    table.add_column("Señales",      justify="right", style="white")
    table.add_column("WR TP1",       justify="right", style="green")
    table.add_column("Expectancy",   justify="right")

    for i, row in enumerate(rows):
        m = row["metrics"]
        is_best = (i == best_idx)
        exp = m["expectancy"]
        exp_color = "green" if exp > 0 else "red"

        param_cell = f"[bold yellow]>> {row['param_value']}[/]" if is_best else str(row["param_value"])
        exp_cell = f"[bold {exp_color}]{exp:.3f}[/]" if is_best else f"[{exp_color}]{exp:.3f}[/{exp_color}]"

        table.add_row(
            param_cell,
            str(m["total_signals"]),
            f"{m['win_rate_tp1']:.1f}%",
            exp_cell,
        )

    console.print(table)

    best_val = rows[best_idx]["param_value"]
    best_exp = rows[best_idx]["metrics"]["expectancy"]
    console.print(
        f"[bold green]Mejor parámetro:[/] {param_label} = [bold]{best_val}[/]  "
        f"[bold green]Expectancy:[/] {best_exp:.3f}"
    )
    console.print()


def print_simulate_summary(
    summary: dict,
    symbol_cli: str,
    tf_cli: str,
    pattern_key: str,
    pattern_params: dict,
) -> None:
    """Imprime la tabla resumen de la simulación de cuenta en terminal."""
    pattern_label = PATTERN_LABELS.get(pattern_key, pattern_key)
    symbol_code = SYMBOLS.get(symbol_cli, symbol_cli)
    params_str = "  ".join(f"{k}={v}" for k, v in pattern_params.items())

    console.print()
    console.print(
        f"[bold cyan]Simulacion:[/] {pattern_label}  "
        f"[bold cyan]Simbolo:[/] {symbol_cli.upper()} ({symbol_code})  "
        f"[bold cyan]TF:[/] {tf_cli}"
        + (f"  [bold cyan]Params:[/] {params_str}" if params_str else "")
    )
    console.print()

    pnl_color  = "green" if summary["total_pnl"] >= 0 else "red"
    sign       = "+" if summary["total_pnl"] >= 0 else ""

    table = Table(box=box.ROUNDED, show_header=True, header_style="bold magenta")
    table.add_column("Metrica",    style="cyan", min_width=26)
    table.add_column("Valor",      justify="right", style="white", min_width=16)

    table.add_row("Balance inicial",        f"${summary['initial_balance']:,.2f}")
    table.add_row("Balance final",          f"[{pnl_color}]${summary['final_balance']:,.2f}[/{pnl_color}]")
    table.add_row("Ganancia total ($)",     f"[{pnl_color}]{sign}${abs(summary['total_pnl']):,.2f}[/{pnl_color}]")
    table.add_row("Ganancia total (%)",     f"[{pnl_color}]{sign}{summary['total_pnl_pct']:.2f}%[/{pnl_color}]")
    table.add_row("Max Drawdown ($)",       f"[red]-${summary['max_drawdown_abs']:,.2f}[/red]")
    table.add_row("Max Drawdown (%)",       f"[red]-{summary['max_drawdown_pct']:.2f}%[/red]")
    table.add_row("Racha perdedora max",    str(summary["max_consecutive_losses"]))
    table.add_row("Total trades",           str(summary["total_trades"]))

    console.print(table)
    console.print()


def plot_balance_curve(trades: list[dict], symbol_cli: str, tf_cli: str) -> None:
    """Grafica la curva de balance y el drawdown con matplotlib."""
    import matplotlib.pyplot as plt
    import matplotlib.ticker as mticker

    nums     = [t["trade_num"]    for t in trades]
    balances = [t["balance"]      for t in trades]
    dds      = [-t["drawdown_pct"] for t in trades]  # negativo para graficar hacia abajo

    fig, (ax1, ax2) = plt.subplots(
        2, 1, figsize=(12, 7), sharex=True,
        gridspec_kw={"height_ratios": [3, 1], "hspace": 0.08},
    )
    fig.suptitle(
        f"Curva de Balance — {symbol_cli.upper()} {tf_cli}",
        fontsize=13, fontweight="bold",
    )

    # ── Panel superior: balance ──────────────────────────────────────────────
    color_line = "#00c896"
    ax1.plot(nums, balances, color=color_line, linewidth=1.4, label="Balance")
    ax1.fill_between(nums, balances, min(balances), alpha=0.12, color=color_line)
    ax1.axhline(balances[0], color="gray", linewidth=0.8, linestyle="--", label="Balance inicial")
    ax1.set_ylabel("Balance ($)", fontsize=10)
    ax1.yaxis.set_major_formatter(mticker.FormatStrFormatter("$%.0f"))
    ax1.legend(fontsize=9)
    ax1.grid(axis="y", linestyle=":", alpha=0.4)
    ax1.set_facecolor("#0d1117")
    fig.patch.set_facecolor("#0d1117")
    ax1.tick_params(colors="white")
    ax1.yaxis.label.set_color("white")
    ax1.title.set_color("white")
    for spine in ax1.spines.values():
        spine.set_edgecolor("#333")

    # ── Panel inferior: drawdown ──────────────────────────────────────────────
    ax2.fill_between(nums, dds, 0, alpha=0.7, color="#e05252", label="Drawdown %")
    ax2.plot(nums, dds, color="#e05252", linewidth=0.8)
    ax2.set_ylabel("Drawdown (%)", fontsize=10)
    ax2.set_xlabel("Numero de trade", fontsize=10)
    ax2.yaxis.set_major_formatter(mticker.FormatStrFormatter("%.1f%%"))
    ax2.legend(fontsize=9)
    ax2.grid(axis="y", linestyle=":", alpha=0.4)
    ax2.set_facecolor("#0d1117")
    ax2.tick_params(colors="white")
    ax2.xaxis.label.set_color("white")
    ax2.yaxis.label.set_color("white")
    for spine in ax2.spines.values():
        spine.set_edgecolor("#333")

    plt.tight_layout()
    plt.show()


def print_validate_table(
    is_metrics: dict,
    oos_metrics: dict,
    is_candles: int,
    oos_candles: int,
    symbol_cli: str,
    tf_cli: str,
    pattern_key: str,
    pattern_params: dict,
) -> None:
    """
    Imprime la tabla comparativa in-sample vs out-of-sample y emite el veredicto.

    Veredicto:
      VALIDO    — Expectancy OOS > 0
      OVERFITTING — Expectancy OOS <= 0
    """
    pattern_label = PATTERN_LABELS.get(pattern_key, pattern_key)
    symbol_code = SYMBOLS.get(symbol_cli, symbol_cli)
    params_str = "  ".join(f"{k}={v}" for k, v in pattern_params.items())

    console.print()
    console.print(
        f"[bold cyan]Validacion:[/] {pattern_label}  "
        f"[bold cyan]Simbolo:[/] {symbol_cli.upper()} ({symbol_code})  "
        f"[bold cyan]TF:[/] {tf_cli}"
        + (f"  [bold cyan]Params:[/] {params_str}" if params_str else "")
    )
    console.print()

    table = Table(box=box.ROUNDED, show_header=True, header_style="bold magenta")
    table.add_column("Metrica",            style="cyan", min_width=22)
    table.add_column("In-Sample",          justify="right", style="white")
    table.add_column("Out-of-Sample",      justify="right", style="white")

    def _exp_cell(val: float) -> str:
        color = "green" if val > 0 else "red"
        return f"[{color}]{val:+.3f}[/{color}]"

    table.add_row("Velas analizadas",   str(is_candles),                      str(oos_candles))
    table.add_row("Senales",            str(is_metrics["total_signals"]),      str(oos_metrics["total_signals"]))
    table.add_row("WR TP1",             f"{is_metrics['win_rate_tp1']:.1f}%",  f"{oos_metrics['win_rate_tp1']:.1f}%")
    table.add_row("WR TP2",             f"{is_metrics['win_rate_tp2']:.1f}%",  f"{oos_metrics['win_rate_tp2']:.1f}%")
    table.add_row("Avg R:R",            f"{is_metrics['avg_rr']:.3f}",         f"{oos_metrics['avg_rr']:.3f}")
    table.add_row("Expectancy",         _exp_cell(is_metrics["expectancy"]),   _exp_cell(oos_metrics["expectancy"]))
    table.add_row("Max Consec Losses",  str(is_metrics["max_consecutive_losses"]), str(oos_metrics["max_consecutive_losses"]))

    console.print(table)
    console.print()

    oos_exp = oos_metrics["expectancy"]
    if oos_exp > 0:
        console.print(
            f"[bold green]Veredicto: VALIDO[/] -- "
            f"Expectancy OOS = [green]{oos_exp:+.3f}[/] (positiva, el sistema generaliza)"
        )
    else:
        console.print(
            f"[bold red]Veredicto: OVERFITTING[/] -- "
            f"Expectancy OOS = [red]{oos_exp:+.3f}[/] (negativa, repensar parametros)"
        )
    console.print()


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

    plot_kwargs = dict(type="candle", style=style, title=title, volume=False)
    if apds:
        plot_kwargs["addplot"] = apds

    mpf.plot(df_plot, **plot_kwargs)
