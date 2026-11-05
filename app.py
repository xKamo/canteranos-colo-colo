import pandas as pd
import streamlit as st
import altair as alt
import os

# Rutas de datos
RUTA_DATA = "data/data.csv"
RUTA_JUGADORES = "data/jugadores.csv"
RUTA_LOGO = "static/logo.png"

@st.cache_data
def cargar_datos():
    data = pd.read_csv(RUTA_DATA, encoding="utf-8-sig")
    jugadores = pd.read_csv(RUTA_JUGADORES, encoding="utf-8-sig")

    jugadores["debut"] = pd.to_numeric(jugadores["debut"], errors="coerce")
    df = data.merge(jugadores, on="jugador", how="left")
    return df


def aplicar_estilos():
    st.markdown("""
        <style>
        div[data-testid="metric-container"] {
            padding: 20px;
            border-radius: 10px;
            box-shadow: 0 4px 10px rgba(0,0,0,0.08);
            border-top: 6px solid #1E1E1E;
        }

        .insight-box {
            background-color: #1E1E1E;
            color: #FAFAFA !important;
            padding: 20px;
            border-radius: 10px;
            font-size: 1.4rem;
            font-weight: 600;
            text-align: center;
            margin-bottom: 30px;
            box-shadow: 0 6px 12px rgba(0,0,0,0.1);
        }

        hr {
            margin-top: 40px;
            margin-bottom: 40px;
            border-top: 1px solid rgba(128,128,128,0.2);
        }
        </style>
    """, unsafe_allow_html=True)


def main():
    if os.path.exists(RUTA_LOGO):
        st.set_page_config(page_title="Canteranos Colo-Colo", layout="wide", page_icon=RUTA_LOGO)
    else:
        st.set_page_config(page_title="Canteranos Colo-Colo", layout="wide", page_icon="⚽")

    aplicar_estilos()

    df = cargar_datos()

    # --- CABECERA ---
    col_logo, col_titulo = st.columns([1, 6])
    with col_logo:
        if os.path.exists(RUTA_LOGO):
            st.markdown('<img src="app/static/logo.png" width="120">', unsafe_allow_html=True)
    with col_titulo:
        st.title("Canteranos de Colo-Colo")
        st.subheader("Análisis de minutos en Primera División (2017-2026)")
        st.markdown("Los datos corresponden exclusivamente al Torneo Nacional (FBref). No incluyen Copa Chile ni torneos internacionales.")

    st.markdown("<br>", unsafe_allow_html=True)

    # --- EL GANCHO PRINCIPAL ---
    total_min_historico = df["minutos"].sum()
    min_cantera_historico = df[df["canterano"] == "SI"]["minutos"].sum()
    pct_historico = (min_cantera_historico / total_min_historico) * 100

    st.markdown(
        f'<div class="insight-box">'
        f'En la última década, los jugadores formados en casa han disputado el <span style="color: #A0A0A0;">{pct_historico:.1f}%</span> de los minutos totales en Primera División.'
        f'</div>',
        unsafe_allow_html=True
    )

    # --- GRÁFICO MACRO (Área al 100%) ---
    st.header("1. La evolución de la confianza en la cantera")

    df_area = df.groupby(["temporada", "canterano"])["minutos"].sum().reset_index()
    df_area["total_temp"] = df_area.groupby("temporada")["minutos"].transform("sum")
    df_area["porcentaje"] = (df_area["minutos"] / df_area["total_temp"]) * 100

    chart_area = alt.Chart(df_area).mark_area().encode(
        x=alt.X('temporada:O', title='', axis=alt.Axis(labelAngle=0, labelColor='#000000', titleColor='#000000', labelOpacity=1)),
        y=alt.Y('porcentaje:Q', title='% de Minutos del Plantel', stack='normalize', axis=alt.Axis(labelColor='#000000', titleColor='#000000', gridColor='#CCCCCC', labelOpacity=1)),
        color=alt.Color('canterano:N',
                        scale=alt.Scale(domain=['SI', 'NO'], range=['#1E1E1E', '#B0B0B0']),
                        title='¿Es Canterano?',
                        legend=alt.Legend(labelColor='#000000', titleColor='#000000')),
        tooltip=['temporada', 'canterano', alt.Tooltip('porcentaje:Q', format='.1f', title='% Minutos')]
    ).properties(height=400).configure(background='transparent').configure_view(strokeWidth=0)

    st.altair_chart(chart_area, use_container_width=True)

    st.markdown("<hr>", unsafe_allow_html=True)

    # --- SECCIÓN 2: FOCO EN UNA TEMPORADA ---
    st.header("2. Radiografía de una temporada")

    col_sel, _ = st.columns([1, 3])
    with col_sel:
        temporadas = sorted(df["temporada"].unique(), reverse=True)
        temporada_sel = st.selectbox("Selecciona un año para analizar en detalle:", temporadas)

    df_temp = df[df["temporada"] == temporada_sel].copy()
    df_temp["nota"] = df_temp["nota"].fillna("")

    tot_min = df_temp["minutos"].sum()
    can_min = df_temp[df_temp["canterano"] == "SI"]["minutos"].sum()
    pct_temp = (can_min / tot_min) * 100 if tot_min > 0 else 0
    edad_prom = df_temp[df_temp["canterano"] == "SI"]["edad"].mean()
    edad_str = f"{edad_prom:.1f} años" if pd.notna(edad_prom) else "N/D"

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Minutos Totales", f"{tot_min:,}")
    c2.metric("Minutos Canteranos", f"{can_min:,}")
    c3.metric("% Cantera en el Año", f"{pct_temp:.1f}%")
    c4.metric("Edad Prom. Canteranos", edad_str)

    st.markdown("<br>", unsafe_allow_html=True)

    # --- MAPA DE POSICIONES Y TOP JUGADORES ---
    col_izq, col_der = st.columns([3, 2])

    with col_izq:
        st.subheader("Top jugadores del año")
        top_n = st.slider("Mostrar Top", 5, len(df_temp), min(15, len(df_temp)))
        dff_graf = df_temp.nlargest(top_n, "minutos")

        chart_barras = alt.Chart(dff_graf).mark_bar().encode(
            x=alt.X('minutos:Q', title='Minutos', axis=alt.Axis(labelColor='#000000', titleColor='#000000', gridColor='#CCCCCC', labelOpacity=1)),
            y=alt.Y('jugador:N', sort='-x', title='', axis=alt.Axis(labelLimit=0, labelFontSize=14, labelColor='#000000', labelOpacity=1)),
            color=alt.condition(
                alt.datum.canterano == 'SI',
                alt.value('#1E1E1E'),
                alt.value('#B0B0B0')
            ),
            tooltip=['jugador', 'minutos', 'canterano']
        ).properties(height=max(350, top_n * 30)).configure(background='transparent').configure_view(strokeWidth=0)

        st.altair_chart(chart_barras, use_container_width=True)

    with col_der:
        st.subheader("Minutos por Posición")

        # Normalizar posiciones (tomar las primeras 2 letras: GK, DF, MF, FW)
        df_temp["pos_base"] = df_temp["posicion"].str[:2]
        df_pos = df_temp.groupby("pos_base")["minutos"].sum().reset_index()

        # Mapear a nombres en español
        map_pos = {"GK": "Arqueros", "DF": "Defensas", "MF": "Mediocampistas", "FW": "Delanteros"}
        df_pos["pos_base"] = df_pos["pos_base"].map(map_pos).fillna("Otros")

        chart_pos = alt.Chart(df_pos).mark_bar(color='#1E1E1E').encode(
            x=alt.X('pos_base:N', title='', axis=alt.Axis(labelAngle=0, labelColor='#000000', titleColor='#000000', labelOpacity=1)),
            y=alt.Y('minutos:Q', title='Minutos Totales', axis=alt.Axis(labelColor='#000000', titleColor='#000000', gridColor='#CCCCCC', labelOpacity=1)),
            tooltip=['pos_base', alt.Tooltip('minutos:Q', format=',', title='Minutos')]
        ).properties(height=350).configure(background='transparent').configure_view(strokeWidth=0)

        st.altair_chart(chart_pos, use_container_width=True)

    # Tabla con ProgressColumn
    st.subheader("Detalle del Plantel")
    columnas = ["jugador", "posicion", "minutos", "canterano", "debut", "nota"]

    max_minutos_temp = int(df_temp["minutos"].max()) if not df_temp.empty else 1

    st.dataframe(
        df_temp[columnas].sort_values("minutos", ascending=False),
        use_container_width=True,
        hide_index=True,
        column_config={
            "jugador": "Jugador",
            "posicion": "Posición",
            "minutos": st.column_config.ProgressColumn(
                "Minutos",
                format="%d",
                min_value=0,
                max_value=max_minutos_temp,
            ),
            "canterano": "Canterano",
            "debut": st.column_config.NumberColumn("Año Debut", format="%d"),
            "nota": "Nota"
        }
    )

    st.markdown("<hr>", unsafe_allow_html=True)

    # --- SECCIÓN 3: LOS JUGADORES ---
    st.header("3. El impacto individual")

    col_top, col_comparar = st.columns(2)

    with col_top:
        st.subheader("Top 10 Histórico (2017-2026)")
        st.markdown("Los canteranos que más minutos acumularon en la década.")
        df_top10 = df[df["canterano"] == "SI"].groupby("jugador")["minutos"].sum().reset_index()
        df_top10 = df_top10.nlargest(10, "minutos")

        chart_top10 = alt.Chart(df_top10).mark_bar(color='#1E1E1E').encode(
            x=alt.X('minutos:Q', title='Minutos Totales', axis=alt.Axis(labelColor='#000000', titleColor='#000000', gridColor='#CCCCCC', labelOpacity=1)),
            y=alt.Y('jugador:N', sort='-x', title='', axis=alt.Axis(labelLimit=0, labelFontSize=13, labelColor='#000000', labelOpacity=1)),
            tooltip=['jugador', alt.Tooltip('minutos:Q', format=',')]
        ).properties(height=400).configure(background='transparent').configure_view(strokeWidth=0)
        st.altair_chart(chart_top10, use_container_width=True)

    with col_comparar:
        st.subheader("Comparador de Jugadores")
        st.markdown("Compara la evolución de dos jugadores en el tiempo.")

        lista_jugadores = sorted(df["jugador"].unique())

        # Dos selectores en la misma fila
        col_j1, col_j2 = st.columns(2)
        with col_j1:
            jugador_1 = st.selectbox("Jugador 1:", lista_jugadores, index=0)
        with col_j2:
            jugador_2 = st.selectbox("Jugador 2:", lista_jugadores, index=1)

        # Crear DataFrame con el rango de años
        años_rango = sorted(df["temporada"].unique())
        df_comp = pd.DataFrame({"temporada": años_rango})

        # Extraer datos del Jugador 1 y rellenar vacíos
        df_j1 = df[df["jugador"] == jugador_1][["temporada", "minutos"]].rename(columns={"minutos": jugador_1})
        df_comp = df_comp.merge(df_j1, on="temporada", how="left").fillna({jugador_1: 0})

        # Extraer datos del Jugador 2 y rellenar vacíos
        df_j2 = df[df["jugador"] == jugador_2][["temporada", "minutos"]].rename(columns={"minutos": jugador_2})
        df_comp = df_comp.merge(df_j2, on="temporada", how="left").fillna({jugador_2: 0})

        # Transformar a formato largo para Altair
        df_long = df_comp.melt(id_vars=["temporada"], var_name="Jugador", value_name="minutos")

        # Gráfico de líneas comparativo
        chart_comp = alt.Chart(df_long).mark_line(
            point=alt.OverlayMarkDef(size=60), strokeWidth=3
        ).encode(
            x=alt.X('temporada:O', title='', axis=alt.Axis(labelAngle=0, labelColor='#000000', titleColor='#000000', labelOpacity=1)),
            y=alt.Y('minutos:Q', title='Minutos en Liga', axis=alt.Axis(labelColor='#000000', titleColor='#000000', gridColor='#CCCCCC', labelOpacity=1)),
            color=alt.Color('Jugador:N',
                            scale=alt.Scale(range=['#1E1E1E', '#888888']), # Negro y Gris
                            legend=alt.Legend(labelColor='#000000', titleColor='#000000')),
            tooltip=['temporada', 'Jugador', alt.Tooltip('minutos:Q', format=',')]
        ).properties(height=300).configure(background='transparent').configure_view(strokeWidth=0)

        st.altair_chart(chart_comp, use_container_width=True)

    st.markdown("<hr>", unsafe_allow_html=True)

    # --- SECCIÓN 4: DEBUTS POR AÑO ---
    st.header("4. Canteranos debutantes por año")
    st.markdown("Cantidad de jugadores formados en casa que hicieron su debut en el primer equipo entre 2017 y 2026.")

    # Filtrar canteranos y que su debut esté en el rango de la década
    df_debut = df[(df['canterano'] == 'SI') & (df['debut'] >= 2017) & (df['debut'] <= 2026)].drop_duplicates(subset=['jugador'])

    # Contar por año
    debuts_por_año = df_debut.groupby('debut').size().reset_index(name='cantidad')

    # Asegurarnos de que estén todos los años, incluso si no hubo debuts
    años_rango = sorted(df["temporada"].unique())
    df_debut_full = pd.DataFrame({"debut": años_rango})
    df_debut_full = df_debut_full.merge(debuts_por_año, on="debut", how="left").fillna(0)
    df_debut_full['debut'] = df_debut_full['debut'].astype(int).astype(str) # Para que no salga "2017.0"

    chart_debuts = alt.Chart(df_debut_full).mark_bar(color='#1E1E1E').encode(
        x=alt.X('debut:O', title='Año de Debut', axis=alt.Axis(labelAngle=0, labelColor='#000000', titleColor='#000000', labelOpacity=1)),
        y=alt.Y('cantidad:Q', title='Cantidad de Jugadores', axis=alt.Axis(labelColor='#000000', titleColor='#000000', gridColor='#CCCCCC', labelOpacity=1)),
        tooltip=['debut', alt.Tooltip('cantidad:Q', format='.0f', title='Jugadores')]
    ).properties(height=300).configure(background='transparent').configure_view(strokeWidth=0)

    st.altair_chart(chart_debuts, use_container_width=True)


if __name__ == "__main__":
    main()