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

# ---------------------------------------------------------------
# 2. Parámetro de selección compartido (cross-filter)
# ---------------------------------------------------------------
brush = alt.selection_interval(encodings=["x"], name="brush")

# ---------------------------------------------------------------
# 3. Definir cada vista
# ---------------------------------------------------------------

# 3.1 Área
area = (
    alt.Chart(df)
    .mark_area(opacity=0.7)
    .encode(
        x=alt.X("temporada:O", title="Temporada"),
        y=alt.Y("sum(minutos):Q", title="Minutos totales", stack="zero"),
        color=alt.Color("tipo_jugador:N", title="Tipo de jugador"),
        tooltip=[
            alt.Tooltip("temporada:O", title="Temporada"),
            alt.Tooltip("tipo_jugador:N", title="Tipo"),
            alt.Tooltip("sum(minutos):Q", title="Minutos totales")
        ],
    )
    .add_params(brush)
    .properties(width=700, height=300, title="Minutos por temporada")
)

# 3.2 Top 10 histórico (Filtro ANTES de agrupar)
top10 = (
    alt.Chart(df)
    .transform_filter(brush)
    .transform_aggregate(total="sum(minutos)", groupby=["jugador"])
    .transform_window(rank="rank()", sort=[alt.SortField("total", order="descending")])
    .transform_filter(alt.datum.rank <= 10)
    .mark_bar()
    .encode(
        x=alt.X("total:Q", title="Minutos totales"),
        y=alt.Y("jugador:N", sort="-x", title="Jugador"),
        tooltip=[
            alt.Tooltip("jugador:N", title="Jugador"),
            alt.Tooltip("total:Q", title="Minutos totales")
        ],
    )
    .properties(width=700, height=300, title="Top 10 histórico (filtrable)")
)

# 3.3 Distribución por posición (Filtro ANTES de agrupar)
posicion = (
    alt.Chart(df)
    .transform_filter(brush)
    .mark_bar()
    .encode(
        x=alt.X("posicion:N", title="Posición"),
        y=alt.Y("sum(minutos):Q", title="Minutos totales"),
        color=alt.Color("tipo_jugador:N", title="Tipo de jugador"),
        tooltip=[
            alt.Tooltip("posicion:N", title="Posición"),
            alt.Tooltip("tipo_jugador:N", title="Tipo"),
            alt.Tooltip("sum(minutos):Q", title="Minutos totales")
        ],
    )
    .properties(width=700, height=300, title="Distribución por posición")
)

# 3.4 Debuts por año (estático)
# Extraemos el año usando regex (busca 4 dígitos seguidos) para evitar que Pandas
# interprete mal las fechas o devuelva 1970.
debuts = (
    jugadores.dropna(subset=["debut"])
    .assign(anio_debut=lambda x: x["debut"].astype(str).str.extract(r'(\d{4})')[0])
    .dropna(subset=["anio_debut"]) # Por si algún dato no tenía año
    .groupby("anio_debut", as_index=False)
    .size()
    .rename(columns={"size": "cantidad"})
)

debut_chart = (
    alt.Chart(debuts)
    .mark_bar(color="#4c78a8")
    .encode(
        x=alt.X("anio_debut:O", title="Año de debut"),
        y=alt.Y("cantidad:Q", title="Jugadores que debutaron"),
        tooltip=[
            alt.Tooltip("anio_debut:O", title="Año"),
            alt.Tooltip("cantidad:Q", title="Cantidad")
        ],
    )
    .properties(width=700, height=250, title="Debuts por año")
)

# ---------------------------------------------------------------
# 4. Componer y exportar
# ---------------------------------------------------------------
dashboard = alt.vconcat(
    area,
    alt.hconcat(top10, posicion),
    debut_chart,
).resolve_scale(color="independent")

OUT = BASE / "docs"
OUT.mkdir(exist_ok=True)

dashboard.save(
    OUT / "index.html",
    inline=True,
    embed_options={"actions": False},
)

(OUT / ".nojekyll").write_text("")

print(f"Generado: {OUT / 'index.html'}")