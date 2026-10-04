# Actividad calificable · Corte 2 — Modelo, consulta y limpieza de datos

**Programa:** Ingeniería Industrial · **Asignatura:** Ciencia de Datos · **Periodo:** 2026-B
**Unidad 2 · Semana 9** · **Entrega:** individual (fork del repositorio de la clase) · **Valor:** 5.0

> Caso de trabajo: **Spotify — capacidad de streaming y curaduría regional** (el mismo de los Cortes 1 y 2). Esta entrega diseña el ERD del caso, limpia el conjunto de datos de Kaggle [3] con pandas, mide la calidad **antes y después**, y responde dos preguntas con consultas en pandas y en SQL.

| Entregable | Archivo |
|---|---|
| ERD | [`diagrama-erd-corte2.svg`](diagrama-erd-corte2.svg) |
| Limpieza + consultas (cuaderno ejecutado) | [`limpieza-y-consultas.ipynb`](limpieza-y-consultas.ipynb) |
| Datos antes / después | [`data/spotify_raw.csv`](data/spotify_raw.csv) · [`data/spotify_limpio.csv`](data/spotify_limpio.csv) |

---

## 1. ERD de mi caso

![ERD del caso Spotify: ARTISTA, ALBUM, PAIS, GENERO, PLAN y METRICA_STREAMING](diagrama-erd-corte2.svg)

*Fig. 1. ERD en notación pata de gallo [4]. Diagrama generado con asistencia de inteligencia artificial (Claude, Anthropic).*

El modelo tiene **6 entidades**. Cinco son catálogos (quién, qué, dónde y bajo qué plan) y una es la tabla de hechos donde se registran las métricas de streaming.

| Entidad | PK | FK | Atributos | Rol |
|---|---|---|---|---|
| **ARTISTA** | `artist_id` | Ninguna (catálogo independiente) | `nombre` | Quién publica |
| **ALBUM** | `album_id` | `artist_id` → ARTISTA | `titulo`, `anio_lanzamiento` | Qué se escucha |
| **PAIS** | `country_id` | Ninguna (catálogo independiente) | `nombre` | Dónde se consume |
| **GENERO** | `genero_id` | Ninguna (catálogo independiente) | `nombre` | Clasificación musical |
| **PLAN** | `plan_id` | Ninguna (catálogo independiente) | `nombre` (Free / Premium) | Tipo de suscripción |
| **METRICA_STREAMING** | `metric_id` | `country_id`, `album_id`, `genero_id`, `plan_id` | `oyentes_mensuales_m`, `streams_totales_m`, `streams_30d_m`, `duracion_prom_min`, `skip_rate_pct`, `horas_esperadas_m` | Hechos: un segmento país × álbum × género × plan |

| Relación | Cardinalidad | Lectura |
|---|---|---|
| ARTISTA — ALBUM | **1:N** | Un artista publica muchos álbumes; cada álbum pertenece a un artista |
| ALBUM — METRICA_STREAMING | **1:N** | Un álbum tiene muchas métricas (una por país, género y plan) |
| PAIS — METRICA_STREAMING | **1:N** | Un país aparece en muchas métricas |
| GENERO — METRICA_STREAMING | **1:N** | Un género aparece en muchas métricas |
| PLAN — METRICA_STREAMING | **1:N** | Un plan aparece en muchas métricas |

**Coherencia del diseño.** Las FK evitan repetir textos (por ejemplo el nombre del país) en cada fila de hechos, y la restricción `UNIQUE (country_id, album_id, genero_id, plan_id)` garantiza una sola fila por segmento. El género va en la tabla de hechos y no en `ALBUM` porque, en estos datos, un mismo álbum aparece con varios géneros. El notebook carga el resultado limpio en estas seis tablas con PK, FK y `CHECK` (por ejemplo `streams_30d_m <= streams_totales_m`) [7] y confirma que no hay violaciones de FK.

---

## 2. Data & cleaning

*(English section — requirement of the activity.)*

The dataset is "Spotify Global Streaming Data (2024)" from Kaggle [3], a CSV with 500 rows and 12 columns that describe streaming metrics by country, artist, album, genre, release year and subscription plan (Free or Premium). I loaded it with pandas [5], measured its quality before touching it, and found no missing values and no exact duplicates, but I did find 26 rows that repeat the same country–album–genre–plan segment and 2 impossible rows where the last-30-days streams exceed the total streams. The cleaning renamed the columns to snake_case, converted the five text columns to the `category` type and the release year to `int16`, dropped the 2 impossible rows, and merged the 26 repeated segments by averaging their metrics, which reduced the data from 500 to 472 rows and the memory use from 170.5 KB to 32.8 KB. I also found that the "hours streamed" column behaves like minutes (it is roughly streams × minutes, not divided by 60), so I kept it only as a reference and added a corrected `horas_esperadas_m` column. The first question asked which countries concentrate the recent demand of Premium users: Italy, South Africa and Mexico lead, but together they hold only 21.9% of the 24,142.6 million Premium streams of the last 30 days, so demand is spread across many countries. The second question asked which genres are skipped the most in albums released since 2022: R&B (23.72%) and Pop (23.51%) are skipped the most, while K-pop (15.62%) and Indie (16.46%) are skipped the least, an 8-point gap that could guide regional curation.

---

## 3. Limpieza de datos: antes y después

La limpieza sigue las dimensiones de calidad del OVA de la Semana 9 (completitud, exactitud, consistencia, unicidad y vigencia) [1] y la idea de que cada fila sea una observación y cada columna una variable [6].

### 3.1 Comparación antes / después

| Indicador | Antes | Después |
|---|---:|---:|
| Filas | 500 | **472** |
| Columnas | 12 | 13 (+`horas_esperadas_m`) |
| Valores nulos | 0 | 0 |
| Duplicados exactos | 0 | 0 |
| Filas repetidas por segmento (país × álbum × género × plan) | 26 | **0** |
| Filas imposibles (streams 30 días > streams totales) | 2 | **0** |
| Celdas de texto con espacios sobrantes | 0 | 0 |
| Memoria | 170.5 KB | **32.8 KB** |

| Columna | Tipo antes | Tipo después |
|---|---|---|
| `pais`, `artista`, `album`, `genero`, `plan` | `str` | `category` |
| `anio_lanzamiento` | `int64` | `int16` |
| Métricas numéricas (6) | `float64` | `float64` |

### 3.2 Bitácora de transformaciones

| # | Dimensión | Paso | Resultado |
|---|---|---|---|
| 1 | Consistencia | Nombres de columna a `snake_case` | 12 columnas renombradas |
| 2 | Completitud | Nulos: imputar mediana (numéricas) o `Desconocido` (texto) | 0 nulos encontrados, 0 celdas modificadas |
| 3 | Consistencia | Quitar espacios y unificar formato (`plan` en Title) | 0 celdas con espacios |
| 4 | Consistencia | Corregir tipos | 5 columnas a `category`, año a `int16` |
| 5 | Unicidad | Duplicados exactos (`drop_duplicates`) | 0 eliminados |
| 6 | Exactitud | Reglas de rango y coherencia (`streams_30d ≤ streams_totales`, skip 0–100, duración > 0) | **2 filas eliminadas** |
| 7 | Unicidad | Una fila por segmento país × álbum × género × plan | **26 filas repetidas consolidadas** (promedio de métricas) |
| 8 | Exactitud | Unidad de la columna de horas | `horas_esperadas_m = streams × min / 60`; la original se conserva como `horas_reportadas_m` |

### 3.3 Decisiones y hallazgos de calidad

- **El archivo ya venía parcialmente limpio.** Se llama *Cleaned_…* y por eso no tenía nulos ni duplicados exactos; los pasos 2, 3 y 5 se dejaron aplicados (con resultado 0) para que el proceso sea reproducible con datos más sucios. Los cambios reales están en los pasos 4, 6, 7 y 8.
- **Repetidos por segmento.** Las 26 filas repetidas no eran copias exactas (las métricas diferían). Se trataron como observaciones repetidas del mismo segmento y se promediaron para evitar contar dos veces un segmento.
- **Inconsistencia de unidad.** La mediana de *horas / (streams × minutos)* es 0.998, es decir, la columna se comporta como minutos. Si fueran horas reales el cociente sería cercano a 1/60 ≈ 0.017. Por eso las consultas usan streams y skip rate, y no la columna de horas original.

---

## 4. Consultas y hallazgos

Ambas preguntas se resolvieron **dos veces** (pandas y SQL sobre las tablas del ERD) y el cuaderno comprueba con `assert` que los resultados coinciden [2].

### 4.1 Pregunta 1 — ¿Qué países concentran la demanda reciente de usuarios Premium?

Filtro: `plan = 'Premium'`. Agregación: suma de `streams_30d_m` por país (demanda reciente, relevante para la capacidad de servidores del caso).

```python
(df[df["plan"] == "Premium"]
   .groupby("pais", observed=True)["streams_30d_m"].sum()
   .sort_values(ascending=False).head(5))
```

```sql
SELECT p.nombre AS pais, ROUND(SUM(m.streams_30d_m), 2) AS streams_30d_m
FROM metrica_streaming m
JOIN pais p  ON p.country_id = m.country_id
JOIN plan pl ON pl.plan_id   = m.plan_id
WHERE pl.nombre = 'Premium'
GROUP BY p.nombre
ORDER BY streams_30d_m DESC
LIMIT 5;
```

| # | País | Streams últimos 30 días (millones) |
|---:|---|---:|
| 1 | Italy | 1,901.34 |
| 2 | South Africa | 1,688.34 |
| 3 | Mexico | 1,685.91 |
| 4 | United Kingdom | 1,550.61 |
| 5 | Brazil | 1,429.94 |

**Hallazgo.** Italia lidera con 1,901 M de streams Premium en 30 días, pero la demanda **no está concentrada**: los tres primeros países suman 5,275.6 M de 24,142.6 M (**21.9 %**) entre 20 países. Para la decisión de capacidad esto sugiere repartir la inversión en CDN entre varias regiones en lugar de reforzar un solo país.

### 4.2 Pregunta 2 — ¿Qué géneros se saltan más los oyentes en lanzamientos recientes?

Filtro: `anio_lanzamiento >= 2022`. Agregación: promedio de `skip_rate_pct` y conteo de segmentos por género.

```python
(df[df["anio_lanzamiento"] >= 2022]
   .groupby("genero", observed=True)
   .agg(skip_rate_prom=("skip_rate_pct", "mean"), segmentos=("skip_rate_pct", "size"))
   .sort_values("skip_rate_prom", ascending=False))
```

```sql
SELECT g.nombre AS genero,
       ROUND(AVG(m.skip_rate_pct), 2) AS skip_rate_prom,
       COUNT(*) AS segmentos
FROM metrica_streaming m
JOIN genero g ON g.genero_id = m.genero_id
JOIN album a  ON a.album_id  = m.album_id
WHERE a.anio_lanzamiento >= 2022
GROUP BY g.nombre
ORDER BY skip_rate_prom DESC;
```

| Género | Skip rate promedio (%) | Segmentos |
|---|---:|---:|
| R&B | 23.72 | 11 |
| Pop | 23.51 | 18 |
| Rock | 22.18 | 25 |
| Hip Hop | 21.82 | 21 |
| Jazz | 21.65 | 18 |
| EDM | 20.94 | 19 |
| Reggaeton | 20.55 | 21 |
| Classical | 18.52 | 25 |
| Indie | 16.46 | 19 |
| K-pop | 15.62 | 15 |

**Hallazgo.** El promedio general en lanzamientos recientes es 20.45 %. R&B y Pop se saltan unos 3 puntos por encima del promedio, y K-pop e Indie unos 4–5 puntos por debajo: la brecha entre extremos es de **8.1 puntos porcentuales**. Para la curaduría regional, K-pop e Indie retienen mejor al oyente y son candidatos a destacarse en las listas de lanzamientos.

### 4.3 Limitaciones

- Los segmentos por género son pocos (11 a 25), y las diferencias no se probaron estadísticamente; el hallazgo es descriptivo, no concluyente.
- El conjunto de Kaggle es agregado y tiene 15 artistas y 15 álbumes; no permite concluir sobre el catálogo completo de la plataforma.
- Hay asociaciones de género poco realistas (por ejemplo, un artista de pop aparece con el género K-pop), lo que sugiere que el campo `genero` es ruidoso; las conclusiones por género deben leerse con cautela.

---

## 5. Cómo reproducirlo

```bash
pip install pandas jupyter
jupyter notebook limpieza-y-consultas.ipynb   # ejecutar todas las celdas
```

El cuaderno lee `data/spotify_raw.csv`, escribe `data/spotify_limpio.csv` y no necesita conexión a internet.

---

## 6. Referencias (formato IEEE)

[1] Corporación Universitaria del Huila (CORHUILA), "Ciencia de Datos · Semana 9 · Transformación y calidad de datos," Objeto Virtual de Aprendizaje (OVA), Neiva, Colombia, 2026. [Online]. Disponible: https://code-corhuila.github.io/ova-web/2026-B/ciencia-datos/09-week/01-session/

[2] Corporación Universitaria del Huila (CORHUILA), "Ciencia de Datos · Semana 7 · Herramientas y lenguajes (SQL, NoSQL, Python)," Objeto Virtual de Aprendizaje (OVA), Neiva, Colombia, 2026. [Online]. Disponible: https://code-corhuila.github.io/ova-web/2026-B/ciencia-datos/07-week/01-session/

[3] A. Soundankar, "Spotify Global Streaming Data (2024)," Kaggle, 2024. [Online]. Disponible: https://www.kaggle.com/datasets/atharvasoundankar/spotify-global-streaming-data-2024

[4] A. Watt and N. Eng, "Chapter 8: The Entity Relationship Data Model," in *Database Design*, 2nd ed. Victoria, BC, Canada: BCcampus, 2014. [Online]. Disponible: https://opentextbc.ca/dbdesign01/chapter/chapter-8-entity-relationship-model/

[5] W. McKinney, "Data structures for statistical computing in Python," in *Proc. 9th Python in Science Conf. (SciPy 2010)*, Austin, TX, USA, 2010, pp. 56–61, doi: 10.25080/Majora-92bf1922-00a. [Online]. Disponible: https://proceedings.scipy.org/articles/Majora-92bf1922-00a

[6] H. Wickham, "Tidy data," *J. Stat. Softw.*, vol. 59, no. 10, pp. 1–23, 2014, doi: 10.18637/jss.v059.i10. [Online]. Disponible: https://www.jstatsoft.org/article/view/v059i10

[7] A. Watt and N. Eng, "Chapter 9: Integrity Rules and Constraints," in *Database Design*, 2nd ed. Victoria, BC, Canada: BCcampus, 2014. [Online]. Disponible: https://opentextbc.ca/dbdesign01/chapter/chapter-9-integrity-rules-and-constraints/
