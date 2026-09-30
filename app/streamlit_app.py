"""Small research demo: fixture, recording upload, or saved report."""
import json
from pathlib import Path
import sys
import tempfile
import streamlit as st

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from pipeline.config import load_yaml
from pipeline.run import assess_recording

st.title("ARTS Defibrillation Assessment")
st.caption("Development preview — clinical rules are pending implementation.")
mode = st.radio("Input", ["Sample report", "Upload recording", "Open saved report"])
report = None
try:
    if mode == "Sample report":
        st.info("Synthetic examples for interface development; these are not clinical assessments.")
        report = json.loads((ROOT / "tests/fixtures/sample_report.json").read_text(encoding="utf-8"))
    elif mode == "Open saved report":
        uploaded = st.file_uploader("Assessment report", type="json")
        if uploaded is not None:
            report = json.load(uploaded)
    else:
        recording = st.file_uploader("Recording", type=["mp4", "mov", "mkv", "avi"])
        config = load_yaml(ROOT / "configs/pipeline.yaml")
        enabled = any(config.get(kind, {}).get("enabled", False) for kind in ("video", "asr", "charging_sound"))
        if not enabled:
            st.info("Model branches have not been configured yet. Use the sample report while the team develops them.")
        if st.button("Assess recording", disabled=recording is None or not enabled):
            with tempfile.TemporaryDirectory(prefix="arts-upload-") as directory:
                path = Path(directory) / ("recording" + Path(recording.name).suffix.lower())
                path.write_bytes(recording.getvalue())
                with st.spinner("Processing recording"):
                    report = assess_recording(config, video=path)
            st.session_state["assessment_report"] = report
        elif "assessment_report" in st.session_state:
            report = st.session_state["assessment_report"]
    if report is not None:
        if report.get("schema_version") != 1:
            raise ValueError("Unsupported report version")
        st.subheader("Timeline")
        st.dataframe(report["events"], use_container_width=True)
        st.subheader("Rules")
        st.dataframe(report["rules"], use_container_width=True)
        for message in report.get("feedback", []):
            st.write(message)
        st.download_button("Download report", json.dumps(report, indent=2), "assessment.json", "application/json")
except Exception as exc:
    st.error(f"Could not produce a report: {exc}")
