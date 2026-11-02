"""Semana 14 · Optimización de una consulta SQL (opción A) — caso Spotify.

Pregunta de negocio: ¿cuántas horas se escucharon en cada país en diciembre de 2025, el mes pico
de la Semana 11? Se compara la consulta lenta (SELECT *, función sobre la columna en el WHERE y
agregación fuera de la base) con versiones mejoradas paso a paso, midiendo el tiempo y el plan.

Datos: la base del caso (Semana 10) solo tiene 498 filas, demasiado pocas para medir. Se genera
una tabla de EVENTOS de reproducción (la del pipeline de la Semana 8) con 2 000 000 de filas,
calibrada con datos reales:
  - país, álbum y plan: proporcionales a los streams de 30 días de Kaggle (base de la Semana 10)
  - mes: proporcional al índice estacional del interés en Wikipedia (Semana 11)
  - segundos escuchados: alrededor de la duración promedio de cada álbum (Kaggle)
La semilla fija hace que siempre se genere la misma tabla. Solo usa sqlite3 y Matplotlib.

Uso:  python optimizacion_sql.py            (genera datos/eventos.db si no existe y mide)
"""
import csv
import random
import sqlite3
import statistics
import time
from collections import defaultdict
from datetime import datetime, timedelta
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

AQUI = Path(__file__).resolve().parent
RAIZ = AQUI.parents[1]
BASE_CASO = RAIZ / "10-week" / "02-optional-activity" / "datos" / "spotify.db"
SERIE = RAIZ / "11-week" / "02-optional-activity" / "datos" / "pageviews_spotify_diario.csv"
EVENTOS = AQUI / "datos" / "eventos.db"            # ~100 MB: se genera, no se versiona
RESULTADOS = AQUI / "datos" / "resultados.csv"
GRAFICO = AQUI / "img" / "tiempos-consulta.png"

N_EVENTOS = 2_000_000
SEMILLA = 2026
REPETICIONES = 5
INICIO, FIN = datetime(2024, 1, 1), datetime(2026, 1, 1)   # dos años de eventos


# ----------------------------------------------------------------------------- datos
def pesos_mensuales():
    """Índice estacional por mes (1..12) a partir de la serie de la Semana 11 (mediana 2016–2025)."""
    por_mes = defaultdict(list)
    with open(SERIE, encoding="utf-8") as f:
        for fila in csv.DictReader(f):
            por_mes[fila["fecha"][:7]].append(int(fila["visitas"]))
    prom = {m: sum(v) / len(v) for m, v in por_mes.items() if m < "2026-01"}
    ratio = defaultdict(list)
    for anio in range(2016, 2025):            # cociente de cada mes frente al promedio de su año
        media = statistics.mean(prom[f"{anio}-{m:02d}"] for m in range(1, 13))
        for m in range(1, 13):
            ratio[m].append(prom[f"{anio}-{m:02d}"] / media)
    return {m: statistics.median(v) for m, v in ratio.items()}


def generar_eventos():
    """Crea datos/eventos.db con los catálogos del caso y 2 millones de eventos calibrados."""
    rng = random.Random(SEMILLA)
    caso = sqlite3.connect(BASE_CASO)
    combos = caso.execute("""
        SELECT country_id, album_id, plan_id, SUM(streams_30d_m), AVG(duracion_prom_min)
        FROM metrica_streaming GROUP BY country_id, album_id, plan_id""").fetchall()
    paises = caso.execute("SELECT country_id, nombre FROM pais").fetchall()
    caso.close()

    pesos_mes = pesos_mensuales()
    dias = [INICIO + timedelta(days=d) for d in range((FIN - INICIO).days)]
    peso_dia = [pesos_mes[d.month] for d in dias]

    EVENTOS.parent.mkdir(exist_ok=True)
    EVENTOS.unlink(missing_ok=True)
    con = sqlite3.connect(EVENTOS)
    con.executescript("""
        PRAGMA journal_mode = OFF; PRAGMA synchronous = OFF;
        CREATE TABLE pais (country_id INTEGER PRIMARY KEY, nombre TEXT NOT NULL);
        CREATE TABLE reproduccion (
            play_id             INTEGER PRIMARY KEY,
            fecha_hora          TEXT    NOT NULL,     -- ISO 8601: 'AAAA-MM-DD HH:MM:SS'
            country_id          INTEGER NOT NULL REFERENCES pais (country_id),
            album_id            INTEGER NOT NULL,
            plan_id             INTEGER NOT NULL,
            dispositivo         TEXT    NOT NULL,
            segundos_escuchados INTEGER NOT NULL
        );""")
    con.executemany("INSERT INTO pais VALUES (?, ?)", paises)

    elegidos = rng.choices(combos, weights=[c[3] for c in combos], k=N_EVENTOS)
    fechas = rng.choices(dias, weights=peso_dia, k=N_EVENTOS)
    disp = rng.choices(["movil", "escritorio", "web", "tv", "consola"], weights=[62, 18, 10, 7, 3], k=N_EVENTOS)

    def filas():
        for i in range(N_EVENTOS):
            pais, album, plan, _, dur = elegidos[i]
            momento = fechas[i] + timedelta(seconds=rng.randrange(86_400))
            segundos = max(5, int(rng.gauss(dur * 60 * 0.8, 45)))
            yield (i + 1, momento.strftime("%Y-%m-%d %H:%M:%S"), pais, album, plan, disp[i], segundos)

    con.executemany("INSERT INTO reproduccion VALUES (?, ?, ?, ?, ?, ?, ?)", filas())
    con.commit()
    con.execute("ANALYZE")
    con.close()


# ----------------------------------------------------------------------------- consultas
def agregar_en_python(filas):
    """Lo que hace la versión lenta en la aplicación: sumar horas por país fila por fila."""
    horas = defaultdict(float)
    for fila in filas:
        horas[fila["nombre"]] += fila["segundos_escuchados"] / 3600
    return sorted(((p, round(h, 1)) for p, h in horas.items()), key=lambda x: -x[1])


LENTA = """
SELECT *
FROM   reproduccion r
JOIN   pais p ON p.country_id = r.country_id
WHERE  strftime('%Y-%m', r.fecha_hora) = '2025-12'"""

CON_FUNCION = """
SELECT p.nombre, ROUND(SUM(r.segundos_escuchados) / 3600.0, 1) AS horas
FROM   reproduccion r
JOIN   pais p ON p.country_id = r.country_id
WHERE  strftime('%Y-%m', r.fecha_hora) = '2025-12'
GROUP  BY p.nombre
ORDER  BY horas DESC"""

RAPIDA = """
SELECT p.nombre, ROUND(SUM(r.segundos_escuchados) / 3600.0, 1) AS horas
FROM   reproduccion r
JOIN   pais p ON p.country_id = r.country_id
WHERE  r.fecha_hora >= '2025-12-01' AND r.fecha_hora < '2026-01-01'
GROUP  BY p.nombre
ORDER  BY horas DESC"""

IDX_SIMPLE = "CREATE INDEX idx_rep_fecha ON reproduccion (fecha_hora)"
IDX_COBERTURA = "CREATE INDEX idx_rep_fecha_cubre ON reproduccion (fecha_hora, country_id, segundos_escuchados)"

PASOS = [
    # (id, descripción, consulta, índices que deben existir, agrega en Python)
    ("0", "Antes: SELECT * + función en el WHERE + suma en Python", LENTA, [], True),
    ("1", "Solo columnas necesarias + GROUP BY en SQL (aún con función)", CON_FUNCION, [], False),
    ("2", "Filtro por rango de fechas, sin índice", RAPIDA, [], False),
    ("3", "Índice en fecha_hora, pero conservando la función", CON_FUNCION, [IDX_SIMPLE], False),
    ("4", "Filtro por rango + índice en fecha_hora", RAPIDA, [IDX_SIMPLE], False),
    ("5", "Después: filtro por rango + índice de cobertura", RAPIDA, [IDX_COBERTURA], False),
]


def preparar_indices(con, indices):
    for nombre in ("idx_rep_fecha", "idx_rep_fecha_cubre"):
        con.execute(f"DROP INDEX IF EXISTS {nombre}")
    for ddl in indices:
        con.execute(ddl)
    con.execute("ANALYZE")


def medir(con, sql, en_python):
    """Mediana de REPETICIONES ejecuciones; devuelve (segundos, filas transferidas, resultado)."""
    tiempos, resultado, transferidas = [], None, 0
    for _ in range(REPETICIONES):
        t0 = time.perf_counter()
        cur = con.execute(sql)
        if en_python:
            columnas = [c[0] for c in cur.description]
            filas = [dict(zip(columnas, f)) for f in cur.fetchall()]
            transferidas = len(filas)
            resultado = agregar_en_python(filas)
        else:
            resultado = [tuple(f) for f in cur.fetchall()]
            transferidas = len(resultado)
        tiempos.append(time.perf_counter() - t0)
    return statistics.median(tiempos), transferidas, resultado


def plan(con, sql):
    return " | ".join(f[3] for f in con.execute("EXPLAIN QUERY PLAN " + sql).fetchall())


def ejecutar():
    if not EVENTOS.exists():
        t0 = time.perf_counter()
        generar_eventos()
        print(f"Tabla de eventos generada en {time.perf_counter() - t0:.0f} s")
    con = sqlite3.connect(EVENTOS)
    total = con.execute("SELECT COUNT(*) FROM reproduccion").fetchone()[0]
    dic = con.execute("SELECT COUNT(*) FROM reproduccion WHERE fecha_hora >= '2025-12-01' "
                      "AND fecha_hora < '2026-01-01'").fetchone()[0]
    filas, referencia = [], None
    for pid, desc, sql, indices, en_py in PASOS:
        preparar_indices(con, indices)
        seg, transf, res = medir(con, sql, en_py)
        if referencia is None:
            referencia = res
        # Mismo resultado: mismos países y horas iguales (tolerancia de 0,1 h por redondeo)
        ref_d, res_d = dict(referencia), dict(res)
        mismo = ref_d.keys() == res_d.keys() and all(abs(ref_d[p] - res_d[p]) <= 0.1 for p in ref_d)
        filas.append({"paso": pid, "descripcion": desc, "mediana_ms": round(seg * 1000, 1),
                      "filas_transferidas": transf, "mismo_resultado": mismo, "plan": plan(con, sql)})
    preparar_indices(con, [IDX_COBERTURA])                        # deja la base en su mejor estado
    con.close()
    base = filas[0]["mediana_ms"]
    for f in filas:
        f["veces_mas_rapida"] = round(base / f["mediana_ms"], 1)
    RESULTADOS.parent.mkdir(exist_ok=True)
    with open(RESULTADOS, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(filas[0]))
        w.writeheader()
        w.writerows(filas)
    return filas, total, dic, referencia


# ----------------------------------------------------------------------------- gráfico
def graficar(filas):
    AZUL, GRIS = "#2a78d6", "#8a8984"
    TINTA, TINTA2, REJILLA, FONDO = "#0b0b0b", "#52514e", "#e7e6e2", "#fcfcfb"
    plt.rcParams.update({"font.family": ["Segoe UI", "DejaVu Sans"], "font.size": 10.5,
                         "figure.facecolor": FONDO, "axes.facecolor": FONDO})
    etiquetas = [f"{f['paso']} · {f['descripcion']}" for f in filas][::-1]
    ms = [f["mediana_ms"] for f in filas][::-1]
    colores = [AZUL if f["paso"] in ("0", "5") else GRIS for f in filas][::-1]
    fig, ax = plt.subplots(figsize=(11.5, 5))
    ax.barh(etiquetas, ms, height=0.58, color=colores, edgecolor=FONDO, linewidth=2)
    for y, (v, f) in enumerate(zip(ms, filas[::-1])):
        ax.text(v + max(ms) * 0.01, y, f"{v:,.0f} ms".replace(",", " ") + (
            f"  (×{f['veces_mas_rapida']:.1f})".replace(".", ",") if f["paso"] != "0" else ""),
            va="center", color=TINTA, fontsize=10)
    ax.set_xlim(0, max(ms) * 1.22)
    ax.set_xlabel("Tiempo de la consulta (mediana de 5 ejecuciones, milisegundos)", color=TINTA2)
    for s in ("top", "right", "left"):
        ax.spines[s].set_visible(False)
    ax.spines["bottom"].set_color(REJILLA)
    ax.tick_params(length=0, colors=TINTA)
    ax.xaxis.grid(True, color=REJILLA)
    ax.set_axisbelow(True)
    mejora = filas[-1]["veces_mas_rapida"]
    fig.suptitle(f"Reescribir la consulta y crear un índice de cobertura la hace {mejora:.0f} veces más rápida",
                 x=0.01, ha="left", fontsize=13.5, fontweight="bold", color=TINTA)
    ax.set_title("Horas escuchadas por país en diciembre de 2025 · 2 000 000 de eventos · "
                 "en azul, la consulta original y la final", loc="left", fontsize=10, color=TINTA2, pad=8)
    fig.tight_layout()
    GRAFICO.parent.mkdir(exist_ok=True)
    fig.savefig(GRAFICO, dpi=140, bbox_inches="tight")
    plt.close(fig)


if __name__ == "__main__":
    filas, total, dic, ref = ejecutar()
    graficar(filas)
    print(f"Eventos: {total:,} · eventos de diciembre de 2025: {dic:,}")
    for f in filas:
        print(f"Paso {f['paso']}: {f['mediana_ms']:>8.1f} ms · x{f['veces_mas_rapida']:<6} · filas {f['filas_transferidas']:>7} "
              f"· mismo resultado: {f['mismo_resultado']} · plan: {f['plan']}")
    print("Top 3 países en diciembre de 2025:", ref[:3])
