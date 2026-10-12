"""Mini-proyecto (cierre del Corte 2): extraer -> limpiar -> cargar -> datos listos para analizar.

Integra lo construido en el corte, sin duplicar código:
  - Extraer:  CSV de Kaggle (Semana 6) + API de MusicBrainz para el género de cada artista (Semana 8).
  - Limpiar:  limpieza_spotify.limpiar() de la Semana 9 (formatos, tipos, duplicados, faltantes,
              año por álbum y valores imposibles).
  - Cargar:   tablas del ERD de la Semana 6 en una base SQLite (datos/spotify.db) con PK, FK y CHECK.

Uso:  python pipeline_spotify.py            (usa la caché de la API si existe)
      python pipeline_spotify.py --api      (vuelve a consultar MusicBrainz)
"""
import sqlite3
import sys
import time
from pathlib import Path

import pandas as pd
import requests

AQUI = Path(__file__).resolve().parent
RAIZ = AQUI.parents[1]
SEMANA6 = RAIZ / "06-week" / "02-optional-activity"
SEMANA9 = RAIZ / "09-week" / "02-optional-activity"
sys.path.insert(0, str(SEMANA9))
import limpieza_spotify as L  # noqa: E402  (script de limpieza de la Semana 9)

CSV_KAGGLE = SEMANA6 / "Spotify_2024_Global_Streaming_Data.csv"
CATALOGOS = SEMANA6 / "datos-normalizados"
ESQUEMA = SEMANA6 / "esquema-spotify.sql"
DATOS = AQUI / "datos"
CACHE_API = DATOS / "catalogo_musicbrainz.csv"
CSV_LIMPIO = DATOS / "spotify_limpio.csv"
BASE = DATOS / "spotify.db"

API = "https://musicbrainz.org/ws/2"
HEADERS = {"User-Agent": "CORHUILA-CienciaDatos-Semana10/1.0 "
                         "( https://github.com/Drewroots/electiva-vi-ciencia-datos-2026-b-g1 )",
           "Accept": "application/json"}


# ----------------------------------------------------------------------------- 1. EXTRAER
def extraer_csv(ruta=CSV_KAGGLE):
    """Lee el CSV de Kaggle como texto; la conversión de tipos es parte de la limpieza."""
    return pd.read_csv(ruta, dtype=str, na_values=L.MARCAS_NULO)


def _get(ruta, params, reintentos=4, pausa=1.1):
    """GET a MusicBrainz con pausa entre peticiones y reintentos si el servidor está ocupado."""
    for intento in range(1, reintentos + 1):
        time.sleep(pausa)
        r = requests.get(f"{API}/{ruta}", params={**params, "fmt": "json"}, headers=HEADERS, timeout=15)
        if r.status_code in (429, 503):
            time.sleep(2 * intento)
            continue
        r.raise_for_status()
        return r.json()
    raise RuntimeError(f"MusicBrainz no respondió: {ruta}")


def extraer_api(artistas, usar_cache=True):
    """Género con más votos de cada artista en MusicBrainz. Guarda una caché para no depender de la red."""
    if usar_cache and CACHE_API.exists():
        return pd.read_csv(CACHE_API)
    filas = []
    for a in artistas.itertuples():
        mejor = _get("artist/", {"query": f'artist:"{a.nombre}"', "limit": 1})["artists"][0]
        detalle = _get(f"artist/{mejor['id']}", {"inc": "genres"})
        generos = detalle.get("genres", [])
        filas.append({
            "artist_id": a.artist_id, "mbid": mejor["id"], "nombre": detalle["name"],
            "tipo": detalle.get("type"), "pais_iso": detalle.get("country"),
            "genero_principal": max(generos, key=lambda g: g["count"])["name"] if generos else None,
            "coincidencia_pct": mejor["score"],
        })
    catalogo = pd.DataFrame(filas)
    assert (catalogo["coincidencia_pct"] == 100).all(), "Alguna búsqueda en la API no coincidió al 100 %"
    DATOS.mkdir(exist_ok=True)
    catalogo.to_csv(CACHE_API, index=False)
    return catalogo


# ----------------------------------------------------------------------------- 2. LIMPIAR
def limpiar(crudo):
    """Reutiliza la limpieza de la Semana 9 sobre el CSV original."""
    return L.limpiar(crudo, L.cargar_catalogos(CATALOGOS))


# ----------------------------------------------------------------------------- 3. CARGAR
def modelar(limpio, catalogo_api):
    """Lleva la tabla limpia a las 6 tablas del ERD, con los mismos id de la Semana 6."""
    cat = {t: pd.read_csv(CATALOGOS / f"{t}.csv") for t in
           ["pais", "genero", "plan_suscripcion", "artista", "album"]}
    artista = cat["artista"].drop(columns="genero_principal").merge(
        catalogo_api[["artist_id", "genero_principal"]], on="artist_id", how="left")

    # El año por álbum sale de la limpieza (moda); debe coincidir con el catálogo de la Semana 6
    anio = limpio.groupby("album", observed=True)["anio_lanzamiento"].first().astype("int64")
    album = cat["album"].assign(anio_lanzamiento=cat["album"]["titulo"].map(anio))
    assert (album["anio_lanzamiento"] == cat["album"]["anio_lanzamiento"]).all(), "Año distinto al de la Semana 6"

    ids = lambda t, col, id_col: dict(zip(cat[t][col], cat[t][id_col]))
    metrica = pd.DataFrame({
        "metric_id": range(1, len(limpio) + 1),
        "country_id": limpio["pais"].astype(str).map(ids("pais", "nombre", "country_id")),
        "album_id": limpio["album"].astype(str).map(ids("album", "titulo", "album_id")),
        "genero_id": limpio["genero"].astype(str).map(ids("genero", "nombre", "genero_id")),
        "plan_id": limpio["plan"].astype(str).map(ids("plan_suscripcion", "nombre", "plan_id")),
        **{c: limpio[c] for c in L.MEDIDAS},
    })
    assert metrica.notna().all().all(), "Alguna FK quedó sin resolver"
    return {"pais": cat["pais"], "genero": cat["genero"], "plan_suscripcion": cat["plan_suscripcion"],
            "artista": artista, "album": album, "metrica_streaming": metrica}


def cargar(tablas, ruta=BASE):
    """Crea la base SQLite con el esquema del ERD y carga las tablas (catálogos primero)."""
    ruta.unlink(missing_ok=True)
    with sqlite3.connect(ruta) as con:
        con.executescript(ESQUEMA.read_text(encoding="utf-8"))
        for nombre, df in tablas.items():
            df.to_sql(nombre, con, if_exists="append", index=False)
        violaciones = con.execute("PRAGMA foreign_key_check").fetchall()
    assert not violaciones, f"Violaciones de FK: {violaciones}"
    return ruta


# ----------------------------------------------------------------------------- ORQUESTACIÓN
def ejecutar(usar_cache=True):
    """Corre el flujo completo y devuelve lo necesario para documentarlo."""
    crudo = extraer_csv()
    catalogo_api = extraer_api(pd.read_csv(CATALOGOS / "artista.csv"), usar_cache)
    limpio, bitacora = limpiar(crudo)
    DATOS.mkdir(exist_ok=True)
    limpio.to_csv(CSV_LIMPIO, index=False)
    tablas = modelar(limpio, catalogo_api)
    cargar(tablas)
    return {"crudo": crudo, "api": catalogo_api, "limpio": limpio,
            "bitacora": bitacora, "tablas": tablas}


if __name__ == "__main__":
    r = ejecutar(usar_cache="--api" not in sys.argv)
    print(r["bitacora"][["paso", "detalle", "filas antes", "filas después"]].to_string(index=False))
    print(f"\nExtraer: {len(r['crudo'])} filas del CSV + {len(r['api'])} artistas de la API")
    print(f"Limpiar: {len(r['crudo'])} -> {len(r['limpio'])} filas -> {CSV_LIMPIO.name}")
    print("Cargar:  " + ", ".join(f"{t} ({len(df)})" for t, df in r["tablas"].items()) + f" -> {BASE.name}")
