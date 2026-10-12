# Semana 7 — Consultas SQL y pandas

**Programa:** Ingeniería Industrial · **Asignatura:** Ciencia de Datos
**Unidad 2:** Modelamiento, transformación y conexión de datos · **Corte 2 · Semana 7** · **Periodo:** 2026-B
**Modalidad:** Individual/parejas · **Tipo:** Formativa (sin nota)

**Julián Andrés Solano Ledesma**

> Continuación del caso **Spotify — capacidad de streaming y curaduría regional**. Sobre el modelo normalizado de la [Semana 6](../../06-week/02-optional-activity/README.md), construido a partir del dataset *Spotify Global Streaming Data (2024)* de Kaggle [2], se escriben **tres consultas SQL**: una con `WHERE`, una con `JOIN` y una con `GROUP BY`. La consulta de agregación se reproduce en **pandas** y se explica qué responde cada una.

---

## 1. Herramientas y datos

**SQL** es el lenguaje para consultar bases relacionales. Con pocas cláusulas se resuelve la mayoría de preguntas: `WHERE` filtra filas, `JOIN` combina tablas por sus claves y `GROUP BY` agrupa para agregar con `COUNT`, `SUM` o `AVG` [1]. Nació como un lenguaje *declarativo*: el usuario describe qué datos quiere, no cómo recorrerlos [4]. El sistema elige por su cuenta la forma más eficiente de ejecutar la consulta [9]. Las uniones se apoyan en el modelo relacional, donde las tablas se vinculan mediante claves [3].

**pandas** es la librería de Python para datos tabulares: carga CSV, Excel o SQL y permite filtrar, agrupar y analizar con pocas líneas [1]. Su estructura central es el `DataFrame`, una tabla en memoria con columnas etiquetadas [5]. Su operación `groupby` sigue la estrategia *dividir–aplicar–combinar*: separa los datos en grupos, aplica una función a cada uno y une los resultados [6].

**Motor:** SQLite en memoria, una base de datos embebida que no necesita servidor y se ejecuta dentro del propio proceso de Python [7]. Las tablas se cargan con el esquema de la Semana 6, con sus PK, FK y `CHECK`.

| Tabla | Filas | Papel en las consultas |
|---|---:|---|
| `metrica_streaming` | 500 | Tabla de hechos: `streams_30d_m`, `skip_rate_pct` y las FK a país, álbum, género y plan |
| `pais` | 20 | Nombre y región del país |
| `album` | 15 | Título del álbum y FK al artista |
| `artista` | 15 | Nombre del artista |
| `plan_suscripcion` | 2 | Free / Premium |

**Revisión previa:** antes de consultar se comprobaron los tipos y los nulos, porque analizar sin revisarlos es un error común [1]. Las 6 tablas tienen **0 nulos** y las medidas están en `float64`.

![Tres consultas SQL sobre el modelo de la Semana 6 y su equivalente en pandas](./diagrama-consultas.svg)

*Fig. 1. De las tablas a las respuestas. Diagrama generado con asistencia de inteligencia artificial (Claude, Anthropic), a partir de las consultas y resultados de este documento.*

---

## 2. Consultas SQL

Las tres consultas están en [`consultas-spotify.sql`](./consultas-spotify.sql). El cuaderno [`consultas-sql-pandas.ipynb`](./consultas-sql-pandas.ipynb) las lee directamente de ese archivo y las ejecuta.

### Q1 · `WHERE` — filtrar filas

```sql
SELECT metric_id, country_id, album_id, streams_30d_m, skip_rate_pct
FROM   metrica_streaming
WHERE  skip_rate_pct > 30
  AND  streams_30d_m > 150
ORDER  BY skip_rate_pct DESC;
```

**Qué responde:** ¿qué registros país–álbum tienen **a la vez** alta demanda reciente (más de 150 M de streams en 30 días) y alto abandono (*skip rate* mayor al 30 %)?

**Resultado:** **24 de 500 registros (4,8 %)**. El de mayor abandono es el registro 14, *SOS* de SZA en Germany, con **39,14 %** de *skip* y 163,39 M de streams.

**Para qué sirve:** son los puntos donde mucha gente escucha pero abandona pronto. Ahí la **curaduría regional** puede actuar primero: revisar en qué playlists y en qué posición aparece ese contenido.

### Q2 · `JOIN` — combinar tablas por sus claves

```sql
SELECT p.nombre AS pais, ar.nombre AS artista, al.titulo AS album,
       ps.nombre AS plan, m.streams_30d_m
FROM   metrica_streaming m
JOIN   pais             p  ON p.country_id = m.country_id
JOIN   album            al ON al.album_id  = m.album_id
JOIN   artista          ar ON ar.artist_id = al.artist_id
JOIN   plan_suscripcion ps ON ps.plan_id   = m.plan_id
ORDER  BY m.streams_30d_m DESC
LIMIT  10;
```

**Qué responde:** ¿qué combinaciones país–artista–álbum concentran más streams en los últimos 30 días?

La tabla de hechos solo guarda claves numéricas, porque así lo dejó la normalización. El `JOIN` recupera los nombres siguiendo cada relación PK–FK del ERD [3]. Cada `JOIN` lleva su condición `ON`: si se olvida, el resultado es un producto cartesiano con todas las combinaciones posibles [1].

**Resultado (top 5 de 10):**

| # | País | Artista | Álbum | Plan | Streams 30 d (M) |
|---:|---|---|---|---|---:|
| 1 | Italy | Taylor Swift | *1989 (Taylor's Version)* | Free | 200,00 |
| 2 | Brazil | Ed Sheeran | *Autumn Variations* | Free | 199,91 |
| 3 | Argentina | Ariana Grande | *Eternal Sunshine* | Free | 198,06 |
| 4 | India | BTS | *Proof* | Premium | 197,84 |
| 5 | South Korea | SZA | *SOS* | Premium | 197,83 |

**Para qué sirve:** muestra qué contenido destacar en cada mercado. De los 10 registros con más demanda, **8 son del plan Free**, una pista para Marketing sobre dónde están los oyentes que podrían pasar a Premium.

### Q3 · `GROUP BY` — agrupar y agregar

```sql
SELECT p.nombre                       AS pais,
       COUNT(*)                       AS n_registros,
       ROUND(SUM(m.streams_30d_m), 2) AS streams_30d_total_m,
       ROUND(AVG(m.streams_30d_m), 2) AS streams_30d_prom_m,
       ROUND(AVG(m.skip_rate_pct), 2) AS skip_rate_prom_pct
FROM   metrica_streaming m
JOIN   pais p ON p.country_id = m.country_id
GROUP  BY p.nombre
ORDER  BY streams_30d_total_m DESC;
```

**Qué responde:** ¿cuánta demanda reciente acumula cada país y cuánto abandono promedio tiene?

`GROUP BY` reduce las 500 observaciones a una fila por país. Cada función de agregado resume su grupo en un solo valor: `COUNT` cuenta, `SUM` suma y `AVG` promedia [8].

**Resultado (top 5 de 20 países):**

| País | Registros | Streams 30 d total (M) | Promedio por registro (M) | Skip prom. (%) |
|---|---:|---:|---:|---:|
| Italy | 34 | 3 227,25 | 94,92 | 22,37 |
| South Korea | 31 | 3 171,34 | 102,30 | 20,97 |
| Brazil | 30 | 3 063,11 | 102,10 | 20,59 |
| South Africa | 32 | 3 024,99 | 94,53 | 22,07 |
| Sweden | 30 | 3 023,20 | 100,77 | 21,79 |

**Cómo leerlo:**

- **Italy** lidera la demanda total, que es lo que importa para la **capacidad de servidores** de la pregunta de negocio. Pero buena parte de esa ventaja viene de tener más registros (34): la correlación entre número de registros y demanda total es de **0,94**.
- Por eso la consulta incluye también el **promedio por registro**, que lidera **United Kingdom** con 110,70 M. Comparar solo sumas favorecería a los países con más filas en el dataset.
- El *skip rate* promedio solo varía entre **16,06 % (Germany) y 23,03 % (Indonesia)**. El abandono por sí solo no distingue a un mercado de otro.

---

## 3. Equivalente en pandas de la consulta `GROUP BY`

```python
m = pd.read_csv("datos/metrica_streaming.csv")
p = pd.read_csv("datos/pais.csv")

q3_pandas = (
    m.merge(p, on="country_id")                       # JOIN pais
     .groupby("nombre")                               # GROUP BY p.nombre
     .agg(n_registros=("metric_id", "count"),         # COUNT(*)
          streams_30d_total_m=("streams_30d_m", "sum"),
          streams_30d_prom_m=("streams_30d_m", "mean"),
          skip_rate_prom_pct=("skip_rate_pct", "mean"))
     .round(2)                                        # ROUND(..., 2)
     .sort_values("streams_30d_total_m", ascending=False)   # ORDER BY ... DESC
     .reset_index()
     .rename(columns={"nombre": "pais"})
)
```

`groupby("nombre")` divide los datos por país, `agg` aplica `count`, `sum` y `mean` a cada grupo, y pandas une los resultados en una sola tabla: es la estrategia *dividir–aplicar–combinar* [6].

**Verificación por código:** `pd.testing.assert_frame_equal(q3_sql, q3_pandas)` confirma que SQL y pandas devuelven **el mismo resultado en los 20 países y las 5 columnas**.

| SQL | pandas |
|---|---|
| `JOIN ... ON` | `merge(..., on=...)` |
| `WHERE` | filtro booleano: `m[m["skip_rate_pct"] > 30]` |
| `GROUP BY` | `groupby(...)` |
| `COUNT` / `SUM` / `AVG` | `count` / `sum` / `mean` dentro de `agg` |
| `ORDER BY ... DESC` | `sort_values(..., ascending=False)` |

**¿Cuándo usar cada uno?** Si los datos viven en una base relacional, conviene filtrar y agrupar en SQL antes de traerlos a Python. Así el motor optimiza la consulta [9] y no se transfiere la tabla completa, que es otro error común [1]. pandas conviene cuando el análisis continúa en Python, por ejemplo con limpieza, gráficos o modelos.

---

## 4. Limitaciones

- El dataset [2] tiene 500 filas **agregadas** por país, álbum, plan y género, sin usuarios individuales. Los resultados describen patrones de mercado, no el comportamiento de una persona.
- Los umbrales de Q1 (30 % y 150 M) son criterios de ejemplo para el caso, no estándares de la industria.

---

## 5. Archivos de la entrega

```
07-week/02-optional-activity/
├── README.md                    ← este documento
├── diagrama-consultas.svg       ← Fig. 1: consultas, resultados y equivalente en pandas
├── consultas-spotify.sql        ← Q1 (WHERE), Q2 (JOIN), Q3 (GROUP BY)
├── consultas-sql-pandas.ipynb   ← ejecución en SQLite + réplica en pandas + verificación
└── datos/                       ← tablas normalizadas de la Semana 6 (6 CSV)
```

**Cómo reproducirlo**

```bash
pip install pandas jupyter
jupyter notebook consultas-sql-pandas.ipynb   # ejecutar todas las celdas
```

El cuaderno carga el esquema desde `../../06-week/02-optional-activity/esquema-spotify.sql`, así que debe ejecutarse desde esta carpeta del repositorio.

---

## 6. Referencias (formato IEEE)

[1] Corporación Universitaria del Huila (CORHUILA), "Ciencia de Datos · Semana 7 · Herramientas y lenguajes (SQL, NoSQL, Python)," Objeto Virtual de Aprendizaje (OVA), Neiva, Colombia, 2026. [Online]. Disponible: https://code-corhuila.github.io/ova-web/2026-B/ciencia-datos/07-week/01-session/

[2] A. Soundankar, "Spotify Global Streaming Data (2024)," Kaggle, 2024. [Online]. Disponible: https://www.kaggle.com/datasets/atharvasoundankar/spotify-global-streaming-data-2024

[3] E. F. Codd, "A relational model of data for large shared data banks," *Communications of the ACM*, vol. 13, no. 6, pp. 377–387, 1970, doi: 10.1145/362384.362685.

[4] D. D. Chamberlin and R. F. Boyce, "SEQUEL: A structured English query language," in *Proc. 1974 ACM SIGFIDET Workshop on Data Description, Access and Control*, Ann Arbor, MI, USA, 1974, pp. 249–264, doi: 10.1145/800296.811515.

[5] W. McKinney, "Data structures for statistical computing in Python," in *Proc. 9th Python in Science Conf. (SciPy)*, Austin, TX, USA, 2010, pp. 56–61, doi: 10.25080/Majora-92bf1922-00a.

[6] H. Wickham, "The split-apply-combine strategy for data analysis," *Journal of Statistical Software*, vol. 40, no. 1, pp. 1–29, 2011, doi: 10.18637/jss.v040.i01.

[7] K. P. Gaffney, M. Prammer, L. Brasfield, D. R. Hipp, D. Kennedy, and J. M. Patel, "SQLite: Past, present, and future," *Proceedings of the VLDB Endowment*, vol. 15, no. 12, pp. 3535–3547, 2022, doi: 10.14778/3554821.3554842.

[8] J. Gray *et al.*, "Data cube: A relational aggregation operator generalizing group-by, cross-tab, and sub-totals," *Data Mining and Knowledge Discovery*, vol. 1, no. 1, pp. 29–53, 1997, doi: 10.1023/A:1009726021843.

[9] P. G. Selinger, M. M. Astrahan, D. D. Chamberlin, R. A. Lorie, and T. G. Price, "Access path selection in a relational database management system," in *Proc. 1979 ACM SIGMOD Int. Conf. Management of Data*, Boston, MA, USA, 1979, pp. 23–34, doi: 10.1145/582095.582099.
