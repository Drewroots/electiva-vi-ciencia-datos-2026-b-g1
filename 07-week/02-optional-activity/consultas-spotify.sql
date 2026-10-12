-- Semana 7 · Consultas SQL y pandas — Caso Spotify (Kaggle, 2024)
-- Motor: SQLite (compatible con ANSI SQL). Esquema: ../06-week/esquema-spotify.sql
-- Autor: Julián Andrés Solano Ledesma · CORHUILA · 2026-B

-- Q1 · WHERE — Registros de alto volumen y alto abandono (riesgo para la curación)
SELECT metric_id, country_id, streams_30d_m, skip_rate_pct
FROM   metrica_streaming
WHERE  skip_rate_pct > 30
  AND  streams_30d_m > 150
ORDER  BY skip_rate_pct DESC;

-- Q2 · JOIN — Top 10 combinaciones país–artista por streams de los últimos 30 días
SELECT p.nombre AS pais, ar.nombre AS artista, al.titulo AS album, m.streams_30d_m
FROM   metrica_streaming m
JOIN   pais    p  ON p.country_id = m.country_id
JOIN   album   al ON al.album_id  = m.album_id
JOIN   artista ar ON ar.artist_id = al.artist_id
ORDER  BY m.streams_30d_m DESC
LIMIT  10;

-- Q3 · GROUP BY — Capacidad (streams 30 d) y abandono promedio por país
SELECT country_id,
       COUNT(*)                        AS n_registros,
       ROUND(SUM(streams_30d_m), 2)    AS streams_30d_total_m,
       ROUND(AVG(skip_rate_pct), 2)    AS skip_rate_prom_pct
FROM   metrica_streaming
GROUP  BY country_id
ORDER  BY skip_rate_prom_pct DESC;
