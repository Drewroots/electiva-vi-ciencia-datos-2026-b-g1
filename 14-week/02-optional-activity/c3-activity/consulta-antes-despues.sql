-- Actividad calificable · Corte 3 · Optimización SQL — caso Spotify
-- Indicador: horas escuchadas por mes en la temporada alta nov 2024 – abr 2025
-- Tabla: reproduccion (2 000 000 de eventos, generada por ../optimizacion_sql.py). Motor: SQLite.

-- ANTES: trae todas las columnas, aplica una función a la columna filtrada y suma en Python
SELECT *
FROM   reproduccion
WHERE  strftime('%Y-%m', fecha_hora) BETWEEN '2024-11' AND '2025-04';

-- DESPUÉS: índice de cobertura, filtro por rango sobre la columna sin transformar y agregación en SQL
CREATE INDEX idx_c3_cubre ON reproduccion (fecha_hora, segundos_escuchados);

SELECT substr(fecha_hora, 1, 7) AS mes,
       ROUND(SUM(segundos_escuchados) / 3600.0, 1) AS horas
FROM   reproduccion
WHERE  fecha_hora >= '2024-11-01' AND fecha_hora < '2025-05-01'
GROUP  BY mes
ORDER  BY mes;
