# Refinamiento geográfico de la interfaz

Se conserva el análisis, sus datos y los adaptadores. La vista predeterminada muestra límites estatales de Natural Earth para ubicar la caja solicitada. Coahuila, Nuevo León, Tamaulipas y una parte de Texas se resaltan como contexto; sólo la intersección con la caja recibe el color de la pendiente. El globo 3D sigue disponible mediante «Planeta 3D» y también muestra límites de esos estados. La caja solicitada cruza la frontera; no implica cobertura estatal completa y las mallas de cada producto son distintas.

La leyenda usa azul para estimaciones negativas y naranja para positivas, sin significar bueno/malo. Su intervalo simétrico se amplía para incluir todos los resultados visibles del mismo periodo. La trama/borde discontinuo señala que el IC incluye cero. Las cifras no cambian al alternar vistas.

Se aplicaron recomendaciones de Taste (copy directo, identidad basada en el producto, evitar relleno) e Impeccable (modo Operate, color funcional, jerarquía y lectura) mediante skills locales en `.agents/skills/`. Los flujos de landing y fotografía de Taste no corresponden a esta herramienta; se preservó el stack y la dirección oscura acordada. No se agregan al runtime de la app.

Los controles siguen distinguiendo borrador y resultado ejecutado. El periodo y variable de la leyenda y el mapa son los del análisis visible. No hay análisis estatal, cobertura nacional, nuevas consultas NASA ni llamadas de IA añadidas.
