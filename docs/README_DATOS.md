# Climate Paradox — primera extracción T2M

La [metodología de datos y análisis](METODOLOGIA.md) documenta las decisiones aplicadas, las limitaciones y las validaciones pendientes.

El [glosario de datos y variables](DATASETS.md) explica los archivos disponibles, sus campos y los productos que faltan.

Las [tres cajas de estudio](REGIONES.md) tienen originales, series procesadas y resultados en rutas separadas por región. Las tres pueden analizarse en la interfaz.

También se descargaron de POWER `T2M_MIN`, `T2M_MAX` y `PRECTOTCORR` para 1992–2024. Consulte la metodología antes de comparar esas series con los índices de extremos de Giovanni o con GPCP.

La lluvia diaria `PRECTOTCORR` de 1992–2024 permite calcular un primer índice regional de máxima lluvia en cinco días. Es un índice derivado de POWER y está documentado en el glosario y la metodología; aún no sustituye al `RX5Day` oficial de Giovanni.

Con Earthdata Login también descargamos CSV oficiales de **GPCP** y **`RX5Day` de Giovanni** para 1992–2024. Sus datos originales, series limpias y resultados están descritos en el glosario. El índice `RX5Day` de Giovanni y el índice anual derivado de POWER tienen definiciones diferentes; sus tendencias no son directamente comparables.

La primera serie real usa **NASA POWER Monthly Regional API**, parámetro `T2M`, caja `[-101, 25, -99, 27]`, enero de 2010 a diciembre de 2012. POWER informa que la fuente meteorológica de esta respuesta es MERRA-2, pero **esta extracción no equivale automáticamente** al producto de Giovanni `M2TMNXSLV_5_12_4_T2M`.

```powershell
python -m pip install -r requirements.txt
python scripts/power_t2m.py
```

El script conserva el JSON original en `data/raw/`, escribe los valores de cada punto de malla en `data/processed/*grid*.csv` y una serie regional en `*region*.csv`. El archivo `*.metadata.json` guarda URL, unidades, cobertura y método de agregación. Puede repetirse con `--start 1992 --end 2024`, una vez revisada la primera extracción.

La extracción histórica y el análisis exploratorio se reproducen así:

```powershell
python scripts/power_t2m.py --start 1992 --end 2024
python scripts/analyze_t2m.py data/processed/power_t2m_region_1992_2024.csv data/results/power_t2m_region_1992_2024.json
```

El JSON de resultados contiene la serie mensual, anomalías contra la climatología mensual fija 1992–2021, promedios anuales y regresión lineal con indicadores mensuales y covarianza HAC de 12 rezagos. El valor p es individual y exploratorio; aún falta contrastar POWER con Giovanni, estudiar sensibilidad del periodo y decidir el protocolo de comparaciones múltiples y variabilidad natural antes de publicar conclusiones.

POWER devuelve un valor anual con clave `YYYY13`: se excluye de la serie mensual. `T2M` viene en °C; los valores faltantes (`-999`) quedan vacíos. El promedio regional pondera cada centro de celda por `cos(latitud)`. Es una aproximación para la caja, sin recorte por fronteras estatales ni máscara de tierra. La caja de prueba no representa por sí sola toda la región Norte-Noreste.

Giovanni requiere una sesión Earthdata para estas exportaciones. Una petición directa al OPeNDAP sin esa sesión respondió HTTP 401. Por ello, el archivo POWER se mantiene identificado como fuente distinta. No se calculan conclusiones de tendencia con el periodo de prueba de tres años.

Fuentes: [POWER Monthly API](https://power.larc.nasa.gov/docs/services/api/temporal/monthly/), [fuentes meteorológicas de POWER](https://power.larc.nasa.gov/docs/methodology/data/sources_meteorology/), [Giovanni](https://giovanni.gsfc.nasa.gov/giovanni/).
