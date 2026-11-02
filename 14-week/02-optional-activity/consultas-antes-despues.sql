-- =============================================================================
-- Semana 14 · Optimización de una consulta SQL (opción A) — caso Spotify
-- Ciencia de Datos · CORHUILA · 2026-B · Julián Andrés Solano Ledesma
-- Base: datos/eventos.db (2 000 000 de eventos de reproducción, generada por optimizacion_sql.py)
-- Pregunta: ¿cuántas horas se escucharon en cada país en diciembre de 2025?
-- =============================================================================

-- ----------------------------------------------------------------- ANTES (lenta)
-- Problemas:
--   1. SELECT *: trae las 9 columnas de los dos lados del JOIN (7 + 2) aunque solo se usan 2.
--   2. strftime() sobre fecha_hora en el WHERE: se calcula fila por fila y el motor
--      no puede usar un índice sobre esa columna (filtro no "sargable").
--   3. Sin GROUP BY: devuelve 91 684 filas y la suma por país se hace en Python.
SELECT *
FROM   reproduccion r
JOIN   pais p ON p.country_id = r.country_id
WHERE  strftime('%Y-%m', r.fecha_hora) = '2025-12';

-- ----------------------------------------------------------------- DESPUÉS (rápida)
-- 1. Solo las columnas necesarias y la agregación dentro de la base (devuelve 20 filas).
-- 2. Filtro por RANGO sobre la columna sin transformar: [2025-12-01, 2026-01-01).
--    Funciona porque las fechas se guardan en ISO 8601 y su orden de texto es cronológico.
-- 3. Índice de cobertura: contiene las 3 columnas que la consulta usa, así que el motor
--    responde leyendo solo el índice, sin saltar a la tabla por cada fila.
CREATE INDEX idx_rep_fecha_cubre
    ON reproduccion (fecha_hora, country_id, segundos_escuchados);

SELECT p.nombre,
       ROUND(SUM(r.segundos_escuchados) / 3600.0, 1) AS horas
FROM   reproduccion r
JOIN   pais p ON p.country_id = r.country_id
WHERE  r.fecha_hora >= '2025-12-01'
  AND  r.fecha_hora <  '2026-01-01'
GROUP  BY p.nombre
ORDER  BY horas DESC;

-- Comprobación del plan (debe decir "SEARCH r USING COVERING INDEX idx_rep_fecha_cubre"):
EXPLAIN QUERY PLAN
SELECT p.nombre, ROUND(SUM(r.segundos_escuchados) / 3600.0, 1) AS horas
FROM   reproduccion r JOIN pais p ON p.country_id = r.country_id
WHERE  r.fecha_hora >= '2025-12-01' AND r.fecha_hora < '2026-01-01'
GROUP  BY p.nombre ORDER BY horas DESC;
