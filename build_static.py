# build_static.py
# Input:  data/data.csv, data/jugadores.csv
# Output: docs/index.html (dashboard Altair con cross-filter)

import pandas as pd
import altair as alt
from pathlib import Path

# ---------------------------------------------------------------
# 1. Cargar datos
# ---------------------------------------------------------------
BASE = Path(__file__).parent
data = pd.read_csv(BASE / "data" / "data.csv")
jugadores = pd.read_csv(BASE / "data" / "jugadores.csv")

# Unir para tener la columna canterano en un solo DataFrame
df = data.merge(jugadores[["jugador", "canterano"]], on="jugador", how="left")
df["canterano"] = df["canterano"].fillna(False).astype(bool)

# ---------------------------------------------------------------
# 2. Parámetro de selección compartido (cross-filter)
# ---------------------------------------------------------------
# Selección por intervalo en el eje X del gráfico de área.
# Al arrastrar sobre el área, se filtran los demás gráficos.
brush = alt.selection_interval(encodings=["x"], name="brush")

# ---------------------------------------------------------------
# 3. Definir cada vista como un objeto Altair
# ---------------------------------------------------------------

# 3.1 Área: minutos totales por temporada, separado por canterano/no canterano
area = (
    alt.Chart(df)
    .mark_area(opacity=0.7)
    .encode(
        x=alt.X("temporada:O", title="Temporada"),
        y=alt.Y("sum(minutos):Q", title="Minutos totales"),
        color=alt.Color("canterano:N", title="Canterano"),
        tooltip=["temporada:O", "canterano:N", "sum(minutos):Q"],
    )
    .add_params(brush)  # el área es el controlador del cross-filter
    .properties(width=700, height=300, title="Minutos por temporada")
)

# 3.2 Top 10 histórico (barras horizontales)
top10 = (
    alt.Chart(df)
    .transform_aggregate(total="sum(minutos)", groupby=["jugador"])
    .transform_window(rank="rank()", sort=[alt.SortField("total", order="descending")])
    .transform_filter(alt.datum.rank <= 10)
    .mark_bar()
    .encode(
        x=alt.X("total:Q", title="Minutos totales"),
        y=alt.Y("jugador:N", sort="-x", title="Jugador"),
        tooltip=["jugador:N", "total:Q"],
    )
    .transform_filter(brush)  # se filtra según la selección del área
    .properties(width=700, height=300, title="Top 10 histórico (filtrable)")
)

# 3.3 Distribución por posición (barras apiladas)
posicion = (
    alt.Chart(df)
    .mark_bar()
    .encode(
        x=alt.X("posicion:N", title="Posición"),
        y=alt.Y("sum(minutos):Q", title="Minutos totales"),
        color=alt.Color("canterano:N", title="Canterano"),
        tooltip=["posicion:N", "canterano:N", "sum(minutos):Q"],
    )
    .transform_filter(brush)
    .properties(width=700, height=300, title="Distribución por posición")
)

# 3.4 Debuts por año (barras simples)
# Necesitamos una fila por jugador con su año de debut
debuts = (
    jugadores.dropna(subset=["debut"])
    .assign(anio_debut=lambda x: pd.to_datetime(x["debut"]).dt.year)
    .groupby("anio_debut", as_index=False)
    .size()
    .rename(columns={"size": "cantidad"})
)

debut_chart = (
    alt.Chart(debuts)
    .mark_bar()
    .encode(
        x=alt.X("anio_debut:O", title="Año de debut"),
        y=alt.Y("cantidad:Q", title="Jugadores que debutaron"),
        tooltip=["anio_debut:O", "cantidad:Q"],
    )
    .properties(width=700, height=250, title="Debuts por año")
)

# ---------------------------------------------------------------
# 4. Componer el dashboard (concatenación vertical + cross-filter)
# ---------------------------------------------------------------
# El brush se declara en 'area'; los demás gráficos lo usan en transform_filter.
# Altair resuelve la vinculación automáticamente al concatenar.

dashboard = alt.vconcat(
    area,
    alt.hconcat(top10, posicion),
    debut_chart,
).resolve_scale(color="independent")  # colores independientes por vista

# ---------------------------------------------------------------
# 5. Exportar HTML autónomo a docs/index.html
# ---------------------------------------------------------------
OUT = BASE / "docs"
OUT.mkdir(exist_ok=True)

# inline=True incrusta Vega, Vega-Lite y vega-embed en el HTML.
# Sin inline, se cargan desde CDN (archivo más liviano, requiere internet).
dashboard.save(
    OUT / "index.html",
    inline=True,          # autónomo; cambia a False si prefieres CDN
    embed_options={"actions": False},  # oculta el menú de exportación de Vega
)

# Archivo necesario para que GitHub Pages no procese el sitio con Jekyll
(OUT / ".nojekyll").write_text("")

print(f"Generado: {OUT / 'index.html'}")