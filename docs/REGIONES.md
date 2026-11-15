# Cajas de estudio del MVP

**Decisión geográfica (14 de noviembre de 2026).** Fijamos tres cajas para contrastar áreas del norte y sur de México antes de examinar sus tendencias. Las coordenadas oficiales del proyecto están en [`config/study-boxes.json`](../config/study-boxes.json), en orden **oeste, sur, este, norte** (longitud y latitud en grados). El periodo de comparación previsto es 1992–2024.

| ID | Área de estudio | Caja [O, S, E, N] | Estado de los datos |
| --- | --- | --- | --- |
| `mx-northeast` | Noreste, caja de prueba actual | `[-101, 25, -99, 27]` | Series procesadas y conectadas a la interfaz. |
| `mx-chihuahua-interior` | Chihuahua interior | `[-107, 28, -105, 30]` | Siete series procesadas y conectadas a la interfaz. |
| `mx-south-humid` | Caja sur (Chiapas–Tabasco) | `[-94, 16, -92, 18]` | Siete series procesadas y conectadas a la interfaz. |

La caja de Chihuahua permite estudiar un entorno interior donde esperamos condiciones más secas; la del sur permite estudiar un entorno donde esperamos mayor precipitación. Son **hipótesis de contraste**, que se comprobarán con las mismas series climáticas antes de describir las diferencias entre cajas. [INEGI documenta la diversidad climática de Chihuahua y Tabasco](https://en.www.inegi.org.mx/contenidos/productos/prod_serv/contenidos/espanol/bvinegi/productos/nueva_estruc/889463921820.pdf).

## Verificación espacial inicial

- La [API regional mensual de NASA POWER](https://power.larc.nasa.gov/docs/services/api/temporal/monthly/) aceptó las dos cajas nuevas para `T2M` en 2010. Devolvió 20 centros de celda en Chihuahua y 15 en la caja sur. Una propuesta de 1,5° × 1° para Tabasco fue rechazada por la API: solicita al menos 2° de amplitud en cada eje.
- Los centros de celda devueltos para las dos cajas nuevas caen dentro de México según los límites estatales de Natural Earth guardados en `public/assets/region-states.json`. En la caja sur, 11 centros corresponden a Chiapas, tres a Tabasco y uno a Veracruz. Esta revisión de centros no equivale a recortar la superficie completa de cada celda.
- La caja actual del noreste intersecta Texas. Ninguna de las tres cajas representa un estado o una región administrativa completa. La caja sur incluye un gradiente de elevación considerable; por ello, los promedios espaciales requieren cautela.

## Regla para la comparación

Para habilitar una caja se necesitan sus archivos originales, cobertura mensual completa para el periodo elegido, metadatos de unidades y malla, una agregación espacial documentada y el resultado analítico por variable. Las series de la caja noreste **no se reutilizan** para las otras cajas. Cada variable procede del mismo producto y usa la misma definición en las tres; para POWER se conservan los valores por celda antes del promedio regional. Los CSV de Giovanni ya contienen el promedio espacial calculado por ese servicio. Las cajas efectivas de Giovanni, POWER y otros productos pueden diferir. La interfaz permite seleccionar cualquiera de las tres y recalcula el análisis con sus series propias.

## Rutas para procesar cada caja

Los scripts aceptan `--region` con uno de los tres ID de la tabla. El valor predeterminado `mx-northeast` conserva las rutas históricas (`data/raw/`, `data/processed/`, `data/results/`) que consume la interfaz. Para las dos cajas nuevas, los archivos se guardan en `data/raw/<id>/`, `data/processed/<id>/` y `data/results/<id>/`. Las descargas diarias quedan en `data/raw/<id>/power_daily_prectotcorr/`. Los análisis comprueban el ID y la caja de los metadatos de entrada antes de escribir el resultado regional.

Ejemplo para la caja de Chihuahua, con los mismos nombres de archivo que la caja actual pero en su subcarpeta:

```powershell
python scripts/power_t2m.py --region mx-chihuahua-interior --start 1992 --end 2024 --variable T2M
python scripts/analyze_t2m.py data/processed/mx-chihuahua-interior/power_t2m_region_1992_2024.csv data/results/mx-chihuahua-interior/power_t2m_region_1992_2024.json --region mx-chihuahua-interior
python scripts/power_daily_rain.py --region mx-chihuahua-interior --start 1992 --end 2024
python scripts/analyze_annual.py data/processed/mx-chihuahua-interior/power_rx5day_annual_region_1992_2024.csv data/results/mx-chihuahua-interior/power_rx5day_annual_region_1992_2024.json --region mx-chihuahua-interior
```

Para una exportación de Giovanni, primero se guarda el CSV original en `data/raw/mx-chihuahua-interior/giovanni/`. Después se ejecuta, por ejemplo:

```powershell
python scripts/normalize_giovanni.py data/raw/mx-chihuahua-interior/giovanni/gpcp_1992_2024.csv data/processed/mx-chihuahua-interior/giovanni_gpcp_1992_2024.csv data/processed/mx-chihuahua-interior/giovanni_gpcp_1992_2024.metadata.json --variable GPCPMON_3_3_sat_gauge_precip --region mx-chihuahua-interior
python scripts/analyze_power.py data/processed/mx-chihuahua-interior/giovanni_gpcp_1992_2024.csv data/results/mx-chihuahua-interior/giovanni_gpcp_1992_2024.json --product-source Giovanni --region mx-chihuahua-interior
```

Se sustituye el ID por `mx-south-humid` para la caja sur. Los scripts no descargan automáticamente Giovanni: requieren sus CSV originales. **Las dos cajas ya tienen** cuatro series mensuales POWER, las series mensuales GPCP y RX5Day de Giovanni, y el RX5day anual derivado de POWER, todas para 1992–2024. Cada serie mensual tiene 396 meses sin faltantes; el índice anual tiene 33 años. Los originales, archivos procesados y resultados están separados por ID de caja. Véase el [glosario](DATASETS.md) para las variables y fuentes.

Estas cajas son áreas de estudio del MVP. Las cinco regiones con polígonos planteadas para una versión posterior requieren otra decisión geográfica y un procesamiento espacial propio.
