# Cajas de estudio del MVP

**Decisión geográfica (14 de noviembre de 2026).** Fijamos tres cajas para contrastar áreas del norte y sur de México antes de examinar sus tendencias. Las coordenadas oficiales del proyecto están en [`config/study-boxes.json`](../config/study-boxes.json), en orden **oeste, sur, este, norte** (longitud y latitud en grados). El periodo de comparación previsto es 1992–2024.

| ID | Área de estudio | Caja [O, S, E, N] | Estado de los datos |
| --- | --- | --- | --- |
| `mx-northeast` | Noreste, caja de prueba actual | `[-101, 25, -99, 27]` | Series procesadas y conectadas a la interfaz. |
| `mx-chihuahua-interior` | Chihuahua interior | `[-107, 28, -105, 30]` | Caja definida; sin series descargadas ni procesadas. |
| `mx-south-humid` | Caja sur (Chiapas–Tabasco) | `[-94, 16, -92, 18]` | Caja definida; sin series descargadas ni procesadas. |

La caja de Chihuahua permite estudiar un entorno interior donde esperamos condiciones más secas; la del sur permite estudiar un entorno donde esperamos mayor precipitación. Son **hipótesis de contraste**, que se comprobarán con las mismas series climáticas antes de describir las diferencias entre cajas. [INEGI documenta la diversidad climática de Chihuahua y Tabasco](https://en.www.inegi.org.mx/contenidos/productos/prod_serv/contenidos/espanol/bvinegi/productos/nueva_estruc/889463921820.pdf).

## Verificación espacial inicial

- La [API regional mensual de NASA POWER](https://power.larc.nasa.gov/docs/services/api/temporal/monthly/) aceptó las dos cajas nuevas para `T2M` en 2010. Devolvió 20 centros de celda en Chihuahua y 15 en la caja sur. Una propuesta de 1,5° × 1° para Tabasco fue rechazada por la API: solicita al menos 2° de amplitud en cada eje.
- Los centros de celda devueltos para las dos cajas nuevas caen dentro de México según los límites estatales de Natural Earth guardados en `public/assets/region-states.json`. En la caja sur, 11 centros corresponden a Chiapas, tres a Tabasco y uno a Veracruz. Esta revisión de centros no equivale a recortar la superficie completa de cada celda.
- La caja actual del noreste intersecta Texas. Ninguna de las tres cajas representa un estado o una región administrativa completa. La caja sur incluye un gradiente de elevación considerable; por ello, los promedios espaciales requieren cautela.

## Regla para la comparación

Para habilitar una caja se necesitan sus archivos originales, cobertura mensual completa para el periodo elegido, metadatos de unidades y malla, una agregación espacial documentada y el resultado analítico por variable. Las series de la caja noreste **no se reutilizarán** para las otras cajas. Cada variable deberá proceder del mismo producto y usar la misma definición en las tres; se conservarán los valores por celda antes del promedio regional. Se documentarán las diferencias entre cajas efectivas de Giovanni, POWER y otros productos. La interfaz seguirá ofreciendo solo la caja noreste mientras las nuevas carezcan de datos procesados.

Los scripts de descarga y normalización existentes aún usan la caja noreste y rutas de salida sin ID regional. Antes de descargar las otras dos cajas habrá que parametrizar esas rutas para evitar sobrescribir los datos actuales.

Estas cajas son áreas de estudio del MVP. Las cinco regiones con polígonos planteadas para una versión posterior requieren otra decisión geográfica y un procesamiento espacial propio.
