# Conversación con Claude

La app consulta la API oficial de Anthropic desde `POST /api/chat`. El navegador envía la pregunta, la selección, la variable y hasta ocho mensajes previos. El servidor reconstruye el análisis del periodo a partir de los datos del repositorio; ignora cualquier estadística enviada por el cliente.

Claude explica los hechos recibidos en respuestas breves. El cálculo de significancia sigue siendo determinista: p de Holm < 0.05. Cada respuesta comienza con un resumen verificado de pendiente, p y significancia. Intervalo y familia permanecen en el contexto y la evidencia expandible. Los resultados significativos con estado pendiente o sensible conservan esa reserva; la IA no los convierte en tendencias robustas ni establece causas. Si se pregunta por predicción, recibe el experimento de la variable y caja activas, con error retrospectivo y proyección de 2025 usando datos hasta diciembre de 2024. No inventa un pronóstico actual ni extrapola el experimento a otro periodo.

## Configuración

En preguntas sobre entrenamiento o predicción, Claude recibe las métricas de la red original y de Red + ENSO por separado. Sólo esta última añade Niño 3.4 histórico, con corte en octubre del año anterior y persistencia para los meses desconocidos. El ganador experimental de validación se separa del modelo actual: el anterior se conserva como predeterminado en las 18 series y ENSO sigue experimental. La evaluación 2021–2024 se identifica como retrospectiva y ya examinada en versiones anteriores; no se presenta como confirmación independiente nueva. Las fuentes de NASA y NOAA se incluyen en el contexto.

Define estas variables sólo en el entorno del servidor o en `.env.local`, que Git ignora:

```dotenv
ANTHROPIC_API_KEY=tu_clave_privada
ANTHROPIC_MODEL=claude-sonnet-5-5
```

No uses el prefijo `NEXT_PUBLIC_`. La clave no forma parte del JavaScript del navegador, los mensajes ni las respuestas. En otra máquina o alojamiento hay que configurar su propio entorno; `git pull` no transmite secretos. El modelo debe estar disponible para esa cuenta. `GET /api/chat` sólo indica si hay configuración; la conexión se verifica al obtener una respuesta real.

Las preguntas, historial y datos del análisis se envían a Anthropic al consultar. El servidor impone 1,500 caracteres por mensaje, ocho mensajes de historial, 20 KiB por petición, dos consultas simultáneas y doce por minuto por proceso. La llamada a Claude tiene un máximo de 45 segundos y no se reintenta automáticamente. Los límites en memoria son para este prototipo de un proceso; un despliegue público con varios procesos necesita un límite compartido y control de acceso acorde a su audiencia.

Los errores distinguen configuración, saldo insuficiente, límites, tiempo de espera y servicio no disponible. No se reemplaza una respuesta fallida con una explicación local etiquetada como Claude. Las pruebas usan respuestas simuladas; la comprobación de integración utiliza una consulta real autorizada por el propietario de la clave.

Referencias oficiales: [Messages API](https://platform.claude.com/docs/en/api/messages/create), [Models API](https://platform.claude.com/docs/en/api/models/list).
