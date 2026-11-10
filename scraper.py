import pandas as pd
import requests
from io import StringIO
import os
from datetime import datetime

# --- CONFIGURACIÓN ---
# URL de la tabla "Playing Time" de Colo-Colo en FBref para la temporada actual
# NOTA: Debes reemplazar '2026' por el año de la temporada que quieres trackear.
# FBref usa el año de finalización de la temporada (ej. 2026 para la 2025-2026).
URL_FBREF = "https://fbref.com/en/squads/09799d9a/2026/Colo-Colo-Stats"
RUTA_DATA = "data/data.csv"
RUTA_JUGADORES = "data/jugadores.csv"

def extraer_tabla_fbref():
    """Extrae la tabla de 'Playing Time' desde FBref, manejando comentarios HTML."""
    print("Conectando a FBref...")
    response = requests.get(URL_FBREF)
    response.raise_for_status()

    # FBref a veces comenta las tablas. Eliminamos los tags de comentario.
    html_limpio = response.text.replace('<!--', '').replace('-->', '')

    # Buscamos la tabla por su ID. En la página de un equipo, el id suele ser "stats_playing_time"
    try:
        tabla = pd.read_html(StringIO(html_limpio), attrs={'id': 'stats_playing_time'})[0]
    except ValueError:
        print("No se encontró la tabla 'stats_playing_time'. La estructura de FBref pudo haber cambiado.")
        return None

    return tabla

def limpiar_y_agregar_datos(tabla_cruda):
    """Limpia y transforma la tabla de FBref para que coincida con tu data.csv."""
    if tabla_cruda is None:
        return

    print("Limpiando datos...")
    df = tabla_cruda.copy()

    # Seleccionar y renombrar columnas para que coincidan con tu CSV
    df = df[['Player', 'Pos', 'Age', 'Min']]
    df.columns = ['jugador', 'posicion', 'edad', 'minutos']

    # Limpiar la columna 'edad' (FBref a veces la formatea como "25-123")
    df['edad'] = df['edad'].astype(str).str.split('-').str[0]
    df['edad'] = pd.to_numeric(df['edad'], errors='coerce').fillna(0).astype(int)

    # Limpiar 'minutos' (por si trae comas o valores nulos)
    df['minutos'] = df['minutos'].astype(str).str.replace(',', '', regex=False)
    df['minutos'] = pd.to_numeric(df['minutos'], errors='coerce').fillna(0).astype(int)

    # Agregar la columna 'temporada' (usamos el año en curso)
    df['temporada'] = datetime.now().year

    # Filtrar filas que sean totales del equipo (a veces FBref agrega una fila "Squad Total")
    df = df[~df['jugador'].astype(str).str.contains('Total|Squad', case=False, na=False)]

    return df

def actualizar_csv(df_nuevo):
    """Agrega los nuevos datos al data.csv existente, evitando duplicados."""
    if os.path.exists(RUTA_DATA):
        df_existente = pd.read_csv(RUTA_DATA, encoding='utf-8-sig')

        # Si ya existen datos para esta temporada, los reemplazamos para evitar duplicados
        df_existente = df_existente[df_existente['temporada'] != df_nuevo['temporada'].iloc[0]]

        # Concatenar y guardar
        df_final = pd.concat([df_existente, df_nuevo], ignore_index=True)
        df_final.to_csv(RUTA_DATA, index=False, encoding='utf-8-sig')
        print(f"Datos de la temporada {df_nuevo['temporada'].iloc[0]} actualizados en {RUTA_DATA}")
    else:
        df_nuevo.to_csv(RUTA_DATA, index=False, encoding='utf-8-sig')
        print("Archivo data.csv creado con los primeros datos.")

def main():
    print("Iniciando pipeline ETL...")
    tabla = extraer_tabla_fbref()
    if tabla is not None:
        df_limpio = limpiar_y_agregar_datos(tabla)
        actualizar_csv(df_limpio)
    else:
        print("El pipeline falló al extraer la tabla.")

if __name__ == "__main__":
    main()
