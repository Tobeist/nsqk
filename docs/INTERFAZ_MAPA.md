# Refinamiento geográfico de la interfaz

La vista predeterminada muestra límites estatales de Natural Earth alrededor de la caja seleccionada. El noreste intersecta Coahuila, Nuevo León, Tamaulipas y Texas; Chihuahua interior intersecta Chihuahua; la caja sur intersecta Chiapas, Tabasco, Veracruz y Oaxaca. Sólo la intersección de cada estado con el recuadro recibe el color de la pendiente del análisis ejecutado. El globo 3D sigue disponible mediante «Planeta 3D» y muestra las tres cajas. Ninguna caja implica cobertura estatal completa y las mallas de cada producto son distintas. `scripts/build-study-intersections.mjs` genera las intersecciones a partir de los límites estatales y de `config/study-boxes.json`.

La leyenda usa azul para estimaciones negativas y naranja para positivas, sin significar bueno/malo. Su intervalo simétrico se amplía para incluir todos los resultados visibles del mismo periodo. La trama/borde discontinuo señala que el IC incluye cero. Las cifras no cambian al alternar vistas.

Se aplicaron recomendaciones de Taste (copy directo, identidad basada en el producto, evitar relleno) e Impeccable (modo Operate, color funcional, jerarquía y lectura) mediante skills locales en `.agents/skills/`. Los flujos de landing y fotografía de Taste no corresponden a esta herramienta; se preservó el stack y la dirección oscura acordada. No se agregan al runtime de la app.

Los controles siguen distinguiendo borrador y resultado ejecutado. El periodo y variable de la leyenda y el mapa son los del análisis visible. No hay análisis estatal, cobertura nacional, nuevas consultas NASA ni llamadas de IA añadidas.
