# build_static.py
import shutil
from pathlib import Path
import altair as alt
import pandas as pd

# ---------------------------------------------------------------
# 1. Cargar datos
# ---------------------------------------------------------------
BASE = Path(__file__).parent
data = pd.read_csv(BASE / "data" / "data.csv")
jugadores = pd.read_csv(BASE / "data" / "jugadores.csv")

jugadores["merge_name"] = jugadores["jugador"].str.replace(r"\s*\(\d{4}\)", "", regex=True).str.strip()
data["merge_name"] = data["jugador"].str.replace(r"\s*\(\d{4}\)", "", regex=True).str.strip()

df = data.merge(jugadores[["merge_name", "canterano"]], on="merge_name", how="left")

df["canterano"] = (
    df["canterano"]
    .astype(str)
    .str.strip()
    .str.upper()
    .map({"SI": True, "NO": False})
    .fillna(False)
)

df["tipo_jugador"] = df["canterano"].map({True: "Canterano", False: "No Canterano"})
df["temporada_str"] = df["temporada"].astype(str).str.strip()

canteranos_jugadores = jugadores[jugadores["canterano"].str.upper() == "SI"]
canteranos_df = df[df["tipo_jugador"] == "Canterano"]

canteranos_2026_df = (
    canteranos_df[canteranos_df["temporada_str"].str.contains("2026", na=False)]
    .groupby("jugador", as_index=False)["minutos"]
    .sum()
    .sort_values("minutos", ascending=False)
)

# ---------------------------------------------------------------
# 2. Paleta y Formatos
# ---------------------------------------------------------------
GRIS_OSCURO = "#1A1A1A"
GRIS_CLARO = "#9E9E9E"
GRIS_BARRAS = "#424242"

color_scale = alt.Scale(
    domain=["Canterano", "No Canterano"],
    range=[GRIS_OSCURO, GRIS_CLARO]
)

# Forzamos el formato de Vega-Lite (d3-format).
FMT_ENTERO = ",.0f"

# ---------------------------------------------------------------
# 3. Cross-filter
# ---------------------------------------------------------------
brush = alt.selection_interval(encodings=["x"], name="brush")

# ---------------------------------------------------------------
# 4. Vistas
# ---------------------------------------------------------------

# 4.1 Área
area = (
    alt.Chart(df)
    .mark_area(opacity=0.85)
    .encode(
        x=alt.X("temporada:O", title="Temporada"),
        # Usamos labelExpr para forzar el formato en el eje Y
        y=alt.Y("sum(minutos):Q", title="Minutos totales", stack="zero",
                axis=alt.Axis(labelExpr="format(datum.value, ',.0f')")),
        color=alt.Color("tipo_jugador:N", title="Tipo de jugador", scale=color_scale),
        order=alt.Order("tipo_jugador", sort="ascending"),
        tooltip=[
            alt.Tooltip("temporada:O", title="Temporada"),
            alt.Tooltip("tipo_jugador:N", title="Tipo"),
            alt.Tooltip("sum(minutos):Q", title="Minutos totales", format=FMT_ENTERO),
        ],
    )
    .add_params(brush)
    .properties(width=780, height=280, title="Minutos por temporada")
)

# 4.2 Top 10
top10 = (
    alt.Chart(df)
    .transform_filter(brush)
    .transform_filter(alt.datum.tipo_jugador == "Canterano")
    .transform_aggregate(total="sum(minutos)", groupby=["jugador"])
    .transform_window(rank="rank()", sort=[alt.SortField("total", order="descending")])
    .transform_filter(alt.datum.rank <= 10)
    .mark_bar(color=GRIS_BARRAS)
    .encode(
        x=alt.X("total:Q", title="Minutos totales",
                axis=alt.Axis(labelExpr="format(datum.value, ',.0f')", tickCount=5)),
        y=alt.Y("jugador:N", sort="-x", title="Jugador"),
        tooltip=[
            alt.Tooltip("jugador:N", title="Jugador"),
            alt.Tooltip("total:Q", title="Minutos totales", format=FMT_ENTERO),
        ],
    )
    .properties(width=360, height=280, title="Top 10 Canteranos")
)

# 4.3 Posiciones
pos_order = (
    canteranos_df.groupby("posicion")["minutos"]
    .sum()
    .sort_values(ascending=False)
    .index.tolist()
)

posicion = (
    alt.Chart(canteranos_df)
    .transform_filter(brush)
    .mark_bar(color=GRIS_BARRAS)
    .encode(
        x=alt.X("posicion:N", title="Posición", sort=pos_order),
        y=alt.Y("sum(minutos):Q", title="Minutos totales",
                axis=alt.Axis(labelExpr="format(datum.value, ',.0f')")),
        tooltip=[
            alt.Tooltip("posicion:N", title="Posición"),
            alt.Tooltip("sum(minutos):Q", title="Minutos totales", format=FMT_ENTERO),
        ],
    )
    .properties(width=360, height=280, title="Distribución por Posición")
)

# 4.4 Canteranos 2026
alto_2026 = max(200, len(canteranos_2026_df) * 26)
canteranos_2026 = (
    alt.Chart(canteranos_2026_df)
    .mark_bar(color=GRIS_BARRAS)
    .encode(
        x=alt.X("minutos:Q", title="Minutos jugados (2026)",
                axis=alt.Axis(labelExpr="format(datum.value, ',.0f')", tickCount=5)),
        y=alt.Y("jugador:N", sort="-x", title="Jugador"),
        tooltip=[
            alt.Tooltip("jugador:N", title="Jugador"),
            alt.Tooltip("minutos:Q", title="Minutos jugados", format=FMT_ENTERO),
        ],
    )
    .properties(width=780, height=alto_2026, title="Canteranos 2026: Minutos por jugador")
)

# 4.5 Debuts
debuts = (
    canteranos_jugadores.dropna(subset=["debut"])
    .assign(anio_debut=lambda x: x["debut"].astype(str).str.extract(r"(\d{4})")[0])
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
        y=alt.Y("cantidad:Q", title="Jugadores que debutaron", axis=alt.Axis(format="d")),
        tooltip=[
            alt.Tooltip("anio_debut:O", title="Año"),
            alt.Tooltip("cantidad:Q", title="Cantidad", format="d"),
        ],
    )
    .properties(width=780, height=240, title="Debuts de canteranos por año")
)

# ---------------------------------------------------------------
# 5. Dashboard
# ---------------------------------------------------------------
dashboard = (
    alt.vconcat(
        area,
        alt.hconcat(top10, posicion, spacing=30),
        canteranos_2026,
        debut_chart,
        spacing=28,
    )
    .resolve_scale(color="independent")
    .properties(padding={"top": 4, "right": 12, "bottom": 8, "left": 12})
    .configure_view(strokeWidth=0)
    .configure_axis(
        labelFont="Inter, sans-serif",
        titleFont="Inter, sans-serif",
        labelColor="#4A4A4A",
        titleColor="#1A1A1A",
        gridColor="#E0E0E0",
        domainColor="#BDBDBD",
    )
    .configure_title(
        font="Inter, sans-serif",
        color="#1A1A1A",
        fontSize=16,
        fontWeight=600,
        anchor="middle",
    )
)

# ---------------------------------------------------------------
# 6. Exportación HTML
# ---------------------------------------------------------------
OUT = BASE / "docs"
OUT.mkdir(exist_ok=True)

shutil.copy(BASE / "static" / "Logo_ColoColo.svg", OUT / "Logo_ColoColo.svg")

chart_html = dashboard.to_html(
    inline=True,
    embed_options={
        "actions": False,
        "formatLocale": {"decimal": ",", "thousands": "."},
    },
)

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
            --fondo: #F8F9FA;
            --texto: #212529;
            --gris: #6C757D;
            --sombra: 0 4px 24px rgba(0, 0, 0, 0.04);
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
            max-width: 920px;
            margin: 0 auto;
        }}
        header {{
            display: flex;
            align-items: center;
            gap: 1.5rem;
            margin-bottom: 2rem;
            padding-bottom: 1.5rem;
            border-bottom: 1px solid #DEE2E6;
        }}
        header img {{
            height: 70px;
            width: auto;
            object-fit: contain;
            /* Sombra sutil al logo para darle profundidad */
            filter: drop-shadow(0px 4px 6px rgba(0,0,0,0.1));
        }}
        header h1 {{
            font-size: 1.85rem;
            font-weight: 700;
            color: var(--texto);
            letter-spacing: -0.03em;
            margin-bottom: 0.2rem;
        }}
        header p {{
            font-size: 1rem;
            color: var(--gris);
            font-weight: 400;
        }}
        .intro {{
            font-size: 0.95rem;
            color: #495057;
            margin-bottom: 1.5rem;
            line-height: 1.7;
        }}
        .card {{
            background: #FFFFFF;
            border-radius: 12px;
            box-shadow: var(--sombra);
            padding: 1.5rem;
            margin-bottom: 2rem;
            overflow-x: auto;
        }}
        .card .vega-embed {{
            width: 100%;
            display: flex;
            justify-content: center;
            align-items: flex-start;
        }}
        .card .vega-embed summary {{
            display: none;
        }}
        .nota {{
            font-size: 0.85rem;
            color: var(--gris);
            margin-top: 1.5rem;
            padding: 1rem;
            background: #F8F9FA;
            border-left: 4px solid #ADB5BD;
            border-radius: 0 4px 4px 0;
        }}
        footer {{
            text-align: center;
            margin-top: 3rem;
            padding-top: 1.5rem;
            border-top: 1px solid #DEE2E6;
            font-size: 0.85rem;
            color: var(--gris);
        }}
        @media (max-width: 768px) {{
            header {{ flex-direction: column; text-align: center; }}
            header h1 {{ font-size: 1.5rem; }}
        }}
    </style>
</head>
<body>
    <div class="container">
        <header>
            <img src="Logo_ColoColo.svg" alt="Escudo Colo-Colo">
            <div>
                <h1>Canteranos Colo-Colo</h1>
                <p>Minutos en Torneo Nacional (Liga de Primera) · 2017–2026</p>
            </div>
        </header>

        <div class="intro">
            <p>Análisis del protagonismo de los jugadores formados en casa. El siguiente dashboard compara los minutos totales otorgados al plantel de honor, destacando la evolución y la distribución de los canteranos a lo largo de las últimas 10 temporadas.</p>
        </div>

        <div class="card">
            {chart_html}
            <div class="nota">
                <strong>Nota histórica:</strong> El peak de minutos y debuts en 2021 se explica por el brote de COVID-19 en el plantel, que obligó a Colo-Colo a alinear a numerosos juveniles (sub-18) ante Audax Italiano y Ñublense, debido a los contagios y contactos estrechos que dejaron al equipo diezmado.
            </div>
        </div>

        <footer>
            Fuente de datos: FBref (minutos) · Transfermarkt y prensa chilena (canteranos) · Proyecto de portafolio por Camilo Escandar
        </footer>
    </div>
</body>
</html>
"""

(OUT / "index.html").write_text(html_template, encoding="utf-8")
(OUT / ".nojekyll").write_text("")

print(f"Generado: {OUT / 'index.html'}")