# Semana 6 — ERD de tu caso

**Programa:** Ingeniería Industrial · **Asignatura:** Ciencia de Datos
**Unidad 2:** Modelamiento, transformación y conexión de datos · **Corte 2 · Semana 6** · **Periodo:** 2026-B
**Modalidad:** Individual/parejas · **Tipo:** Formativa (sin nota)

**Julián Andrés Solano Ledesma**

> Continuación del caso **Spotify — capacidad de streaming y curaduría regional** del Corte 1. Aquí se convierte el dataset de Kaggle *Spotify Global Streaming Data (2024)* [1] en un **modelo entidad-relación (ERD)**. El modelo tiene claves PK/FK y una relación N:M resuelta con una tabla intermedia. Además se justifica la decisión relacional frente a NoSQL y se muestra, con los datos reales, dónde se aplicó la normalización.

---

## 1. Punto de partida: qué debe responder el modelo

Modelar sin saber qué preguntas se responderán con los datos es un error común [2]. Por eso el ERD se deriva de la pregunta de negocio del Corte 1: *¿en qué países y en qué momentos aumentará la demanda de streaming, para escalar la infraestructura y priorizar el contenido por región?* El modelo debe permitir, como mínimo:

- sumar **streams y horas de escucha por país**, para la decisión de capacidad;
- identificar los **artistas y álbumes más escuchados por país**, para la decisión de curaduría;
- comparar el comportamiento por **género** y por **plan** (Free/Premium), por ejemplo el *skip rate*.

El dataset [1] es un archivo plano de **500 filas × 12 columnas**, sin celdas nulas ni filas duplicadas. Cada fila es una observación de métricas de un álbum en un país, para un plan y un género.

---

## 2. Diagrama entidad-relación (ERD)

![ERD del caso Spotify con 6 entidades, PK/FK y la relación N:M PAIS–ALBUM resuelta con METRICA_STREAMING](./diagrama-erd-spotify.svg)

*Fig. 1. ERD del caso Spotify en notación de pata de gallo. Diagrama generado con asistencia de inteligencia artificial (Claude, Anthropic), a partir del modelo diseñado en este documento.*

El modelo entidad-relación representa el dominio con **entidades**, sus **atributos** y las **relaciones** entre ellas [3]. Al pasarlo al modelo relacional, cada entidad se convierte en una tabla identificada por una **clave primaria (PK)**. Las tablas se enlazan mediante **claves foráneas (FK)**: columnas que toman sus valores de la PK de otra tabla [4].

### 2.1 Entidades

| Entidad | PK | FK | Atributos | Origen en el CSV |
|---|---|---|---|---|
| **PAIS** | `country_id` | Ninguna | `codigo_iso`, `nombre`, `region` | `Country` (20 valores). El código ISO y la región se agregan para analizar por zona |
| **ARTISTA** | `artist_id` | Ninguna | `nombre`, `genero_principal` | `Artist` (15 valores) |
| **ALBUM** | `album_id` | `artist_id` → ARTISTA | `titulo`, `anio_lanzamiento` | `Album`, `Release Year` (15 álbumes) |
| **GENERO** | `genero_id` | Ninguna | `nombre` | `Genre` (10 valores) |
| **PLAN_SUSCRIPCION** | `plan_id` | Ninguna | `nombre` | `Platform Type` (Free, Premium) |
| **METRICA_STREAMING** | `metric_id` | `country_id`, `album_id`, `genero_id`, `plan_id` | `oyentes_mensuales_m`, `streams_totales_m`, `horas_totales_m`, `duracion_prom_min`, `streams_30d_m`, `skip_rate_pct` | Las 6 columnas numéricas. **Tabla intermedia** de la relación N:M |

> **¿Por qué hay entidades sin FK?** Una FK existe solo cuando una tabla *depende* de otra. PAIS, ARTISTA, GENERO y PLAN_SUSCRIPCION son catálogos raíz: no referencian a nadie, y son las demás tablas las que los referencian [4].

### 2.2 Relaciones y cardinalidades

Cada cardinalidad se comprobó sobre los datos en [`normalizacion-spotify.ipynb`](./normalizacion-spotify.ipynb).

| Relación | Cardinalidad | Lectura | Evidencia en el CSV |
|---|---|---|---|
| ARTISTA — ALBUM | 1:N | Un artista publica álbumes; cada álbum tiene un solo artista | `Album → Artist` se cumple en los 15 álbumes. Hoy hay 1 álbum por artista, pero el modelo admite varios |
| ALBUM — METRICA_STREAMING | 1:N | Un álbum se mide en muchas observaciones | Cada álbum aparece en 14 a 19 países |
| PAIS — METRICA_STREAMING | 1:N | Un país registra muchas observaciones | Cada país tiene de 10 a 15 álbumes distintos |
| GENERO — METRICA_STREAMING | 1:N | Cada observación se clasifica en un género | 10 géneros repartidos en las 500 filas |
| PLAN_SUSCRIPCION — METRICA_STREAMING | 1:N | Cada observación pertenece a un plan | 2 planes: Free y Premium |
| **PAIS — ALBUM** | **N:M** | Un país escucha muchos álbumes y un álbum se escucha en muchos países | 244 combinaciones distintas país–álbum. **Se resuelve con METRICA_STREAMING** |

### 2.3 La relación N:M y su tabla intermedia

Una relación N:M no se puede guardar directamente en una tabla: se resuelve con una **tabla intermedia** [2]. En el modelo entidad-relación, la relación misma puede tener atributos propios, y al pasarla a tablas se convierte en una tabla con las claves de ambas entidades [3].

**METRICA_STREAMING** cumple ese papel:

- divide la relación PAIS ↔ ALBUM en dos relaciones 1:N (PAIS—METRICA y ALBUM—METRICA);
- guarda la FK de cada lado (`country_id`, `album_id`);
- guarda además los atributos que pertenecen a la *combinación* y no a una sola entidad: oyentes, streams, horas, duración y *skip rate*. Los streams de *Guts* en Brasil no son un dato del álbum ni del país, sino de los dos juntos.

**¿Por qué una clave sustituta (`metric_id`)?** La combinación natural (país, álbum, plan) se repite en **158 filas**, e incluso añadiendo el género quedan 26 repeticiones. Ninguna combinación de columnas identifica una fila de forma única. Por eso `metric_id` toma el número de fila del CSV original, lo que además permite rastrear cada registro hasta su fuente.

### 2.4 Esquema SQL

El script completo, con PK, FK, `UNIQUE` y `CHECK`, está en [`esquema-spotify.sql`](./esquema-spotify.sql). Este es el núcleo de la relación N:M:

```sql
CREATE TABLE album (
  album_id          INT          PRIMARY KEY,
  artist_id         INT          NOT NULL REFERENCES artista (artist_id),
  titulo            VARCHAR(150) NOT NULL,
  anio_lanzamiento  SMALLINT     NOT NULL CHECK (anio_lanzamiento BETWEEN 1900 AND 2100),
  UNIQUE (artist_id, titulo)
);

-- Tabla intermedia de la relación N:M  PAIS <-> ALBUM
CREATE TABLE metrica_streaming (
  metric_id      INT           PRIMARY KEY,             -- fila del CSV original
  country_id     INT           NOT NULL REFERENCES pais (country_id),
  album_id       INT           NOT NULL REFERENCES album (album_id),
  genero_id      INT           NOT NULL REFERENCES genero (genero_id),
  plan_id        SMALLINT      NOT NULL REFERENCES plan_suscripcion (plan_id),
  streams_30d_m  DECIMAL(10,2) NOT NULL CHECK (streams_30d_m >= 0),
  skip_rate_pct  DECIMAL(5,2)  NOT NULL CHECK (skip_rate_pct BETWEEN 0 AND 100)
  -- ... más las otras 4 medidas numéricas
);
```

---

## 3. ¿Relacional o NoSQL?

**Decisión: modelo relacional** (PostgreSQL en producción, SQLite para la validación local).

Las bases relacionales organizan los datos en tablas con esquema fijo e integridad, mientras que las NoSQL usan documentos o pares clave-valor con estructura flexible y escalan horizontalmente [2]. El modelo relacional separa la estructura lógica de los datos de su almacenamiento físico y expresa los vínculos entre tablas mediante claves [4]. Los sistemas NoSQL, en cambio, están pensados para repartir operaciones simples sobre muchos servidores y para admitir esquemas cambiantes. A cambio, suelen relajar las garantías de consistencia de las transacciones [5].

| Criterio | Relacional | NoSQL | Qué pide el caso |
|---|---|---|---|
| **Estructura del dato** | Esquema fijo y declarado [4] | Esquema flexible, cada documento puede variar [5] | 12 columnas estables, sin nulos y con tipos fijos → **relacional** |
| **Integridad** | PK, FK y restricciones `CHECK` | La aplicación debe garantizar la coherencia [5] | La normalización detectó años contradictorios (sección 4.3); las FK y los `CHECK` impiden que vuelva a pasar → **relacional** |
| **Consultas** | `JOIN` y agregaciones nativas | Acceso eficiente a un documento o clave completos [5] | Las preguntas del negocio son agregaciones por país, artista, género y plan → **relacional** |
| **Transacciones** | Propiedades ACID: atomicidad, consistencia, aislamiento y durabilidad [6] | Garantías más débiles a cambio de escalabilidad [5] | Una recarga del catálogo debe aplicarse completa o no aplicarse → **relacional** |
| **Escala** | Suficiente para miles o millones de filas en un servidor | Escalado horizontal en muchos nodos [5] | 500 filas y 6 tablas: no hay un problema de escala que justifique NoSQL |

En síntesis, los datos son **estructurados, estables y se consultan cruzando tablas**: es el escenario para el que fue diseñado el modelo relacional [4]. Elegir NoSQL sin necesidad es otro de los errores comunes del modelamiento [2]. NoSQL solo tendría sentido en una fase posterior, si se ingirieran los eventos individuales de reproducción en JSON a gran escala. Aun así, quedaría como capa de ingesta previa y no reemplazaría este modelo curado.

---

## 4. Normalización aplicada

La normalización organiza las tablas para que **cada dato viva en un solo lugar**, reduciendo la redundancia y los errores de actualización [2]. Su regla práctica es que todo atributo que no sea clave debe describir *la clave, toda la clave y nada más que la clave*. Cuando esto no se cumple aparecen la redundancia y las anomalías de actualización, inserción y borrado [7].

### 4.1 El punto de partida: una tabla plana

El CSV [1] guarda todo en una sola tabla. Los nombres de país, artista, álbum, género y plan se repiten en cada una de las 500 filas, es decir, **2 500 celdas de texto** para apenas **62 valores distintos**.

### 4.2 Dependencias funcionales encontradas en los datos

Antes de separar tablas se comprobó qué depende de qué. `X → Y` significa que cada valor de `X` tiene un único valor de `Y`. El resultado decide dónde vive cada atributo [7]:

| Dependencia | ¿Se cumple? | Consecuencia en el modelo |
|---|:---:|---|
| `Album → Artist` | Sí (15/15) | El artista se guarda una vez en ALBUM (`artist_id`) y no en cada fila |
| `Album → Release Year` | **No: cada álbum tiene 6 años distintos** | Es una anomalía. El año pertenece al álbum, así que se corrige y se guarda una sola vez en ALBUM (ver 4.3) |
| `Album → Genre` | No (9–10 géneros por álbum) | El género **no** es atributo del álbum: queda como FK en METRICA_STREAMING |
| `Artist → Genre` | No | Por eso `genero_principal` de ARTISTA queda vacío: los datos no asignan un género único por artista |
| `Album → Monthly Listeners` | No | Los oyentes son una medida de cada observación: se quedan en METRICA_STREAMING |

### 4.3 La anomalía que la normalización hace visible

En la tabla plana, el álbum *1989 (Taylor's Version)* aparece con los años 2018, 2019, 2020, 2021, 2022 y 2023, y **lo mismo ocurre con los 15 álbumes**. Es justamente la anomalía de actualización que describe la teoría: si un dato del álbum se copia en cada fila, nada impide que las copias se contradigan [7].

Al normalizar, el año pasa a vivir **una sola vez** en ALBUM, y la contradicción ya no puede repetirse. Para elegir ese único valor se aplicó una regla reproducible: el **año más frecuente** de cada álbum, y en caso de empate el menor. Es una decisión de limpieza documentada, no una verificación del año real. Ninguno de los 6 valores del archivo puede tomarse como cierto sin una fuente de catálogo. Del mismo modo, los géneros del CSV no siempre corresponden a la discografía real: Taylor Swift aparece, por ejemplo, como K-pop. El modelo representa lo que dicen los datos, sin corregirlos por fuera de ellos.

### 4.4 Formas normales aplicadas

| Forma normal | Qué exige [7] | Cómo se aplicó |
|---|---|---|
| **1FN** | Valores atómicos, sin listas ni grupos repetidos | El CSV ya la cumple: cada celda tiene un solo valor. Se conserva una observación por fila en METRICA_STREAMING |
| **2FN** | Ningún atributo depende solo de *una parte* de la clave | Del identificador natural (país, álbum, plan), el título, el artista y el año dependen **solo del álbum** → pasan a ALBUM. El nombre del país depende solo del país → pasa a PAIS |
| **3FN** | Sin dependencias transitivas entre atributos no clave | La cadena observación → álbum → artista se rompe: METRICA referencia al álbum, y el artista vive en ARTISTA, enlazado desde ALBUM. Género y plan pasan a sus propios catálogos |

### 4.5 Qué se evitó repetir

| Dato | Veces en el CSV plano | Vive solo en | Veces que se guarda | Se referencia por |
|---|---:|---|---:|---|
| Nombre del país | 500 | `pais` | 20 | `country_id` |
| Nombre del artista | 500 | `artista` | 15 | `artist_id` (desde `album`) |
| Título del álbum | 500 | `album` | 15 | `album_id` |
| Año de lanzamiento | 500 (con contradicciones) | `album` | 15 | `album_id` |
| Nombre del género | 500 | `genero` | 10 | `genero_id` |
| Tipo de plan | 500 | `plan_suscripcion` | 2 | `plan_id` |

Las 2 500 celdas de texto repetidas pasan a 62 valores, cada uno guardado una sola vez. METRICA_STREAMING conserva sus 500 filas, pero ya solo con FK numéricas y las 6 medidas.

### 4.6 Verificación con los datos

El cuaderno [`normalizacion-spotify.ipynb`](./normalizacion-spotify.ipynb) usa pandas [8] para separar las tablas y las carga en SQLite [9] con el esquema del ERD:

- **Integridad:** `PRAGMA foreign_key_check` reporta **0 violaciones**, y la FK rechaza una métrica que apunta a un álbum inexistente.
- **Descomposición sin pérdida:** al unir las 6 tablas con `JOIN` se reconstruyen **las 500 filas idénticas** al CSV original en las 11 columnas restantes. La única que cambia es `Release Year`, porque ahora tiene un valor por álbum. Normalizar quitó redundancia sin perder información.

| Tabla | Filas |
|---|---:|
| `pais` | 20 |
| `genero` | 10 |
| `plan_suscripcion` | 2 |
| `artista` | 15 |
| `album` | 15 |
| `metrica_streaming` | 500 |

---

## 5. Archivos de la entrega

```
06-week/02-optional-activity/
├── README.md                                  ← este documento
├── diagrama-erd-spotify.svg                   ← Fig. 1: ERD con PK/FK y la relación N:M
├── esquema-spotify.sql                        ← CREATE TABLE con PK, FK, UNIQUE y CHECK
├── normalizacion-spotify.ipynb                ← dependencias, normalización y validación
├── Spotify_2024_Global_Streaming_Data.csv     ← dataset original de Kaggle [2]
└── datos-normalizados/                        ← un CSV por tabla del modelo
    ├── pais.csv · genero.csv · plan_suscripcion.csv
    └── artista.csv · album.csv · metrica_streaming.csv
```

**Cómo reproducirlo**

```bash
pip install pandas jupyter
jupyter notebook normalizacion-spotify.ipynb   # ejecutar todas las celdas
```

---

## 6. Referencias (formato IEEE)

[1] A. Soundankar, "Spotify Global Streaming Data (2024)," Kaggle, 2024. [Online]. Disponible: https://www.kaggle.com/datasets/atharvasoundankar/spotify-global-streaming-data-2024

[2] Corporación Universitaria del Huila (CORHUILA), "Ciencia de Datos · Semana 6 · Modelamiento de datos," Objeto Virtual de Aprendizaje (OVA), Neiva, Colombia, 2026. [Online]. Disponible: https://code-corhuila.github.io/ova-web/2026-B/ciencia-datos/06-week/01-session/

[3] P. P.-S. Chen, "The entity-relationship model—Toward a unified view of data," *ACM Transactions on Database Systems*, vol. 1, no. 1, pp. 9–36, 1976, doi: 10.1145/320434.320440.

[4] E. F. Codd, "A relational model of data for large shared data banks," *Communications of the ACM*, vol. 13, no. 6, pp. 377–387, 1970, doi: 10.1145/362384.362685.

[5] R. Cattell, "Scalable SQL and NoSQL data stores," *ACM SIGMOD Record*, vol. 39, no. 4, pp. 12–27, 2011, doi: 10.1145/1978915.1978919.

[6] T. Haerder and A. Reuter, "Principles of transaction-oriented database recovery," *ACM Computing Surveys*, vol. 15, no. 4, pp. 287–317, 1983, doi: 10.1145/289.291.

[7] W. Kent, "A simple guide to five normal forms in relational database theory," *Communications of the ACM*, vol. 26, no. 2, pp. 120–125, 1983, doi: 10.1145/358024.358054.

[8] W. McKinney, "Data structures for statistical computing in Python," in *Proc. 9th Python in Science Conf. (SciPy)*, Austin, TX, USA, 2010, pp. 56–61, doi: 10.25080/Majora-92bf1922-00a.

[9] K. P. Gaffney, M. Prammer, L. Brasfield, D. R. Hipp, D. Kennedy, and J. M. Patel, "SQLite: Past, present, and future," *Proceedings of the VLDB Endowment*, vol. 15, no. 12, pp. 3535–3547, 2022, doi: 10.14778/3554821.3554842.
