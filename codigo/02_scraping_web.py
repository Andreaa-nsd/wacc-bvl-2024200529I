# Autora: Andrea Nicolle Sinche De La Cruz
# Código de matrícula: 2024200529I
# Tema 57: Estimación del WACC de las empresas listadas en la Bolsa de Valores de Lima
# Fecha de extracción: 2026-11-22

"""
02_scraping_web.py
Vía 2 (web scraping). Rastrea el portal SIMV de la Superintendencia del Mercado de Valores (SMV)
y extrae, para cada emisora y trimestre, las cuentas de los estados financieros INDIVIDUALES
necesarias para el WACC:
  - Otros Pasivos Financieros (corrientes y no corrientes)  -> deuda financiera (D)
  - Total Patrimonio                                         -> patrimonio contable
  - Gastos Financieros                                       -> costo de la deuda (Kd)
  - Ganancia (Pérdida) antes de Impuestos e Ingreso (Gasto) por Impuesto -> tasa efectiva (t)
  - Ingresos de Actividades Ordinarias (control de tamaño)

Cómo funciona el portal (formulario ASP.NET):
  1. Se abre la página "Información Financiera" y se leen los campos ocultos (__VIEWSTATE, etc.).
  2. Se envía el formulario de búsqueda (empresa, Individual, Trimestral, año).
  3. En la tabla de resultados se "pulsa" el botón de la fila "Estados Financieros" de cada trimestre.
  4. La respuesta contiene un enlace a Frm_DetalleInfoFinanciera, que trae los estados en tablas HTML.
  5. Se guarda el HTML original en /datos_crudos/smv_html (evidencia primaria) y se leen las cuentas.
"""

# ------------------------------------------------------------
# BLOQUE 1. Librerías
# ------------------------------------------------------------
import re
import sys
import time
from datetime import datetime
from pathlib import Path

import pandas as pd
import requests
from bs4 import BeautifulSoup

# ------------------------------------------------------------
# BLOQUE 2. Parámetros congelados de la consulta (numeral 2.4.5)
# ------------------------------------------------------------
ANIO_INICIO = 2015
ANIO_CORTE = 2025
CODIGO_MATRICULA = "2024200529I"

URL_BASE = "https://www.smv.gob.pe/SIMV/"
URL_INFO = URL_BASE + "Frm_InformacionFinanciera?data=A70181B60967D74090DCD93C4920AA1D769614EC12"
URL_ROBOTS = "https://www.smv.gob.pe/robots.txt"

USER_AGENT = "UNCP-Finanzas-I/1.0 (e_2024200529I@uncp.edu.pe)"
PAUSA_SEGUNDOS = 1           # pausa mínima entre solicitudes (numeral 2.4.8)
INTENTOS_MAXIMOS = 3

# Ticker de Yahoo -> texto que identifica a la emisora en la lista de la SMV.
# Es una expresión regular: basta con una parte del nombre.
EMISORAS_SMV = {
    "ALICORC1.LM": r"^ALICORP S\.A\.A",
    "BACKUSI1.LM": r"BACKUS",
    "INRETC1.LM": r"INRETAIL",
    "FERREYC1.LM": r"^FERREYCORP",
    "UNACEMC1.LM": r"^UNACEM",
    "CPACASC1.LM": r"^CEMENTOS PACASMAYO",
    "CORAREI1.LM": r"^CORPORACION ACEROS AREQUIPA",
    "SIDERC1.LM": r"SIDERPERU",
    "BVN": r"^COMPAÑIA DE MINAS BUENAVENTURA",
    "SCCO": r"SOUTHERN",
    "MINSURI1.LM": r"^MINSUR",
    "CVERDEC1.LM": r"CERRO VERDE",
    "VOLCABC1.LM": r"^VOLCAN COMPAÑIA MINERA",
    "ENGIEC1.LM": r"^ENGIE ENERGIA PERU",
    "LUSURC1.LM": r"^LUZ DEL SUR",
    "NEXAPEC1.LM": r"NEXA RESOURCES PERU",
    "ATACOBC1.LM": r"ATACOCHA",
    "BROCALI1.LM": r"EL BROCAL",
    "MOROCOI1.LM": r"SAN IGNACIO DE MOROCOCHA",
    "AIHC1.LM": r"^ANDINO INVESTMENT HOLDING",
    "AUSTRAC1.LM": r"^AUSTRAL GROUP",
    "CREDITC1.LM": r"^CREDITEX",
}

# Cuentas que se extraen: variable -> nombres posibles en la SMV.
# Los nombres cambiaron entre 2015-2016 y 2017 en adelante, por eso hay sinónimos.
# La comparación no distingue mayúsculas ni espacios dobles.
CUENTAS_BALANCE = {
    "otros_pasivos_financieros": ["Otros Pasivos Financieros"],   # corriente + no corriente (se suman)
    "total_pasivos": ["Total Pasivos"],
    "total_patrimonio": ["Total Patrimonio"],
}
CUENTAS_RESULTADOS = {
    "ingresos": ["Ingresos de Actividades Ordinarias"],
    "gastos_financieros": ["Gastos Financieros"],
    "utilidad_antes_impuestos": ["Ganancia (Pérdida) antes de Impuestos",
                                 "Resultado antes de Impuesto a las Ganancias"],
    "impuesto": ["Ingreso (Gasto) por Impuesto", "Gasto por Impuesto a las Ganancias"],
    "utilidad_neta": ["Ganancia (Pérdida) Neta del Ejercicio"],
}
TRIMESTRES = {"I": 1, "II": 2, "III": 3, "IV": 4}

# ------------------------------------------------------------
# BLOQUE 3. Rutas relativas a la carpeta del proyecto (sin C:\Users\...)
# ------------------------------------------------------------
RAIZ = Path(__file__).resolve().parent.parent
CARPETA_CRUDOS = RAIZ / "datos_crudos"
CARPETA_HTML = CARPETA_CRUDOS / "smv_html"
ARCHIVO_LOG = RAIZ / "log_ejecucion.txt"
CARPETA_HTML.mkdir(parents=True, exist_ok=True)


# ------------------------------------------------------------
# BLOQUE 4. Registro en pantalla y en log_ejecucion.txt
# ------------------------------------------------------------
def registrar(mensaje):
    marca = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    linea = f"[{marca}] {mensaje}"
    print(linea)
    with open(ARCHIVO_LOG, "a", encoding="utf-8") as log:
        log.write(linea + "\n")


# ------------------------------------------------------------
# BLOQUE 5. Solicitudes con pausa, reintentos y User-Agent identificable
# ------------------------------------------------------------
sesion = requests.Session()
sesion.headers.update({"User-Agent": USER_AGENT})


def solicitar(metodo, url, datos=None):
    for intento in range(1, INTENTOS_MAXIMOS + 1):
        try:
            time.sleep(PAUSA_SEGUNDOS)
            respuesta = sesion.request(metodo, url, data=datos, timeout=60)
            if respuesta.status_code == 200:
                return respuesta
            registrar(f"HTTP {respuesta.status_code} en {url[:70]} (intento {intento})")
        except requests.exceptions.RequestException as error:
            registrar(f"Error de conexión (intento {intento}): {error}")
        time.sleep(PAUSA_SEGUNDOS * intento)
    return None


def campos_formulario(html):
    """Lee todos los campos del formulario ASP.NET (ocultos, selects, radios) como diccionario."""
    sopa = BeautifulSoup(html, "html.parser")
    campos = {}
    for entrada in sopa.select("form input[name]"):
        tipo = (entrada.get("type") or "").lower()
        if tipo in ("submit", "image", "button", "checkbox", "radio"):
            continue
        campos[entrada["name"]] = entrada.get("value", "")
    for lista in sopa.select("form select[name]"):
        elegida = lista.find("option", selected=True) or lista.find("option")
        campos[lista["name"]] = elegida.get("value", "") if elegida else ""
    return campos, sopa


# ------------------------------------------------------------
# BLOQUE 6. Funciones para leer los estados financieros
# ------------------------------------------------------------
def a_numero(texto):
    """Convierte '1,461,048' -> 1461048 y '(69,227)' -> -69227."""
    texto = texto.strip().replace(",", "")
    if texto in ("", "-"):
        return None
    negativo = texto.startswith("(") and texto.endswith(")")
    texto = texto.strip("()")
    try:
        valor = float(texto)
    except ValueError:
        return None
    return -valor if negativo else valor


def normalizar(texto):
    """Minúsculas y un solo espacio entre palabras, para comparar nombres de cuentas."""
    return " ".join(texto.lower().split())


def leer_cuentas(sopa, id_tabla, cuentas, columna):
    """Devuelve {variable: valor} buscando cada cuenta en la tabla indicada.
    Si una cuenta aparece varias veces (corriente y no corriente), los valores se suman."""
    resultado = {}
    tabla = sopa.find("table", id=id_tabla)
    if tabla is None:
        return resultado
    nombres = {normalizar(n): variable for variable, lista in cuentas.items() for n in lista}
    for fila in tabla.find_all("tr"):
        celdas = [c.get_text(" ", strip=True) for c in fila.find_all("td")]
        if len(celdas) <= columna:
            continue
        variable = nombres.get(normalizar(celdas[0]))
        if variable:
            valor = a_numero(celdas[columna])
            if valor is not None:
                resultado[variable] = resultado.get(variable, 0) + valor
    return resultado


def leer_moneda(sopa):
    """Busca la unidad del reporte, por ejemplo '( EN MILES DE NUEVOS SOLES )'."""
    texto = sopa.get_text(" ", strip=True).upper()
    coincidencia = re.search(r"\(\s*EN ([A-ZÁÉÍÓÚÑ ]+?)\s*\)", texto)
    return coincidencia.group(1).strip() if coincidencia else "NO IDENTIFICADA"


# ------------------------------------------------------------
# BLOQUE 7. Búsqueda de una emisora y un año, y descarga de cada trimestre
# ------------------------------------------------------------
def campos_nuevos():
    """Vuelve a abrir la página de la SMV para obtener un formulario (y sesión) nuevos.
    La sesión ASP.NET caduca a los ~40 minutos; sin esto la búsqueda devuelve una tabla vacía."""
    pagina = solicitar("GET", URL_INFO)
    return campos_formulario(pagina.text)[0] if pagina is not None else None


def procesar_anio(ticker, id_empresa, nombre_empresa, anio, campos_iniciales, reintento=False):
    filas = []
    # 7.1 Enviar el formulario de búsqueda
    datos = dict(campos_iniciales)
    datos.update({
        "ctl00$MainContent$cboDenominacionSocial": id_empresa,
        "ctl00$MainContent$cboTipo": "I",          # I = Individual
        "ctl00$MainContent$cboPeriodo": "T",       # T = Trimestral
        "ctl00$MainContent$cboAnio": str(anio),
        "ctl00$MainContent$cboTrimestre": "-1",    # -1 = todos los trimestres
        "ctl00$MainContent$cbBuscar": "Buscar",
    })
    respuesta = solicitar("POST", URL_INFO, datos)
    if respuesta is None:
        registrar(f"{ticker} {anio}: falló la búsqueda")
        return filas
    campos_busqueda, sopa = campos_formulario(respuesta.text)

    # 7.2 Ubicar en la tabla de resultados las filas "Estados Financieros"
    botones = {}
    documentos = set()
    for fila in sopa.select("#MainContent_grdInfoFinanciera tr"):
        celdas = [c.get_text(" ", strip=True) for c in fila.find_all("td")]
        boton = fila.find("input", attrs={"type": "image"})
        if len(celdas) >= 5 and boton and celdas[0] in TRIMESTRES:
            documentos.add(celdas[2])
            if normalizar(celdas[2]).startswith("estados financieros"):
                # si hay rectificaciones, se queda la última presentada (la que aparece al final)
                botones[TRIMESTRES[celdas[0]]] = (boton["name"], celdas[3])
    if not botones and not documentos and not reintento:
        frescos = campos_nuevos()          # tabla vacía: probablemente caducó la sesión
        if frescos:
            return procesar_anio(ticker, id_empresa, nombre_empresa, anio, frescos, reintento=True)
    if not botones:
        registrar(f"{ticker} {anio}: sin estados financieros en la SMV "
                  f"(documentos encontrados: {sorted(documentos) or 'ninguno'})")

    # 7.3 "Pulsar" cada botón, seguir el enlace al detalle y guardar el HTML original
    for trimestre, (nombre_boton, expediente) in sorted(botones.items()):
        archivo_html = CARPETA_HTML / f"smv_{ticker}_{anio}_T{trimestre}_{CODIGO_MATRICULA}.html"
        if archivo_html.exists():      # permite reanudar sin volver a descargar
            html_detalle = archivo_html.read_text(encoding="utf-8")
        else:
            datos_boton = dict(campos_busqueda)
            datos_boton.pop("ctl00$MainContent$cbBuscar", None)
            datos_boton[nombre_boton + ".x"] = "10"
            datos_boton[nombre_boton + ".y"] = "10"
            respuesta_boton = solicitar("POST", URL_INFO, datos_boton)
            enlace = re.search(r"window\.open\('(Frm_DetalleInfoFinanciera[^']+)'",
                               respuesta_boton.text if respuesta_boton else "")
            if not enlace:
                registrar(f"{ticker} {anio} T{trimestre}: no se encontró el enlace al detalle")
                continue
            detalle = solicitar("GET", URL_BASE + enlace.group(1))
            if detalle is None:
                continue
            html_detalle = detalle.text
            archivo_html.write_text(html_detalle, encoding="utf-8")

        sopa_detalle = BeautifulSoup(html_detalle, "html.parser")
        # Balance: columna 2 = fecha de cierre del trimestre
        # Resultados: columna 2 = "Específico" del trimestre, columna 4 = "Acumulado" del año
        balance = leer_cuentas(sopa_detalle, "grdBalanceGeneral", CUENTAS_BALANCE, 2)
        resultados_trim = leer_cuentas(sopa_detalle, "grdEstadoGP", CUENTAS_RESULTADOS, 2)
        resultados_acum = leer_cuentas(sopa_detalle, "grdEstadoGP", CUENTAS_RESULTADOS, 4)

        fila = {
            "ticker": ticker,
            "empresa_smv": nombre_empresa,
            "anio": anio,
            "trimestre": trimestre,
            "expediente": expediente,
            "moneda": leer_moneda(sopa_detalle),
            **balance,
            **{f"{k}_trim": v for k, v in resultados_trim.items()},
            **{f"{k}_acum": v for k, v in resultados_acum.items()},
            "url_fuente": URL_INFO,
        }
        filas.append(fila)
        registrar(f"{ticker} {anio} T{trimestre}: HTTP 200, {len(balance) + len(resultados_trim)} cuentas leídas")
    return filas


# ------------------------------------------------------------
# BLOQUE 8. Programa principal
# ------------------------------------------------------------
def main():
    registrar("=== Inicio de scraping SMV ===")
    registrar(f"Parámetros: ANIO_INICIO={ANIO_INICIO}, ANIO_CORTE={ANIO_CORTE}")

    # 8.1 Revisar robots.txt (ética del scraping, numeral 2.4.8)
    robots = solicitar("GET", URL_ROBOTS)
    if robots is not None and "user-agent" in robots.text.lower()[:5000]:
        (CARPETA_CRUDOS / "smv_robots.txt").write_text(robots.text, encoding="utf-8")
        registrar("robots.txt: HTTP 200, guardado en datos_crudos/smv_robots.txt (revisar reglas Disallow)")
    elif robots is not None:
        registrar(f"robots.txt: la SMV no publica robots.txt (la dirección redirige a {robots.url}); "
                  "no hay rutas prohibidas declaradas")
    else:
        registrar("robots.txt: no disponible (se documenta en incidencias_fuente.md)")

    # 8.2 Abrir la página y leer la lista de emisoras
    inicio = solicitar("GET", URL_INFO)
    if inicio is None:
        registrar("No se pudo abrir la página de la SMV. Fin.")
        return
    campos_iniciales, sopa = campos_formulario(inicio.text)
    opciones = {o.get_text(strip=True): o.get("value")
                for o in sopa.select("#MainContent_cboDenominacionSocial option")}

    # Si se escriben tickers al ejecutar (py 02_scraping_web.py ALICORC1.LM), solo se procesan esos.
    # Sin argumentos se procesan todas las emisoras.
    elegidas = {t: p for t, p in EMISORAS_SMV.items() if not sys.argv[1:] or t in sys.argv[1:]}

    todas = []
    for ticker, patron in elegidas.items():
        coincidencias = [nombre for nombre in opciones if re.search(patron, nombre, re.IGNORECASE)]
        if not coincidencias:
            registrar(f"{ticker}: no se encontró en la lista de la SMV (patrón '{patron}')")
            continue
        nombre = coincidencias[0]
        registrar(f"{ticker}: emisora SMV = {nombre} (id {opciones[nombre]})")
        campos_iniciales = campos_nuevos() or campos_iniciales   # formulario nuevo para cada emisora
        for anio in range(ANIO_INICIO, ANIO_CORTE + 1):
            todas.extend(procesar_anio(ticker, opciones[nombre], nombre, anio, campos_iniciales))

    # 8.3 Guardar el crudo (tal como se leyó, sin limpiar)
    crudo = pd.DataFrame(todas)
    sufijo = "" if len(elegidas) == len(EMISORAS_SMV) else "_prueba"
    archivo = CARPETA_CRUDOS / f"datos_crudos_smv_{CODIGO_MATRICULA}{sufijo}.csv"
    crudo.to_csv(archivo, index=False, encoding="utf-8")
    registrar(f"Guardado {archivo.name}: {len(crudo)} filas (emisora-trimestre)")
    registrar("=== Fin de scraping SMV ===")

    if not crudo.empty:
        print(crudo.groupby("ticker")["anio"].agg(["min", "max", "count"]))


if __name__ == "__main__":
    main()
