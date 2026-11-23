# Autora: Andrea Nicolle Sinche De La Cruz
# Código de matrícula: 2024200529I
# Tema 57: Estimación del WACC de las empresas listadas en la Bolsa de Valores de Lima
# Fecha de extracción: 2026-11-22

"""
01_extraccion_api.py
Vía 1 (API). Descarga:
  (a) precios diarios de las emisoras de la BVL y del índice general (Yahoo Finance, librería yfinance)
  (b) rendimiento del bono del Tesoro de EE. UU. a 10 años, tasa libre de riesgo (API de BCRPData)
y guarda los datos crudos tal como salen de la fuente.
Con estos datos, el script 04 calcula retornos, beta y costo del patrimonio (Ke).
"""

# ------------------------------------------------------------
# BLOQUE 1. Librerías
# ------------------------------------------------------------
import time
import warnings
from datetime import datetime
from pathlib import Path

import pandas as pd
import requests
import yfinance as yf

warnings.filterwarnings("ignore")  # oculta avisos (FutureWarning) que no son errores

# ------------------------------------------------------------
# BLOQUE 2. Parámetros congelados de la consulta (numeral 2.4.5)
# No se usan fechas dinámicas tipo "hoy": así la consulta es reproducible.
# ------------------------------------------------------------
FECHA_INICIO = "2015-01-01"
FECHA_CORTE = "2025-12-31"
# Los precios empiezan 3 años antes: la beta del 2015 necesita 36 meses previos de rendimientos
FECHA_INICIO_PRECIOS = "2012-01-01"
CODIGO_MATRICULA = "2024200529I"

# Proxy del mercado peruano para la beta: fondo iShares MSCI Peru (EPU).
# (El índice S&P/BVL ^SPBLPGPT no está disponible en Yahoo Finance: se probó el 22/11/2026.)
INDICE = "EPU"

# Emisoras NO financieras (en bancos la deuda son depósitos: no aplica el WACC usual)
# Ticker -> sector. Los que no tengan historia desde 2015 se reemplazan.
EMISORAS = {
    "ALICORC1.LM": "Consumo",
    "BACKUSI1.LM": "Consumo",
    "INRETC1.LM": "Consumo",
    "FERREYC1.LM": "Industrial",
    "UNACEMC1.LM": "Construcción",
    "CPACASC1.LM": "Construcción",
    "CORAREI1.LM": "Siderurgia",
    "SIDERC1.LM": "Siderurgia",
    "BVN": "Minería",
    "SCCO": "Minería",
    "MINSURI1.LM": "Minería",
    "CVERDEC1.LM": "Minería",
    "VOLCABC1.LM": "Minería",
    "ENGIEC1.LM": "Energía",
    "LUSURC1.LM": "Energía",
    "NEXAPEC1.LM": "Minería",
    "ATACOBC1.LM": "Minería",
    "BROCALI1.LM": "Minería",
    "MOROCOI1.LM": "Minería",
    "AIHC1.LM": "Infraestructura",
    "AUSTRAC1.LM": "Pesca",
    "CREDITC1.LM": "Textil",
}

# BCRPData: rendimiento del bono del Tesoro de EE. UU. a 10 años (%), diario
# (la misma serie que usé en la Unidad I)
SERIE_RF = "PD04719XD"
URL_BCRP = "https://estadisticas.bcrp.gob.pe/estadisticas/series/api"

USER_AGENT = "UNCP-Finanzas-I/1.0 (e_2024200529I@uncp.edu.pe)"
PAUSA_SEGUNDOS = 1           # pausa mínima entre solicitudes
INTENTOS_MAXIMOS = 3         # reintentos si la solicitud falla

# ------------------------------------------------------------
# BLOQUE 3. Rutas relativas a la carpeta del proyecto (sin C:\Users\...)
# ------------------------------------------------------------
RAIZ = Path(__file__).resolve().parent.parent
CARPETA_CRUDOS = RAIZ / "datos_crudos"
ARCHIVO_LOG = RAIZ / "log_ejecucion.txt"
CARPETA_CRUDOS.mkdir(exist_ok=True)


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
# BLOQUE 5. Descarga de precios de Yahoo Finance con manejo de errores
# ------------------------------------------------------------
def descargar_precios(ticker):
    for intento in range(1, INTENTOS_MAXIMOS + 1):
        try:
            datos = yf.download(ticker, start=FECHA_INICIO_PRECIOS, end=FECHA_CORTE,
                                auto_adjust=True, progress=False)
            if not datos.empty:
                # yfinance a veces devuelve columnas de dos niveles: se aplanan
                if isinstance(datos.columns, pd.MultiIndex):
                    datos.columns = datos.columns.get_level_values(0)
                tabla = datos[["Close", "Volume"]].reset_index()
                tabla.columns = ["fecha", "precio_cierre", "volumen"]
                tabla["ticker"] = ticker
                return tabla
            registrar(f"{ticker}: 0 filas (intento {intento})")
        except Exception as error:
            registrar(f"{ticker}: error (intento {intento}): {error}")
        time.sleep(PAUSA_SEGUNDOS * intento)
    return None


# ------------------------------------------------------------
# BLOQUE 6. Descarga de la tasa libre de riesgo desde BCRPData
# ------------------------------------------------------------
def descargar_bcrp(codigo):
    url = f"{URL_BCRP}/{codigo}/json/{FECHA_INICIO}/{FECHA_CORTE}/esp"
    for intento in range(1, INTENTOS_MAXIMOS + 1):
        try:
            respuesta = requests.get(url, headers={"User-Agent": USER_AGENT}, timeout=60)
            if respuesta.status_code == 200:
                return respuesta, url
            registrar(f"{codigo}: HTTP {respuesta.status_code} (intento {intento})")
        except requests.exceptions.RequestException as error:
            registrar(f"{codigo}: error de conexión (intento {intento}): {error}")
        time.sleep(PAUSA_SEGUNDOS * intento)
    return None, url


# ------------------------------------------------------------
# BLOQUE 7. Programa principal
# ------------------------------------------------------------
def main():
    registrar("=== Inicio de extracción API (Yahoo Finance + BCRPData) ===")
    registrar(f"Parámetros: FECHA_INICIO={FECHA_INICIO} (precios desde {FECHA_INICIO_PRECIOS}), FECHA_CORTE={FECHA_CORTE}")

    # 7.1 Precios de emisoras e índice
    tablas, fallidas = [], []
    for ticker in list(EMISORAS) + [INDICE]:
        tabla = descargar_precios(ticker)
        if tabla is None:
            registrar(f"{ticker}: NO se pudo descargar.")
            fallidas.append(ticker)
        else:
            tabla["sector"] = EMISORAS.get(ticker, "Índice de mercado")
            tablas.append(tabla)
            registrar(f"{ticker}: HTTP 200, {len(tabla)} filas descargadas "
                      f"(desde {tabla['fecha'].min():%Y-%m-%d})")
        time.sleep(PAUSA_SEGUNDOS)

    precios = pd.concat(tablas, ignore_index=True)
    archivo = CARPETA_CRUDOS / f"datos_crudos_yahoo_{CODIGO_MATRICULA}.csv"
    precios.to_csv(archivo, index=False, encoding="utf-8")
    registrar(f"Guardado {archivo.name}: {len(precios)} filas, {precios['ticker'].nunique()} tickers")

    # 7.2 Tasa libre de riesgo (BCRPData): se guarda la respuesta exacta
    respuesta, url = descargar_bcrp(SERIE_RF)
    if respuesta is None:
        registrar(f"{SERIE_RF}: NO se pudo descargar.")
        fallidas.append(SERIE_RF)
    else:
        archivo_json = CARPETA_CRUDOS / f"bcrp_{SERIE_RF}_{CODIGO_MATRICULA}.json"
        archivo_json.write_text(respuesta.text, encoding="utf-8")
        registrar(f"{SERIE_RF} (tesoro_eeuu_10a): HTTP {respuesta.status_code}, guardado {archivo_json.name}")

    if fallidas:
        registrar(f"ATENCIÓN: no descargados: {', '.join(fallidas)}")
    registrar("=== Fin de extracción API ===")

    # Resumen en pantalla: primera fecha, última fecha y filas por ticker
    print(precios.groupby("ticker")["fecha"].agg(["min", "max", "count"]))


if __name__ == "__main__":
    main()
