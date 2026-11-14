# Cartografía local

- Fuente: Natural Earth, Admin 0 Countries, escala 1:110m.
- GeoJSON: https://github.com/nvkelso/natural-earth-vector/blob/master/geojson/ne_110m_admin_0_countries.geojson
- Licencia: dominio público. https://www.naturalearthdata.com/about/terms-of-use/
- Descarga: 2026-11-14.
- `earth-map.png`, `earth-map.svg`, `earth-fallback.svg`: representaciones cartográficas derivadas con D3 y Sharp; regenerar con `node scripts/build-map.mjs`.
- Sólo la caja de prueba del noreste de México dispone de análisis en la interfaz. No se ofrece cobertura nacional.
- La caja no es un límite administrativo ni una cuenca.
- No se usa identidad gráfica ni logotipos oficiales NASA. La cartografía no aporta mediciones climáticas; las series proceden de POWER y Giovanni.

## Límites estatales

`region-states.json`: subconjunto de México y el estado de Texas de Natural Earth Admin-1, escala 1:10m, dominio público. Fuente: https://github.com/nvkelso/natural-earth-vector/blob/master/geojson/ne_10m_admin_1_states_provinces.geojson . Descarga: 2026-11-14. El recorte contra la caja solicitada `[-101,25,-99,27]` usa `polygon-clipping`; regeneración: `node scripts/build-region-map.mjs /ruta/al/archivo/original.geojson`.

Coahuila, Nuevo León, Tamaulipas y una parte de Texas intersectan la caja. El relleno de estados completos sólo es contexto geográfico. El color que codifica la pendiente se limita al recuadro analizado. Estos límites cartográficos son generalizados, no un deslinde catastral. La huella efectiva de cada producto puede diferir de la caja solicitada, como documenta METODOLOGIA.md.

Tipografía: IBM Plex Sans, IBM / Google Fonts, SIL Open Font License 1.1. Licencia conservada en `public/fonts/OFL.txt`.
