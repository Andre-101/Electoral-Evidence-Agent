
import requests
import streamlit as st

st.set_page_config(
    page_title="Electoral Evidence Agent",
    page_icon="🗳️",
    layout="wide",
)

st.markdown("""
<style>
:root{
  --slate:#0f172a;
  --muted:#64748b;
  --line:#e2e8f0;
  --soft:#f8fafc;
  --cyan:#0891b2;
  --ok:#059669;
  --warn:#d97706;
}
.block-container{padding-top:2rem;max-width:1180px}
.hero{
  border:1px solid var(--line);
  border-radius:24px;
  padding:28px;
  background:linear-gradient(135deg,#f8fafc 0%,#eef6ff 100%);
  margin-bottom:22px;
}
.hero h1{font-size:2.35rem;margin:0;color:var(--slate);font-weight:850}
.hero p{font-size:1.05rem;color:#475569;margin:.6rem 0 0}
.card{
  border:1px solid var(--line);
  border-radius:20px;
  padding:22px;
  background:white;
  box-shadow:0 1px 3px rgba(15,23,42,.06);
  margin-bottom:16px;
}
.report-card{
  border:1px solid #cbd5e1;
  border-radius:22px;
  padding:24px;
  background:white;
  box-shadow:0 2px 8px rgba(15,23,42,.07);
  min-height:210px;
}
.report-card h3{margin-top:0;color:var(--slate)}
.soft{color:var(--muted);font-size:.95rem}
.notice{
  border-left:5px solid var(--cyan);
  background:#f0f9ff;
  padding:14px 18px;
  border-radius:12px;
  color:#075985;
  margin-bottom:18px;
}
.warning{
  border-left:5px solid var(--warn);
  background:#fffbeb;
  padding:14px 18px;
  border-radius:12px;
  color:#78350f;
  margin-bottom:18px;
}
.success{
  border-left:5px solid var(--ok);
  background:#ecfdf5;
  padding:14px 18px;
  border-radius:12px;
  color:#064e3b;
  margin-bottom:18px;
}
.badge{
  display:inline-block;
  padding:5px 11px;
  border-radius:999px;
  background:#e0f2fe;
  color:#075985;
  font-weight:700;
  font-size:.8rem;
}
.step{
  border:1px solid var(--line);
  border-radius:16px;
  padding:14px;
  text-align:center;
  background:#f8fafc;
  color:#475569;
  font-size:.9rem;
}
.step.done{border-color:#86efac;background:#f0fdf4;color:#166534;font-weight:700}
.result-title{font-size:1.35rem;font-weight:800;color:var(--slate);margin-bottom:.2rem}
</style>
""", unsafe_allow_html=True)

def init_state():
    defaults = {
        "mode_admin": False,
        "analysis_done": False,
        "last_analysis": None,
        "ingestion_id": "",
        "review_case_id": "",
        "case_report_id": "",
        "executive_report_id": "",
        "review_cases_created": 0,
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value

init_state()

with st.sidebar:
    st.header("Configuración")
    api_base = st.text_input("API interna", "http://api:8000")
    browser_api_base = st.text_input("API reportes", "http://localhost:8000")
    use_llm = st.checkbox("Usar IA si está disponible", value=True)
    st.caption("Proveedor y modelo se configuran en el servidor.")
    st.markdown("---")
    st.session_state["mode_admin"] = st.toggle("Modo administrador", value=False)
    st.caption("Muestra detalles técnicos, IDs y herramientas de diagnóstico.")

def call_api(method: str, path: str, **kwargs):
    try:
        response = requests.request(method, f"{api_base}{path}", timeout=180, **kwargs)
        try:
            return response.json()
        except Exception:
            return {"success": False, "status_code": response.status_code, "text": response.text}
    except Exception as exc:
        return {"success": False, "errors": [{"message": str(exc)}]}

def report_url(report_id: str) -> str:
    return f"{browser_api_base}/reports/{report_id}/html"

def save_result(data: dict):
    st.session_state["analysis_done"] = True
    st.session_state["last_analysis"] = data
    st.session_state["ingestion_id"] = data.get("ingestion_run_id", "")
    st.session_state["review_case_id"] = data.get("first_review_case_id", "")
    st.session_state["case_report_id"] = data.get("case_report_id", "")
    st.session_state["executive_report_id"] = data.get("executive_report_id", "")
    st.session_state["review_cases_created"] = data.get("review_cases_created", 0)

def pipeline_steps(done=True):
    labels = ["Datos", "Análisis", "Evidencia", "Reporte"]
    cols = st.columns(4)
    for idx, label in enumerate(labels):
        css = "step done" if done else "step"
        icon = "✅" if done else "○"
        cols[idx].markdown(f'<div class="{css}">{icon}<br>{label}</div>', unsafe_allow_html=True)

def report_card(title: str, description: str, report_id: str | None, button_text: str):
    st.markdown('<div class="report-card">', unsafe_allow_html=True)
    st.markdown(f"### {title}")
    st.markdown('<span class="badge">Reporte HTML</span>', unsafe_allow_html=True)
    st.write(description)
    if report_id:
        st.link_button(button_text, report_url(report_id), use_container_width=True)
        if st.session_state["mode_admin"]:
            with st.expander("Detalles técnicos"):
                st.code(report_id)
                st.write(report_url(report_id))
    else:
        st.button("Aún no generado", disabled=True, use_container_width=True)
    st.markdown("</div>", unsafe_allow_html=True)

def run_demo_analysis():
    return call_api("POST", "/demo/run")

def run_uploaded_file_analysis(uploaded, source_name: str):
    files = {"file": (uploaded.name, uploaded.getvalue(), "text/csv")}
    data = {"source_name": source_name, "execution_mode": "EXPLORATORY"}
    created = call_api("POST", "/ingestions", data=data, files=files)
    if not created.get("success"):
        return created

    ingestion_id = created["data"]["ingestion_run_id"]

    steps = [
        ("profile", "POST", f"/ingestions/{ingestion_id}/profile", {}),
        ("map", "POST", f"/ingestions/{ingestion_id}/map", {"json": {}}),
        ("load_core", "POST", f"/ingestions/{ingestion_id}/load-core", {}),
        ("quality", "POST", f"/ingestions/{ingestion_id}/validate-quality", {}),
        ("basic_metrics", "POST", f"/ingestions/{ingestion_id}/calculate-basic-metrics", {}),
        ("territorial_metrics", "POST", f"/ingestions/{ingestion_id}/calculate-territorial-metrics", {}),
        ("eda_alerts", "POST", f"/ingestions/{ingestion_id}/generate-eda-alerts", {}),
        ("scores", "POST", f"/ingestions/{ingestion_id}/calculate-scores", {}),
    ]

    trace = {"ingestion": created, "steps": {}}
    for name, method, path, kwargs in steps:
        result = call_api(method, path, **kwargs)
        trace["steps"][name] = result
        if not result.get("success"):
            return {"success": False, "status": "FAILED", "failed_step": name, "trace": trace}

    cases = call_api("GET", f"/ingestions/{ingestion_id}/review-cases")
    trace["review_cases"] = cases
    if not cases.get("success") or not cases["data"]["items"]:
        return {
            "success": True,
            "status": "COMPLETED_NO_CASES",
            "data": {
                "ingestion_run_id": ingestion_id,
                "review_cases_created": 0,
                "first_review_case_id": None,
                "case_report_id": None,
                "executive_report_id": None,
            },
            "trace": trace,
        }

    review_case_id = cases["data"]["items"][0]["review_case_id"]

    evidence = call_api("POST", f"/review-cases/{review_case_id}/evidence-items/generate")
    dossier = call_api(
        "POST",
        f"/review-cases/{review_case_id}/dossier?force_regenerate=true&use_llm={str(use_llm).lower()}",
    )
    case_report = call_api("POST", f"/reports/case/{review_case_id}")
    executive_report = call_api("POST", f"/reports/executive/{ingestion_id}")

    trace["evidence"] = evidence
    trace["dossier"] = dossier
    trace["case_report"] = case_report
    trace["executive_report"] = executive_report

    return {
        "success": True,
        "status": "COMPLETED",
        "data": {
            "ingestion_run_id": ingestion_id,
            "review_cases_created": cases["data"]["total"],
            "first_review_case_id": review_case_id,
            "evidence_dossier_id": dossier.get("data", {}).get("evidence_dossier_id"),
            "case_report_id": case_report.get("data", {}).get("report_id"),
            "executive_report_id": executive_report.get("data", {}).get("report_id"),
        },
        "trace": trace,
    }

def render_results(data: dict):
    cases = data.get("review_cases_created", 0)

    if cases == 0:
        st.markdown(
            '<div class="success">Análisis completado. No se generaron casos de revisión con los umbrales actuales.</div>',
            unsafe_allow_html=True,
        )
    else:
        st.markdown(
            f'<div class="success">Análisis completado. Se generaron <b>{cases}</b> caso(s) priorizado(s) para revisión.</div>',
            unsafe_allow_html=True,
        )

    pipeline_steps(done=True)

    st.subheader("Reportes disponibles")
    r1, r2 = st.columns(2)
    with r1:
        report_card(
            "Reporte de caso",
            "Explica el caso priorizado con evidencia, score, trazabilidad, limitaciones y próximos pasos recomendados.",
            data.get("case_report_id"),
            "Abrir reporte de caso",
        )
    with r2:
        report_card(
            "Reporte ejecutivo",
            "Resume la ejecución completa y los casos de revisión encontrados.",
            data.get("executive_report_id"),
            "Abrir reporte ejecutivo",
        )

    if st.session_state["mode_admin"]:
        with st.expander("Detalles técnicos de la ejecución"):
            st.json(data)

st.markdown(
    """
    <div class="hero">
      <h1>Revisión asistida de resultados electorales</h1>
      <p>Carga un archivo CSV, ejecuta el análisis y obtén reportes claros para revisión humana. El sistema no concluye fraude; organiza señales y evidencia.</p>
    </div>
    """,
    unsafe_allow_html=True,
)

main_tab, reports_tab, admin_tab = st.tabs(["Analizar", "Reportes", "Administración"])

with main_tab:
    st.header("Nuevo análisis")

    st.markdown(
        '<div class="notice">Para una prueba rápida, ejecuta la demo. Para usar datos propios, carga un CSV electoral.</div>',
        unsafe_allow_html=True,
    )

    c1, c2 = st.columns([1, 1])

    with c1:
        st.markdown('<div class="card">', unsafe_allow_html=True)
        st.subheader("Opción 1: Demo")
        st.write("Usa datos sintéticos incluidos para probar el flujo completo.")
        if st.button("Ejecutar demo", type="primary", use_container_width=True):
            with st.spinner("Analizando datos y generando reportes..."):
                result = run_demo_analysis()
            if result.get("success"):
                save_result(result["data"])
                st.session_state["last_raw_result"] = result
            else:
                st.error("La demo falló.")
                st.json(result)
        st.markdown("</div>", unsafe_allow_html=True)

    with c2:
        st.markdown('<div class="card">', unsafe_allow_html=True)
        st.subheader("Opción 2: Cargar CSV")
        uploaded = st.file_uploader("Archivo CSV", type=["csv", "txt"], label_visibility="collapsed")
        source_name = st.text_input("Nombre de la fuente", "manual_upload")
        if uploaded and st.button("Analizar archivo", use_container_width=True):
            with st.spinner("Procesando archivo, calculando métricas y generando reportes..."):
                result = run_uploaded_file_analysis(uploaded, source_name)
            if result.get("success"):
                save_result(result["data"])
                st.session_state["last_raw_result"] = result
            else:
                st.error("El análisis falló.")
                if st.session_state["mode_admin"]:
                    st.json(result)
                else:
                    st.write("Revisa que el CSV tenga columnas reconocibles como departamento, municipio, puesto, mesa, opción/candidato y votos.")
        st.markdown("</div>", unsafe_allow_html=True)

    st.divider()

    if st.session_state["analysis_done"]:
        render_results(st.session_state["last_analysis"])
    else:
        st.subheader("Flujo del análisis")
        pipeline_steps(done=False)

with reports_tab:
    st.header("Reportes")

    if st.session_state.get("case_report_id") or st.session_state.get("executive_report_id"):
        c1, c2 = st.columns(2)
        with c1:
            report_card(
                "Último reporte de caso",
                "Reporte detallado del caso de revisión priorizado.",
                st.session_state.get("case_report_id"),
                "Abrir reporte de caso",
            )
        with c2:
            report_card(
                "Último reporte ejecutivo",
                "Resumen general del análisis realizado.",
                st.session_state.get("executive_report_id"),
                "Abrir reporte ejecutivo",
            )
    else:
        st.info("Aún no hay reportes. Ejecuta una demo o analiza un CSV primero.")

    if st.session_state["mode_admin"]:
        st.subheader("Abrir reporte por ID")
        report_id = st.text_input("Report ID")
        if report_id:
            st.link_button("Abrir HTML", report_url(report_id), use_container_width=True)
            if st.button("Consultar metadatos"):
                st.json(call_api("GET", f"/reports/{report_id}"))

with admin_tab:
    if not st.session_state["mode_admin"]:
        st.info("Activa el modo administrador en la barra lateral para ver herramientas técnicas.")
    else:
        st.header("Administración técnica")

        c1, c2, c3 = st.columns(3)
        with c1:
            if st.button("Health"):
                st.json(call_api("GET", "/health"))
        with c2:
            if st.button("Version"):
                st.json(call_api("GET", "/version"))
        with c3:
            if st.button("LLM status"):
                st.json(call_api("GET", "/llm/status"))

        st.subheader("IDs actuales")
        st.json(
            {
                "ingestion_id": st.session_state.get("ingestion_id"),
                "review_case_id": st.session_state.get("review_case_id"),
                "case_report_id": st.session_state.get("case_report_id"),
                "executive_report_id": st.session_state.get("executive_report_id"),
            }
        )

        if "last_raw_result" in st.session_state:
            st.subheader("Última respuesta cruda")
            st.json(st.session_state["last_raw_result"])
