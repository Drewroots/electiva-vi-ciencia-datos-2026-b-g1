"""Semana 15 · Storytelling del proyecto: gráfico clave y dashboard con títulos revisados.

Reutiliza el trabajo previo sin duplicarlo:
  - Semana 11 (serie_tiempo_spotify): serie de interés, media móvil 2x12 e índice estacional.
  - Semana 13 (dashboard_spotify): KPI y tablero; aquí se genera la versión 2 con un título
    principal que dice la conclusión.

Uso:  python storytelling_spotify.py
"""
import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

AQUI = Path(__file__).resolve().parent
RAIZ = AQUI.parents[1]
sys.path.insert(0, str(RAIZ / "11-week" / "02-optional-activity"))
sys.path.insert(0, str(RAIZ / "13-week" / "02-optional-activity"))
import serie_tiempo_spotify as S11   # noqa: E402
import dashboard_spotify as D13      # noqa: E402

IMG = AQUI / "img"
MESES = ["ene", "feb", "mar", "abr", "may", "jun", "jul", "ago", "sep", "oct", "nov", "dic"]
AZUL, NARANJA = "#2a78d6", "#eb6834"
TINTA, TINTA2, REJILLA, FONDO = "#0b0b0b", "#52514e", "#e7e6e2", "#fcfcfb"
TITULO_V2 = ("La demanda cae un 19,5 % pero diciembre sigue siendo el pico: "
             "la capacidad debe planearse por temporada")


def es(n, dec=1):
    return f"{n:,.{dec}f}".replace(",", " ").replace(".", ",")


def efecto_estacional():
    """Efecto típico de cada mes sobre la tendencia, en % (mismo cálculo que la Semana 11)."""
    diaria = S11.extraer(usar_cache=True)
    m = S11.mensual(diaria)
    tendencia = S11.media_movil_centrada(m["visitas_dia_prom"])
    indice = S11.indice_estacional(m["visitas_dia_prom"], tendencia)
    return [round((indice[k] - 1) * 100, 1) for k in range(1, 13)]


def grafico_clave(efecto):
    """Efecto de cada mes con las dos acciones de la recomendación marcadas sobre el calendario."""
    plt.rcParams.update({"font.family": ["Segoe UI", "DejaVu Sans"], "font.size": 10.5,
                         "figure.facecolor": FONDO, "axes.facecolor": FONDO})
    fig, ax = plt.subplots(figsize=(11.5, 5.2))
    x = range(12)
    ax.axvspan(9.5, 11.5, color=AZUL, alpha=0.07, lw=0)       # nov–dic: refuerzo de capacidad
    ax.axvspan(4.5, 7.5, color=NARANJA, alpha=0.08, lw=0)      # jun–ago: ventana de mantenimiento
    ax.bar(x, efecto, width=0.62, color=[AZUL if v >= 0 else NARANJA for v in efecto],
           edgecolor=FONDO, linewidth=2)
    ax.axhline(0, color=TINTA2, lw=1)
    ax.set_xticks(list(x), MESES)
    for i in (11, 5):
        v = efecto[i]
        ax.text(i, v + (0.7 if v > 0 else -0.7), f"{'+' if v > 0 else ''}{es(v)} %", ha="center",
                va="bottom" if v > 0 else "top", fontsize=11, fontweight="bold", color=TINTA)
    ax.text(10.5, 15.2, "Reforzar capacidad\n27 nov – 7 dic: +11 %", ha="center", va="top",
            fontsize=10.5, color=TINTA, fontweight="bold")
    ax.text(6.0, 15.2, "Ventana de mantenimiento\njunio – agosto", ha="center", va="top",
            fontsize=10.5, color=TINTA, fontweight="bold")
    ax.set_ylim(-17, 16)
    ax.set_ylabel("% sobre / bajo la tendencia", color=TINTA2)
    for s in ("top", "right", "left", "bottom"):
        ax.spines[s].set_visible(False)
    ax.tick_params(length=0, colors=TINTA2)
    ax.yaxis.grid(True, color=REJILLA)
    ax.set_axisbelow(True)
    fig.suptitle("Diciembre exige un 11 % más de capacidad y junio–agosto libera margen para mantenimiento",
                 x=0.01, ha="left", fontsize=13.5, fontweight="bold", color=TINTA)
    ax.set_title("Efecto típico de cada mes sobre la tendencia del interés en Spotify (mediana 2016–2026) · "
                 "azul: meses sobre la tendencia · naranja: bajo la tendencia",
                 loc="left", fontsize=10, color=TINTA2, pad=8)
    fig.tight_layout()
    IMG.mkdir(exist_ok=True)
    fig.savefig(IMG / "grafico-clave-estacionalidad.png", dpi=140, bbox_inches="tight")
    plt.close(fig)


def dashboard_v2():
    """Tablero de la Semana 13 con el título principal reescrito como conclusión."""
    mensual = D13.interes_mensual()
    k1, k2, k3 = D13.kpi_interes(mensual), D13.kpi_skip(), D13.kpi_premium()
    D13.dibujar(k1, k2, k3, mensual, D13.skip_por_artista(), D13.premium_por_region(),
                titulo=TITULO_V2, salida=IMG / "dashboard-v2.png")
    return k1, k2, k3


if __name__ == "__main__":
    efecto = efecto_estacional()
    grafico_clave(efecto)
    k = dashboard_v2()
    print("Efecto por mes (%):", dict(zip(MESES, efecto)))
    print(f"KPI: interés {k[0]:.1f} % · skip {k[1]:.2f} % · Premium {k[2]:.2f} %")
    print("Imágenes en", IMG)
