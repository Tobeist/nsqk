# Cartografía local

- Fuente: Natural Earth, Admin 0 Countries, escala 1:110m.
- GeoJSON: https://github.com/nvkelso/natural-earth-vector/blob/master/geojson/ne_110m_admin_0_countries.geojson
- Licencia: dominio público. https://www.naturalearthdata.com/about/terms-of-use/
- Descarga: 2026-11-14.
- `earth-map.png`, `earth-map.svg`, `earth-fallback.svg`: representaciones cartográficas derivadas con D3 y Sharp; regenerar con `node scripts/build-map.mjs`.
- Sólo la caja de prueba del noreste de México dispone de análisis en la interfaz. No se ofrece cobertura nacional.
- La caja no es un límite administrativo ni una cuenca.
- No se usa identidad gráfica ni logotipos oficiales NASA. La cartografía no aporta mediciones climáticas; las series proceden de POWER y Giovanni.
