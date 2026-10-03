-- =============================================================================
-- Spotify · Streaming Global — Esquema relacional normalizado (3FN)
-- Ciencia de Datos · Semana 6 · Modelamiento de datos (CORHUILA, 2026-B)
-- Motor objetivo: PostgreSQL / SQLite (sintaxis ANSI; compatible con ambos)
-- Diagrama de referencia: diagrama-erd-spotify.svg
--
-- Parte A: núcleo transaccional del ERD (eventos de reproducción).
-- Parte B: extensión para cargar el CSV agregado de Kaggle
--          (dimensiones genero y plan_suscripcion + tabla de hechos agregada).
-- Las tablas pais, artista y album son compartidas por ambas partes.
-- =============================================================================

PRAGMA foreign_keys = ON;   -- SQLite; en PostgreSQL esta línea se omite.

-- ---------- PARTE A · Núcleo transaccional --------------------------------

CREATE TABLE pais (
  country_id  INT          PRIMARY KEY,
  codigo_iso  CHAR(2)      NOT NULL UNIQUE,
  nombre      VARCHAR(80)  NOT NULL UNIQUE,
  region      VARCHAR(40)  NOT NULL
);

CREATE TABLE dispositivo (
  device_id          SMALLINT    PRIMARY KEY,
  tipo               VARCHAR(30) NOT NULL,
  sistema_operativo  VARCHAR(30) NOT NULL,
  UNIQUE (tipo, sistema_operativo)
);

CREATE TABLE usuario (
  user_id         BIGINT      PRIMARY KEY,            -- seudonimizado
  country_id      INT         NOT NULL REFERENCES pais (country_id),
  fecha_registro  DATE        NOT NULL,
  tipo_plan       VARCHAR(20) NOT NULL
);

CREATE TABLE artista (
  artist_id         INT          PRIMARY KEY,
  nombre            VARCHAR(100) NOT NULL UNIQUE,
  genero_principal  VARCHAR(40)
);

CREATE TABLE album (
  album_id          INT          PRIMARY KEY,
  artist_id         INT          NOT NULL REFERENCES artista (artist_id),
  titulo            VARCHAR(150) NOT NULL,
  anio_lanzamiento  SMALLINT     CHECK (anio_lanzamiento BETWEEN 1900 AND 2100),
  UNIQUE (artist_id, titulo, anio_lanzamiento)
);

CREATE TABLE cancion (
  track_id      BIGINT       PRIMARY KEY,
  album_id      INT          NOT NULL REFERENCES album (album_id),
  titulo        VARCHAR(150) NOT NULL,
  duracion_seg  INT          NOT NULL CHECK (duracion_seg > 0)
);

-- Tabla intermedia de la relación N:M usuario <-> cancion
CREATE TABLE reproduccion (
  play_id              BIGINT    PRIMARY KEY,         -- clave sustituta
  user_id              BIGINT    NOT NULL REFERENCES usuario (user_id),
  track_id             BIGINT    NOT NULL REFERENCES cancion (track_id),
  device_id            SMALLINT  NOT NULL REFERENCES dispositivo (device_id),
  country_id           INT       NOT NULL REFERENCES pais (country_id),
  fecha_hora           TIMESTAMP NOT NULL,
  segundos_escuchados  INT       NOT NULL CHECK (segundos_escuchados >= 0)
);

CREATE INDEX idx_reproduccion_pais_fecha ON reproduccion (country_id, fecha_hora);

-- ---------- PARTE B · Extensión para el CSV agregado de Kaggle -------------

CREATE TABLE genero (
  genero_id  INT         PRIMARY KEY,
  nombre     VARCHAR(40) NOT NULL UNIQUE
);

CREATE TABLE plan_suscripcion (            -- "Platform Type" del CSV (p. ej. Free / Premium)
  plan_id  SMALLINT    PRIMARY KEY,
  nombre   VARCHAR(30) NOT NULL UNIQUE
);

-- Hechos agregados: una fila por observación país × álbum × plan del CSV.
-- Las medidas están en millones, como en la fuente.
CREATE TABLE metrica_streaming (
  metric_id            INT           PRIMARY KEY,
  country_id           INT           NOT NULL REFERENCES pais (country_id),
  album_id             INT           NOT NULL REFERENCES album (album_id),
  genero_id            INT           NOT NULL REFERENCES genero (genero_id),
  plan_id              SMALLINT      NOT NULL REFERENCES plan_suscripcion (plan_id),
  oyentes_mensuales_m  DECIMAL(10,2) NOT NULL CHECK (oyentes_mensuales_m >= 0),
  streams_totales_m    DECIMAL(10,2) NOT NULL CHECK (streams_totales_m >= 0),
  horas_totales_m      DECIMAL(10,2) NOT NULL CHECK (horas_totales_m >= 0),
  duracion_prom_min    DECIMAL(6,2)  NOT NULL CHECK (duracion_prom_min > 0),
  streams_30d_m        DECIMAL(10,2) NOT NULL CHECK (streams_30d_m >= 0),
  skip_rate_pct        DECIMAL(5,2)  NOT NULL CHECK (skip_rate_pct BETWEEN 0 AND 100)
);

CREATE INDEX idx_metrica_pais  ON metrica_streaming (country_id);
CREATE INDEX idx_metrica_album ON metrica_streaming (album_id);
