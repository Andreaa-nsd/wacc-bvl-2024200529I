# Autora: Andrea Nicolle Sinche De La Cruz
# Código de matrícula: 2024200529I
# Tema 57: Estimación del WACC de las empresas listadas en la Bolsa de Valores de Lima
# Fecha de extracción: 2026-11-22

"""
04_analisis.py
A partir de la base procesada (script 03) estima, para cada emisora y trimestre:
  beta  : pendiente de la regresión de rendimientos mensuales de la acción contra el mercado (EPU),
          con los 36 meses previos (mínimo 24)
  Ke    : costo del patrimonio por CAPM = rf + beta * prima de riesgo de mercado
  Kd    : costo de la deuda = gastos financieros anualizados / deuda financiera
  t     : tasa efectiva de impuesto = impuesto / utilidad antes de impuestos
  WACC  = E/(D+E) * Ke + D/(D+E) * Kd * (1 - t)
Guarda la base con el WACC, tablas descriptivas, gráficos y una simulación de Monte Carlo.
"""

# ------------------------------------------------------------
# BLOQUE 1. Librerías
# ------------------------------------------------------------
from datetime import datetime
from pathlib import Path

import matplotlib
matplotlib.use("Agg")                   # guarda los gráficos sin abrir ventanas
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

# ------------------------------------------------------------
# BLOQUE 2. Parámetros del modelo
# ------------------------------------------------------------
CODIGO_MATRICULA = "2024200529I"
SEMILLA = 529                           # últimos dígitos del código, para la simulación
VENTANA_BETA = 36                       # meses para estimar la beta
MINIMO_MESES = 24
PRIMA_RIESGO_MERCADO = 0.06             # prima de mercado + riesgo país (Damodaran); citar la fuente en el artículo
TASA_IMPUESTO_LEGAL = 0.295             # impuesto a la renta en el Perú; se usa si la tasa efectiva no es válida
LIMITE_KD = (0.0, 0.30)                 # Kd fuera de este rango se considera dato atípico
SIMULACIONES = 10_000

RAIZ = Path(__file__).resolve().parent.parent
CARPETA_PROCESADOS = RAIZ / "datos_procesados"
CARPETA_SALIDAS = RAIZ / "salidas"
ARCHIVO_LOG = RAIZ / "log_ejecucion.txt"
CARPETA_SALIDAS.mkdir(exist_ok=True)


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
# BLOQUE 4. Beta móvil con rendimientos mensuales
# ------------------------------------------------------------
def calcular_betas(mensual):
    """Para cada emisora y cada fin de trimestre, beta = cov(Ri, Rm) / var(Rm) de los 36 meses previos."""
    mensual = mensual.dropna(subset=["rendimiento", "rendimiento_mercado"]).copy()
    mensual["mes"] = pd.PeriodIndex(mensual["mes"], freq="M")
    filas = []
    for ticker, grupo in mensual.groupby("ticker"):
        grupo = grupo.set_index("mes").sort_index()
        for mes in grupo.index[grupo.index.month % 3 == 0]:          # meses de cierre de trimestre
            ventana = grupo.loc[mes - VENTANA_BETA + 1: mes]
            if len(ventana) < MINIMO_MESES:
                continue
            x, y = ventana["rendimiento_mercado"], ventana["rendimiento"]
            beta = np.cov(y, x)[0, 1] / np.var(x, ddof=1)
            residuos = y - (y.mean() - beta * x.mean()) - beta * x
            error_beta = np.sqrt(residuos.var(ddof=2) / ((x - x.mean()) ** 2).sum())
            filas.append({"ticker": ticker, "periodo": str(mes.asfreq("Q")),
                          "beta": beta, "error_beta": error_beta, "meses_beta": len(ventana)})
    return pd.DataFrame(filas)


# ------------------------------------------------------------
# BLOQUE 5. Componentes del WACC
# ------------------------------------------------------------
def calcular_wacc(base):
    b = base.copy()
    rf = b["rf_anual_pct"] / 100

    # Ke por CAPM
    b["ke"] = rf + b["beta"] * PRIMA_RIESGO_MERCADO

    # Kd: los gastos financieros acumulados del año se llevan a 12 meses
    gastos_anuales = b["gastos_financieros_acum"] * 4 / b["trimestre"]
    b["kd"] = np.where(b["deuda_financiera"] > 0, gastos_anuales / b["deuda_financiera"], np.nan)
    b.loc[(b["kd"] < LIMITE_KD[0]) | (b["kd"] > LIMITE_KD[1]), "kd"] = np.nan

    # Tasa efectiva de impuesto; si no es válida (pérdidas o fuera de 0-50 %) se usa la legal
    tasa = b["impuesto_acum"] / b["utilidad_antes_impuestos_acum"]
    valida = (b["utilidad_antes_impuestos_acum"] > 0) & tasa.between(0, 0.5)
    b["t"] = np.where(valida, tasa, TASA_IMPUESTO_LEGAL)
    b["t_es_legal"] = ~valida

    # Pesos con valores contables (D = deuda financiera, E = patrimonio)
    valida_estructura = (b["patrimonio"] > 0) & (b["deuda_financiera"] >= 0)
    total = b["deuda_financiera"] + b["patrimonio"]
    b["peso_deuda"] = np.where(valida_estructura, b["deuda_financiera"] / total, np.nan)
    b["peso_patrimonio"] = 1 - b["peso_deuda"]

    # Sin deuda financiera el WACC es igual al Ke
    kd_efectivo = np.where(b["peso_deuda"] == 0, 0, b["kd"])
    b["wacc"] = b["peso_patrimonio"] * b["ke"] + b["peso_deuda"] * kd_efectivo * (1 - b["t"])
    return b


# ------------------------------------------------------------
# BLOQUE 6. Simulación de Monte Carlo del WACC (último trimestre de cada emisora)
# ------------------------------------------------------------
def simular_wacc(resultado):
    generador = np.random.default_rng(SEMILLA)
    ultimo = resultado.dropna(subset=["wacc"]).sort_values("periodo").groupby("ticker").tail(1)
    filas = []
    for _, fila in ultimo.iterrows():
        betas = generador.normal(fila["beta"], fila["error_beta"], SIMULACIONES)
        primas = generador.normal(PRIMA_RIESGO_MERCADO, 0.01, SIMULACIONES)
        ke = fila["rf_anual_pct"] / 100 + betas * primas
        kd = fila["kd"] if fila["peso_deuda"] > 0 else 0
        wacc = fila["peso_patrimonio"] * ke + fila["peso_deuda"] * kd * (1 - fila["t"])
        filas.append({"ticker": fila["ticker"], "periodo": fila["periodo"], "wacc_estimado": fila["wacc"],
                      "wacc_p5": np.percentile(wacc, 5), "wacc_mediana": np.median(wacc),
                      "wacc_p95": np.percentile(wacc, 95)})
    return pd.DataFrame(filas)


# ------------------------------------------------------------
# BLOQUE 7. Gráficos
# ------------------------------------------------------------
def graficar(resultado):
    anual = resultado.groupby(["anio", "sector"])["wacc"].median().unstack()
    figura, eje = plt.subplots(figsize=(9, 5))
    (anual * 100).plot(ax=eje, marker="o")
    eje.set_title("WACC mediano por sector, 2015-2025")
    eje.set_xlabel("Año")
    eje.set_ylabel("WACC (%)")
    eje.grid(alpha=0.3)
    figura.tight_layout()
    figura.savefig(CARPETA_SALIDAS / f"fig1_wacc_sector_{CODIGO_MATRICULA}.png", dpi=200)
    plt.close(figura)

    orden = resultado.groupby("ticker")["wacc"].median().sort_values().index
    datos = [resultado.loc[resultado["ticker"] == t, "wacc"].dropna() * 100 for t in orden]
    figura, eje = plt.subplots(figsize=(10, 5))
    eje.boxplot(datos, tick_labels=[t.replace(".LM", "") for t in orden])
    eje.set_title("Distribución del WACC trimestral por emisora")
    eje.set_ylabel("WACC (%)")
    eje.tick_params(axis="x", rotation=60)
    eje.grid(alpha=0.3, axis="y")
    figura.tight_layout()
    figura.savefig(CARPETA_SALIDAS / f"fig2_wacc_emisora_{CODIGO_MATRICULA}.png", dpi=200)
    plt.close(figura)


# ------------------------------------------------------------
# BLOQUE 8. Programa principal
# ------------------------------------------------------------
def main():
    registrar("=== Inicio de análisis WACC ===")
    base = pd.read_csv(CARPETA_PROCESADOS / f"datos_procesados_{CODIGO_MATRICULA}.csv",
                       dtype={"expediente": str})
    mensual = pd.read_csv(CARPETA_PROCESADOS / f"rendimientos_mensuales_{CODIGO_MATRICULA}.csv")

    betas = calcular_betas(mensual)
    registrar(f"Betas estimadas: {len(betas)} emisora-trimestre (ventana {VENTANA_BETA} meses)")

    resultado = calcular_wacc(base.merge(betas, on=["ticker", "periodo"], how="left"))
    completos = resultado["wacc"].notna().sum()
    registrar(f"WACC calculado en {completos} de {len(resultado)} observaciones "
              f"({resultado['t_es_legal'].sum()} con tasa de impuesto legal)")

    # Referencia: prima histórica del mercado en la muestra (para comparar con el parámetro)
    rm_anual = (1 + mensual.drop_duplicates("mes")["rendimiento_mercado"].dropna()).prod() ** \
               (12 / mensual["mes"].nunique()) - 1
    registrar(f"Rendimiento anual promedio del mercado (EPU) en la muestra: {rm_anual:.2%}; "
              f"prima usada: {PRIMA_RIESGO_MERCADO:.2%}")

    resultado.to_csv(CARPETA_SALIDAS / f"wacc_trimestral_{CODIGO_MATRICULA}.csv", index=False, encoding="utf-8")

    variables = ["beta", "ke", "kd", "t", "peso_deuda", "wacc"]
    descriptivos = resultado[variables].describe().T
    descriptivos.to_csv(CARPETA_SALIDAS / f"tabla1_descriptivos_{CODIGO_MATRICULA}.csv", encoding="utf-8")
    por_sector = resultado.groupby("sector")[variables].median()
    por_sector.to_csv(CARPETA_SALIDAS / f"tabla2_mediana_sector_{CODIGO_MATRICULA}.csv", encoding="utf-8")
    por_emisora = resultado.groupby(["ticker", "sector"])[variables].median()
    por_emisora.to_csv(CARPETA_SALIDAS / f"tabla3_mediana_emisora_{CODIGO_MATRICULA}.csv", encoding="utf-8")

    simulacion = simular_wacc(resultado)
    simulacion.to_csv(CARPETA_SALIDAS / f"tabla4_montecarlo_{CODIGO_MATRICULA}.csv", index=False, encoding="utf-8")
    registrar(f"Monte Carlo: {SIMULACIONES} simulaciones por emisora (semilla {SEMILLA})")

    graficar(resultado)
    registrar("Guardadas tablas 1-4 y figuras 1-2 en salidas/")
    registrar("=== Fin de análisis WACC ===")

    pd.set_option("display.float_format", "{:.4f}".format)
    print("\nMediana por emisora:")
    print(por_emisora)


if __name__ == "__main__":
    main()
