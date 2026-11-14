# Trend Detectives

Interfaz funcional para explorar tendencias históricas en regiones de México y Estados Unidos. Next.js 16, React 19, TypeScript, Tailwind 4, Three.js / React Three Fiber / Drei, D3 y Anime.js. Proyecto independiente para Space Apps 2026, sin respaldo oficial de NASA.

## Abrir localmente

Requiere Node.js 20.19 o posterior (probado con 20.20.2).

```bash
npm ci
npm run dev
```

App: http://localhost:3000 · Demo separada: http://localhost:3000/demo

```bash
npm run typecheck
npm run lint
npm test
npm run build
npm start
```

No requiere credenciales, autenticación ni base de datos. No hay llamadas a NASA o Claude, backend científico ni despliegue automático.

## Datos y scripts existentes del repositorio

Se conservan sin modificación `data/`, los scripts Python originales, `requirements.txt`, `docs/DATASETS.md` y `docs/METODOLOGIA.md`. Su README original está íntegro en [docs/README_DATOS.md](docs/README_DATOS.md). Esos resultados exploratorios todavía no alimentan este frontend; la interfaz muestra sólo fixtures identificadas como demo.

## Qué funciona

- Cuatro cajas de demostración, dos en México y dos en Estados Unidos; selección mediante globo 3D y selector accesible. Rotación, zoom, iluminación y atmósfera. Cartografía local Natural Earth de dominio público; alternativa estática si WebGL no está disponible.
- Catálogo separado por Calor, Lluvia y Suelo; tres variables con fixtures y seis pendientes. Hasta tres variables por análisis; periodos de diez años o más dentro de 1984–2024.
- Borrador independiente del análisis ejecutado; aviso de cambios pendientes. Estados inicial, preparando, error/reintento, sin datos y sin conexión de chat.
- Series D3/SVG con ejes y unidades, tooltip por ratón o flechas, huecos en faltantes, tendencia activable, ampliación y comparación de hasta tres series con ejes Y independientes.
- Mapa con leyenda de pendiente por década: colorea sólo regiones ya analizadas para la variable y periodo vigentes. Borde discontinuo si el IC incluye cero. No se colorean países completos ni se inventa cobertura.
- Evidencia con fuente usada y prevista, método, límites, serie tabular y CSV del análisis visible.
- Chat explícitamente simulado, preguntas sugeridas, composer, carga, error/reintento y evidencia enlazada. Historial aislado por ID de análisis y variable; volver a la misma selección recupera su conversación durante la sesión. Los cambios pendientes no alteran el contexto visible.
- Responsive: tres paneles en escritorio, reorganización en tablet y secciones Explorar / Resultados / Chat en móvil. Diálogos nativos, foco, teclado y reduced motion.
- Stageshow instalado a nivel de proyecto y demo ilustrada en `/demo`, fuera de la app. Su kit MIT está en `components/demo/kit`; helpers de captura en `scripts/stageshow`.

## Datos y contratos de integración

**Todas las series, pendientes e intervalos son sintéticos.** No son hallazgos NASA ni resultados climáticos validados. La cartografía tiene geografía real; no aporta mediciones ambientales.

`lib/catalog.ts`: catálogo, disponibilidad, unidades y cajas.
`lib/contracts.ts`: contratos AnalysisAdapter / ChatAdapter, selección, series, estadísticos, método y procedencia.
`lib/fixtures.ts`: fixtures anuales deterministas y ajuste OLS ilustrativo con intervalo t aproximado. Sólo para coherencia de la UI. No aplica HAC ni controles ENSO/PDO; no usar como pipeline científico.
`lib/adapters.ts`: análisis simulado, contexto completo de chat y CSV. No hay endpoints operativos inventados.
`lib/map-layer.ts`: colores y elegibilidad de regiones según análisis ejecutados.

Para conectar datos: implementar AnalysisAdapter con resultados reproducibles y validados, producto/versiones, huella espacial, resolución, unidades, faltantes, método e incertidumbre. Habilitar catálogo sólo tras esa validación. Para Claude: implementar ChatAdapter mediante una ruta de servidor; enviar ChatContext con ID, selección, variable, serie, unidades, pendiente/IC, método, fuentes y límites. Las claves permanecen en servidor; no añadirlas al cliente. No se ha seleccionado un modelo ni hecho llamadas reales.

El ejemplo de temperatura tiene IC que excluye cero; el de lluvia es inconcluso. Humedad superficial de California central no tiene fixture y activa el estado sin datos.

## Escenarios de revisión

- `/?empty=1`: sin análisis.
- `/?simulate=analysis-error`: el primer intento de Analizar falla; reintentar funciona.
- `/?simulate=chat-error`: la primera respuesta falla; reintentar funciona.
- `/?simulate=chat-offline`: chat sin proveedor disponible; evidencia sigue accesible.
- `/?simulate=webgl-off`: fallback estático.

Ver `docs/QA.md` para lo ejecutado y sus límites. La investigación de comparación de variables está en `docs/GIOVANNI.md`. Los dos posts de X del encargo devolvieron 403; se usaron las APIs oficiales de las librerías y la skill Stageshow.

## Licencias y demo

Cartografía y derivaciones: `public/assets/ATTRIBUTION.md`. Kit y scripts Stageshow: MIT, Benji Taylor; copia de su licencia y aviso en `components/demo/kit` y `scripts/stageshow`. Para reinstalar la skill local:

```bash
npx skills add benjitaylor/skills --skill stageshow
```

Para repetir las capturas de la demo con un navegador Chromium instalado:

```bash
CHROME_PATH='/ruta/al/binario/chromium' node scripts/stageshow/film.mjs http://localhost:3000/demo --every 1000 --count 16 --gate --out artifacts/demo/film.png
```

Las notas históricas de investigación del workspace se conservan localmente y no forman parte del repositorio público de la interfaz.
