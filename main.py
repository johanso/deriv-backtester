# CLI principal del backtester de Deriv
# Uso: python main.py backtest --symbol v75 --tf 5m

import sys
from pathlib import Path
from typing import Optional

import typer
from rich.console import Console

# Agregar el directorio raíz al path para importaciones relativas
sys.path.insert(0, str(Path(__file__).parent))

from config import SYMBOLS, TIMEFRAMES, DEFAULT_CANDLE_COUNT, PATTERN_LABELS, OPTIMIZE_PARAMS
from api.deriv import fetch_ohlc
from patterns import PATTERN_REGISTRY
from backtest.engine import run_backtest
from report.output import (
    print_results, export_csv, print_chart,
    print_optimize_table, print_validate_table,
    print_simulate_summary, plot_balance_curve,
)
from backtest.simulator import simulate_account

app = typer.Typer(
    name="deriv-backtester",
    help="Backtester de patrones para índices sintéticos de Deriv.",
    add_completion=False,
)
console = Console()


def _validate_symbol(symbol: str) -> str:
    if symbol not in SYMBOLS:
        console.print(f"[red]Símbolo inválido:[/] {symbol}. Opciones: {list(SYMBOLS.keys())}")
        raise typer.Exit(1)
    return symbol


def _validate_tf(tf: str) -> int:
    if tf not in TIMEFRAMES:
        console.print(f"[red]Temporalidad inválida:[/] {tf}. Opciones: {list(TIMEFRAMES.keys())}")
        raise typer.Exit(1)
    return TIMEFRAMES[tf]


def _validate_pattern(pattern: Optional[str]) -> Optional[str]:
    if pattern and pattern not in PATTERN_REGISTRY:
        console.print(f"[red]Patrón inválido:[/] {pattern}. Opciones: {list(PATTERN_REGISTRY.keys())}")
        raise typer.Exit(1)
    return pattern


@app.command()
def backtest(
    symbol: str = typer.Option("v75", "--symbol", "-s", help="Símbolo a analizar"),
    tf: str = typer.Option("5m", "--tf", "-t", help="Temporalidad (1m/5m/15m/1h/4h)"),
    pattern: Optional[str] = typer.Option(None, "--pattern", "-p", help="Patrón específico (opcional)"),
    count: int = typer.Option(DEFAULT_CANDLE_COUNT, "--count", "-c", help="Número de velas"),
    export: Optional[str] = typer.Option(None, "--export", "-e", help="Exportar resultados a CSV"),
) -> None:
    """Descarga datos y ejecuta el backtesting de patrones."""

    _validate_symbol(symbol)
    granularity = _validate_tf(tf)
    _validate_pattern(pattern)

    console.print(f"[bold]Descargando {count} velas[/] de {symbol.upper()} ({tf})...")

    try:
        df = fetch_ohlc(SYMBOLS[symbol], granularity, count)
    except ConnectionError as e:
        console.print(f"[red]Error de conexión:[/] {e}")
        raise typer.Exit(1)

    console.print(f"[green]Descargadas {len(df)} velas.[/] Ejecutando backtesting...")

    # Determinar qué patrones ejecutar
    patterns_to_run = {pattern: PATTERN_REGISTRY[pattern]} if pattern else PATTERN_REGISTRY

    results = {}
    for pat_key, detect_fn in patterns_to_run.items():
        label = PATTERN_LABELS.get(pat_key, pat_key)
        console.print(f"  Detectando patrón: [cyan]{label}[/]...")
        signals = detect_fn(df)
        results[pat_key] = run_backtest(df, signals)

    print_results(results, symbol, tf, len(df))

    if export:
        export_csv(results, symbol, tf, export)


@app.command()
def chart(
    symbol: str = typer.Option("v75", "--symbol", "-s", help="Símbolo a graficar"),
    tf: str = typer.Option("5m", "--tf", "-t", help="Temporalidad"),
    pattern: str = typer.Option("consolidation", "--pattern", "-p", help="Patrón a visualizar"),
    last: int = typer.Option(200, "--last", "-l", help="Número de velas a mostrar"),
    count: int = typer.Option(DEFAULT_CANDLE_COUNT, "--count", "-c", help="Velas a descargar"),
) -> None:
    """Muestra un gráfico de velas con las señales del patrón marcadas."""

    _validate_symbol(symbol)
    granularity = _validate_tf(tf)
    _validate_pattern(pattern)

    console.print(f"[bold]Descargando datos[/] para el gráfico...")

    try:
        df = fetch_ohlc(SYMBOLS[symbol], granularity, count)
    except ConnectionError as e:
        console.print(f"[red]Error de conexión:[/] {e}")
        raise typer.Exit(1)

    detect_fn = PATTERN_REGISTRY[pattern]
    signals = detect_fn(df)
    console.print(f"[green]{len(signals)} señales detectadas.[/] Mostrando gráfico...")

    print_chart(df, signals, pattern, symbol, tf, last)


@app.command()
def compare(
    pattern: str = typer.Option("bounce", "--pattern", "-p", help="Patrón a comparar"),
    tf: str = typer.Option("5m", "--tf", "-t", help="Temporalidad"),
    count: int = typer.Option(DEFAULT_CANDLE_COUNT, "--count", "-c", help="Velas por símbolo"),
    export: Optional[str] = typer.Option(None, "--export", "-e", help="Exportar a CSV"),
) -> None:
    """Compara un patrón en todos los símbolos disponibles."""

    _validate_tf(tf)
    _validate_pattern(pattern)
    granularity = TIMEFRAMES[tf]
    detect_fn = PATTERN_REGISTRY[pattern]

    all_results: dict[str, dict] = {}

    for sym_cli, sym_code in SYMBOLS.items():
        console.print(f"  Procesando [cyan]{sym_cli}[/] ({sym_code})...")
        try:
            df = fetch_ohlc(sym_code, granularity, count)
            signals = detect_fn(df)
            metrics = run_backtest(df, signals)
        except Exception as e:
            console.print(f"  [yellow]Omitiendo {sym_cli}:[/] {e}")
            continue

        all_results[sym_cli] = metrics

    # Reusar print_results usando el nombre del patrón como "símbolo"
    console.print()
    console.print(f"[bold]Comparativa — Patrón:[/] {PATTERN_LABELS.get(pattern, pattern)}  [bold]TF:[/] {tf}")

    from rich.table import Table
    from rich import box

    table = Table(box=box.ROUNDED, header_style="bold magenta")
    table.add_column("Símbolo",   style="cyan")
    table.add_column("Señales",   justify="right")
    table.add_column("WR TP1",    justify="right", style="green")
    table.add_column("WR TP2",    justify="right", style="green")
    table.add_column("Avg R:R",   justify="right", style="yellow")
    table.add_column("Expectancy", justify="right", style="yellow")

    for sym, m in all_results.items():
        exp = m["expectancy"]
        exp_color = "green" if exp > 0 else "red"
        table.add_row(
            sym,
            str(m["total_signals"]),
            f"{m['win_rate_tp1']:.1f}%",
            f"{m['win_rate_tp2']:.1f}%",
            f"{m['avg_rr']:.2f}",
            f"[{exp_color}]{exp:.3f}[/{exp_color}]",
        )

    console.print(table)
    console.print()

    if export:
        export_csv(all_results, "all", tf, export)


@app.command()
def optimize(
    symbol: str = typer.Option("v75",   "--symbol",  "-s", help="Símbolo a analizar"),
    tf: str     = typer.Option("5m",    "--tf",      "-t", help="Temporalidad (1m/5m/15m/1h/4h)"),
    pattern: str = typer.Option("ncandle", "--pattern", "-p", help="Patrón a optimizar"),
    count: int  = typer.Option(DEFAULT_CANDLE_COUNT, "--count", "-c", help="Número de velas"),
    param_min:  int = typer.Option(None, "--min",  help="Valor mínimo del parámetro"),
    param_max:  int = typer.Option(None, "--max",  help="Valor máximo del parámetro"),
    param_step: int = typer.Option(None, "--step", help="Paso entre valores"),
    export: Optional[str] = typer.Option(None, "--export", "-e", help="Exportar resultados a CSV"),
) -> None:
    """Barre un rango de parámetros de un patrón y muestra cuál maximiza Expectancy."""

    _validate_symbol(symbol)
    granularity = _validate_tf(tf)
    _validate_pattern(pattern)

    if pattern not in OPTIMIZE_PARAMS:
        supported = list(OPTIMIZE_PARAMS.keys())
        console.print(f"[red]Optimización no soportada para '{pattern}'.[/] Patrones válidos: {supported}")
        raise typer.Exit(1)

    opt = OPTIMIZE_PARAMS[pattern]
    p_min  = param_min  if param_min  is not None else opt["default_min"]
    p_max  = param_max  if param_max  is not None else opt["default_max"]
    p_step = param_step if param_step is not None else opt["default_step"]

    console.print(f"[bold]Descargando {count} velas[/] de {symbol.upper()} ({tf})...")
    try:
        df = fetch_ohlc(SYMBOLS[symbol], granularity, count)
    except ConnectionError as e:
        console.print(f"[red]Error de conexión:[/] {e}")
        raise typer.Exit(1)

    console.print(
        f"[green]Descargadas {len(df)} velas.[/] "
        f"Barriendo {opt['label']} de {p_min} a {p_max} (paso {p_step})..."
    )

    detect_fn = PATTERN_REGISTRY[pattern]
    param_name = opt["param_name"]
    param_values = list(range(p_min, p_max + 1, p_step))

    rows = []
    for val in param_values:
        signals = detect_fn(df, **{param_name: val})
        metrics = run_backtest(df, signals)
        rows.append({"param_value": val, "metrics": metrics})
        console.print(
            f"  {opt['label']}={val:>3}  "
            f"señales={metrics['total_signals']:>4}  "
            f"WR={metrics['win_rate_tp1']:>5.1f}%  "
            f"exp={metrics['expectancy']:>+.3f}"
        )

    print_optimize_table(rows, symbol, tf, pattern, len(df))

    if export:
        _export_optimize_csv(rows, symbol, tf, pattern, opt["param_name"], export)


def _export_optimize_csv(
    rows: list[dict],
    symbol_cli: str,
    tf_cli: str,
    pattern_key: str,
    param_name: str,
    filepath: str,
) -> None:
    """Exporta los resultados de optimización a CSV."""
    import csv
    from pathlib import Path

    path = Path(filepath)
    fieldnames = [
        param_name, "symbol", "timeframe",
        "total_signals", "win_rate_tp1", "win_rate_tp2",
        "avg_rr", "expectancy", "max_consecutive_losses",
    ]

    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            m = row["metrics"]
            writer.writerow({
                param_name:              row["param_value"],
                "symbol":                symbol_cli,
                "timeframe":             tf_cli,
                "total_signals":         m["total_signals"],
                "win_rate_tp1":          m["win_rate_tp1"],
                "win_rate_tp2":          m["win_rate_tp2"],
                "avg_rr":                m["avg_rr"],
                "expectancy":            m["expectancy"],
                "max_consecutive_losses": m["max_consecutive_losses"],
            })

    console.print(f"[green]Optimización exportada a:[/] {path.resolve()}")


@app.command()
def simulate(
    symbol: str   = typer.Option("v75",     "--symbol",    "-s", help="Símbolo a analizar"),
    tf: str       = typer.Option("1m",      "--tf",        "-t", help="Temporalidad (1m/5m/15m/1h/4h)"),
    pattern: str  = typer.Option("ncandle", "--pattern",   "-p", help="Patrón a simular"),
    count: int    = typer.Option(6000,      "--count",     "-c", help="Número de velas"),
    balance: float = typer.Option(1000.0,  "--balance",   "-b", help="Balance inicial en $"),
    risk_pct: float = typer.Option(1.0,    "--risk-pct",  "-r", help="Riesgo por trade en % del balance"),
    n_candles: Optional[int] = typer.Option(None, "--n-candles", help="n_candles para el patrón ncandle"),
    csv_out: str  = typer.Option("balance_curve.csv", "--csv", help="Ruta del CSV de salida"),
    no_chart: bool = typer.Option(False,   "--no-chart",  help="Omitir el gráfico matplotlib"),
) -> None:
    """Simula el crecimiento de cuenta trade a trade con riesgo porcentual fijo."""

    _validate_symbol(symbol)
    granularity = _validate_tf(tf)
    _validate_pattern(pattern)

    if risk_pct <= 0 or risk_pct > 100:
        console.print("[red]--risk-pct debe estar entre 0 y 100.[/]")
        raise typer.Exit(1)
    if balance <= 0:
        console.print("[red]--balance debe ser positivo.[/]")
        raise typer.Exit(1)

    console.print(f"[bold]Descargando {count} velas[/] de {symbol.upper()} ({tf})...")
    try:
        df = fetch_ohlc(SYMBOLS[symbol], granularity, count)
    except ConnectionError as e:
        console.print(f"[red]Error de conexión:[/] {e}")
        raise typer.Exit(1)

    pattern_params: dict = {}
    if pattern == "ncandle" and n_candles is not None:
        pattern_params["n_candles"] = n_candles

    console.print(f"[green]Descargadas {len(df)} velas.[/] Detectando señales...")
    signals = PATTERN_REGISTRY[pattern](df, **pattern_params)
    console.print(f"  {len(signals)} señales detectadas. Simulando cuenta...")

    trades, summary = simulate_account(df, signals, balance, risk_pct)

    print_simulate_summary(summary, symbol, tf, pattern, pattern_params)

    # Exportar CSV
    _write_balance_csv(trades, csv_out)
    console.print(f"[green]Curva de balance guardada en:[/] {csv_out}")

    if not no_chart and trades:
        plot_balance_curve(trades, symbol, tf)


def _write_balance_csv(trades: list[dict], filepath: str) -> None:
    """Escribe la evolución del balance trade por trade a CSV."""
    import csv
    from pathlib import Path

    fieldnames = [
        "trade_num", "signal_index", "direction", "outcome",
        "risk_amount", "pnl", "balance", "peak_balance",
        "drawdown_abs", "drawdown_pct",
    ]
    with open(Path(filepath), "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(trades)


@app.command()
def validate(
    symbol: str  = typer.Option("v75",     "--symbol",    "-s", help="Símbolo a analizar"),
    tf: str      = typer.Option("1m",      "--tf",        "-t", help="Temporalidad (1m/5m/15m/1h/4h)"),
    pattern: str = typer.Option("ncandle", "--pattern",   "-p", help="Patrón a validar"),
    count: int   = typer.Option(6000,      "--count",     "-c", help="Total de velas (se divide en 2)"),
    n_candles: Optional[int] = typer.Option(None, "--n-candles", help="Parámetro n_candles para ncandle"),
    export: Optional[str]    = typer.Option(None, "--export", "-e", help="Exportar métricas a CSV"),
) -> None:
    """Divide los datos en in-sample / out-of-sample y compara métricas de ambas mitades."""

    _validate_symbol(symbol)
    granularity = _validate_tf(tf)
    _validate_pattern(pattern)

    console.print(f"[bold]Descargando {count} velas[/] de {symbol.upper()} ({tf})...")
    try:
        df = fetch_ohlc(SYMBOLS[symbol], granularity, count)
    except ConnectionError as e:
        console.print(f"[red]Error de conexión:[/] {e}")
        raise typer.Exit(1)

    total = len(df)
    if total < 2:
        console.print("[red]No hay suficientes velas para dividir.[/]")
        raise typer.Exit(1)

    split = total // 2
    df_is  = df.iloc[:split].reset_index(drop=True)
    df_oos = df.iloc[split:].reset_index(drop=True)

    console.print(
        f"[green]Descargadas {total} velas.[/]  "
        f"In-sample: 0-{split - 1} ({split} velas)  "
        f"Out-of-sample: {split}-{total - 1} ({total - split} velas)"
    )

    # Construir kwargs específicos del patrón
    pattern_params: dict = {}
    if pattern == "ncandle" and n_candles is not None:
        pattern_params["n_candles"] = n_candles

    detect_fn = PATTERN_REGISTRY[pattern]

    console.print("  Ejecutando in-sample...")
    is_signals  = detect_fn(df_is,  **pattern_params)
    is_metrics  = run_backtest(df_is,  is_signals)

    console.print("  Ejecutando out-of-sample...")
    oos_signals = detect_fn(df_oos, **pattern_params)
    oos_metrics = run_backtest(df_oos, oos_signals)

    print_validate_table(
        is_metrics, oos_metrics,
        split, total - split,
        symbol, tf, pattern, pattern_params,
    )

    if export:
        _export_validate_csv(is_metrics, oos_metrics, symbol, tf, pattern, pattern_params, export)


def _export_validate_csv(
    is_metrics: dict,
    oos_metrics: dict,
    symbol_cli: str,
    tf_cli: str,
    pattern_key: str,
    pattern_params: dict,
    filepath: str,
) -> None:
    """Exporta la comparativa IS/OOS a CSV."""
    import csv
    from pathlib import Path

    path = Path(filepath)
    fieldnames = [
        "split", "symbol", "timeframe", "pattern",
        *pattern_params.keys(),
        "total_signals", "win_rate_tp1", "win_rate_tp2",
        "avg_rr", "expectancy", "max_consecutive_losses",
    ]

    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for label, m in (("in-sample", is_metrics), ("out-of-sample", oos_metrics)):
            writer.writerow({
                "split":    label,
                "symbol":   symbol_cli,
                "timeframe": tf_cli,
                "pattern":  pattern_key,
                **pattern_params,
                "total_signals":          m["total_signals"],
                "win_rate_tp1":           m["win_rate_tp1"],
                "win_rate_tp2":           m["win_rate_tp2"],
                "avg_rr":                 m["avg_rr"],
                "expectancy":             m["expectancy"],
                "max_consecutive_losses": m["max_consecutive_losses"],
            })

    console.print(f"[green]Validación exportada a:[/] {path.resolve()}")


if __name__ == "__main__":
    app()
