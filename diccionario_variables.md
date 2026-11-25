# Diccionario de variables

**Proyecto:** Estimación del WACC de las empresas listadas en la BVL (2015–2025)
**Autora:** Sinche De La Cruz, Andrea Nicolle · 2024200529I
**Llave de unión:** `ticker` + `periodo` (año y trimestre)

## 0. Fuentes, frecuencia y endpoints

| Fuente | Frecuencia | Endpoint o URL de origen | Variables que aporta |
|---|---|---|---|
| Yahoo Finance | Diaria (llevada a mensual y trimestral) | Librería `yfinance` 1.8.0, función `download`, tickers `*.LM` y `EPU` | precio_cierre, volumen, rendimientos, beta |
| BCRPData (BCRP) | Diaria (promedio trimestral y mensual) | `https://estadisticas.bcrp.gob.pe/estadisticas/series/api/PD04719XD/json/2015-01-01/2025-12-31/esp` | rf_anual_pct |
| SMV (portal SIMV) | Trimestral | `https://www.smv.gob.pe/SIMV/Frm_InformacionFinanciera` → `Frm_DetalleInfoFinanciera.aspx` | deuda_financiera, patrimonio, gastos financieros, utilidad antes de impuestos, impuesto, ingresos, utilidad neta |

## 1. Datos crudos

### `datos_crudos_yahoo_2024200529I.csv` (Yahoo Finance, diario, 2012–2025, 80 559 filas)

| Variable | Tipo | Unidad | Descripción |
|---|---|---|---|
| fecha | fecha | AAAA-MM-DD | Día de negociación |
| precio_cierre | decimal | moneda de cotización | Precio de cierre ajustado por dividendos y splits |
| volumen | entero | acciones | Acciones negociadas en el día |
| ticker | texto | — | Código de la acción en Yahoo Finance (por ejemplo, ALICORC1.LM) o EPU |
| sector | texto | — | Sector económico asignado por la autora |

### `bcrp_PD04719XD_2024200529I.json` (BCRPData, diario, 2015–2025)

| Variable | Tipo | Unidad | Descripción |
|---|---|---|---|
| periods.name | texto | DD.Mes.AA | Fecha en formato del BCRP (por ejemplo, 02.Ene.15) |
| periods.values | texto | % anual | Rendimiento del bono del Tesoro de EE. UU. a 10 años; "n.d." = sin dato |

### `datos_crudos_smv_2024200529I.csv` (SMV, trimestral, 2015–2025, 924 filas)

| Variable | Tipo | Unidad | Descripción |
|---|---|---|---|
| ticker | texto | — | Código de la acción (igual que en Yahoo) |
| empresa_smv | texto | — | Razón social registrada en la SMV |
| anio, trimestre | entero | — | Periodo del estado financiero |
| expediente | texto | — | Número de expediente de la presentación a la SMV |
| moneda | texto | — | Moneda del reporte: miles de soles o miles de dólares |
| otros_pasivos_financieros | decimal | miles | Deuda financiera: corriente + no corriente |
| total_pasivos | decimal | miles | Total pasivos |
| total_patrimonio | decimal | miles | Total patrimonio |
| ingresos_trim / _acum | decimal | miles | Ingresos de actividades ordinarias del trimestre / acumulados en el año |
| gastos_financieros_trim / _acum | decimal | miles | Gastos financieros (con signo negativo en el original) |
| utilidad_antes_impuestos_trim / _acum | decimal | miles | Ganancia (pérdida) antes de impuestos |
| impuesto_trim / _acum | decimal | miles | Gasto por impuesto a las ganancias (negativo = gasto) |
| utilidad_neta_trim / _acum | decimal | miles | Ganancia (pérdida) neta |
| url_fuente | texto | — | Página de la SMV consultada |

## 2. Datos procesados

### `datos_procesados_2024200529I.csv` (trimestral, 924 filas, 23 columnas)

Incluye `ticker`, `anio`, `trimestre`, `empresa_smv`, `expediente`, `moneda`, `total_pasivos`, `ingresos_trim` y `utilidad_neta_trim` con el mismo significado que arriba, más:

| Variable | Tipo | Unidad | Descripción |
|---|---|---|---|
| periodo | texto | AAAAQn | Trimestre (por ejemplo, 2015Q1) |
| sector | texto | — | Sector económico |
| precio_cierre_trim | decimal | moneda de cotización | Último precio de cierre del trimestre |
| volumen_trim | entero | acciones | Volumen total negociado en el trimestre |
| dias_negociados | entero | días | Días del trimestre con volumen mayor que cero |
| rendimiento_trim | decimal | proporción | Variación del precio de cierre respecto al trimestre anterior |
| rendimiento_mercado_trim | decimal | proporción | Rendimiento trimestral del fondo EPU |
| deuda_financiera | decimal | miles | = otros_pasivos_financieros |
| patrimonio | decimal | miles | = total_patrimonio |
| gastos_financieros_trim / _acum | decimal | miles | Gastos financieros en valor positivo |
| utilidad_antes_impuestos_acum | decimal | miles | Utilidad antes de impuestos acumulada en el año |
| impuesto_acum | decimal | miles | Impuesto acumulado en el año, positivo = gasto |
| rf_anual_pct | decimal | % anual | Promedio trimestral del bono del Tesoro de EE. UU. a 10 años |

### `rendimientos_mensuales_2024200529I.csv` (mensual, 3686 filas)

| Variable | Tipo | Unidad | Descripción |
|---|---|---|---|
| ticker | texto | — | Código de la acción |
| mes | texto | AAAA-MM | Mes |
| precio_cierre | decimal | moneda de cotización | Último precio del mes |
| rendimiento | decimal | proporción | Rendimiento mensual de la acción |
| rendimiento_mercado | decimal | proporción | Rendimiento mensual del fondo EPU |
| rf_anual_pct | decimal | % anual | Promedio mensual del bono del Tesoro de EE. UU. a 10 años |

## 3. Salidas

### `wacc_trimestral_2024200529I.csv` (924 filas)

Contiene todas las variables de la base procesada, más:

| Variable | Tipo | Unidad | Descripción |
|---|---|---|---|
| beta | decimal | — | Pendiente de la regresión de 36 meses de la acción contra el EPU |
| error_beta | decimal | — | Error estándar de la beta |
| meses_beta | entero | meses | Meses usados en la regresión (24 a 36) |
| ke | decimal | proporción anual | Costo del patrimonio (CAPM) |
| kd | decimal | proporción anual | Costo de la deuda; vacío si sale fuera de 0–30 % |
| t | decimal | proporción | Tasa de impuesto usada |
| t_es_legal | booleano | — | True si se usó la tasa legal de 29,5 % |
| peso_deuda | decimal | proporción | D / (D + E) |
| peso_patrimonio | decimal | proporción | E / (D + E) |
| wacc | decimal | proporción anual | Costo promedio ponderado de capital |

### Tablas y figuras

| Archivo | Contenido |
|---|---|
| `tabla1_descriptivos_2024200529I.csv` | Estadísticos descriptivos de beta, Ke, Kd, t, peso de la deuda y WACC |
| `tabla2_mediana_sector_2024200529I.csv` | Medianas por sector |
| `tabla3_mediana_emisora_2024200529I.csv` | Medianas por empresa |
| `tabla4_montecarlo_2024200529I.csv` | WACC estimado y percentiles 5, 50 y 95 de 10 000 simulaciones |
| `fig1_wacc_sector_2024200529I.png` | WACC mediano anual por sector |
| `fig2_wacc_emisora_2024200529I.png` | Distribución del WACC trimestral por empresa |
