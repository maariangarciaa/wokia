import streamlit as st

import modules.causal as causal
import modules.graphics as graphics
import modules.introduction as introduction
import modules.summary as summary
import modules.upload as upload


APP_NAME = "Wokia"
APP_TAGLINE = "Tu espacio para explorar datos con criterio."

PAGES = {
    "welcome": {
        "label": "Inicio",
        "description": "Vista general del workspace",
    },
    "upload": {
        "label": "Datos",
        "description": "Carga CSV o Excel",
    },
    "summary": {
        "label": "Perfilado",
        "description": "Perfilado y calidad",
    },
    "graphics": {
        "label": "Visualizaciones",
        "description": "Visualizaciones guiadas",
    },
    "causal": {
        "label": "Causalidad",
        "description": "Hipotesis y efecto causal",
    },
    "intro": {
        "label": "Ayuda",
        "description": "Como usar la app",
    },
}


if "page" not in st.session_state:
    st.session_state["page"] = "welcome"


st.set_page_config(
    page_title=APP_NAME,
    page_icon="W",
    layout="wide",
    initial_sidebar_state="expanded",
)


st.markdown(
    """
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Manrope:wght@400;500;600;700;800&display=swap');

        :root {
            --bg: #f6f8fb;
            --surface: #ffffff;
            --surface-soft: #eef4f3;
            --ink: #162033;
            --muted: #667085;
            --line: #dce5e8;
            --brand: #14a886;
            --brand-dark: #0d6f61;
            --teal: #14a886;
            --amber: #b7791f;
            --rose: #b8325d;
            --violet: #5266d8;
            --sidebar: #111827;
            --sidebar-soft: #172033;
        }

        .stApp {
            background:
                radial-gradient(circle at 18% 0%, rgba(20, 168, 134, 0.18) 0, transparent 310px),
                radial-gradient(circle at 88% 8%, rgba(82, 102, 216, 0.12) 0, transparent 300px),
                linear-gradient(180deg, #f4fbf9 0px, #f7f9fc 310px, #f7f9fc 100%),
                var(--bg);
            color: var(--ink);
            font-family: Manrope, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
        }

        html, body, [class*="css"] {
            font-family: Manrope, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
        }

        section[data-testid="stSidebar"] {
            background:
                linear-gradient(180deg, var(--sidebar-soft) 0%, var(--sidebar) 100%);
            border-right: 1px solid rgba(148, 163, 184, 0.18);
        }

        section[data-testid="stSidebar"] * {
            color: #e5e7eb;
        }

        section[data-testid="stSidebar"] .stButton > button {
            background: transparent;
            border: 1px solid rgba(148, 163, 184, 0.24);
            color: #e5e7eb;
            justify-content: flex-start;
        }

        section[data-testid="stSidebar"] .stButton > button:hover {
            background: rgba(20, 168, 134, 0.16);
            border-color: rgba(94, 234, 212, 0.44);
            color: #ffffff;
        }

        section[data-testid="stSidebar"] .stButton > button:focus,
        section[data-testid="stSidebar"] .stButton > button:active,
        section[data-testid="stSidebar"] .stButton > button:focus-visible {
            background: rgba(20, 168, 134, 0.18);
            border-color: rgba(94, 234, 212, 0.56);
            color: #ffffff;
            box-shadow: none;
            outline: none;
        }

        .block-container {
            padding-top: 4.25rem;
            padding-bottom: 3rem;
            max-width: 1280px;
        }

        h1, h2, h3 {
            letter-spacing: 0;
            color: var(--ink);
        }

        p, li, label, span, div {
            letter-spacing: 0;
        }

        div[data-testid="stExpander"] {
            background: var(--surface);
            border: 1px solid var(--line);
            border-radius: 8px;
        }

        .stButton > button {
            width: 100%;
            min-height: 42px;
            border-radius: 8px;
            border: 1px solid rgba(20, 168, 134, 0.38);
            background: #dff8f2;
            color: var(--brand-dark);
            font-weight: 650;
            transition: background 0.15s ease, border-color 0.15s ease, transform 0.15s ease;
        }

        .stButton > button:hover {
            background: #ccf3eb;
            border-color: rgba(20, 168, 134, 0.58);
            color: var(--brand-dark);
            transform: translateY(-1px);
        }

        .app-shell {
            padding: 8px 4px 24px;
        }

        .hero {
            position: relative;
            overflow: hidden;
            background:
                linear-gradient(135deg, rgba(255,255,255,0.96), rgba(255,255,255,0.88)),
                radial-gradient(circle at 82% 12%, rgba(20, 168, 134, 0.12), transparent 260px);
            border: 1px solid var(--line);
            border-radius: 12px;
            padding: 34px 34px 28px;
            margin-bottom: 22px;
            box-shadow: 0 18px 46px rgba(31, 45, 76, 0.08);
        }

        .hero::before {
            content: "";
            position: absolute;
            inset: 0 0 auto 0;
            height: 5px;
            background: linear-gradient(90deg, var(--brand), var(--teal), var(--violet));
        }

        .eyebrow {
            display: inline-flex;
            align-items: center;
            gap: 8px;
            font-size: 13px;
            font-weight: 700;
            color: var(--brand-dark);
            background: #dff8f2;
            border: 1px solid #9be9da;
            border-radius: 999px;
            padding: 6px 10px;
            margin-bottom: 16px;
        }

        .hero-title {
            font-size: 52px;
            line-height: 1.05;
            font-weight: 800;
            color: #172033;
            margin: 0 0 12px;
        }

        .hero-copy {
            max-width: 720px;
            font-size: 18px;
            line-height: 1.55;
            color: var(--muted);
            margin: 0;
        }

        .metric-row {
            display: grid;
            grid-template-columns: repeat(4, minmax(0, 1fr));
            gap: 14px;
            margin: 18px 0 24px;
        }

        .metric-card, .feature-card {
            background: var(--surface);
            border: 1px solid var(--line);
            border-radius: 10px;
            padding: 18px;
            box-shadow: 0 10px 24px rgba(31, 45, 76, 0.045);
        }

        .metric-card {
            border-top: 3px solid var(--brand);
        }

        .metric-card:nth-child(2) {
            border-top-color: var(--teal);
        }

        .metric-card:nth-child(3) {
            border-top-color: var(--violet);
        }

        .metric-card:nth-child(4) {
            border-top-color: var(--amber);
        }

        .feature-card {
            border-left: 3px solid rgba(36, 87, 214, 0.26);
            transition: border-color 0.15s ease, transform 0.15s ease, box-shadow 0.15s ease;
        }

        .feature-card:hover {
            border-left-color: var(--brand);
            transform: translateY(-1px);
            box-shadow: 0 14px 30px rgba(31, 45, 76, 0.07);
        }

        .page-kicker {
            display: flex;
            align-items: center;
            gap: 10px;
            color: var(--muted);
            font-size: 13px;
            font-weight: 750;
            line-height: 1.4;
            letter-spacing: 0.02em;
            text-transform: uppercase;
            margin: 8px 0 8px;
        }

        .page-kicker::before {
            content: "";
            width: 18px;
            height: 18px;
            border: 2px solid #111827;
            border-radius: 6px;
            box-shadow: inset 5px 0 0 var(--brand);
            display: inline-block;
        }

        .page-title {
            color: var(--ink);
            font-size: 34px;
            line-height: 1.15;
            font-weight: 850;
            margin: 0 0 8px;
        }

        .page-subtitle {
            color: var(--muted);
            font-size: 16px;
            line-height: 1.5;
            margin: 0 0 22px;
            max-width: 760px;
        }

        .section-title {
            color: var(--ink);
            font-size: 20px;
            font-weight: 800;
            margin: 22px 0 8px;
        }

        .metric-label {
            color: var(--muted);
            font-size: 13px;
            font-weight: 700;
            text-transform: uppercase;
        }

        .metric-value {
            color: var(--ink);
            font-size: 24px;
            font-weight: 800;
            margin-top: 6px;
        }

        .feature-grid {
            display: grid;
            grid-template-columns: repeat(2, minmax(0, 1fr));
            gap: 14px;
            margin-top: 14px;
        }

        .feature-title {
            font-size: 18px;
            font-weight: 800;
            margin-bottom: 8px;
        }

        .feature-text {
            color: var(--muted);
            line-height: 1.5;
            margin: 0;
        }

        .sidebar-brand {
            padding: 12px 2px 18px;
            border-bottom: 1px solid rgba(148, 163, 184, 0.22);
            margin-bottom: 14px;
        }

        .brand-lockup {
            display: flex;
            align-items: center;
            gap: 10px;
        }

        .brand-mark {
            width: 34px;
            height: 34px;
            border-radius: 9px;
            background: linear-gradient(135deg, #dff8f2, #8fded0 48%, #8290f0);
            border: 1px solid rgba(255, 255, 255, 0.38);
            box-shadow: inset 0 0 0 3px rgba(15, 23, 42, 0.16);
        }

        .sidebar-title {
            font-size: 23px;
            font-weight: 850;
            color: #ffffff;
            margin: 0;
        }

        .sidebar-caption {
            color: #b8c2d3;
            font-size: 13px;
            margin-top: 4px;
            line-height: 1.35;
        }

        .nav-caption {
            color: #94a3b8;
            font-size: 12px;
            margin: -4px 0 10px;
        }

        .footer-note {
            color: #64748b;
            font-size: 13px;
            margin-top: 22px;
        }

        @media (max-width: 900px) {
            .hero-title {
                font-size: 34px;
            }

            .metric-row,
            .feature-grid {
                grid-template-columns: 1fr;
            }

            .hero {
                padding: 24px;
            }
        }
    </style>
    """,
    unsafe_allow_html=True,
)


def go_to(page_key: str):
    st.session_state["page"] = page_key


def nav_button(page_key: str):
    page = PAGES[page_key]
    active = st.session_state["page"] == page_key
    label = f"{'● ' if active else ''}{page['label']}"
    if st.sidebar.button(label, key=f"nav_{page_key}"):
        go_to(page_key)
        st.rerun()
    st.sidebar.markdown(f"<div class='nav-caption'>{page['description']}</div>", unsafe_allow_html=True)


with st.sidebar:
    st.markdown(
        f"""
        <div class="sidebar-brand">
            <div class="brand-lockup">
                <div class="brand-mark"></div>
                <div class="sidebar-title">{APP_NAME}</div>
            </div>
            <div class="sidebar-caption">Tu espacio para explorar datos con criterio.</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    for page_key in ["welcome", "upload", "summary", "graphics", "causal", "intro"]:
        nav_button(page_key)

    st.markdown(
        "<div class='footer-note'>Analisis, visualizacion y causalidad en un mismo flujo.</div>",
        unsafe_allow_html=True,
    )


page_container = st.empty()

with page_container.container():
    if st.session_state["page"] == "welcome":
        st.markdown('<div class="app-shell">', unsafe_allow_html=True)
        st.markdown(
            f"""
            <section class="hero">
                <div class="eyebrow">Workbench de ciencia de datos asistida</div>
                <h1 class="hero-title">{APP_NAME}</h1>
                <p class="hero-copy">{APP_TAGLINE} Sube una base de datos nueva, entiende su estructura, detecta senales de calidad, genera visualizaciones y prueba hipotesis causales con apoyo guiado.</p>
            </section>
            """,
            unsafe_allow_html=True,
        )

        st.markdown(
            """
            <div class="metric-row">
                <div class="metric-card">
                    <div class="metric-label">Entrada</div>
                    <div class="metric-value">CSV / Excel</div>
                </div>
                <div class="metric-card">
                    <div class="metric-label">Analisis</div>
                    <div class="metric-value">Perfilado</div>
                </div>
                <div class="metric-card">
                    <div class="metric-label">Visual</div>
                    <div class="metric-value">Visuales</div>
                </div>
                <div class="metric-card">
                    <div class="metric-label">Hipotesis</div>
                    <div class="metric-value">Causalidad</div>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        st.markdown(
            """
            <div class="feature-grid">
                <div class="feature-card">
                    <div class="feature-title">Lectura inicial</div>
                    <p class="feature-text">Abre un dataset nuevo y entiende rapidamente dimensiones, tipos de variables y primeras senales de calidad.</p>
                </div>
                <div class="feature-card">
                    <div class="feature-title">Perfilado estadistico</div>
                    <p class="feature-text">Convierte nulos, duplicados, distribuciones y metricas en explicaciones breves y accionables.</p>
                </div>
                <div class="feature-card">
                    <div class="feature-title">Visualizaciones guiadas</div>
                    <p class="feature-text">Pide histogramas, dispersiones, boxplots o correlaciones en lenguaje natural, sin escribir codigo manualmente.</p>
                </div>
                <div class="feature-card">
                    <div class="feature-title">Causalidad guiada</div>
                    <p class="feature-text">Formula hipotesis, genera tratamientos, revisa el DAG y estima efectos con herramientas causales.</p>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        c1, c2, c3 = st.columns([1, 1, 2])
        with c1:
            if st.button("Empezar"):
                go_to("upload")
                st.rerun()
        with c2:
            if st.button("Ver ayuda"):
                go_to("intro")
                st.rerun()

        st.markdown("</div>", unsafe_allow_html=True)

    elif st.session_state["page"] == "intro":
        introduction.mostrar_introduccion()

    elif st.session_state["page"] == "upload":
        upload.mostrar_subida_archivo()

    elif st.session_state["page"] == "summary":
        summary.mostrar_agente()

    elif st.session_state["page"] == "graphics":
        graphics.mostrar_graficos()

    elif st.session_state["page"] == "causal":
        causal.mostrar_inferencia_causal()
