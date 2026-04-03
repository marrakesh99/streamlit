import pandas as pd
import plotly.express as px
import streamlit as st

# =========================
# Configuración general
# =========================
st.set_page_config(
    page_title="Observatorio del mercado educativo",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)

FILE_PATH = "Dashboard mejores universidades El Universal 2026.csv"

# =========================
# Estilos
# =========================
st.markdown(
    """
    <style>
    .block-container {
        padding-top: 1.2rem;
        padding-bottom: 2rem;
        max-width: 1400px;
    }

    .main-title {
        font-size: 2.2rem;
        font-weight: 800;
        line-height: 1.05;
        margin-bottom: 0.25rem;
        color: #172033;
    }

    .main-subtitle {
        color: #5f6b85;
        font-size: 1rem;
        margin-bottom: 1.25rem;
    }

    .section-title {
        font-size: 1.15rem;
        font-weight: 700;
        color: #172033;
        margin-bottom: 0.4rem;
    }

    div[data-testid="stMetric"] {
        background: #ffffff;
        border: 1px solid #e8ebf3;
        border-radius: 18px;
        padding: 0.9rem 1rem;
        box-shadow: 0 6px 20px rgba(23, 32, 51, 0.04);
    }

    div[data-testid="stMetricLabel"] {
        color: #5f6b85;
        font-weight: 600;
    }

    div[data-testid="stMetricValue"] {
        color: #172033;
        font-weight: 800;
    }

    .card {
        background: #ffffff;
        border: 1px solid #e8ebf3;
        border-radius: 22px;
        padding: 1rem 1rem 0.5rem 1rem;
        box-shadow: 0 8px 24px rgba(23, 32, 51, 0.05);
        margin-bottom: 1rem;
    }

    .small-note {
        color: #6b7280;
        font-size: 0.85rem;
        margin-top: -0.25rem;
        margin-bottom: 0.75rem;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

# =========================
# Carga y limpieza
# =========================
@st.cache_data
def load_data_from_path(file_path: str) -> pd.DataFrame:
    return _clean_df(pd.read_csv(file_path, encoding="utf-8-sig"))


@st.cache_data
def load_data_from_upload(uploaded_file) -> pd.DataFrame:
    return _clean_df(pd.read_csv(uploaded_file, encoding="utf-8-sig"))


def _clean_df(df: pd.DataFrame) -> pd.DataFrame:
    df.columns = (
        df.columns.astype(str)
        .str.replace("\ufeff", "", regex=False)
        .str.strip()
    )

    text_cols = ["TIPO DE REGISTRO", "CARRERA", "UNIVERSIDAD", "Nivel del salario"]
    for col in text_cols:
        if col in df.columns:
            df[col] = df[col].fillna("").astype(str).str.strip()

    num_cols = ["CALIFICACIÓN", "RANKING", "Salario Promedio"]
    for col in num_cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")

    required = ["TIPO DE REGISTRO", "CARRERA", "UNIVERSIDAD", "CALIFICACIÓN", "RANKING"]
    missing = [c for c in required if c not in df.columns]
    if missing:
        raise ValueError(f"Faltan columnas requeridas: {missing}")

    return df


@st.cache_data
def prepare_data(df: pd.DataFrame):
    alumnos = (
        df[df["TIPO DE REGISTRO"] == "Evaluación Alumnos"]
        [["CARRERA", "UNIVERSIDAD", "CALIFICACIÓN", "RANKING"]]
        .dropna(subset=["CARRERA", "UNIVERSIDAD", "CALIFICACIÓN", "RANKING"])
        .copy()
        .rename(columns={
            "CALIFICACIÓN": "eval_alumnos",
            "RANKING": "ranking_alumnos"
        })
    )

    academicos = (
        df[df["TIPO DE REGISTRO"] == "Evaluación Académicos"]
        [["CARRERA", "UNIVERSIDAD", "CALIFICACIÓN", "RANKING"]]
        .dropna(subset=["CARRERA", "UNIVERSIDAD", "CALIFICACIÓN", "RANKING"])
        .copy()
        .rename(columns={
            "CALIFICACIÓN": "eval_academicos",
            "RANKING": "ranking_academicos"
        })
    )

    merged = alumnos.merge(
        academicos,
        on=["CARRERA", "UNIVERSIDAD"],
        how="inner"
    )

    return alumnos, academicos, merged


# =========================
# Sidebar
# =========================
st.sidebar.title("Configuración")

source_mode = st.sidebar.radio(
    "Fuente de datos",
    ["Archivo local", "Subir CSV"],
    index=0
)

uploaded_file = None
if source_mode == "Subir CSV":
    uploaded_file = st.sidebar.file_uploader("Sube tu archivo CSV", type=["csv"])

# =========================
# Título
# =========================
st.markdown('<div class="main-title">Observatorio del mercado educativo</div>', unsafe_allow_html=True)
st.markdown(
    '<div class="main-subtitle">Prototipo interactivo para explorar rankings, evaluaciones y patrones por carrera y por institución.</div>',
    unsafe_allow_html=True
)

# =========================
# Carga de datos
# =========================
try:
    if source_mode == "Subir CSV":
        if uploaded_file is None:
            st.info("Sube un archivo CSV para comenzar.")
            st.stop()
        df = load_data_from_upload(uploaded_file)
    else:
        df = load_data_from_path(FILE_PATH)

    alumnos, academicos, merged = prepare_data(df)

except Exception as e:
    st.error(f"Error al cargar datos: {e}")
    st.stop()

carreras = sorted(alumnos["CARRERA"].dropna().unique().tolist())
escuelas = sorted(alumnos["UNIVERSIDAD"].dropna().unique().tolist())

if not carreras or not escuelas:
    st.error("No se encontraron carreras o escuelas válidas en el dataset.")
    st.stop()

# =========================
# Filtros
# =========================
st.sidebar.markdown("---")
st.sidebar.subheader("Filtros")

carrera_sel = st.sidebar.selectbox(
    "Carrera",
    options=carreras,
    index=carreras.index("Actuaría") if "Actuaría" in carreras else 0
)

escuela_sel = st.sidebar.selectbox(
    "Escuela",
    options=escuelas,
    index=escuelas.index("UNAM-CU") if "UNAM-CU" in escuelas else 0
)

mostrar_solo_carrera_scatter = st.sidebar.checkbox(
    "Limitar scatter a la carrera seleccionada",
    value=False
)

# =========================
# Vistas preparadas
# =========================
vista_carrera = (
    alumnos[alumnos["CARRERA"] == carrera_sel]
    .sort_values(["ranking_alumnos", "eval_alumnos"], ascending=[True, False])
    .copy()
)

vista_escuela = (
    alumnos[alumnos["UNIVERSIDAD"] == escuela_sel]
    .sort_values(["ranking_alumnos", "eval_alumnos", "CARRERA"], ascending=[True, False, True])
    .copy()
)

if mostrar_solo_carrera_scatter:
    scatter_df = merged[merged["CARRERA"] == carrera_sel].copy()
else:
    scatter_df = merged.copy()

# =========================
# KPIs
# =========================
promedio_carrera = vista_carrera["eval_alumnos"].mean() if not vista_carrera.empty else 0
max_carrera = vista_carrera["eval_alumnos"].max() if not vista_carrera.empty else 0
num_escuelas = vista_carrera["UNIVERSIDAD"].nunique() if not vista_carrera.empty else 0
num_carreras_escuela = vista_escuela["CARRERA"].nunique() if not vista_escuela.empty else 0

k1, k2, k3, k4 = st.columns(4)
k1.metric("Escuelas en la carrera", f"{num_escuelas}")
k2.metric("Promedio de evaluación", f"{promedio_carrera:.2f}")
k3.metric("Mejor evaluación", f"{max_carrera:.2f}")
k4.metric("Carreras de la escuela", f"{num_carreras_escuela}")

st.markdown("")

# =========================
# Tabs principales
# =========================
tab1, tab2, tab3, tab4 = st.tabs([
    "Ranking por carrera",
    "Alumnos vs académicos",
    "Distribución por carrera",
    "Vista por escuela"
])

# =========================
# Tab 1
# =========================
with tab1:
    st.markdown('<div class="section-title">Ranking de escuelas</div>', unsafe_allow_html=True)
    st.markdown(
        f'<div class="small-note">Carrera seleccionada: <strong>{carrera_sel}</strong></div>',
        unsafe_allow_html=True
    )

    fig_bar = px.bar(
        vista_carrera.sort_values("eval_alumnos", ascending=True),
        x="eval_alumnos",
        y="UNIVERSIDAD",
        orientation="h",
        text="ranking_alumnos",
        labels={
            "eval_alumnos": "Evaluación alumnos",
            "UNIVERSIDAD": "Universidad"
        }
    )

    fig_bar.update_traces(textposition="outside")
    fig_bar.update_layout(
        height=720,
        yaxis_title="",
        showlegend=False,
        margin=dict(l=10, r=30, t=20, b=10)
    )

    st.plotly_chart(fig_bar, use_container_width=True)

    with st.expander("Ver tabla del ranking"):
        tabla_ranking = vista_carrera.rename(columns={
            "UNIVERSIDAD": "Universidad",
            "ranking_alumnos": "Ranking",
            "eval_alumnos": "Evaluación alumnos"
        })[["Ranking", "Universidad", "Evaluación alumnos"]]

        st.dataframe(
            tabla_ranking,
            use_container_width=True,
            hide_index=True
        )

# =========================
# Tab 2
# =========================
with tab2:
    st.markdown('<div class="section-title">Percepción de alumnos vs evaluación académica</div>', unsafe_allow_html=True)
    st.markdown(
        '<div class="small-note">Busca alineaciones y divergencias entre ambas dimensiones de evaluación.</div>',
        unsafe_allow_html=True
    )

    fig_scatter = px.scatter(
        scatter_df,
        x="eval_alumnos",
        y="eval_academicos",
        color="CARRERA",
        hover_name="UNIVERSIDAD",
        hover_data={
            "CARRERA": True,
            "eval_alumnos": ":.2f",
            "eval_academicos": ":.2f",
            "ranking_alumnos": True,
            "ranking_academicos": True
        },
        labels={
            "eval_alumnos": "Evaluación alumnos",
            "eval_academicos": "Evaluación académicos"
        }
    )

    fig_scatter.add_shape(
        type="line",
        x0=scatter_df["eval_alumnos"].min() if not scatter_df.empty else 0,
        y0=scatter_df["eval_alumnos"].min() if not scatter_df.empty else 0,
        x1=scatter_df["eval_alumnos"].max() if not scatter_df.empty else 10,
        y1=scatter_df["eval_alumnos"].max() if not scatter_df.empty else 10,
        line=dict(dash="dash")
    )

    fig_scatter.update_layout(
        height=700,
        margin=dict(l=10, r=10, t=20, b=10)
    )

    st.plotly_chart(fig_scatter, use_container_width=True)

# =========================
# Tab 3
# =========================
with tab3:
    st.markdown('<div class="section-title">Distribución de evaluaciones por carrera</div>', unsafe_allow_html=True)
    st.markdown(
        '<div class="small-note">Cada punto representa una universidad. Esta vista ayuda a detectar concentración, dispersión y outliers.</div>',
        unsafe_allow_html=True
    )

    fig_strip = px.strip(
        alumnos,
        x="eval_alumnos",
        y="CARRERA",
        hover_name="UNIVERSIDAD",
        hover_data={
            "ranking_alumnos": True,
            "eval_alumnos": ":.2f"
        },
        labels={
            "eval_alumnos": "Evaluación alumnos",
            "CARRERA": "Carrera"
        }
    )

    fig_strip.update_layout(
        height=800,
        margin=dict(l=10, r=10, t=20, b=10)
    )

    st.plotly_chart(fig_strip, use_container_width=True)

# =========================
# Tab 4
# =========================
with tab4:
    st.markdown('<div class="section-title">Desempeño de una escuela a través de las carreras</div>', unsafe_allow_html=True)
    st.markdown(
        f'<div class="small-note">Escuela seleccionada: <strong>{escuela_sel}</strong></div>',
        unsafe_allow_html=True
    )

    if vista_escuela.empty:
        st.info("No hay datos para la escuela seleccionada.")
    else:
        fig_school = px.bar(
            vista_escuela.sort_values("ranking_alumnos", ascending=False),
            x="ranking_alumnos",
            y="CARRERA",
            orientation="h",
            text="eval_alumnos",
            labels={
                "ranking_alumnos": "Ranking",
                "CARRERA": "Carrera"
            }
        )

        fig_school.update_layout(
            height=650,
            margin=dict(l=10, r=20, t=20, b=10)
        )

        st.plotly_chart(fig_school, use_container_width=True)

        with st.expander("Ver tabla por escuela"):
            tabla_escuela = vista_escuela.rename(columns={
                "CARRERA": "Carrera",
                "ranking_alumnos": "Ranking",
                "eval_alumnos": "Evaluación alumnos"
            })[["Carrera", "Ranking", "Evaluación alumnos"]]

            st.dataframe(
                tabla_escuela,
                use_container_width=True,
                hide_index=True
            )

# =========================
# Footer
# =========================
st.markdown("---")
st.caption("Versión inicial del explorador. Siguiente paso sugerido: añadir salarios, comparativos por tipo de institución y narrativas guiadas.")