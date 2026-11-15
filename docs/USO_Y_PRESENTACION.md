# Uso y presentación del MVP

## Usuarios

Diseñado para estudiantes, docentes y personas que desean explorar cambios ambientales sin una formación estadística previa. Los analistas conservan acceso a los datos, las fuentes y el método. Es un enfoque de diseño que requiere validación con usuarios, no una conclusión de investigación de mercado.

## Leer un resultado

1. Elegir lugar. El análisis corresponde sólo al recuadro geográfico.
2. Abrir «Cambiar datos» para elegir hasta tres variables y años disponibles. Pulsar «Analizar selección» aplica cualquier cambio.
3. Leer gráfica, cambio cada diez años y respuesta a «¿Es significativo?». Los detalles de p, intervalos, autocorrelación y ajustes están en «Datos y método».
4. «Explicar este resultado» abre preguntas en lenguaje natural. La IA explica la selección visible; el motor estadístico calcula la significancia.

«Herramientas avanzadas» conserva exportación CSV, comparación de varias variables, mapa 3D, predicción experimental y limpieza del resultado. Predicción no determina la significancia histórica.

## Dos minutos ante el jurado

| Tiempo | Mostrar | Mensaje |
|---|---|---|
| 0–15 s | Vista principal | Ver subir una curva no basta para saber cuánto cambia ni si hay evidencia suficiente. |
| 15–30 s | Lugar y Cambiar datos | Elegimos variable, región y años; el prototipo reúne evolución, magnitud, evidencia y explicación. |
| 30–60 s | Chihuahua, temperatura, 1992–2024 | +0.49 °C cada diez años, significativo; posible salto por comprobar. Gráfica y conclusión juntas. |
| 60–80 s | Respuesta ya comprobada de Claude | Explica el resultado y una reserva en lenguaje sencillo. |
| 80–105 s | Noreste, misma variable y años | +0.27 °C cada diez años, sin significancia. Magnitud y evidencia son preguntas distintas. |
| 105–120 s | Resultado y área | MVP con siete variables y tres cajas de estudio; fuentes y método verificables. |

Preparar ambas regiones antes y ensayar con cronómetro. No esperar una respuesta nueva de Claude durante el pitch: la llamada puede tardar hasta 45 segundos. Mantener respaldo del recorrido real. No mostrar todos los controles ni abrir los experimentos neuronales en los dos minutos.

## Preguntas del jurado

- **¿Por qué significativo y con reservas?** La prueba supera el umbral, pero un salto puede explicar la serie; eso requiere contraste antes de afirmar un cambio gradual estable.
- **¿Cómo se calcula?** Regresión mensual con calendario y Niño 3.4; incertidumbre que considera dependencia temporal y comparaciones múltiples. El método completo se consulta en la app.
- **¿Cubre México?** Son tres cajas de estudio; los estados son contexto geográfico.
- **¿Qué hace la IA?** Explica datos y resultados que el servidor verifica. No decide por apariencia de la gráfica ni inventa significancia.

No se alteraron datos ni métodos al simplificar la interfaz.
