# Giovanni y la comparación de variables

Investigación: 14 nov 2026. No se generó una consulta autenticada ni se descargaron observaciones NASA.

Fuentes primarias:

- Guía oficial Giovanni v2024.1: https://giovanni.gsfc.nasa.gov/giovanni/doc/UsersManualworkingdocument.docx.html
- Aplicación clásica v4.40: https://giovanni.gsfc.nasa.gov/giovanni/
- Giovanni Beta actual: https://giovanni.earthdata.nasa.gov/
- Presentación NASA 2024 (ejemplo de dos variables y una tercera gráfica de su diferencia): https://ntrs.nasa.gov/api/citations/20240015071/downloads/Giovanni-agu-zl.pdf

Verificado: elegir varias variables no determina un único tipo de visualización. La guía admite una o varias variables. Area-Averaged Time Series promedia espacialmente cada variable por paso temporal. Scatter y Correlation comparan dos variables emparejadas; Difference requiere cantidades/unidades compatibles. Regridding puede ser necesario para emparejar celdas. Una línea ajustada no constituye por sí sola una conclusión científica de tendencia.

Límite de la verificación: el sitio Beta requiere Earthdata Login para generar gráficas. Se inspeccionaron su selector de tipo y catálogo sin iniciar sesión. No se confirmó un máximo de tres variables ni qué gráfica concreta vio el usuario. El enlace del sitio Beta a su guía en uui-test no fue accesible vía web; el video oficial de múltiples series tampoco se pudo recuperar. No se asume equivalencia completa de funciones entre v4 y Beta.

Decisión de interfaz: hasta tres variables configurables; pestaña de variable activa y una comparación en paneles alineados temporalmente, cada uno con unidad y eje Y propio. No sumar grados, precipitación y humedad; no usar un índice combinado ni inferir causalidad.

Mapa de tendencias: color = pendiente por década de la variable activa del análisis ejecutado; azul = estimación negativa, neutral = cero, coral = positiva. Límites fijos explícitos por variable; valores fuera del dominio saturan. Borde discontinuo = IC incluye cero. Sólo se rellenan cajas con resultados ejecutados para el mismo periodo; regiones sin análisis o sin datos permanecen neutrales. Fuente de cifras: fixtures sintéticas, no Giovanni. Cambiar borradores no recolorea resultados antiguos.
