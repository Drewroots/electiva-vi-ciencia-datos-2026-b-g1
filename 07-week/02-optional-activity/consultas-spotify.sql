-- =============================================================================
-- Semana 7 · Consultas SQL — caso Spotify (Spotify Global Streaming Data 2024, Kaggle)
-- Ciencia de Datos · CORHUILA · 2026-B · Julián Andrés Solano Ledesma
-- Motor: SQLite (ANSI SQL) · Esquema: ../../06-week/02-optional-activity/esquema-spotify.sql
-- Datos: datos/*.csv (tablas normalizadas de la Semana 6)
-- =============================================================================

-- Q1 · WHERE — ¿Qué registros combinan alta demanda reciente y alto abandono?
--      Filtra filas: más de 150 M de streams en 30 días Y skip rate mayor al 30 %.
SELECT metric_id,
       country_id,
       album_id,
       streams_30d_m,
       skip_rate_pct
FROM   metrica_streaming
WHERE  skip_rate_pct > 30
  AND  streams_30d_m > 150
ORDER  BY skip_rate_pct DESC;

-- Q2 · JOIN — ¿Qué combinaciones país–artista–álbum concentran la mayor demanda reciente?
--      Une 5 tablas por sus claves PK–FK; cada JOIN lleva su condición ON.
SELECT p.nombre        AS pais,
       ar.nombre       AS artista,
       al.titulo       AS album,
       ps.nombre       AS plan,
       m.streams_30d_m
FROM   metrica_streaming m
JOIN   pais             p  ON p.country_id = m.country_id
JOIN   album            al ON al.album_id  = m.album_id
JOIN   artista          ar ON ar.artist_id = al.artist_id
JOIN   plan_suscripcion ps ON ps.plan_id   = m.plan_id
ORDER  BY m.streams_30d_m DESC
LIMIT  10;

-- Q3 · GROUP BY — ¿Cuánta demanda reciente y cuánto abandono tiene cada país?
--      Agrupa las 500 observaciones en 20 países y agrega con COUNT, SUM y AVG.
SELECT p.nombre                         AS pais,
       COUNT(*)                         AS n_registros,
       ROUND(SUM(m.streams_30d_m), 2)   AS streams_30d_total_m,
       ROUND(AVG(m.streams_30d_m), 2)   AS streams_30d_prom_m,
       ROUND(AVG(m.skip_rate_pct), 2)   AS skip_rate_prom_pct
FROM   metrica_streaming m
JOIN   pais p ON p.country_id = m.country_id
GROUP  BY p.nombre
ORDER  BY streams_30d_total_m DESC;
