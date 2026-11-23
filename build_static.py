# build_static.py
# Input:  data/data.csv, data/jugadores.csv, static/logo.png
# Output: docs/index.html, docs/logo.png

import pandas as pd
import altair as alt
from pathlib import Path
import shutil

# ---------------------------------------------------------------
# 1. Cargar datos
# ---------------------------------------------------------------
BASE = Path(__file__).parent
data = pd.read_csv(BASE / "data" / "data.csv")
jugadores = pd.read_csv(BASE / "data" / "jugadores.csv")

# Limpiar nombres para el merge (quitar años de nacimiento como "(1986)")
jugadores["merge_name"] = jugadores["jugador"].str.replace(r"\s*\(\d{4}\)", "", regex=True).str.strip()
data["merge_name"] = data["jugador"].str.replace(r"\s*\(\d{4}\)", "", regex=True).str.strip()

# Hacemos el merge usando los nombres limpios
df = data.merge(jugadores[["merge_name", "canterano"]], on="merge_name", how="left")

# Fix definitivo: Convertir "SI" a True y "NO" a False
df["canterano"] = (
    df["canterano"]
    .astype(str)
    .str.strip()
    .str.upper()
    .map({"SI": True, "NO": False})
    .fillna(False)
)

df["tipo_jugador"] = df["canterano"].map({True: "Canterano", False: "No Canterano"})

# Subconjunto de jugadores canteranos (para debuts)
canteranos_jugadores = jugadores[jugadores["canterano"].str.upper() == "SI"]

# Subconjunto de minutos de canteranos (para el gráfico de posiciones)
canteranos_df = df[df["tipo_jugador"] == "Canterano"]

# ---------------------------------------------------------------
# 2. Paleta de colores (Escala de grises)
# ---------------------------------------------------------------
GRIS_OSCURO = "#1A1A1A"
GRIS_CLARO = "#9E9E9E"
GRIS_BARRAS = "#424242"

color_scale = alt.Scale(
    domain=["Canterano", "No Canterano"],
    range=[GRIS_OSCURO, GRIS_CLARO]
)

# ---------------------------------------------------------------
# 3. Parámetro de selección compartido (cross-filter)
# ---------------------------------------------------------------
brush = alt.selection_interval(encodings=["x"], name="brush")

# ---------------------------------------------------------------
# 4. Definir cada vista
# ---------------------------------------------------------------

# 4.1 Área
area = (
    alt.Chart(df)
    .mark_area(opacity=0.85)
    .encode(
        x=alt.X("temporada:O", title="Temporada"),
        y=alt.Y("sum(minutos):Q", title="Minutos totales", stack="zero", axis=alt.Axis(format=",.0f")),
        color=alt.Color("tipo_jugador:N", title="Tipo de jugador", scale=color_scale),
        order=alt.Order("tipo_jugador", sort="ascending"),
        tooltip=[
            alt.Tooltip("temporada:O", title="Temporada"),
            alt.Tooltip("tipo_jugador:N", title="Tipo"),
            alt.Tooltip("sum(minutos):Q", title="Minutos totales", format=",.0f")
        ],
    )
    .add_params(brush)
    .properties(width=800, height=300, title="Minutos por temporada")
)

# 4.2 Top 10 histórico (SOLO CANTERANOS)
top10 = (
    alt.Chart(df)
    .transform_filter(brush)
    .transform_filter(alt.datum.tipo_jugador == "Canterano")
    .transform_aggregate(total="sum(minutos)", groupby=["jugador"])
    .transform_window(rank="rank()", sort=[alt.SortField("total", order="descending")])
    .transform_filter(alt.datum.rank <= 10)
    .mark_bar(color=GRIS_BARRAS)
    .encode(
        x=alt.X("total:Q", title="Minutos totales", axis=alt.Axis(format=",.0f", tickCount=5)),
        y=alt.Y("jugador:N", sort="-x", title="Jugador"),
        tooltip=[
            alt.Tooltip("jugador:N", title="Jugador"),
            alt.Tooltip("total:Q", title="Minutos totales", format=",.0f")
        ],
    )
    .properties(width=380, height=300, title="Top 10 Canteranos")
)

# 4.3 Distribución por posición (SOLO CANTERANOS)
pos_order = (
    canteranos_df.groupby("posicion")["minutos"].sum()
    .sort_values(ascending=False)
    .index.tolist()
)

posicion = (
    alt.Chart(canteranos_df)
    .transform_filter(brush)
    .mark_bar(color=GRIS_BARRAS)
    .encode(
        x=alt.X("posicion:N", title="Posición", sort=pos_order),
        y=alt.Y("sum(minutos):Q", title="Minutos totales", axis=alt.Axis(format=",.0f")),
        tooltip=[
            alt.Tooltip("posicion:N", title="Posición"),
            alt.Tooltip("sum(minutos):Q", title="Minutos totales", format=",.0f")
        ],
    )
    .properties(width=380, height=300, title="Distribución de Canteranos por Posición")
)

# 4.4 Debuts por año (SOLO CANTERANOS) - Usando canteranos_jugadores
debuts = (
    canteranos_jugadores.dropna(subset=["debut"])
    .assign(anio_debut=lambda x: x["debut"].astype(str).str.extract(r'(\d{4})')[0])
    .dropna(subset=["anio_debut"])
    .groupby("anio_debut", as_index=False)
    .size()
    .rename(columns={"size": "cantidad"})
)

debut_chart = (
    alt.Chart(debuts)
    .mark_bar(color=GRIS_BARRAS)
    .encode(
        x=alt.X("anio_debut:O", title="Año de debut"),
        y=alt.Y("cantidad:Q", title="Jugadores que debutaron", axis=alt.Axis(format=",.0f")),
        tooltip=[
            alt.Tooltip("anio_debut:O", title="Año"),
            alt.Tooltip("cantidad:Q", title="Cantidad", format=",.0f")
        ],
    )
    .properties(width=800, height=250, title="Debuts de canteranos por año")
)

# ---------------------------------------------------------------
# 5. Componer dashboard y estilos
# ---------------------------------------------------------------
dashboard = alt.vconcat(
    area,
    alt.hconcat(top10, posicion),
    debut_chart,
).resolve_scale(color="independent").configure_view(
    strokeWidth=0
).configure_axis(
    labelFont="Inter, sans-serif",
    titleFont="Inter, sans-serif",
    labelColor="#4A4A4A",
    titleColor="#1A1A1A",
    gridColor="#E0E0E0",
    domainColor="#BDBDBD"
).configure_title(
    font="Inter, sans-serif",
    color="#1A1A1A",
    fontSize=16,
    fontWeight=600,
    anchor="middle"
)

# ---------------------------------------------------------------
# 6. Generar HTML y exportar
# ---------------------------------------------------------------
OUT = BASE / "docs"
OUT.mkdir(exist_ok=True)

# Copiar logo a docs/
shutil.copy(BASE / "static" / "Logo_ColoColo.svg", OUT / "Logo_ColoColo.svg")

chart_html = dashboard.to_html(
    inline=True,
    embed_options={
        "actions": False,
        "formatLocale": {"decimal": ",", "thousands": "."}
    }
)

# Plantilla HTML con subtítulo corregido y nota al pie
html_template = f"""<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Canteranos Colo-Colo | Dashboard</title>
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;600;700&display=swap" rel="stylesheet">
    <style>
        :root {{
            --fondo: #F5F5F5;
            --texto: #1A1A1A;
            --gris: #6C757D;
            --sombra: 0 4px 20px rgba(0, 0, 0, 0.05);
        }}
        * {{ box-sizing: border-box; margin: 0; padding: 0; }}
        body {{
            font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
            background: var(--fondo);
            color: var(--texto);
            line-height: 1.6;
            padding: 2rem 1rem;
        }}
        .container {{
            max-width: 900px;
            margin: 0 auto;
        }}
        header {{
            display: flex;
            align-items: center;
            gap: 1.5rem;
            margin-bottom: 2.5rem;
            padding-bottom: 1.5rem;
            border-bottom: 2px solid #E0E0E0;
        }}
        header img {{
            height: 65px;
            width: auto;
        }}
        header h1 {{
            font-size: 1.75rem;
            font-weight: 700;
            color: var(--texto);
            letter-spacing: -0.02em;
        }}
        header p {{
            font-size: 0.95rem;
            color: var(--gris);
            font-weight: 300;
        }}
        .card {{
            background: #FFFFFF;
            border-radius: 16px;
            box-shadow: var(--sombra);
            padding: 1.5rem;
            margin-bottom: 1.5rem;
            overflow-x: auto;
        }}
        .card .vega-embed {{
            width: 100%;
            display: flex;
            justify-content: center;
        }}
        .nota {{
            font-size: 0.8rem;
            color: var(--gris);
            margin-top: 1rem;
            padding: 0.75rem 1rem;
            background: #F8F9FA;
            border-left: 3px solid #BDBDBD;
            border-radius: 4px;
        }}
        footer {{
            text-align: center;
            margin-top: 3rem;
            font-size: 0.85rem;
            color: var(--gris);
        }}
        @media (max-width: 768px) {{
            header {{ flex-direction: column; text-align: center; }}
            header h1 {{ font-size: 1.4rem; }}
        }}
    </style>
</head>
<body>
    <div class="container">
        <header>
            <img src="Logo_ColoColo.svg" alt="Escudo Colo-Colo">
            <div>
                <h1>Canteranos Colo-Colo</h1>
                <p>Minutos jugados en Torneo Nacional - Liga de Primera · 2017–2026.</p>
            </div>
        </header>

        <div class="card">
            {chart_html}
            <div class="nota">
                <strong>Nota:</strong> El peak de 2021 se explica por el brote de COVID-19 en el plantel, que obligó a Colo-Colo a alinear a numerosos juveniles (sub-18) ante Audax Italiano y Ñublense, debido a los 7 contagios y 44 contactos estrechos que dejaron al equipo diezmado.
            </div>
        </div>

        <footer>
            Datos: FBref · Canteranos: Transfermarkt y prensa chilena · Proyecto de portafolio
        </footer>
    </div>
</body>
</html>
"""

(OUT / "index.html").write_text(html_template, encoding="utf-8")
(OUT / ".nojekyll").write_text("")

print(f"Generado: {OUT / 'index.html'}")