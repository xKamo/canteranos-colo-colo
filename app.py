import pandas as pd
import streamlit as st
import altair as alt
import os

# Rutas de datos
RUTA_DATA = "data/data.csv"
RUTA_JUGADORES = "data/jugadores.csv"
RUTA_LOGO = "assets/logo.png"

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
        /* FONDO OSCURO */
        .stApp { background-color: #0E1117; }

        /* ELIMINAR ESPACIO SUPERIOR */
        header { display: none !important; }
        .block-container { padding-top: 2rem !important; padding-bottom: 2rem !important; }
        #MainMenu { visibility: hidden; }
        footer { visibility: hidden; }

        /* TIPOGRAFÍA CLARA */
        h1 { color: #FAFAFA; font-family: 'Helvetica Neue', sans-serif; font-weight: 900; margin-bottom: 0px;}
        h2 { color: #E0E0E0; font-weight: 700; margin-top: 10px;}
        h3 { color: #CCCCCC; font-weight: 600;}
        p, label { font-size: 1.1rem; color: #A0A0A0 !important; }

        /* TARJETAS DE MÉTRICAS */
        div[data-testid="metric-container"] {
            background-color: #1E1E1E;
            padding: 20px;
            border-radius: 10px;
            box-shadow: 0 4px 10px rgba(0,0,0,0.5);
            border-top: 6px solid #FFFFFF;
        }
        div[data-testid="metric-container"] > div { color: #FAFAFA; }

        /* CAJA DE INSIGHT (Invertida para contrastar) */
        .insight-box {
            background-color: #FFFFFF;
            color: #000000;
            padding: 20px;
            border-radius: 10px;
            font-size: 1.4rem;
            font-weight: 600;
            text-align: center;
            margin-bottom: 30px;
            box-shadow: 0 6px 12px rgba(0,0,0,0.4);
        }

        hr { margin-top: 40px; margin-bottom: 40px; border-top: 1px solid #333333; }

        /* SELECTBOXES Y SLIDERS OSCUROS */
        div[data-baseweb="select"] > div { background-color: #1E1E1E; color: white; border-color: #444; }
        div[role="slider"] { background-color: #FFFFFF !important; }
        </style>
    """, unsafe_allow_html=True)


def main():
    # Configurar página con favicon (usa el logo)
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
            st.image(RUTA_LOGO, width=120)
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
        f'En la última década, los jugadores formados en casa han disputado el <span style="color: #555555;">{pct_historico:.1f}%</span> de los minutos totales en Primera División.'
        f'</div>',
        unsafe_allow_html=True
    )

    # --- GRÁFICO MACRO (Área al 100%) ---
    st.header("1. La evolución de la confianza en la cantera")

    df_area = df.groupby(["temporada", "canterano"])["minutos"].sum().reset_index()
    df_area["total_temp"] = df_area.groupby("temporada")["minutos"].transform("sum")
    df_area["porcentaje"] = (df_area["minutos"] / df_area["total_temp"]) * 100

    chart_area = alt.Chart(df_area).mark_area().encode(
        x=alt.X('temporada:O', title='', axis=alt.Axis(labelAngle=0, labelColor='#A0A0A0', titleColor='#A0A0A0')),
        y=alt.Y('porcentaje:Q', title='% de Minutos del Plantel', stack='normalize', axis=alt.Axis(labelColor='#A0A0A0', titleColor='#A0A0A0', gridColor='#333333')),
        color=alt.Color('canterano:N',
                        scale=alt.Scale(domain=['SI', 'NO'], range=['#FFFFFF', '#444444']), # Blanco para canteranos, gris oscuro para el resto
                        title='¿Es Canterano?',
                        legend=alt.Legend(labelColor='#FAFAFA', titleColor='#FAFAFA')),
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

    # Gráfico de barras
    st.subheader("Top jugadores del año")
    top_n = st.slider("Mostrar Top", 5, len(df_temp), min(15, len(df_temp)))
    dff_graf = df_temp.nlargest(top_n, "minutos")

    chart_barras = alt.Chart(dff_graf).mark_bar().encode(
        x=alt.X('minutos:Q', title='Minutos', axis=alt.Axis(labelColor='#A0A0A0', titleColor='#A0A0A0', gridColor='#333333')),
        y=alt.Y('jugador:N', sort='-x', title='', axis=alt.Axis(labelLimit=0, labelFontSize=14, labelColor='#FAFAFA')),
        color=alt.condition(
            alt.datum.canterano == 'SI',
            alt.value('#FFFFFF'), # Blanco
            alt.value('#555555')  # Gris oscuro
        ),
        tooltip=['jugador', 'minutos', 'canterano']
    ).properties(height=max(350, top_n * 30)).configure(background='transparent').configure_view(strokeWidth=0)

    st.altair_chart(chart_barras, use_container_width=True)

    # Tabla con ProgressColumn
    st.subheader("Detalle del Plantel")
    columnas = ["jugador", "posicion", "minutos", "canterano", "debut", "nota"]

    # Calcular el máximo de minutos del año para escalar las barras (la barra del que más jugó será 100%)
    max_minutos_temp = int(df_temp["minutos"].max()) if not df_temp.empty else 1

    st.dataframe(
        df_temp[columnas].sort_values("minutos", ascending=False),
        use_container_width=True,
        hide_index=True,
        column_config={
            "jugador": "Jugador",
            "posicion": "Posición",
            # BARRAS DE PROGRESO
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

    col_top, col_buscar = st.columns(2)

    with col_top:
        st.subheader("Top 10 Histórico (2017-2026)")
        st.markdown("Los canteranos que más minutos acumularon en la década.")
        df_top10 = df[df["canterano"] == "SI"].groupby("jugador")["minutos"].sum().reset_index()
        df_top10 = df_top10.nlargest(10, "minutos")

        chart_top10 = alt.Chart(df_top10).mark_bar(color='#FFFFFF').encode(
            x=alt.X('minutos:Q', title='Minutos Totales', axis=alt.Axis(labelColor='#A0A0A0', titleColor='#A0A0A0', gridColor='#333333')),
            y=alt.Y('jugador:N', sort='-x', title='', axis=alt.Axis(labelLimit=0, labelFontSize=13, labelColor='#FAFAFA')),
            tooltip=['jugador', alt.Tooltip('minutos:Q', format=',')]
        ).properties(height=400).configure(background='transparent').configure_view(strokeWidth=0)
        st.altair_chart(chart_top10, use_container_width=True)

    with col_buscar:
        st.subheader("Buscador de Jugadores")
        st.markdown("Analiza la trayectoria de cualquier jugador en el tiempo.")
        lista_jugadores = sorted(df["jugador"].unique())
        jugador_sel = st.selectbox("Escribe o selecciona un jugador:", lista_jugadores)

        df_jugador = df[df["jugador"] == jugador_sel]
        años_rango = sorted(df["temporada"].unique())
        df_jugador_full = pd.DataFrame({"temporada": años_rango})
        df_jugador_full = df_jugador_full.merge(df_jugador[["temporada", "minutos"]], on="temporada", how="left")
        df_jugador_full["minutos"] = df_jugador_full["minutos"].fillna(0)

        debut = df_jugador["debut"].iloc[0] if not df_jugador["debut"].isna().all() else "N/D"
        es_canterano = df_jugador["canterano"].iloc[0]
        nota = df_jugador["nota"].iloc[0] if pd.notna(df_jugador["nota"].iloc[0]) else "Sin información adicional"

        # Ficha visual oscura
        st.info(f"**Debut:** {int(debut) if debut != 'N/D' else 'No registrado'} | **Canterano:** {es_canterano} | **Info:** {nota}")

        chart_jugador = alt.Chart(df_jugador_full).mark_line(
            color='#FFFFFF', point=alt.OverlayMarkDef(color='#FFFFFF', size=60), strokeWidth=3
        ).encode(
            x=alt.X('temporada:O', title='', axis=alt.Axis(labelAngle=0, labelColor='#A0A0A0', titleColor='#A0A0A0')),
            y=alt.Y('minutos:Q', title='Minutos en Liga', axis=alt.Axis(labelColor='#A0A0A0', titleColor='#A0A0A0', gridColor='#333333')),
            tooltip=['temporada', 'minutos']
        ).properties(height=280).configure(background='transparent').configure_view(strokeWidth=0)

        st.altair_chart(chart_jugador, use_container_width=True)


if __name__ == "__main__":
    main()