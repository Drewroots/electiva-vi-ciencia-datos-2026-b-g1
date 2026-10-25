"""Semana 12 · Rediseño de gráficos con datos del caso Spotify.

Genera dos pares ANTES/DESPUÉS a partir de la base limpia del mini-proyecto (Semana 10):
  A. Participación de cada país en la demanda de los últimos 30 días.
     Antes: torta 3D con 20 porciones, colores arcoíris y sin título.
     Después: barras horizontales ordenadas, desde 0, con referencia de reparto uniforme.
  B. Abandono promedio (skip rate) por región.
     Antes: barras 3D con el eje truncado en 17 %, arcoíris y sin unidades.
     Después: barras desde 0 %, ordenadas, con el valor y el tamaño de muestra.

Los gráficos "antes" se construyen mal a propósito, para diagnosticarlos.
Solo usa la biblioteca estándar (sqlite3) y Matplotlib.

Uso:  python rediseno_graficos.py
"""
import sqlite3
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import cm
from mpl_toolkits.mplot3d import Axes3D  # noqa: F401  (registra la proyección 3D)

AQUI = Path(__file__).resolve().parent
BASE = AQUI.parents[1] / "10-week" / "02-optional-activity" / "datos" / "spotify.db"
IMG = AQUI / "img"
DPI = 150

# Paleta del rediseño: un color de énfasis, un gris neutro y tintas para el texto
AZUL, GRIS = "#2a78d6", "#8a8984"
TINTA, TINTA2, REJILLA, FONDO = "#0b0b0b", "#52514e", "#e7e6e2", "#fcfcfb"


# ----------------------------------------------------------------------------- datos
def consultar(sql, params=()):
    with sqlite3.connect(BASE) as con:
        return con.execute(sql, params).fetchall()


def participacion_por_pais():
    """[(pais, region, streams_30d_m, participacion_pct)] ordenado de mayor a menor."""
    total = consultar("SELECT SUM(streams_30d_m) FROM metrica_streaming")[0][0]
    filas = consultar("""
        SELECT p.nombre, p.region, SUM(m.streams_30d_m)
        FROM metrica_streaming m JOIN pais p ON p.country_id = m.country_id
        GROUP BY p.nombre, p.region ORDER BY 3 DESC""")
    return [(n, r, s, 100 * s / total) for n, r, s in filas], total


def skip_por_region():
    """[(region, skip_rate_prom_pct, registros)] ordenado de mayor a menor."""
    return consultar("""
        SELECT p.region, AVG(m.skip_rate_pct), COUNT(*)
        FROM metrica_streaming m JOIN pais p ON p.country_id = m.country_id
        GROUP BY p.region ORDER BY 2 DESC""")


def factor_de_mentira(valor_a, valor_b, base_eje):
    """Factor de mentira de Tufte: tamaño del efecto en el gráfico / tamaño del efecto en los datos.

    El efecto se mide como el cambio relativo entre dos valores. Con un eje truncado, la barra
    solo dibuja la parte por encima de `base_eje`, así que el efecto visual se exagera.
    """
    efecto_datos = (valor_a - valor_b) / valor_b
    efecto_grafico = ((valor_a - base_eje) - (valor_b - base_eje)) / (valor_b - base_eje)
    return efecto_grafico / efecto_datos, efecto_grafico, efecto_datos


# ----------------------------------------------------------------------------- estilo
def estilo_limpio():
    plt.rcdefaults()
    plt.rcParams.update({"font.family": "Segoe UI", "font.size": 10.5, "axes.edgecolor": REJILLA,
                         "axes.labelcolor": TINTA2, "xtick.color": TINTA2, "ytick.color": TINTA,
                         "figure.facecolor": FONDO, "axes.facecolor": FONDO})


def ejes_minimos(ax, eje_valor="x"):
    for s in ("top", "right", "left", "bottom"):
        ax.spines[s].set_visible(False)
    ax.tick_params(length=0)
    getattr(ax, f"{eje_valor}axis").grid(True, color=REJILLA, lw=0.8)
    ax.set_axisbelow(True)


def es(n, dec=1):
    """Número con coma decimal y espacio de miles, como se escribe en español."""
    return f"{n:,.{dec}f}".replace(",", " ").replace(".", ",")


# ----------------------------------------------------------------------------- A. antes
def a_antes(datos):
    """Torta 3D saturada: 20 porciones, arcoíris, porcentajes en todas, sin título."""
    plt.rcdefaults()
    nombres = [d[0] for d in datos]
    valores = [d[2] for d in datos]
    colores = cm.jet([i / (len(datos) - 1) for i in range(len(datos))])
    fig, ax = plt.subplots(figsize=(10, 6.2))
    # "Grosor" 3D: la misma torta repetida hacia abajo en tonos oscuros
    for k in range(14, 0, -1):
        ax.pie(valores, colors=[(r * 0.55, g * 0.55, b * 0.55, 1) for r, g, b, _ in colores],
               startangle=20, center=(0, -k * 0.018), radius=1, wedgeprops={"linewidth": 0})
    ax.pie(valores, colors=colores, startangle=20, autopct="%1.1f%%", pctdistance=0.78,
           textprops={"fontsize": 7, "color": "white", "fontweight": "bold"},
           wedgeprops={"linewidth": 0.6, "edgecolor": "white"}, shadow=True)
    ax.set_aspect(0.5)                                   # inclinación: la torta se ve "acostada"
    ax.legend(nombres, loc="center left", bbox_to_anchor=(1.0, 0.5), fontsize=8, ncol=1)
    ax.set_title("Gráfico 1", fontsize=10)
    fig.savefig(IMG / "A-antes-torta-3d.png", dpi=DPI, bbox_inches="tight")
    plt.close(fig)


# ----------------------------------------------------------------------------- A. después
def a_despues(datos, total):
    """Barras horizontales ordenadas desde 0, con la referencia de un reparto uniforme (5 %)."""
    estilo_limpio()
    uniforme = 100 / len(datos)
    nombres = [d[0] for d in datos][::-1]
    pct = [d[3] for d in datos][::-1]
    colores = [AZUL if v > uniforme else GRIS for v in pct]
    fig, ax = plt.subplots(figsize=(10, 7.2))
    y = range(len(nombres))
    ax.barh(list(y), pct, height=0.62, color=colores, edgecolor=FONDO, linewidth=2)
    ax.set_yticks(list(y), nombres)
    ax.axvline(uniforme, color=TINTA2, lw=1.1, ls=(0, (4, 3)))
    ax.text(uniforme + 0.08, len(nombres) - 0.35, "5 % = reparto uniforme entre 20 países",
            color=TINTA2, fontsize=9.5, va="bottom")
    for yi, v in zip(y, pct):                           # etiquetas: máximo, mínimo y valores clave
        if v == max(pct) or v == min(pct):
            ax.text(v + 0.08, yi, f"{es(v, 1)} %", va="center", color=TINTA, fontsize=9.5, fontweight="bold")
    ax.set_xlim(0, max(pct) * 1.15)
    ax.set_xlabel("Participación en los streams de los últimos 30 días (%)")
    ejes_minimos(ax)
    sobre = sum(v > uniforme for v in pct)
    fig.suptitle("La demanda reciente está repartida: ningún país supera el 6,6 % del total",
                 x=0.01, ha="left", fontsize=14, fontweight="bold", color=TINTA)
    ax.set_title(f"{sobre} países (azul) superan el reparto uniforme; el más alto (Italy) apenas lo excede "
                 f"en 1,6 puntos · total: {es(total, 0)} M de streams",
                 loc="left", fontsize=10, color=TINTA2, pad=8)
    fig.tight_layout()
    fig.savefig(IMG / "A-despues-barras.png", dpi=DPI, bbox_inches="tight")
    plt.close(fig)


# ----------------------------------------------------------------------------- B. antes
def b_antes(datos, base_eje=17):
    """Barras 3D, eje vertical truncado en 17 %, arcoíris, sin título ni unidades."""
    plt.rcdefaults()
    regiones = [d[0] for d in datos]
    valores = [d[1] for d in datos]
    fig = plt.figure(figsize=(9, 6.2))
    ax = fig.add_subplot(projection="3d")
    xs = range(len(regiones))
    colores = cm.rainbow([i / (len(regiones) - 1) for i in xs])
    ax.bar3d(list(xs), [0] * len(xs), [base_eje] * len(xs), 0.6, 0.6,
             [v - base_eje for v in valores], color=colores, shade=True)
    ax.set_zlim(base_eje, 23)                           # eje truncado: no empieza en 0
    ax.set_xticks([x + 0.3 for x in xs], regiones, fontsize=8, rotation=15)
    ax.set_yticks([])
    ax.view_init(elev=22, azim=-62)
    fig.savefig(IMG / "B-antes-barras-3d.png", dpi=DPI, bbox_inches="tight")
    plt.close(fig)


# ----------------------------------------------------------------------------- B. después
def b_despues(datos):
    """Barras horizontales desde 0 %, un solo color, valor y tamaño de muestra en cada barra."""
    estilo_limpio()
    regiones = [d[0] for d in datos][::-1]
    valores = [d[1] for d in datos][::-1]
    n = [d[2] for d in datos][::-1]
    fig, ax = plt.subplots(figsize=(10, 4.6))
    y = range(len(regiones))
    ax.barh(list(y), valores, height=0.58, color=AZUL, edgecolor=FONDO, linewidth=2)
    ax.set_yticks(list(y), [f"{r}  (n = {k})" for r, k in zip(regiones, n)])
    for yi, v in zip(y, valores):
        ax.text(v + 0.3, yi, f"{es(v, 1)} %", va="center", color=TINTA, fontsize=10)
    ax.set_xlim(0, 30)
    ax.set_xlabel("Skip rate promedio (% de reproducciones abandonadas)")
    ejes_minimos(ax)
    fig.suptitle(f"El abandono es parecido en todas las regiones: entre {es(min(valores))} % y {es(max(valores))} %",
                 x=0.01, ha="left", fontsize=14, fontweight="bold", color=TINTA)
    ax.set_title("Eje desde 0 %: la diferencia entre la región más alta y la más baja es de "
                 f"{es(max(valores) - min(valores))} puntos · n = registros de cada región",
                 loc="left", fontsize=10, color=TINTA2, pad=8)
    fig.tight_layout()
    fig.savefig(IMG / "B-despues-barras.png", dpi=DPI, bbox_inches="tight")
    plt.close(fig)


if __name__ == "__main__":
    IMG.mkdir(exist_ok=True)
    pais, total = participacion_por_pais()
    region = skip_por_region()
    a_antes(pais); a_despues(pais, total)
    b_antes(region); b_despues(region)

    alto, bajo = region[0], region[-1]
    lf, eg, ed = factor_de_mentira(alto[1], bajo[1], base_eje=17)
    print(f"A · {len(pais)} países · máximo {pais[0][0]} {pais[0][3]:.2f} % · mínimo {pais[-1][0]} {pais[-1][3]:.2f} %")
    print(f"B · {alto[0]} {alto[1]:.2f} % vs {bajo[0]} {bajo[1]:.2f} %: efecto real {ed:.1%}, "
          f"efecto dibujado con eje en 17 % {eg:.1%} -> factor de mentira {lf:.1f}")
    print("Imágenes en", IMG)
