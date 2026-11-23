# Incidencias de fuente

**Estudiante:** Sinche de la Cruz, Andrea Nicolle · Código 2024200529I
**Tema 57:** Estimación del WACC de las empresas listadas en la Bolsa de Valores de Lima
**Vía afectada:** Vía 2 (scraping o descarga programática) · Superintendencia del Mercado de Valores (SMV)

## 1. Bloqueo registrado

| Campo | Detalle |
|---|---|
| URL consultada | https://www.smv.gob.pe/SIMV/Frm_InformacionFinanciera?data=A70181B60967D74090DCD93C4920AA1D769614EC12 |
| Fecha y hora | 2026-11-22 21:07:15 UTC (16:07 hora de Lima) |
| Código de respuesta HTTP | 418 |
| robots.txt | https://www.smv.gob.pe/robots.txt también responde 418 (no se puede leer) |
| User-Agent usado | Proyecto academico UNCP Finanzas I - estudiante 2024200529I |
| Herramienta | Python `requests` en Google Colab |
| Evidencia | Captura `evidencia_smv_418.png` |

**Observación:** el portal abre con normalidad en un navegador. Los estados financieros trimestrales existen, incluido el archivo estructurado XBRL. Sin embargo, el servidor rechaza toda solicitud programática con el código 418. Además, la descarga de cada documento se hace mediante formularios ASP.NET (postback con `__VIEWSTATE`), no con enlaces directos. No se intentó eludir el bloqueo, por ejemplo simulando un navegador, en cumplimiento del numeral 2.4.8 (ética del web scraping).

## 2. Resolución: la SMV sí responde desde una conexión en el Perú

| Campo | Detalle |
|---|---|
| Fecha y hora de la nueva prueba | 2026-11-22 18:13 (hora de Lima) |
| Equipo | PC personal con Windows 11 y Python 3.14, conexión doméstica en el Perú |
| Resultado | HTTP 200, la página incluye el formulario ASP.NET (`__VIEWSTATE`) |
| robots.txt | La dirección redirige a https://www.gob.pe/smv; no se declaran rutas prohibidas |

El bloqueo 418 ocurría solo desde los servidores de Google Colab (fuera del país). Desde la PC de la autora la consulta funciona sin cambiar el User-Agent ni simular un navegador. Por eso **se mantuvo la SMV como vía 2** y no fue necesario pedir una fuente sustituta. La prueba en Colab queda documentada en la sección 1 y en `evidencia_smv_418.png`.

## 3. Otras incidencias durante la extracción (22/11/2026)

| Incidencia | Qué pasó | Cómo se resolvió |
|---|---|---|
| Sesión vencida | Después de unos 40 minutos la SMV devolvía tablas vacías | El script 02 pide un formulario nuevo para cada emisora y reintenta una vez si la tabla sale vacía |
| Southern Copper (SCCO) | No presenta estados financieros a la SMV (reporta en EE. UU.); el log registra "sin estados financieros" en los 11 años | Se excluye de la base; quedan 21 empresas |
| Índice S&P/BVL | El ticker ^SPBLPGPT no está disponible en Yahoo Finance | Se usa el fondo iShares MSCI Peru (EPU) como mercado para la beta |
| Betas de 2015 y 2016 | Faltaban 36 meses de historia previa | El script 01 descarga precios desde 2012-01-01 |
| Duración | Las 924 consultas (21 empresas × 44 trimestres) con pausa de 1 s tardaron 1 h 29 min (20:47 a 22:16) | — |

Resultado final de la vía 2: `datos_crudos_smv_2024200529I.csv` con 924 filas, una por empresa y trimestre.
