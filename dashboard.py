import os
import httpx
import pandas as pd
import streamlit as st
from dotenv import load_dotenv

load_dotenv()
st.set_page_config(page_title="PlatformCare", page_icon="◉", layout="wide")
API = os.getenv("PLATFORM_API", "http://127.0.0.1:8000")
HEADERS = {"X-Platform-Token": os.getenv("PLATFORM_TOKEN", "local-demo-change-me")}
st.title("PlatformCare")
st.caption("Data platform health & support · Synthetic workload · Local portfolio lab")

try:
    response = httpx.get(API + "/overview", headers=HEADERS, timeout=5)
    response.raise_for_status()
    data = response.json()
except httpx.HTTPError:
    st.error("Start the API and check PLATFORM_API / PLATFORM_TOKEN. See README.")
    st.stop()

state, support = data["health"], data["support"]
cols = st.columns(4)
cols[0].metric("Usage analytics", state["status"].upper())
age = state["freshness_seconds"]
cols[1].metric("Last successful output age", f"{age:.0f}s" if age is not None else "No successful run")
cols[2].metric("Freshness objective", "≤ 300s")
cols[3].metric("Open incidents", support["open_incidents"])
st.info("Consumer: Daily usage dashboard · Owner: demo-data-team. Failed jobs can affect data readiness even while the API remains available.")

health_tab, help_tab, support_tab = st.tabs(["Platform & incidents", "Investigate", "Support experience"])
with health_tab:
    st.subheader("Run a controlled scenario")
    scenario = st.selectbox("Synthetic workload", ["healthy", "invalid_input", "dependency_outage", "slow_job"])
    if st.button("Execute pipeline", type="primary"):
        try:
            response = httpx.post(API + "/runs", headers=HEADERS, json={"scenario": scenario, "source": "dashboard"}, timeout=15)
            response.raise_for_status()
            st.rerun()
        except httpx.HTTPError:
            st.error("Pipeline request failed; check the API.")
    st.subheader("Recent runs")
    if data["runs"]:
        frame = pd.DataFrame(data["runs"])
        frame["started_utc"] = pd.to_datetime(frame["started"], unit="s", utc=True)
        st.dataframe(frame[["id", "started_utc", "status", "scenario", "source", "records"]], hide_index=True, width="stretch")
        st.bar_chart(frame.groupby("status").size().rename("Runs"))
        selected_run = st.selectbox("Inspect logs for a run", frame["id"].tolist())
        try:
            logs = httpx.get(API + f"/runs/{selected_run}/logs", headers=HEADERS, timeout=5)
            logs.raise_for_status()
            st.dataframe(pd.DataFrame(logs.json()), hide_index=True, width="stretch")
        except httpx.HTTPError:
            st.error("Could not load logs for this run.")
    else:
        st.write("No runs yet. Execute a healthy run first.")
    st.subheader("Incident timeline")
    for incident in data["incidents"]:
        with st.expander(f"{'RESOLVED' if incident['resolved'] else 'OPEN'} · {incident['title']} · {incident['id']}"):
            st.json(incident)
            st.write("Next step: investigate the latest job, inspect logs, and consult the matching runbook.")
    st.link_button("Open Grafana", "http://localhost:3001")
    st.link_button("Open Airflow", "http://localhost:8080")

with help_tab:
    st.caption("Offline mode is deterministic MCP replay. Live mode uses a configured tool-calling LLM. The response labels its mode.")
    question = st.text_input("Support question", "Why is the usage pipeline unhealthy?")
    if st.button("Investigate using MCP"):
        with st.spinner("Inspecting job evidence and runbooks…"):
            try:
                response = httpx.post(API + "/support", headers=HEADERS, json={"question": question}, timeout=190)
                response.raise_for_status()
                st.session_state["investigation"] = response.json()
            except httpx.HTTPError:
                st.error("Investigation request failed.")
    if "investigation" in st.session_state:
        result = st.session_state["investigation"]
        st.caption(f"Mode: {result['mode']} · Request: {result['request_id']}")
        st.write(result["summary"])
        for key in ("evidence", "runbooks", "next_steps"):
            st.markdown(f"**{key.replace('_', ' ').title()}**")
            for item in result.get(key, []):
                st.write("• " + str(item))
        if result.get("escalate"):
            st.warning("Manual investigation recommended. Escalation is recorded, not paged to a real person.")
        with st.expander("MCP tool trace"):
            st.json(result.get("trace", []))
        useful = st.radio("Was this response useful?", ["Yes", "No"], horizontal=True)
        if st.button("Save feedback"):
            response = httpx.post(API + f"/support/{result['request_id']}/feedback", headers=HEADERS,
                                  json={"helpful": useful == "Yes"}, timeout=5)
            if response.is_success:
                st.success("Feedback saved. Refresh to update metrics.")

with support_tab:
    cols = st.columns(4)
    cols[0].metric("Support requests", support["requests"])
    cols[1].metric("Unanswered", support["unanswered"])
    cols[2].metric("Escalations", support["escalations"])
    cols[3].metric("Feedback responses", support["feedback_count"])
    st.json(support)
    st.caption("First response: request creation to persisted investigation response. Mean resolution: resolved incidents only. Open incidents are counted separately. These are local demo observations, not production performance claims.")
    if data["requests"]:
        frame = pd.DataFrame(data["requests"])
        frame["date_utc"] = pd.to_datetime(frame["opened"], unit="s", utc=True).dt.date.astype(str)
        st.bar_chart(frame.groupby("date_utc").size().rename("Support requests"))
        st.dataframe(frame.drop(columns=["date_utc"]), hide_index=True, width="stretch")

if st.button("Refresh"):
    st.rerun()
