# Verificación de la interfaz

14 nov 2026. Node 20.20.2, Next.js 16.4.6, navegador integrado Chromium y Brave Chromium para capturas Stageshow.

Ejecutado y aprobado: build de producción, TypeScript, ESLint del código propio y cinco pruebas de contratos/fixtures. El kit Stageshow vendorizado se conserva con su licencia y se excluye del lint propio; sí participa en TypeScript y build. npm audit sin vulnerabilidades reportadas.

Recorrido ejecutado en navegador: elegir México/Texas, añadir variables y periodo, analizar, ampliar gráfica, preguntar, abrir evidencia, descargar CSV, cambiar región y volver a analizar. La conversación previa no aparece en el nuevo contexto. Comparación de tres variables con ejes Y y unidades independientes; mapa acumula dos regiones ejecutadas para el mismo periodo. Precipitación muestra caso inconcluso, y humedad de California el estado sin datos. Teclado: consultar año con flecha y cerrar diálogo con Escape.

Escenarios ejecutados: error de análisis y reintento; error de chat y reintento; chat sin conexión; fallback WebGL con evidencia disponible; estado sin análisis. Responsive observado a 1440×900, 1280×800 y 390×844, sin desbordamiento horizontal. Capturas en `artifacts/`.

Consola de la app: sin errores JavaScript observados; Three/Fiber emite una advertencia de deprecación de THREE.Clock. No se ha probado un dispositivo móvil físico, Safari, lector de pantalla ni una integración real de NASA/Claude. Las pruebas de visualización no validan científicamente las fixtures.

La demo separada sigue Stageshow, con captura del gold ai-chat, stills, film y estados. Sus capturas y evaluación de movimiento son locales en `artifacts/demo/`; el muestreo de animación registró huecos, por lo que no se afirma una validación completa de cada frame. Ver `components/demo/REHEARSAL.md` para el cierre de esa revisión. No se usa la demo como interacción de la aplicación principal.
