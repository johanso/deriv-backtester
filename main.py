# CLI principal del backtester de Deriv
# Uso: python main.py backtest --symbol v75 --tf 5m

import sys
from pathlib import Path
from typing import Optional

import typer
from rich.console import Console

# Agregar el directorio raíz al path para importaciones relativas
sys.path.insert(0, str(Path(__file__).parent))

from config import SYMBOLS, TIMEFRAMES, DEFAULT_CANDLE_COUNT, PATTERN_LABELS
from api.deriv import fetch_ohlc
from patterns import PATTERN_REGISTRY
from backtest.engine import run_backtest
from report.output import print_results, export_csv, print_chart

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


if __name__ == "__main__":
    app()
