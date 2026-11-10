import pandas as pd
from io import StringIO
import os
import time
import cloudscraper

# --- CONFIGURACIÓN ---
URL_FBREF = "https://fbref.com/en/squads/09799d9a/2026/Colo-Colo-Stats"
RUTA_DATA = "data/data.csv"

def extraer_tabla_fbref():
    """Extrae la tabla de 'Playing Time' desde FBref usando cloudscraper."""
    print("Conectando a FBref con cloudscraper...")

    scraper = cloudscraper.create_scraper(
        browser={
            'browser': 'chrome',
            'platform': 'windows',
            'desktop': True
        }
    )

    try:
        response = scraper.get(URL_FBREF, timeout=30)

        if response.status_code == 403:
            print("Error 403: Cloudflare sigue bloqueando.")
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

    except Exception as e:
        print(f"Error durante la extracción: {e}")
        return None

def limpiar_y_agregar_datos(tabla_cruda):
    if tabla_cruda is None:
        return None

    print("Limpiando datos...")
    df = tabla_cruda.copy()

    # Seleccionar y renombrar columnas
    df = df[['Player', 'Pos', 'Age', 'Min']]
    df.columns = ['jugador', 'posicion', 'edad', 'minutos']

    # Limpiar la columna 'edad' (FBref a veces usa "25-123" para años-días)
    df['edad'] = df['edad'].astype(str).str.split('-').str[0]
    df['edad'] = pd.to_numeric(df['edad'], errors='coerce').fillna(0).astype(int)

    # Limpiar 'minutos'
    df['minutos'] = df['minutos'].astype(str).str.replace(',', '', regex=False)
    df['minutos'] = pd.to_numeric(df['minutos'], errors='coerce').fillna(0).astype(int)

    # Agregar la columna 'temporada' (fijada en 2026 para este ejemplo)
    df['temporada'] = 2026

    # Filtrar filas de totales del equipo
    df = df[~df['jugador'].astype(str).str.contains('Total|Squad', case=False, na=False)]

    return df

def actualizar_csv(df_nuevo):
    if df_nuevo is None or df_nuevo.empty:
        print("No hay datos nuevos para guardar.")
        return

    if os.path.exists(RUTA_DATA):
        df_existente = pd.read_csv(RUTA_DATA, encoding='utf-8-sig')
        # Borramos la temporada actual para reemplazarla con los datos frescos
        df_existente = df_existente[df_existente['temporada'] != df_nuevo['temporada'].iloc[0]]

        df_final = pd.concat([df_existente, df_nuevo], ignore_index=True)
        df_final.to_csv(RUTA_DATA, index=False, encoding='utf-8-sig')
        print(f"Datos de la temporada {df_nuevo['temporada'].iloc[0]} actualizados.")
    else:
        df_nuevo.to_csv(RUTA_DATA, index=False, encoding='utf-8-sig')
        print("Archivo data.csv creado.")

def main():
    print("Iniciando pipeline ETL...")
    time.sleep(3)
    tabla = extraer_tabla_fbref()

    if tabla is not None:
        df_limpio = limpiar_y_agregar_datos(tabla)
        actualizar_csv(df_limpio)
    else:
        print("El pipeline falló al extraer la tabla. Revisa los logs.")
        exit(1) # Fuerza el error en GitHub Actions

if __name__ == "__main__":
    main()