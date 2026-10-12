-- =============================================================================
-- Semana 10 · Mini-proyecto (cierre del Corte 2) — consultas de análisis
-- Ciencia de Datos · CORHUILA · 2026-B · Julián Andrés Solano Ledesma
-- Base: datos/spotify.db (generada por pipeline_spotify.py con el esquema de la Semana 6)
-- Cada consulta combina un FILTRO (WHERE) con una AGREGACIÓN (GROUP BY).
-- =============================================================================

-- Q1 · Capacidad — En el plan Premium, ¿qué regiones concentran la demanda de los últimos 30 días?
--      Filtro: plan = 'Premium'   ·   Agregación: SUM por región, % del total y promedio por país.
SELECT p.region,
       COUNT(DISTINCT p.country_id)                       AS paises,
       COUNT(*)                                           AS registros,
       ROUND(SUM(m.streams_30d_m), 2)                     AS streams_30d_total_m,
       ROUND(100.0 * SUM(m.streams_30d_m) /
             SUM(SUM(m.streams_30d_m)) OVER (), 1)        AS participacion_pct,
       ROUND(SUM(m.streams_30d_m) /
             COUNT(DISTINCT p.country_id), 2)             AS streams_30d_por_pais_m
FROM   metrica_streaming m
JOIN   pais             p  ON p.country_id = m.country_id
JOIN   plan_suscripcion ps ON ps.plan_id   = m.plan_id
WHERE  ps.nombre = 'Premium'
GROUP  BY p.region
ORDER  BY streams_30d_total_m DESC;

-- Q2 · Curaduría — En Latinoamérica, ¿qué artistas acumulan más demanda reciente,
--      con cuánto abandono y qué género les asigna MusicBrainz (API, Semana 8)?
--      Filtro: región = 'Latinoamérica'   ·   Agregación: SUM y AVG por artista.
SELECT ar.nombre                         AS artista,
       ar.genero_principal               AS genero_musicbrainz,
       COUNT(*)                          AS registros,
       ROUND(SUM(m.streams_30d_m), 2)    AS streams_30d_total_m,
       ROUND(AVG(m.skip_rate_pct), 2)    AS skip_rate_prom_pct
FROM   metrica_streaming m
JOIN   pais    p  ON p.country_id = m.country_id
JOIN   album   al ON al.album_id  = m.album_id
JOIN   artista ar ON ar.artist_id = al.artist_id
WHERE  p.region = 'Latinoamérica'
GROUP  BY ar.nombre, ar.genero_principal
ORDER  BY streams_30d_total_m DESC;
