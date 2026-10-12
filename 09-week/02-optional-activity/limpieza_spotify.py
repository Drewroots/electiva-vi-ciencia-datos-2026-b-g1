"""Limpieza del dataset de Spotify con pandas: nulos, duplicados, tipos y formatos de texto.

Las reglas son generales: no dependen de saber qué problemas se inyectaron. Los valores
de texto se validan contra los catálogos maestros del modelo de la Semana 6
(pais, genero, plan_suscripcion, artista, album).

Uso:  python limpieza_spotify.py   (lee datos/spotify_sucio.csv y escribe datos/spotify_limpio.csv)
"""
import re
import unicodedata
from pathlib import Path

import pandas as pd

ENTRADA = Path("datos/spotify_sucio.csv")
SALIDA = Path("datos/spotify_limpio.csv")
CATALOGOS = Path("../../06-week/02-optional-activity/datos-normalizados")

# Marcadores de texto que en realidad significan "sin dato"
MARCAS_NULO = ["", "N/A", "NA", "n/a", "-", "null", "None"]

# Nombres de columna en snake_case, alineados con el modelo de la Semana 6
COLUMNAS = {
    "Country": "pais", "Artist": "artista", "Album": "album", "Genre": "genero",
    "Release Year": "anio_lanzamiento",
    "Monthly Listeners (Millions)": "oyentes_mensuales_m",
    "Total Streams (Millions)": "streams_totales_m",
    "Total Hours Streamed (Millions)": "horas_totales_m",
    "Avg Stream Duration (Min)": "duracion_prom_min",
    "Platform Type": "plan",
    "Streams Last 30 Days (Millions)": "streams_30d_m",
    "Skip Rate (%)": "skip_rate_pct",
}
TEXTO = ["pais", "artista", "album", "genero", "plan"]
MEDIDAS = ["oyentes_mensuales_m", "streams_totales_m", "horas_totales_m",
           "duracion_prom_min", "streams_30d_m", "skip_rate_pct"]

# Escrituras alternativas conocidas -> valor oficial del catálogo
SINONIMOS = {"usa": "United States", "us": "United States", "uk": "United Kingdom"}


def clave(texto):
    """Forma comparable de un texto: sin tildes, sin espacios ni signos y en minúsculas."""
    sin_tildes = unicodedata.normalize("NFKD", str(texto)).encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z0-9]", "", sin_tildes.lower())


def cargar_catalogos(ruta=CATALOGOS):
    """Valores oficiales de cada columna de texto, tomados del modelo de la Semana 6."""
    leer = lambda t, c: pd.read_csv(ruta / f"{t}.csv")[c].tolist()
    return {"pais": leer("pais", "nombre"), "genero": leer("genero", "nombre"),
            "plan": leer("plan_suscripcion", "nombre"), "artista": leer("artista", "nombre"),
            "album": leer("album", "titulo")}


def leer_sucio(ruta=ENTRADA):
    """Lee el CSV reconociendo los marcadores de nulo y sin convertir tipos todavía."""
    return pd.read_csv(ruta, na_values=MARCAS_NULO, keep_default_na=True, dtype=str)


def a_numero(serie):
    """Texto -> número: quita separadores de miles y el símbolo %."""
    limpio = serie.str.replace(",", "", regex=False).str.replace("%", "", regex=False).str.strip()
    return pd.to_numeric(limpio, errors="coerce")


def moda_menor(serie):
    conteo = serie.value_counts()
    return int(conteo[conteo == conteo.max()].index.min())


def limpiar(sucio, catalogos=None):
    """Devuelve (df_limpio, bitacora) con cada paso y su efecto en filas y celdas."""
    catalogos = catalogos or cargar_catalogos()
    df = sucio.copy()
    bitacora = []

    def anotar(paso, dimension, detalle, filas_antes):
        bitacora.append({"paso": paso, "dimensión": dimension, "detalle": detalle,
                         "filas antes": filas_antes, "filas después": len(df)})

    # 1. Nombres de columna: snake_case y en español, como en el modelo
    df = df.rename(columns=COLUMNAS)
    anotar("1. Nombres de columna", "Consistencia", "12 columnas a snake_case (modelo Semana 6)", len(df))

    # 2. Formato de texto: espacios, mayúsculas y sinónimos -> valor oficial del catálogo
    n = len(df)
    cambiadas, fuera = 0, 0
    for col in TEXTO:
        oficial = {clave(v): v for v in catalogos[col]}
        oficial.update({k: v for k, v in SINONIMOS.items() if v in catalogos[col]})
        antes = df[col].copy()
        df[col] = df[col].map(lambda v: oficial.get(clave(v), "__FUERA__") if pd.notna(v) else v)
        fuera += int((df[col] == "__FUERA__").sum())
        df[col] = df[col].replace("__FUERA__", pd.NA)
        cambiadas += int((antes.notna() & df[col].notna() & (antes != df[col])).sum())
    anotar("2. Formato de texto", "Consistencia",
           f"{cambiadas} celdas llevadas a su valor oficial; {fuera} fuera de catálogo -> nulo", n)

    # 3. Tipos: números guardados como texto -> float; año -> entero
    n = len(df)
    no_numericas = sum(int(df[c].notna().sum() - a_numero(df[c]).notna().sum()) for c in MEDIDAS)
    for col in MEDIDAS:
        df[col] = a_numero(df[col])
    df["anio_lanzamiento"] = a_numero(df["anio_lanzamiento"]).astype("Int16")
    anotar("3. Tipos", "Exactitud",
           f"6 medidas a float64 y el año a Int16 ({no_numericas} celdas no convertibles)", n)

    # 4. Duplicados exactos (después de normalizar, para detectar también los de formato)
    n = len(df)
    df = df.drop_duplicates().reset_index(drop=True)
    anotar("4. Duplicados", "Unicidad", f"{n - len(df)} filas repetidas eliminadas", n)

    # 5. Faltantes: sin clave no hay registro; las medidas se imputan con la mediana del álbum
    n = len(df)
    df = df.dropna(subset=TEXTO + ["anio_lanzamiento"]).reset_index(drop=True)
    imputadas = int(df[MEDIDAS].isna().sum().sum())
    for col in MEDIDAS:
        mediana_album = df.groupby("album")[col].transform("median")
        df[col] = df[col].fillna(mediana_album).fillna(df[col].median()).round(2)
    anotar("5. Faltantes", "Completitud",
           f"{n - len(df)} filas sin país/género eliminadas; {imputadas} medidas imputadas (mediana del álbum)", n)

    # 6. Un solo año de lanzamiento por álbum (regla de la Semana 6: moda; empate -> menor)
    n = len(df)
    anio = df.groupby("album")["anio_lanzamiento"].transform(moda_menor).astype("Int16")
    corregidas = int((df["anio_lanzamiento"] != anio).sum())
    df["anio_lanzamiento"] = anio
    anotar("6. Año por álbum", "Consistencia", f"{corregidas} celdas corregidas a un año por álbum", n)

    # 7. Valores imposibles: streams de 30 días mayores que los totales, o skip fuera de 0-100 %
    n = len(df)
    imposible = (df["streams_30d_m"] > df["streams_totales_m"]) | ~df["skip_rate_pct"].between(0, 100)
    df = df[~imposible].reset_index(drop=True)
    anotar("7. Valores imposibles", "Exactitud", f"{n - len(df)} filas con streams 30 d > streams totales", n)

    # Tipos finales de las columnas de texto
    for col in TEXTO:
        df[col] = df[col].astype("category")
    return df, pd.DataFrame(bitacora)


def perfil(df, columnas_texto):
    """Indicadores de calidad comparables entre la versión sucia y la limpia."""
    texto = df[columnas_texto].astype("string")
    espacios = sum(int((texto[c] != texto[c].str.strip()).sum()) for c in columnas_texto)
    return {
        "Filas": len(df),
        "Celdas nulas": int(df.isna().sum().sum()),
        "Filas duplicadas exactas": int(df.duplicated().sum()),
        "Columnas numéricas (de 7)": int(df.select_dtypes("number").shape[1]),
        "Celdas de texto con espacios sobrantes": espacios,
        "Formas distintas de escribir el país": int(texto[columnas_texto[0]].dropna().nunique()),
        "Formas distintas de escribir el plan": int(texto[columnas_texto[-1]].dropna().nunique()),
    }


if __name__ == "__main__":
    sucio = leer_sucio()
    limpio, bitacora = limpiar(sucio)
    SALIDA.parent.mkdir(exist_ok=True)
    limpio.to_csv(SALIDA, index=False)
    print(bitacora.to_string(index=False))
    print(f"\n{len(sucio)} filas -> {len(limpio)} filas en {SALIDA}")
