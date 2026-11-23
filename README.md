# Estimación del WACC de las empresas listadas en la Bolsa de Valores de Lima (2015–2025)

**Autora:** Sinche De La Cruz, Andrea Nicolle · Código 2024200529I
**Curso:** Finanzas I (055D) · Facultad de Economía, UNCP · Semestre 2026-II · Unidad II
**Docente:** Dr. Ciro Iván Machacuay Meza
**Tema 57:** Estimación del WACC de las empresas listadas en la BVL

Este repositorio contiene los datos y el código para estimar, cada trimestre entre 2015 y 2025, el costo promedio ponderado de capital (WACC) de 21 empresas no financieras que cotizan en la BVL.

## 1. Pregunta y método

¿Cuánto les cuesta financiarse a las empresas no financieras de la BVL y cómo cambia ese costo entre sectores y en el tiempo?

$$WACC = \frac{E}{D+E}\,K_e + \frac{D}{D+E}\,K_d\,(1-t)$$

| Componente | Cómo se calcula | Fuente |
|---|---|---|
| $K_e$ | CAPM: $r_f + \beta \times PRM$, con PRM = 6 % | Yahoo Finance, BCRPData |
| $\beta$ | Regresión de los rendimientos mensuales de la acción contra el fondo EPU (iShares MSCI Peru), ventana móvil de 36 meses (mínimo 24) | Yahoo Finance |
| $r_f$ | Bono del Tesoro de EE. UU. a 10 años, promedio del trimestre (serie PD04719XD) | BCRPData |
| $K_d$ | Gastos financieros del año llevados a 12 meses / deuda financiera (se descartan valores fuera de 0–30 %) | SMV |
| $t$ | Impuesto / utilidad antes de impuestos; si no es válida, la tasa legal de 29,5 % | SMV |
| $D$, $E$ | Otros pasivos financieros y total patrimonio (valores contables) | SMV |

Además se hace una simulación de Monte Carlo (10 000 escenarios, semilla 529) para el último trimestre de cada empresa, variando la beta y la prima de mercado.

## 2. Fuentes de datos (dos vías de extracción)

| Vía | Fuente | Script | Archivo crudo |
|---|---|---|---|
| 1. API | Yahoo Finance (`yfinance`): precios diarios de 22 acciones y del fondo EPU, 2012–2025 | `01_extraccion_api.py` | `datos_crudos_yahoo_2024200529I.csv` |
| 1. API | BCRPData: rendimiento diario del bono del Tesoro de EE. UU. a 10 años, 2015–2025 | `01_extraccion_api.py` | `bcrp_PD04719XD_2024200529I.json` |
| 2. Scraping | SMV, portal SIMV (`Frm_InformacionFinanciera`): estados financieros trimestrales individuales, 2015–2025 | `02_scraping_web.py` | `datos_crudos_smv_2024200529I.csv` |

**Ética del scraping:** se revisó el robots.txt (la SMV no lo publica: la dirección redirige a gob.pe), se envía un User-Agent que identifica el proyecto, se hace una pausa de al menos 1 segundo entre solicitudes y no se simula un navegador. Las incidencias de la fuente están en `incidencias_fuente.md`.

**Parámetros congelados:** fecha de inicio 2015-01-01 (precios desde 2012-01-01 para tener 36 meses de historia en la primera beta), fecha de corte 2025-12-31. Extracción realizada el 22/11/2026.

## 3. Estructura del repositorio

```
├── codigo/
│   ├── 01_extraccion_api.py      Vía 1: Yahoo Finance + BCRPData
│   ├── 02_scraping_web.py        Vía 2: estados financieros de la SMV
│   ├── 03_limpieza_union.py      Limpieza y unión por ticker + periodo
│   └── 04_analisis_wacc.py       Beta, Ke, Kd, t, WACC, tablas, gráficos y Monte Carlo
├── datos_crudos/                 Datos tal como se descargaron (no se modifican)
├── datos_procesados/             Base trimestral unida y rendimientos mensuales
├── salidas/                      WACC trimestral, tablas 1-4 y figuras 1-2
├── diccionario_variables.md
├── incidencias_fuente.md
├── evidencia_smv_418.png
├── log_ejecucion.txt             Registro con fecha y hora de cada ejecución
├── requirements.txt
└── .env.example
```

## 4. Cómo reproducir

```
py -m pip install -r requirements.txt
cd codigo
py 01_extraccion_api.py      # unos 2 minutos
py 02_scraping_web.py        # unas 1 h 30 min (924 consultas con pausa)
py 03_limpieza_union.py
py 04_analisis_wacc.py
```

Los scripts usan rutas relativas (`Path(__file__).parent.parent`), así que funcionan desde cualquier carpeta. Cada ejecución queda anotada en `log_ejecucion.txt`. Las copias HTML de cada consulta a la SMV (924 archivos, 229 MB) se guardan en `datos_crudos/smv_html/` pero no se suben al repositorio por su tamaño.

## 5. Resultados principales

| Indicador | Valor |
|---|---|
| Observaciones (empresa-trimestre) | 924 (21 empresas × 44 trimestres) |
| Observaciones con WACC | 803 |
| WACC mediano | 5,96 % (rango 1,6 %–13,8 %) |
| Beta mediana | 0,53 |
| Kd mediano | 5,8 % |
| Sector con mayor WACC | Minería (7,8 %) |
| Sector con menor WACC | Pesca (3,0 %) |

Southern Copper (SCCO) tiene precios en Yahoo Finance pero no presenta estados financieros a la SMV, por eso queda fuera de la base. Las 121 observaciones sin WACC corresponden a trimestres con patrimonio negativo o con un Kd fuera de rango.

## 6. Integridad de los datos (SHA-256)

| Archivo | SHA-256 |
|---|---|
| `datos_crudos/datos_crudos_yahoo_2024200529I.csv` | `497fa24e32df343fa8ea422070f5566eabbb19466517186b9d931e1eed28d0d3` |
| `datos_crudos/bcrp_PD04719XD_2024200529I.json` | `be9d774f67d6f0398778979aac69fc6d2fe9e684162473fbba213bc259cb758d` |
| `datos_crudos/datos_crudos_smv_2024200529I.csv` | `097e768866bda31a22d52f379e5f815d11ea36c8892a2839b35619848defa86c` |
| `datos_procesados/datos_procesados_2024200529I.csv` | `ae1ad8466519c6b249f9adeb03de2704a59dbd6d310b2d93f18376e0c76b3082` |
| `datos_procesados/rendimientos_mensuales_2024200529I.csv` | `99bafce791999b42ac1d909e9d06425c93bd67cae525bfa73092f45cffe80a13` |
| `salidas/wacc_trimestral_2024200529I.csv` | `3d53c940372688ea5ecf7d4a9e1f5684cd8b1fcaa317a4504d12b014e8d51279` |

Para comprobar un archivo en Windows: `certutil -hashfile datos_crudos\datos_crudos_smv_2024200529I.csv SHA256`

## 7. Limitaciones

- Los pesos D/(D+E) usan valores contables porque la SMV no publica el número de acciones en circulación.
- La tasa libre de riesgo está en dólares, mientras que parte de los estados financieros está en soles (13 empresas) y parte en dólares (8 empresas). El WACC se calcula con razones, así que la moneda no cambia los pesos ni el Kd.
- La beta se mide contra el fondo EPU porque el índice S&P/BVL no está disponible en Yahoo Finance. Algunas acciones de la BVL se negocian poco, lo que tiende a bajar su beta.
- La prima de riesgo de mercado (6 %) es un parámetro; la simulación de Monte Carlo muestra cuánto cambia el WACC si se mueve.
