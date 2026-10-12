"""Serie de tiempo del caso Spotify: visitas diarias al artículo "Spotify" en Wikipedia.

El dataset de Kaggle del curso no tiene fechas, así que la dimensión temporal se toma de una
fuente real y pública: la API de páginas vistas de Wikimedia (JSON, sin clave), como la API de
la Semana 8. Las visitas miden la atención del público sobre Spotify, un indicador de interés
que se usa como aproximación de la demanda.

Flujo:  extraer (API con caché) -> índice de fechas -> resample mensual -> media móvil 2x12
        -> índice estacional por mes del año.

Uso:  python serie_tiempo_spotify.py          (usa la caché si existe)
      python serie_tiempo_spotify.py --api    (vuelve a descargar)
"""
import sys
import time
from pathlib import Path

import pandas as pd
import requests

AQUI = Path(__file__).resolve().parent
CACHE = AQUI / "datos" / "pageviews_spotify_diario.csv"

ARTICULO, PROYECTO = "Spotify", "en.wikipedia"
INICIO, FIN = "20160101", "20260930"          # 10 años y 9 meses completos
URL = ("https://wikimedia.org/api/rest_v1/metrics/pageviews/per-article/"
       f"{PROYECTO}/all-access/user/{ARTICULO}/daily/{INICIO}/{FIN}")
HEADERS = {"User-Agent": "CORHUILA-CienciaDatos-Semana11/1.0 "
                         "(https://github.com/Drewroots/electiva-vi-ciencia-datos-2026-b-g1)"}


def extraer(usar_cache=True, reintentos=5):
    """Serie diaria con la fecha como índice (DatetimeIndex). Guarda una caché en CSV."""
    if usar_cache and CACHE.exists():
        df = pd.read_csv(CACHE, parse_dates=["fecha"])
        return df.set_index("fecha")["visitas"]
    for intento in range(1, reintentos + 1):
        try:
            r = requests.get(URL, headers=HEADERS, timeout=60)
            r.raise_for_status()
            break
        except requests.RequestException:
            if intento == reintentos:
                raise
            time.sleep(3 * intento)
    items = pd.DataFrame(r.json()["items"])
    serie = pd.DataFrame({
        "fecha": pd.to_datetime(items["timestamp"].str[:8], format="%Y%m%d"),   # texto -> fecha
        "visitas": items["views"].astype("int64"),
    })
    CACHE.parent.mkdir(exist_ok=True)
    serie.to_csv(CACHE, index=False)
    return serie.set_index("fecha")["visitas"]


def mensual(diaria):
    """Agrega por mes. El promedio diario evita que febrero (28 días) parezca un mes 'bajo'."""
    return pd.DataFrame({
        "visitas_total": diaria.resample("MS").sum(),
        "visitas_dia_prom": diaria.resample("MS").mean().round(1),
        "dias": diaria.resample("MS").count(),
    })


def media_movil_centrada(serie, ventana=12):
    """Media móvil 2x12 centrada: promedia 12 meses (un año completo) y la centra en el mes.

    Con 12 meses la estacionalidad anual se cancela y queda la tendencia. Como 12 es par, se
    promedian dos medias de 12 consecutivas para que el valor quede centrado en un mes exacto.
    """
    return serie.rolling(ventana).mean().rolling(2).mean().shift(-(ventana // 2))


def indice_estacional(serie, tendencia):
    """Cuánto se aparta cada mes del año de su tendencia (1,00 = igual a la tendencia).

    Se usa la mediana por mes de calendario para que un mes atípico de un solo año
    (como octubre de 2022) no defina el patrón de todos los años.
    """
    ratio = (serie / tendencia).dropna()
    idx = ratio.groupby(ratio.index.month).median()
    return (idx / idx.mean()).round(3)          # normalizado: el promedio de los 12 meses es 1


if __name__ == "__main__":
    diaria = extraer(usar_cache="--api" not in sys.argv)
    m = mensual(diaria)
    m["media_movil_2x12"] = media_movil_centrada(m["visitas_dia_prom"]).round(1)
    est = indice_estacional(m["visitas_dia_prom"], m["media_movil_2x12"])
    print(f"Serie diaria: {len(diaria)} días ({diaria.index.min().date()} a {diaria.index.max().date()})")
    print(f"Serie mensual: {len(m)} meses\n")
    print("Índice estacional (mediana por mes):")
    print(est.rename(index=lambda k: pd.Timestamp(2000, k, 1).strftime("%b")).to_string())
