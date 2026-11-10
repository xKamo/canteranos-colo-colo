import pandas as pd
import requests
from io import StringIO
import os
import time
from datetime import datetime

# --- CONFIGURACIÓN ---
URL_FBREF = "https://fbref.com/en/squads/09799d9a/2026/Colo-Colo-Stats"
RUTA_DATA = "data/data.csv"

def extraer_tabla_fbref():
    """Extrae la tabla de 'Playing Time' desde FBref, manejando comentarios HTML."""
    print("Conectando a FBref...")

    # --- SOLUCIÓN AL BLOQUEO: Cabeceras de navegador real ---
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept-Language': 'en-US,en;q=0.9',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8'
    }

    try:
        # Hacemos la petición con las cabeceras y un timeout de 15 seg
        response = requests.get(URL_FBREF, headers=headers, timeout=15)

        # Si FBref nos bloquea, esto lanzará un error explícito
        if response.status_code == 403:
            print("Error 403: FBref bloqueó la petición. Intenta de nuevo más tarde.")
            return None

        response.raise_for_status()

        # Eliminamos los tags de comentario que esconde FBref
        html_limpio = response.text.replace('<!--', '').replace('-->', '')

        # Buscamos la tabla por su ID
        tablas = pd.read_html(StringIO(html_limpio), attrs={'id': 'stats_playing_time'})
        if not tablas:
            print("No se encontró la tabla 'stats_playing_time'.")
            return None

        return tablas[0]

    except requests.exceptions.RequestException as e:
        print(f"Error de conexión: {e}")
        return None
    except ValueError as e:
        print(f"Error al parsear HTML (posible cambio en FBref): {e}")
        return None

def limpiar_y_agregar_datos(tabla_cruda):
    if tabla_cruda is None:
        return None

    print("Limpiando datos...")
    df = tabla_cruda.copy()

    # Seleccionar y renombrar columnas
    df = df[['Player', 'Pos', 'Age', 'Min']]
    df.columns = ['jugador', 'posicion', 'edad', 'minutos']

    # Limpiar la columna 'edad'
    df['edad'] = df['edad'].astype(str).str.split('-').str[0]
    df['edad'] = pd.to_numeric(df['edad'], errors='coerce').fillna(0).astype(int)

    # Limpiar 'minutos'
    df['minutos'] = df['minutos'].astype(str).str.replace(',', '', regex=False)
    df['minutos'] = pd.to_numeric(df['minutos'], errors='coerce').fillna(0).astype(int)

    # Agregar la columna 'temporada'
    df['temporada'] = 2026 # Dejamos el año fijo para evitar problemas si el robot corre en enero

    # Filtrar filas de totales
    df = df[~df['jugador'].astype(str).str.contains('Total|Squad', case=False, na=False)]

    return df

def actualizar_csv(df_nuevo):
    if df_nuevo is None or df_nuevo.empty:
        print("No hay datos nuevos para guardar.")
        return

    if os.path.exists(RUTA_DATA):
        df_existente = pd.read_csv(RUTA_DATA, encoding='utf-8-sig')
        # Borramos la temporada que vamos a actualizar para no duplicar
        df_existente = df_existente[df_existente['temporada'] != df_nuevo['temporada'].iloc[0]]

        df_final = pd.concat([df_existente, df_nuevo], ignore_index=True)
        df_final.to_csv(RUTA_DATA, index=False, encoding='utf-8-sig')
        print(f"Datos de la temporada {df_nuevo['temporada'].iloc[0]} actualizados en {RUTA_DATA}")
    else:
        df_nuevo.to_csv(RUTA_DATA, index=False, encoding='utf-8-sig')
        print("Archivo data.csv creado con los primeros datos.")

def main():
    print("Iniciando pipeline ETL...")
    time.sleep(2) # Pequeña pausa para no saturar el servidor
    tabla = extraer_tabla_fbref()

    if tabla is not None:
        df_limpio = limpiar_y_agregar_datos(tabla)
        actualizar_csv(df_limpio)
    else:
        print("El pipeline falló al extraer la tabla. Revisa los logs.")
        exit(1) # Forzar el error para que GitHub Actions lo marque como fallido

if __name__ == "__main__":
    main()