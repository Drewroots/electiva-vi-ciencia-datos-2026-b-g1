-- =============================================================================
-- Spotify · Streaming Global 2024 — Esquema relacional normalizado (3FN)
-- Ciencia de Datos · Semana 6 · ERD de tu caso (CORHUILA, 2026-B)
-- Fuente: Spotify_2024_Global_Streaming_Data.csv (Kaggle, 500 filas × 12 columnas)
-- Motor: SQLite / PostgreSQL (sintaxis ANSI)   ·   Diagrama: diagrama-erd-spotify.svg
--
-- Relación N:M  PAIS <-> ALBUM  resuelta con la tabla intermedia METRICA_STREAMING.
-- =============================================================================

PRAGMA foreign_keys = ON;   -- SQLite; en PostgreSQL esta línea se omite.

-- ---------- Catálogos (no dependen de otra tabla) ---------------------------

CREATE TABLE pais (
  country_id  INT          PRIMARY KEY,
  codigo_iso  CHAR(2)      NOT NULL UNIQUE,
  nombre      VARCHAR(80)  NOT NULL UNIQUE,      -- "Country" del CSV
  region      VARCHAR(40)  NOT NULL
);

CREATE TABLE genero (
  genero_id  INT          PRIMARY KEY,
  nombre     VARCHAR(40)  NOT NULL UNIQUE        -- "Genre" del CSV
);

CREATE TABLE plan_suscripcion (
  plan_id  SMALLINT     PRIMARY KEY,
  nombre   VARCHAR(30)  NOT NULL UNIQUE          -- "Platform Type": Free / Premium
);

CREATE TABLE artista (
  artist_id         INT           PRIMARY KEY,
  nombre            VARCHAR(100)  NOT NULL UNIQUE,  -- "Artist" del CSV
  genero_principal  VARCHAR(40)                     -- vacío: el CSV no asigna un género único por artista
);

-- ---------- Álbum: depende de artista (1:N) ---------------------------------

CREATE TABLE album (
  album_id          INT           PRIMARY KEY,
  artist_id         INT           NOT NULL REFERENCES artista (artist_id),
  titulo            VARCHAR(150)  NOT NULL,         -- "Album" del CSV
  anio_lanzamiento  SMALLINT      NOT NULL CHECK (anio_lanzamiento BETWEEN 1900 AND 2100),
  UNIQUE (artist_id, titulo)
);

-- ---------- Tabla intermedia de la relación N:M PAIS <-> ALBUM --------------
-- Una fila = una observación del CSV (metric_id = número de fila en la fuente).
-- Se usa clave sustituta porque (país, álbum, plan) se repite 158 veces en el CSV.
-- Medidas en millones, como en la fuente.

CREATE TABLE metrica_streaming (
  metric_id            INT            PRIMARY KEY,
  country_id           INT            NOT NULL REFERENCES pais (country_id),
  album_id             INT            NOT NULL REFERENCES album (album_id),
  genero_id            INT            NOT NULL REFERENCES genero (genero_id),
  plan_id              SMALLINT       NOT NULL REFERENCES plan_suscripcion (plan_id),
  oyentes_mensuales_m  DECIMAL(10,2)  NOT NULL CHECK (oyentes_mensuales_m >= 0),
  streams_totales_m    DECIMAL(10,2)  NOT NULL CHECK (streams_totales_m >= 0),
  horas_totales_m      DECIMAL(10,2)  NOT NULL CHECK (horas_totales_m >= 0),
  duracion_prom_min    DECIMAL(6,2)   NOT NULL CHECK (duracion_prom_min > 0),
  streams_30d_m        DECIMAL(10,2)  NOT NULL CHECK (streams_30d_m >= 0),
  skip_rate_pct        DECIMAL(5,2)   NOT NULL CHECK (skip_rate_pct BETWEEN 0 AND 100)
);

CREATE INDEX idx_metrica_pais  ON metrica_streaming (country_id);
CREATE INDEX idx_metrica_album ON metrica_streaming (album_id);
