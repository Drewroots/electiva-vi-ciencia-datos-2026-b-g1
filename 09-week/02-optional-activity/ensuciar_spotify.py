"""Genera una versión "sucia" y reproducible del dataset de Spotify (Kaggle, 2024).

El CSV original no tiene nulos ni duplicados, así que, como permite la guía de la
Semana 9, se le inyectan los problemas típicos de un dataset real: formatos de texto
inconsistentes, números guardados como texto, valores faltantes y filas duplicadas.
La semilla fija garantiza que siempre se genere el mismo archivo.

Uso:  python ensuciar_spotify.py
"""
from pathlib import Path

import numpy as np
import pandas as pd

ORIGEN = Path("../../06-week/02-optional-activity/Spotify_2024_Global_Streaming_Data.csv")
DESTINO = Path("datos/spotify_sucio.csv")
SEMILLA = 2026


def _variante(texto, rng):
    """Una de las formas en que un mismo valor suele llegar escrito distinto."""
    formas = [str.lower, str.upper, lambda s: f"  {s} ", lambda s: f"{s}   ",
              lambda s: s.replace(" ", "  ")]
    return formas[rng.integers(len(formas))](texto)


def ensuciar(df, semilla=SEMILLA):
    """Devuelve (df_sucio, resumen) con los problemas inyectados y cuántas celdas afectó cada uno."""
    rng = np.random.default_rng(semilla)
    d = df.copy().astype(object)
    n = len(d)
    resumen = []

    def filas(k, donde=None):
        base = d.index if donde is None else d.index[donde]
        return rng.choice(base, size=k, replace=False)

    # 1. Formato de texto: mayúsculas, minúsculas y espacios sobrantes
    for col, k in [("Country", 50), ("Genre", 30), ("Platform Type", 30), ("Artist", 15)]:
        idx = filas(k)
        d.loc[idx, col] = [_variante(v, rng) for v in d.loc[idx, col]]
        resumen.append(("Formato de texto", col, k, "mayúsculas/minúsculas y espacios sobrantes"))

    # 2. Sinónimos y escrituras alternativas de una misma categoría
    idx_us = filas(4, (df["Country"] == "United States").to_numpy())
    idx_uk = filas(3, (df["Country"] == "United Kingdom").to_numpy())
    d.loc[idx_us, "Country"], d.loc[idx_uk, "Country"] = "USA", "UK"
    resumen.append(("Sinónimos", "Country", 7, '"USA" y "UK" en lugar del nombre completo'))
    idx_hh = filas(5, (df["Genre"] == "Hip Hop").to_numpy())
    idx_kp = filas(5, (df["Genre"] == "K-pop").to_numpy())
    d.loc[idx_hh, "Genre"], d.loc[idx_kp, "Genre"] = "Hip-Hop", "KPOP"
    resumen.append(("Sinónimos", "Genre", 10, '"Hip-Hop" y "KPOP"'))

    # 3. Tipos incorrectos: números guardados como texto
    idx = filas(40)
    d.loc[idx, "Total Streams (Millions)"] = [f"{v:,.2f}" for v in df.loc[idx, "Total Streams (Millions)"]]
    resumen.append(("Tipo incorrecto", "Total Streams (Millions)", 40, 'separador de miles: "3,695.53"'))
    idx = filas(60)
    d.loc[idx, "Skip Rate (%)"] = [f"{v}%" for v in df.loc[idx, "Skip Rate (%)"]]
    resumen.append(("Tipo incorrecto", "Skip Rate (%)", 60, 'símbolo de porcentaje: "2.24%"'))

    # 4. Valores faltantes (vacíos y marcadores de texto como "N/A" o "-")
    for col, k, marca in [("Monthly Listeners (Millions)", 25, np.nan),
                          ("Skip Rate (%)", 15, np.nan),
                          ("Streams Last 30 Days (Millions)", 10, np.nan),
                          ("Avg Stream Duration (Min)", 5, "-"),
                          ("Country", 6, np.nan),
                          ("Genre", 4, "N/A")]:
        d.loc[filas(k), col] = marca
        resumen.append(("Faltante", col, k, "vacío" if marca is np.nan else f'marcador "{marca}"'))

    # 5. Duplicados exactos y duplicados que solo difieren en el formato
    exactos = d.loc[filas(12)]
    con_pais = d["Country"].notna() & ~d["Country"].isin(["USA", "UK"])
    casi = d.loc[filas(8, con_pais.to_numpy())].copy()
    casi["Country"] = casi["Country"].str.strip().str.upper()
    d = pd.concat([d, exactos, casi], ignore_index=True)
    resumen.append(("Duplicado", "fila completa", 12, "copia exacta de una fila"))
    resumen.append(("Duplicado", "fila completa", 8, "copia con el país en MAYÚSCULAS"))

    # Las filas añadidas se mezclan para que no queden al final del archivo
    d = d.sample(frac=1, random_state=semilla).reset_index(drop=True)
    resumen = pd.DataFrame(resumen, columns=["problema", "columna", "celdas o filas", "cómo se inyectó"])
    return d, resumen


if __name__ == "__main__":
    original = pd.read_csv(ORIGEN)
    sucio, resumen = ensuciar(original)
    DESTINO.parent.mkdir(exist_ok=True)
    sucio.to_csv(DESTINO, index=False)
    print(resumen.to_string(index=False))
    print(f"\n{len(original)} filas originales -> {len(sucio)} filas sucias en {DESTINO}")
