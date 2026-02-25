import streamlit as st
import os
import asyncio
from dotenv import load_dotenv

# Load environment variables (API keys, etc.)
load_dotenv()

# Import our custom safety guard
try:
    from gemini_safety_guard import create_local_client
except ImportError:
    st.error("Gemini Safety Guard not found. Please install the package using 'pip install -e .'")
    st.stop()


# ─── Page Config ─────────────────────────────────────────────────────────────
st.set_page_config(page_title="Prompt Injection Detector", page_icon="🛡️", layout="wide")

# ─── Custom CSS ──────────────────────────────────────────────────────────────
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');

    html, body, [class*="css"] {
        font-family: 'Inter', sans-serif;
    }

    .main-header {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        background-clip: text;
        font-size: 2.4rem;
        font-weight: 700;
        margin-bottom: 0;
    }

    .sub-header {
        color: #8b8fa3;
        font-size: 1rem;
        margin-top: -8px;
        margin-bottom: 24px;
    }

    .mode-badge-local {
        background: linear-gradient(135deg, #00c9ff 0%, #92fe9d 100%);
        color: #0a2f1f;
        padding: 4px 14px;
        border-radius: 20px;
        font-weight: 600;
        font-size: 0.8rem;
        display: inline-block;
    }



    .stChatMessage {
        border-radius: 12px;
    }

    div[data-testid="stSidebar"] {
        background: linear-gradient(180deg, #1a1a2e 0%, #16213e 100%);
    }

    div[data-testid="stSidebar"] .stMarkdown p,
    div[data-testid="stSidebar"] .stMarkdown h1,
    div[data-testid="stSidebar"] .stMarkdown h2,
    div[data-testid="stSidebar"] .stMarkdown h3 {
        color: #e0e0e0;
    }

    .confidence-meter {
        background: #1e1e2f;
        border-radius: 10px;
        padding: 12px 16px;
        margin-top: 8px;
        border-left: 4px solid #667eea;
    }
</style>
""", unsafe_allow_html=True)

# ─── Header ──────────────────────────────────────────────────────────────────
st.markdown('<p class="main-header">🛡️ Prompt Injection Detector</p>', unsafe_allow_html=True)
st.markdown('<p class="sub-header">Fast local detection powered by DistilBert</p>', unsafe_allow_html=True)

# ─── Sidebar ─────────────────────────────────────────────────────────────────
st.sidebar.markdown("## ⚙️ Configuration")

# Model path (for local mode) - Check multiple locations
MODEL_PATHS = [
    # Relative to examples folder (examples/../../../prompt_injection_model)
    os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", "prompt_injection_model")),
    # Relative to workspace root
    os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../../..", "prompt_injection_model")),
    # Direct path to workspace
    "/Users/hemanthsatviktokala/Desktop/hemanthagent/prompt_injection_model",
]

MODEL_PATH = None
for path in MODEL_PATHS:
    if os.path.isdir(path):
        MODEL_PATH = path
        break

if not MODEL_PATH:
    st.sidebar.error(f"❌ Model not found. Tried:\n" + "\n".join(MODEL_PATHS))
    st.stop()

st.sidebar.markdown("---")

# Show model status
st.sidebar.markdown("### 📁 Model Status")
st.sidebar.caption(f"✅ Model: {os.path.basename(MODEL_PATH)}")
st.sidebar.caption(f"📍 Path: `{MODEL_PATH}`", help="Local model files location")

# Show active mode badge
st.sidebar.markdown("---")
st.sidebar.markdown(
    '<span class="mode-badge-local">🧠 Local DistilBert Model</span>',
    unsafe_allow_html=True
)
st.sidebar.caption("Fast local detection (primary)")


st.sidebar.markdown("---")
st.sidebar.markdown("### 🔑 Status")
st.sidebar.success("✅ System operational")



# ─── Initialize Safety Client ──────────────────────────────────────────────
@st.cache_resource
def get_local_safety_client(path):
    """Load the local DistilBert model (cached — only loads once)."""
    return create_local_client(model_path=path)


# Get safety client
try:
    safety_client = get_local_safety_client(MODEL_PATH)
except Exception as e:
    st.error(f"❌ Failed to initialize safety client: {e}")
    st.stop()


# ─── Detection History ──────────────────────────────────────────────────────
if "detections" not in st.session_state:
    st.session_state.detections = []

# Display Detection History
if st.session_state.detections:
    st.markdown("### 📊 Detection History")
    for detection in st.session_state.detections:
        col1, col2 = st.columns([3, 1])
        with col1:
            if detection["classification"] == "block":
                st.error(f"🚫 **BLOCKED**: {detection['text'][:100]}...")
            else:
                st.success(f"✅ **SAFE**: {detection['text'][:100]}...")
        with col2:
            st.caption(f"Conf: {detection['confidence']:.0%}")
        with st.expander("Details"):
            st.markdown(f"**Reasoning:** {detection['reasoning']}")
            if detection['violations']:
                st.markdown(f"**Violations:** {', '.join(detection['violations'])}")
            if detection['cwe_codes']:
                st.markdown(f"**CWE:** {', '.join(detection['cwe_codes'])}")
        st.divider()


# ─── Async wrapper for local model ────────────────────────────────────────────
async def check_safety(client, text):
    return await client.guard(text)





# ─── Main Detection Interface ────────────────────────────────────────────────
st.markdown("---")
st.markdown("### 🔍 Analyze Text for Prompt Injection")

# Input section
col1, col2 = st.columns([4, 1])
with col1:
    user_input = st.text_area("Enter text to analyze:", height=120, placeholder="Paste text here...")
with col2:
    st.markdown("")  # Spacer
    detect_button = st.button("🔍 Analyze", use_container_width=True, key="detect_btn")

# Clear button
if st.button("🗑️ Clear History", use_container_width=False):
    st.session_state.detections = []
    st.rerun()

# Process detection
if detect_button and user_input:
    # Stage 1: Local Model Detection
    with st.spinner("🧠 Stage 1/2: Running DistilBert model..."):
        try:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            guard_result = loop.run_until_complete(check_safety(safety_client, user_input))
            loop.close()

            # Extract confidence from reasoning
            confidence = 0.0
            if "with " in guard_result.reasoning and "%" in guard_result.reasoning:
                try:
                    conf_str = guard_result.reasoning.split("with ")[-1].split("%")[0]
                    confidence = float(conf_str) / 100
                except:
                    confidence = 0.0

            local_prediction = guard_result.classification
            local_reasoning = guard_result.reasoning
            local_violations = guard_result.violation_types
            local_cwe_codes = guard_result.cwe_codes

            final_classification = local_prediction
            final_reasoning = local_reasoning
            corrected = False


            # Store detection
            detection_record = {
                "text": user_input,
                "classification": final_classification,
                "confidence": confidence,
                "reasoning": final_reasoning,
                "violations": local_violations,
                "cwe_codes": local_cwe_codes,
                "local_pred": local_prediction,
                "verified": False,
                "corrected": False,

            }
            st.session_state.detections.append(detection_record)

            # Display result
            st.markdown("---")
            st.markdown("### 📊 Final Verdict")
            
            if final_classification == "block":
                st.error("🚫 **PROMPT INJECTION DETECTED!**")

                
                col1, col2 = st.columns(2)
                with col1:
                    st.metric("Status", "BLOCKED")
                with col2:
                    st.metric("Confidence", f"{confidence:.1%}")

                
                st.markdown("**Reasoning:**")
                st.info(final_reasoning)
                
                if local_violations:
                    st.markdown("**Violation Types:**")
                    for v in local_violations:
                        st.warning(f"🔴 {v}")
                
                if local_cwe_codes:
                    st.markdown("**CWE Codes:**")
                    for code in local_cwe_codes:
                        st.code(code)
            else:
                st.success("✅ **TEXT IS SAFE**")

                
                col1, col2 = st.columns(2)
                with col1:
                    st.metric("Status", "PASSED")
                with col2:
                    st.metric("Confidence", f"{confidence:.1%}")

                
                st.markdown("**Reasoning:**")
                st.info(final_reasoning)

        except Exception as e:
            st.error(f"❌ Error during detection: {e}")
            import traceback
            st.code(traceback.format_exc())
