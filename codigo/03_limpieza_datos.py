# Autora: Andrea Nicolle Sinche De La Cruz
# Código de matrícula: 2024200529I
# Tema 57: Estimación del WACC de las empresas listadas en la Bolsa de Valores de Lima
# Fecha de extracción: 2026-11-22

"""
03_limpieza_datos.py
Limpia y une las tres fuentes crudas en una sola base trimestral (llave: ticker + año + trimestre):
  (a) precios diarios de Yahoo Finance  -> precio de cierre y rendimiento trimestral
  (b) estados financieros de la SMV     -> deuda financiera, patrimonio, gastos financieros, impuestos
  (c) bono del Tesoro EE. UU. 10 años (BCRPData) -> tasa libre de riesgo promedio del trimestre
Además guarda los rendimientos mensuales, que el script 04 usa para estimar la beta.
No modifica los archivos crudos: solo los lee.
"""

# ------------------------------------------------------------
# BLOQUE 1. Librerías
# ------------------------------------------------------------
import json
from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd

# ------------------------------------------------------------
# BLOQUE 2. Parámetros y rutas relativas
# ------------------------------------------------------------
CODIGO_MATRICULA = "2024200529I"
FECHA_INICIO = "2015-01-01"
FECHA_CORTE = "2025-12-31"
INDICE = "EPU"

RAIZ = Path(__file__).resolve().parent.parent
CARPETA_CRUDOS = RAIZ / "datos_crudos"
CARPETA_PROCESADOS = RAIZ / "datos_procesados"
ARCHIVO_LOG = RAIZ / "log_ejecucion.txt"
CARPETA_PROCESADOS.mkdir(exist_ok=True)

ARCHIVO_YAHOO = CARPETA_CRUDOS / f"datos_crudos_yahoo_{CODIGO_MATRICULA}.csv"
ARCHIVO_SMV = CARPETA_CRUDOS / f"datos_crudos_smv_{CODIGO_MATRICULA}.csv"
ARCHIVO_BCRP = CARPETA_CRUDOS / f"bcrp_PD04719XD_{CODIGO_MATRICULA}.json"

MESES_BCRP = {"Ene": 1, "Feb": 2, "Mar": 3, "Abr": 4, "May": 5, "Jun": 6,
              "Jul": 7, "Ago": 8, "Set": 9, "Sep": 9, "Oct": 10, "Nov": 11, "Dic": 12}


# ------------------------------------------------------------
# BLOQUE 3. Registro en pantalla y en log_ejecucion.txt
# ------------------------------------------------------------
def registrar(mensaje):
    marca = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    linea = f"[{marca}] {mensaje}"
    print(linea)
    with open(ARCHIVO_LOG, "a", encoding="utf-8") as log:
        log.write(linea + "\n")


# ------------------------------------------------------------
# BLOQUE 4. Yahoo Finance: de precios diarios a datos trimestrales y mensuales
# ------------------------------------------------------------
def preparar_yahoo():
    precios = pd.read_csv(ARCHIVO_YAHOO, parse_dates=["fecha"])
    filas_antes = len(precios)
    precios = precios.dropna(subset=["precio_cierre"])
    precios = precios[precios["precio_cierre"] > 0]
    precios = precios.drop_duplicates(subset=["ticker", "fecha"]).sort_values(["ticker", "fecha"])
    registrar(f"Yahoo: {filas_antes} filas crudas, {len(precios)} tras quitar vacíos, ceros y duplicados")

    # Último precio de cada mes y de cada trimestre (precio de cierre del periodo)
    precios["mes"] = precios["fecha"].dt.to_period("M")
    precios["periodo"] = precios["fecha"].dt.to_period("Q")
    mensual = precios.groupby(["ticker", "mes"]).agg(precio_cierre=("precio_cierre", "last")).reset_index()
    mensual["rendimiento"] = mensual.groupby("ticker")["precio_cierre"].pct_change(fill_method=None)

    trimestral = precios.groupby(["ticker", "periodo"]).agg(
        sector=("sector", "first"),
        precio_cierre_trim=("precio_cierre", "last"),
        volumen_trim=("volumen", "sum"),
        dias_negociados=("volumen", lambda v: int((v > 0).sum())),
    ).reset_index()
    trimestral["rendimiento_trim"] = trimestral.groupby("ticker")["precio_cierre_trim"].pct_change(fill_method=None)

    # El índice (EPU) va como columna aparte: rendimiento del mercado
    mercado_t = trimestral[trimestral["ticker"] == INDICE][["periodo", "rendimiento_trim"]]
    mercado_t = mercado_t.rename(columns={"rendimiento_trim": "rendimiento_mercado_trim"})
    trimestral = trimestral[trimestral["ticker"] != INDICE].merge(mercado_t, on="periodo", how="left")

    mercado_m = mensual[mensual["ticker"] == INDICE][["mes", "rendimiento"]]
    mercado_m = mercado_m.rename(columns={"rendimiento": "rendimiento_mercado"})
    mensual = mensual[mensual["ticker"] != INDICE].merge(mercado_m, on="mes", how="left")
    return trimestral, mensual


# ------------------------------------------------------------
# BLOQUE 5. BCRPData: tasa libre de riesgo (promedio del trimestre y del mes)
# ------------------------------------------------------------
def leer_fecha_bcrp(texto):
    dia, mes, anio = texto.split(".")           # formato "02.Ene.15"
    return pd.Timestamp(2000 + int(anio), MESES_BCRP[mes], int(dia))


def preparar_bcrp():
    datos = json.loads(ARCHIVO_BCRP.read_text(encoding="utf-8"))
    filas = []
    for periodo in datos["periods"]:
        valor = periodo["values"][0]
        if valor in ("n.d.", "", None):         # días sin dato (feriados)
            continue
        filas.append({"fecha": leer_fecha_bcrp(periodo["name"]), "rf": float(valor)})
    rf = pd.DataFrame(filas)
    registrar(f"BCRP: {len(datos['periods'])} días crudos, {len(rf)} con dato")
    rf["periodo"] = rf["fecha"].dt.to_period("Q")
    rf["mes"] = rf["fecha"].dt.to_period("M")
    rf_trim = rf.groupby("periodo")["rf"].mean().rename("rf_anual_pct").reset_index()
    rf_mes = rf.groupby("mes")["rf"].mean().rename("rf_anual_pct").reset_index()
    return rf_trim, rf_mes


# ------------------------------------------------------------
# BLOQUE 6. SMV: estados financieros trimestrales
# ------------------------------------------------------------
def preparar_smv():
    smv = pd.read_csv(ARCHIVO_SMV, dtype={"expediente": str})
    filas_antes = len(smv)
    # Si una empresa rectificó su reporte, se queda el último expediente presentado
    smv = smv.sort_values("expediente").drop_duplicates(["ticker", "anio", "trimestre"], keep="last")
    smv["periodo"] = pd.PeriodIndex.from_fields(year=smv["anio"], quarter=smv["trimestre"], freq="Q")
    registrar(f"SMV: {filas_antes} filas crudas, {len(smv)} tras quitar rectificaciones duplicadas")

    # Nombres más claros para las variables que usa el WACC
    smv = smv.rename(columns={
        "otros_pasivos_financieros": "deuda_financiera",
        "total_patrimonio": "patrimonio",
    })
    # Los gastos financieros y el impuesto vienen con signo negativo (son gastos): se pasan a positivo
    for columna in ["gastos_financieros_trim", "gastos_financieros_acum"]:
        smv[columna] = smv[columna].abs()
    for columna in ["impuesto_trim", "impuesto_acum"]:
        smv[columna] = -smv[columna]
    columnas = ["ticker", "periodo", "empresa_smv", "expediente", "moneda",
                "deuda_financiera", "total_pasivos", "patrimonio",
                "ingresos_trim", "gastos_financieros_trim", "gastos_financieros_acum",
                "utilidad_antes_impuestos_acum", "impuesto_acum", "utilidad_neta_trim"]
    return smv[[c for c in columnas if c in smv.columns]]


# ------------------------------------------------------------
# BLOQUE 7. Programa principal: unión por la llave ticker + periodo
# ------------------------------------------------------------
def main():
    registrar("=== Inicio de limpieza y unión ===")
    trimestral, mensual = preparar_yahoo()
    rf_trim, rf_mes = preparar_bcrp()
    smv = preparar_smv()

    base = (trimestral.merge(smv, on=["ticker", "periodo"], how="inner")
                      .merge(rf_trim, on="periodo", how="left"))
    base = base[(base["periodo"] >= pd.Period(FECHA_INICIO, "Q")) &
                (base["periodo"] <= pd.Period(FECHA_CORTE, "Q"))]
    base.insert(1, "anio", base["periodo"].dt.year)
    base.insert(2, "trimestre", base["periodo"].dt.quarter)
    base["periodo"] = base["periodo"].astype(str)
    base = base.sort_values(["ticker", "anio", "trimestre"]).reset_index(drop=True)

    sin_smv = sorted(set(trimestral["ticker"]) - set(smv["ticker"]))
    if sin_smv:
        registrar(f"Emisoras con precios pero sin estados financieros SMV: {', '.join(sin_smv)}")

    archivo = CARPETA_PROCESADOS / f"datos_procesados_{CODIGO_MATRICULA}.csv"
    base.to_csv(archivo, index=False, encoding="utf-8")
    registrar(f"Guardado {archivo.name}: {len(base)} filas, {base['ticker'].nunique()} emisoras, "
              f"{base.shape[1]} columnas")

    mensual = mensual.merge(rf_mes, on="mes", how="left")
    mensual["mes"] = mensual["mes"].astype(str)
    archivo_m = CARPETA_PROCESADOS / f"rendimientos_mensuales_{CODIGO_MATRICULA}.csv"
    mensual.to_csv(archivo_m, index=False, encoding="utf-8")
    registrar(f"Guardado {archivo_m.name}: {len(mensual)} filas")
    registrar("=== Fin de limpieza y unión ===")

    # Resumen: observaciones por emisora y valores faltantes por columna
    print(base.groupby("ticker")["periodo"].agg(["min", "max", "count"]))
    print("\nValores faltantes por columna:")
    print(base.isna().sum()[lambda s: s > 0])


if __name__ == "__main__":
    main()
