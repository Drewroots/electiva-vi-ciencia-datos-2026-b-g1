"""Semana 13 · Prototipo del dashboard de operación del caso Spotify.

Calcula los 3 KPI con datos reales del curso y dibuja el tablero con la jerarquía del boceto:
  fila 1 · filtros   fila 2 · 3 tarjetas KPI   fila 3 · tendencia (KPI 1)   fila 4 · KPI 2 y KPI 3.

Fuentes (reutilizadas, sin copiar datos):
  - datos/spotify.db de la Semana 10 (métricas de Kaggle, ya limpias y en el modelo de la Semana 6)
  - datos/pageviews_spotify_diario.csv de la Semana 11 (interés diario en Wikipedia)
Solo usa la biblioteca estándar y Matplotlib.

Uso:  python dashboard_spotify.py
"""
import csv
import sqlite3
from collections import defaultdict
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch

AQUI = Path(__file__).resolve().parent
RAIZ = AQUI.parents[1]
BASE = RAIZ / "10-week" / "02-optional-activity" / "datos" / "spotify.db"
SERIE = RAIZ / "11-week" / "02-optional-activity" / "datos" / "pageviews_spotify_diario.csv"
SALIDA = AQUI / "img" / "prototipo-dashboard.png"

# Metas SMART propuestas (línea base de los datos; horizonte: primer trimestre de 2027)
META_INTERES = 0.0      # KPI 1: variación interanual del interés >= 0 %
META_SKIP = 20.0        # KPI 2: skip rate promedio <= 20 %
META_PREMIUM = 53.0     # KPI 3: participación Premium en streams >= 53 % (+2 puntos)

# Paleta: un color de datos, gris de contexto y colores de estado reservados (siempre con ícono y texto)
AZUL, NARANJA, GRIS = "#2a78d6", "#eb6834", "#8a8984"
BUENO, ALERTA, CRITICO = "#0ca30c", "#fab219", "#d03b3b"
TINTA, TINTA2, REJILLA, FONDO, TARJETA = "#0b0b0b", "#52514e", "#e7e6e2", "#f6f5f2", "#ffffff"
MESES = ["ene", "feb", "mar", "abr", "may", "jun", "jul", "ago", "sep", "oct", "nov", "dic"]


def es(n, dec=1):
    return f"{n:,.{dec}f}".replace(",", " ").replace(".", ",")


# ----------------------------------------------------------------------------- KPI
def interes_mensual():
    """Promedio diario de visitas por mes: {"AAAA-MM": valor}."""
    por_mes = defaultdict(list)
    with open(SERIE, encoding="utf-8") as f:
        for fila in csv.DictReader(f):
            por_mes[fila["fecha"][:7]].append(int(fila["visitas"]))
    return {m: sum(v) / len(v) for m, v in sorted(por_mes.items())}


def kpi_interes(mensual, anio=2026, hasta_mes=9):
    """KPI 1: variación del interés en lo corrido del año frente al mismo periodo del año anterior.

    Se compara el mismo tramo de meses para no confundir estacionalidad con tendencia.
    """
    actual = sum(mensual[f"{anio}-{m:02d}"] for m in range(1, hasta_mes + 1))
    previo = sum(mensual[f"{anio - 1}-{m:02d}"] for m in range(1, hasta_mes + 1))
    return 100 * (actual / previo - 1)


def consultar(sql):
    with sqlite3.connect(BASE) as con:
        return con.execute(sql).fetchall()


def kpi_skip():
    """KPI 2: skip rate promedio de todas las observaciones."""
    return consultar("SELECT AVG(skip_rate_pct) FROM metrica_streaming")[0][0]


def kpi_premium():
    """KPI 3: % de los streams de los últimos 30 días que provienen del plan Premium."""
    return consultar("""
        SELECT 100.0 * SUM(CASE WHEN ps.nombre = 'Premium' THEN m.streams_30d_m END) / SUM(m.streams_30d_m)
        FROM metrica_streaming m JOIN plan_suscripcion ps ON ps.plan_id = m.plan_id""")[0][0]


def skip_por_artista():
    return consultar("""
        SELECT ar.nombre, AVG(m.skip_rate_pct)
        FROM metrica_streaming m JOIN album al ON al.album_id = m.album_id
        JOIN artista ar ON ar.artist_id = al.artist_id
        GROUP BY ar.nombre ORDER BY 2 DESC""")


def premium_por_region():
    return consultar("""
        SELECT p.region,
               100.0 * SUM(CASE WHEN ps.nombre = 'Premium' THEN m.streams_30d_m END) / SUM(m.streams_30d_m)
        FROM metrica_streaming m JOIN pais p ON p.country_id = m.country_id
        JOIN plan_suscripcion ps ON ps.plan_id = m.plan_id
        GROUP BY p.region ORDER BY 2""")


def estado(valor, meta, mayor_es_mejor, tolerancia):
    """Semáforo: (color, ícono, texto). Amarillo si está fuera de la meta por menos de `tolerancia`."""
    brecha = (valor - meta) if mayor_es_mejor else (meta - valor)
    if brecha >= 0:
        return BUENO, "✓", "En meta"
    if brecha >= -tolerancia:
        return ALERTA, "!", "Cerca de la meta"
    return CRITICO, "✕", "Fuera de meta"


# ----------------------------------------------------------------------------- dibujo
def caja(fig, x, y, w, h, color=TARJETA, borde=REJILLA):
    fig.patches.append(FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0,rounding_size=0.008",
                                      transform=fig.transFigure, facecolor=color, edgecolor=borde, lw=1,
                                      zorder=-10))          # detrás de los gráficos


def tarjeta(fig, x, y, w, h, numero, titulo, valor, unidad, meta_txt, est, nota):
    caja(fig, x, y, w, h)
    col, icono, txt = est
    fig.text(x + 0.012, y + h - 0.034, f"KPI {numero} · {titulo}", fontsize=11, color=TINTA2, fontweight="bold")
    num = fig.text(x + 0.012, y + h - 0.102, valor, fontsize=34, color=TINTA, fontweight="bold")
    # La unidad se coloca justo después del número, midiendo su ancho real
    ancho = num.get_window_extent(fig.canvas.get_renderer()).width / fig.bbox.width
    fig.text(x + 0.012 + ancho + 0.006, y + h - 0.102, unidad, fontsize=12, color=TINTA2)
    fig.text(x + 0.012, y + 0.042, meta_txt, fontsize=10.5, color=TINTA2)
    fig.patches.append(FancyBboxPatch((x + w - 0.135, y + h - 0.047), 0.123, 0.03,
                                      boxstyle="round,pad=0,rounding_size=0.012", transform=fig.transFigure,
                                      facecolor=col, edgecolor="none", zorder=-5))
    fig.text(x + w - 0.0735, y + h - 0.032, f"{icono}  {txt}", fontsize=9.5, ha="center", va="center",
             color="#ffffff" if col != ALERTA else TINTA, fontweight="bold")
    fig.text(x + 0.012, y + 0.016, nota, fontsize=9.5, color=TINTA2, style="italic")


def ejes_limpios(ax, eje="y"):
    for s in ("top", "right", "left"):
        ax.spines[s].set_visible(False)
    ax.spines["bottom"].set_color(REJILLA)
    ax.tick_params(length=0, colors=TINTA2)
    getattr(ax, f"{eje}axis").grid(True, color=REJILLA, lw=0.8)
    ax.set_axisbelow(True)
    ax.set_facecolor(TARJETA)


def dibujar(k1, k2, k3, mensual, skip_art, prem_reg, titulo=None, salida=SALIDA):
    """Dibuja el tablero. `titulo` y `salida` permiten generar versiones revisadas (Semana 15)."""
    plt.rcParams.update({"font.family": ["Segoe UI", "Segoe UI Symbol", "DejaVu Sans"], "font.size": 10})
    fig = plt.figure(figsize=(16, 11.2), facecolor=FONDO)

    # Encabezado y filtros (fila 1)
    fig.text(0.02, 0.965, titulo or "Tablero de operación · Spotify: demanda, curaduría y monetización",
             fontsize=19, fontweight="bold", color=TINTA)
    fig.text(0.02, 0.940, "Datos: métricas de Kaggle 2024 (498 registros limpios) · interés diario en Wikipedia "
             "ene 2016 – sep 2026 · metas propuestas para el T1 2027", fontsize=10.5, color=TINTA2)
    filtros = ["Fecha: ene 2023 – sep 2026", "Región: Todas", "País: Todos", "Plan: Todos",
               "Género: Todos", "Artista: Todos"]
    x = 0.02
    for f_ in filtros:
        w = 0.0062 * len(f_) + 0.03
        caja(fig, x, 0.885, w, 0.033, color=TARJETA, borde="#c9c8c3")
        fig.text(x + 0.01, 0.9015, f_ + "  ▾", fontsize=10, va="center", color=TINTA)
        x += w + 0.008

    # Tarjetas KPI (fila 2)
    tw, th, ty = 0.307, 0.165, 0.705
    tarjeta(fig, 0.02, ty, tw, th, 1, "Demanda (interés)", f"{es(k1)}", "% interanual",
            f"Meta: ≥ {es(META_INTERES, 0)} % · ene–sep 2026 frente a ene–sep 2025",
            estado(k1, META_INTERES, True, 5), "Próximo pico estacional: diciembre (+10,5 % sobre la tendencia)")
    tarjeta(fig, 0.02 + tw + 0.0165, ty, tw, th, 2, "Curaduría (abandono)", f"{es(k2)}", "% skip rate",
            f"Meta: ≤ {es(META_SKIP, 0)} % · promedio de los 498 registros",
            estado(k2, META_SKIP, False, 2), "Menos abandono = mejor recomendación de contenido")
    tarjeta(fig, 0.02 + 2 * (tw + 0.0165), ty, tw, th, 3, "Monetización (Premium)", f"{es(k3)}", "% de streams",
            f"Meta: ≥ {es(META_PREMIUM, 0)} % · streams de los últimos 30 días",
            estado(k3, META_PREMIUM, True, 3), "Participación del plan Premium en la demanda")

    # Tendencia del interés (fila 3, KPI 1)
    caja(fig, 0.02, 0.405, 0.955, 0.282)
    ax = fig.add_axes([0.06, 0.435, 0.9, 0.18])
    meses = [m for m in mensual if m >= "2023-01"]
    valores = [mensual[m] / 1000 for m in meses]
    ax.plot(range(len(meses)), valores, color=AZUL, lw=2)
    previo = [mensual.get(f"{int(m[:4]) - 1}{m[4:]}", None) for m in meses]
    ax.plot(range(len(meses)), [p / 1000 for p in previo], color=GRIS, lw=1.4, ls=(0, (4, 3)))
    ax.text(len(meses) - 0.6, valores[-1], "2026", color=TINTA, fontsize=9.5, va="center")
    ax.text(len(meses) - 0.6, previo[-1] / 1000, "año anterior", color=TINTA2, fontsize=9.5, va="center")
    ticks = [i for i, m in enumerate(meses) if m.endswith(("-01", "-07"))]
    ax.set_xticks(ticks, [f"{MESES[int(meses[i][5:]) - 1]} {meses[i][:4]}" for i in ticks])
    ax.set_xlim(-0.5, len(meses) + 3.5)
    ax.set_ylabel("Miles de visitas por día", color=TINTA2)
    ejes_limpios(ax)
    fig.text(0.035, 0.66, f"El interés cae desde 2022: {es(k1)} % frente a 2025, aunque diciembre sigue siendo "
             "el pico del año", fontsize=12.5, fontweight="bold", color=TINTA)
    fig.text(0.035, 0.64, "KPI 1 · promedio diario de visitas por mes (azul) frente al mismo mes del año anterior (gris)",
             fontsize=10, color=TINTA2)

    # KPI 2: skip rate por artista (fila 4, izquierda)
    caja(fig, 0.02, 0.025, 0.47, 0.36)
    ax2 = fig.add_axes([0.13, 0.085, 0.34, 0.23])
    nombres = [a for a, _ in skip_art][::-1]
    vals = [v for _, v in skip_art][::-1]
    ax2.barh(nombres, vals, height=0.62, color=[AZUL if v > META_SKIP else GRIS for v in vals],
             edgecolor=TARJETA, linewidth=1.5)
    ax2.axvline(META_SKIP, color=TINTA, lw=1.1, ls=(0, (4, 3)))
    ax2.text(META_SKIP + 0.3, len(nombres) - 0.4, "meta 20 %", fontsize=9, color=TINTA)
    ax2.set_xlim(0, 25)
    ax2.set_xlabel("Skip rate promedio (%)", color=TINTA2)
    ejes_limpios(ax2, "x")
    sobre = sum(v > META_SKIP for v in vals)
    fig.text(0.035, 0.355, f"{sobre} de {len(vals)} artistas superan la meta de abandono del 20 %",
             fontsize=12.5, fontweight="bold", color=TINTA)
    fig.text(0.035, 0.335, "KPI 2 · en azul, los artistas por encima de la meta", fontsize=10, color=TINTA2)

    # KPI 3: Premium por región (fila 4, derecha)
    caja(fig, 0.505, 0.025, 0.47, 0.36)
    ax3 = fig.add_axes([0.62, 0.085, 0.33, 0.23])
    regiones = [r for r, _ in prem_reg]
    pv = [v for _, v in prem_reg]
    ax3.barh(regiones, pv, height=0.58, color=[AZUL if v < META_PREMIUM else GRIS for v in pv],
             edgecolor=TARJETA, linewidth=1.5)
    ax3.axvline(META_PREMIUM, color=TINTA, lw=1.1, ls=(0, (4, 3)))
    ax3.text(META_PREMIUM + 0.8, len(regiones) - 0.45, "meta 53 %", fontsize=9, color=TINTA)
    for i, v in enumerate(pv):
        ax3.text(v + 0.8, i, f"{es(v, 1)} %", va="center", fontsize=9.5, color=TINTA)
    ax3.set_xlim(0, 80)
    ax3.set_xlabel("Participación Premium en los streams de 30 días (%)", color=TINTA2)
    ejes_limpios(ax3, "x")
    fig.text(0.52, 0.355, f"Asia frena la monetización: {es(pv[0], 1)} % Premium frente a la meta de 53 %",
             fontsize=12.5, fontweight="bold", color=TINTA)
    fig.text(0.52, 0.335, "KPI 3 · en azul, las regiones por debajo de la meta", fontsize=10, color=TINTA2)

    salida.parent.mkdir(exist_ok=True)
    fig.savefig(salida, dpi=130, facecolor=FONDO)
    plt.close(fig)


if __name__ == "__main__":
    mensual = interes_mensual()
    k1, k2, k3 = kpi_interes(mensual), kpi_skip(), kpi_premium()
    dibujar(k1, k2, k3, mensual, skip_por_artista(), premium_por_region())
    print(f"KPI 1 · interés ene–sep 2026 vs 2025: {k1:.1f} %  (meta >= {META_INTERES:.0f} %)")
    print(f"KPI 2 · skip rate promedio:          {k2:.2f} % (meta <= {META_SKIP:.0f} %)")
    print(f"KPI 3 · participación Premium:        {k3:.2f} % (meta >= {META_PREMIUM:.0f} %)")
    print("Prototipo:", SALIDA)
