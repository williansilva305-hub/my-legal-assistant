import io
import os
import time
import html
import base64
import tempfile
from pathlib import Path
from typing import Optional

import streamlit as st
import streamlit.components.v1 as components
from google import genai
from google.genai import types
from docx import Document
from openpyxl import load_workbook

# ============================================================
# CONFIG
# ============================================================
st.set_page_config(page_title="Falcon", page_icon="🦅", layout="wide")


# ============================================================
# LOGO (corta transparência para não ficar minúsculo)
# ============================================================
def get_logo_data_uri() -> Optional[str]:
    candidates = [
        Path("assets/falcon_logo.png"),
        Path("static/falcon_logo.png"),
        Path("falcon_logo.png"),
        Path("assets/logo.png"),
    ]

    for p in candidates:
        if not (p.exists() and p.is_file()):
            continue

        try:
            # tenta recortar transparência (resolve logo "pequeno")
            from PIL import Image  # pillow normalmente vem no Streamlit
            img = Image.open(p).convert("RGBA")

            # usa alpha para achar bbox real do desenho
            alpha = img.getchannel("A")
            bbox = alpha.getbbox()

            if bbox:
                img = img.crop(bbox)

            # pequena margem opcional
            margin = 24
            w, h = img.size
            canvas = Image.new("RGBA", (w + margin * 2, h + margin * 2), (0, 0, 0, 0))
            canvas.paste(img, (margin, margin))
            img = canvas

            bio = io.BytesIO()
            img.save(bio, format="PNG")
            b64 = base64.b64encode(bio.getvalue()).decode("utf-8")
            return f"data:image/png;base64,{b64}"
        except Exception:
            # fallback simples
            raw = p.read_bytes()
            mime = "image/png"
            if p.suffix.lower() in [".jpg", ".jpeg"]:
                mime = "image/jpeg"
            b64 = base64.b64encode(raw).decode("utf-8")
            return f"data:{mime};base64,{b64}"

    return None


LOGO_URI = get_logo_data_uri()


# ============================================================
# CSS (mais fiel ao mock)
# ============================================================
sidebar_logo = (
    f'<img src="{LOGO_URI}" class="logo-sidebar-img" />'
    if LOGO_URI
    else '<div class="logo-sidebar-fallback">🦅</div>'
)
top_logo = (
    f'<img src="{LOGO_URI}" class="logo-top-img" />'
    if LOGO_URI
    else '<div class="logo-top-fallback">⚖️</div>'
)

st.markdown(
    f"""
<style>
#MainMenu, footer, header {{
    visibility: hidden;
}}
[data-testid="collapsedControl"] {{
    display: none;
}}

html, body, [data-testid="stAppViewContainer"] {{
    background: #edf1f6 !important;
}}

/* Margens da página */
.block-container {{
    padding-top: 0.6rem !important;
    padding-bottom: 0.6rem !important;
    max-width: 1400px !important;
}}

/* ================= SIDEBAR ================= */
[data-testid="stSidebar"] {{
    background:
      radial-gradient(circle at 18% 8%, rgba(255,189,79,0.12) 0%, rgba(255,189,79,0.00) 34%),
      linear-gradient(180deg, #111827 0%, #0b1118 100%) !important;
    border-right: 1px solid rgba(255,255,255,0.06);
}}
[data-testid="stSidebar"] * {{
    color: #f3f4f6 !important;
}}

.sidebar-brand {{
    display: flex;
    align-items: center;
    gap: 12px;
    margin: 4px 2px 12px 2px;
    padding: 4px;
}}
.logo-sidebar-img {{
    width: 54px;
    height: 54px;
    object-fit: contain;
    display: block;
    filter: drop-shadow(0 2px 8px rgba(0,0,0,0.28));
}}
.logo-sidebar-fallback {{
    width: 54px;
    height: 54px;
    border-radius: 12px;
    background: rgba(255,255,255,0.06);
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 28px;
}}
.sidebar-brand-text .title {{
    font-weight: 700;
    font-size: 1.05rem;
    color: #fff;
    line-height: 1.1;
}}
.sidebar-brand-text .sub {{
    font-size: 0.78rem;
    color: #a7b2c2;
    margin-top: 2px;
}}

[data-testid="stSidebar"] .stButton > button,
[data-testid="stSidebar"] .stPopover > button {{
    width: 100%;
    justify-content: flex-start;
    border-radius: 12px;
    border: 1px solid rgba(255,255,255,0.10);
    background: rgba(255,255,255,0.03);
    color: #f9fafb !important;
    padding: 0.68rem 0.9rem;
}}
[data-testid="stSidebar"] .stButton > button:hover,
[data-testid="stSidebar"] .stPopover > button:hover {{
    background: rgba(255,255,255,0.08);
    border-color: rgba(255,255,255,0.18);
}}

/* ================= TOPO AZUL ================= */
.top-wrap {{
    border-radius: 14px;
    overflow: hidden;
    box-shadow: 0 10px 20px rgba(13,67,180,0.12);
    margin-bottom: 10px;
}}
.top-main {{
    background: linear-gradient(90deg, #0d2f7d 0%, #0f46ba 100%);
    min-height: 52px;
    padding: 10px 14px;
    display: flex;
    align-items: center;
    justify-content: space-between;
}}
.top-left {{
    display: flex;
    align-items: center;
    gap: 10px;
}}
.logo-top-img {{
    width: 34px;
    height: 34px;
    object-fit: contain;
    display: block;
    filter: drop-shadow(0 1px 4px rgba(0,0,0,0.2));
}}
.logo-top-fallback {{
    width: 34px;
    height: 34px;
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 20px;
    color: white;
}}
.top-title {{
    color: #ffffff;
    font-weight: 700;
    font-size: 1.02rem;
}}
.top-avatar {{
    width: 34px;
    height: 34px;
    border-radius: 999px;
    background: rgba(255,255,255,0.20);
    border: 1px solid rgba(255,255,255,0.30);
    color: #fff;
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 15px;
}}
.top-sub {{
    background: #f4f6fa;
    border: 1px solid #dbe3ef;
    border-top: none;
    padding: 8px 14px;
    color: #4b5563;
    font-size: 0.88rem;
}}

/* botão live */
.top-actions {{
    display: flex;
    justify-content: flex-end;
    margin-bottom: 10px;
}}
.live-pill {{
    display: inline-flex;
    align-items: center;
    gap: 6px;
    border-radius: 999px;
    border: 1px solid #d6deea;
    background: #ffffff;
    color: #0f172a;
    text-decoration: none;
    padding: 8px 12px;
    font-size: 0.88rem;
}}
.live-pill:hover {{
    background: #f8fafc;
    border-color: #c6d2e2;
}}

/* ================= CHAT CARD ================= */
.chat-outer {{
    background: #ffffff;
    border: 1px solid #dbe3ef;
    border-radius: 14px;
    box-shadow: 0 8px 20px rgba(15,23,42,0.05);
    overflow: hidden;
}}

.chat-scroll {{
    height: calc(100vh - 355px);
    min-height: 300px;
    max-height: calc(100vh - 355px);
    overflow-y: auto;
    padding: 14px 14px 10px 14px;
    background: #ffffff;
}}

.chat-divider {{
    height: 1px;
    background: #e6ecf3;
}}

.input-shell {{
    background: #f8fafd;
    padding: 10px 12px;
}}

/* mensagens */
.msg-row {{
    display: flex;
    width: 100%;
    margin: 10px 0;
}}
.msg-row.user {{
    justify-content: flex-end;
}}
.msg-row.assistant {{
    justify-content: flex-start;
}}

.bubble {{
    max-width: 78%;
    border-radius: 14px;
    padding: 10px 12px;
    font-size: 0.96rem;
    line-height: 1.42;
    white-space: pre-wrap;
    word-wrap: break-word;
}}
.bubble.user {{
    background: linear-gradient(180deg, #0e4dac 0%, #0a3d8d 100%);
    color: #ffffff;
    border: 1px solid rgba(255,255,255,0.14);
    box-shadow: 0 4px 10px rgba(10,61,141,0.18);
}}
.bubble.assistant {{
    background: #eef2f7;
    color: #111827;
    border: 1px solid #e2e8f0;
}}
.bubble .label {{
    font-weight: 700;
    margin-bottom: 4px;
    color: #111827;
}}

.empty-state {{
    height: 100%;
    min-height: 220px;
    display: flex;
    align-items: center;
    justify-content: center;
    text-align: center;
    color: #667085;
    font-size: 0.97rem;
    line-height: 1.5;
}}

/* chips anexos */
.chips-wrap {{
    display: flex;
    gap: 6px;
    flex-wrap: wrap;
    margin: 0 0 8px 0;
}}
.chip {{
    border-radius: 999px;
    border: 1px solid #d8e2ee;
    background: #ffffff;
    color: #334155;
    padding: 4px 10px;
    font-size: 0.80rem;
}}

/* Input row widgets */
.input-row-label {{
    display:none;
}}

.send-btn button {{
    width: 100%;
    min-height: 42px;
    border-radius: 10px !important;
    border: 1px solid #d4deea !important;
    background: linear-gradient(180deg, #0f4fb2 0%, #0c3f95 100%) !important;
    color: #fff !important;
}}
.send-btn button:hover {{
    filter: brightness(1.04);
}}

.icon-btn button, .icon-popover > button {{
    width: 100%;
    min-height: 42px;
    border-radius: 10px !important;
    border: 1px solid #d4deea !important;
    background: #ffffff !important;
    color: #111827 !important;
}}

.input-text input {{
    border-radius: 12px !important;
    border: 1px solid #d4deea !important;
    background: #ffffff !important;
    min-height: 42px !important;
    box-shadow: none !important;
}}

/* Esconde label do text_input */
.input-text [data-testid="stTextInputRootElement"] > label {{
    display: none;
}}

/* Popover do anexo */
[data-testid="stPopoverContent"] {{
    border-radius: 12px !important;
}}

/* mobile */
@media (max-width: 900px) {{
    .chat-scroll {{
        height: calc(100vh - 410px);
        max-height: calc(100vh - 410px);
    }}
    .bubble {{
        max-width: 90%;
    }}
}}
</style>
""",
    unsafe_allow_html=True,
)

# ============================================================
# GEMINI
# ============================================================
API_KEY = st.secrets.get("GEMINI_API_KEY")
LIVE_URL = st.secrets.get("LIVE_URL", "http://localhost:8000/live")

if not API_KEY:
    st.error("❌ Falta configurar `GEMINI_API_KEY` no Streamlit Secrets.")
    st.stop()

@st.cache_resource
def get_client(api_key: str):
    return genai.Client(api_key=api_key)

client = get_client(API_KEY)

# Modelos free (deixa opções mais seguras)
FREE_MODELS = [
    "gemini-2.0-flash-lite",
    "gemini-2.0-flash",
    "gemini-1.5-flash",
]

DEFAULT_MODEL = FREE_MODELS[0]
DEFAULT_TEMP = 0.6

INSTRUCAO_MESTRA = """
Você é o Falcão, meu assistente jurídico e professor particular.

ESTILO:
- Fale em português do Brasil.
- Responda de forma natural, fluida e humana.
- Evite tom robótico.
- Em temas jurídicos, explique com clareza e didática.
- Se eu enviar documentos, imagens, áudio ou vídeo, analise com organização.
- Quando útil, organize em: fatos, questões jurídicas, riscos e estratégia.

CUIDADOS:
- Não invente leis, artigos, súmulas ou precedentes.
- Se estiver em dúvida, diga com clareza.
- Diferencie explicação educativa de orientação profissional definitiva.
"""

def create_chat(model_name: str, temperature: float):
    return client.chats.create(
        model=model_name,
        config=types.GenerateContentConfig(
            system_instruction=INSTRUCAO_MESTRA,
            temperature=temperature,
            top_p=0.95,
            max_output_tokens=4096,
        ),
    )

# ============================================================
# SESSION
# ============================================================
if "model_name" not in st.session_state:
    st.session_state.model_name = DEFAULT_MODEL
if "temperature" not in st.session_state:
    st.session_state.temperature = DEFAULT_TEMP
if "chat" not in st.session_state:
    st.session_state.chat = create_chat(st.session_state.model_name, st.session_state.temperature)
if "messages" not in st.session_state:
    st.session_state.messages = []
if "uploader_key" not in st.session_state:
    st.session_state.uploader_key = 0
if "show_history" not in st.session_state:
    st.session_state.show_history = False
if "draft_message" not in st.session_state:
    st.session_state.draft_message = ""


# ============================================================
# UTILIDADES ARQUIVOS
# ============================================================
def docx_to_text(file_bytes: bytes) -> str:
    doc = Document(io.BytesIO(file_bytes))
    parts = []

    for p in doc.paragraphs:
        txt = (p.text or "").strip()
        if txt:
            parts.append(txt)

    for table in doc.tables:
        parts.append("\n[TABELA]")
        for row in table.rows:
            vals = [(c.text or "").replace("\n", " ").strip() for c in row.cells]
            parts.append(" | ".join(vals))

    return "\n".join(parts).strip()


def xlsx_to_text(file_bytes: bytes, max_rows_per_sheet: int = 200, max_cols: int = 20) -> str:
    wb = load_workbook(io.BytesIO(file_bytes), data_only=True)
    lines = []

    for ws in wb.worksheets:
        lines.append(f"\n### PLANILHA: {ws.title}")
        count = 0
        for row in ws.iter_rows(values_only=True):
            if count >= max_rows_per_sheet:
                lines.append("[... linhas omitidas ...]")
                break
            vals = ["" if c is None else str(c) for c in row[:max_cols]]
            if any(v.strip() for v in vals):
                lines.append(" | ".join(vals))
                count += 1

    return "\n".join(lines).strip()


def normalize_uploaded_file_to_temp(uploaded_file):
    raw = uploaded_file.getvalue()
    ext = Path(uploaded_file.name).suffix.lower()

    if ext == ".docx":
        txt = docx_to_text(raw) or "[DOCX sem texto extraível]"
        tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".txt")
        tmp.write(txt.encode("utf-8"))
        tmp.flush()
        tmp.close()
        return tmp.name, f"{uploaded_file.name} (documento)"

    if ext in [".xlsx", ".xlsm"]:
        txt = xlsx_to_text(raw) or "[Planilha sem conteúdo legível]"
        tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".txt")
        tmp.write(txt.encode("utf-8"))
        tmp.flush()
        tmp.close()
        return tmp.name, f"{uploaded_file.name} (planilha)"

    if ext == ".doc":
        raise ValueError(f"{uploaded_file.name}: formato .doc antigo. Converta para .docx ou PDF.")

    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=ext if ext else ".bin")
    tmp.write(raw)
    tmp.flush()
    tmp.close()
    return tmp.name, uploaded_file.name


def wait_file_active(file_obj, timeout_sec: int = 240):
    start = time.time()
    while True:
        f = client.files.get(name=file_obj.name)
        state = getattr(f, "state", None)
        state_name = getattr(state, "name", str(state)).upper()

        if "ACTIVE" in state_name:
            return f
        if "FAILED" in state_name:
            raise RuntimeError("Falha ao processar o arquivo no Gemini.")
        if time.time() - start > timeout_sec:
            raise TimeoutError("O arquivo demorou demais para processar.")
        time.sleep(2)


def upload_attachments(files):
    refs = []
    labels = []
    temp_paths = []

    try:
        for uf in files:
            temp_path, label = normalize_uploaded_file_to_temp(uf)
            temp_paths.append(temp_path)

            uploaded = client.files.upload(file=temp_path)
            uploaded = wait_file_active(uploaded)

            refs.append(uploaded)
            labels.append(label)

        return refs, labels
    finally:
        for p in temp_paths:
            try:
                os.remove(p)
            except Exception:
                pass


# ============================================================
# RENDER CHAT (HTML + scroll)
# ============================================================
def build_chat_html(messages, partial_assistant_text=None):
    rows = []

    if not messages and not partial_assistant_text:
        rows.append(
            '<div class="empty-state">'
            'Posso analisar documentos, imagens, áudios e vídeos.<br>'
            'Pergunte algo ao Falcão ou envie anexos para análise.'
            '</div>'
        )
    else:
        for msg in messages:
            role = msg["role"]
            content = msg["content"]
            safe = html.escape(content).replace("\n", "<br>")
            label = '<div class="label">Falcão:</div>' if role == "assistant" else ""
            rows.append(
                f'<div class="msg-row {role}">'
                f'<div class="bubble {role}">{label}{safe}</div>'
                f'</div>'
            )

        if partial_assistant_text:
            safe = html.escape(partial_assistant_text).replace("\n", "<br>")
            rows.append(
                '<div class="msg-row assistant">'
                '<div class="bubble assistant"><div class="label">Falcão:</div>'
                f'{safe}</div></div>'
            )

    return (
        '<div class="chat-outer">'
        '<div id="falcon-chat-scroll" class="chat-scroll">'
        + "".join(rows)
        + '</div>'
        '<div class="chat-divider"></div>'
        '<div class="input-shell"></div>'  # shell visual; widgets vêm abaixo
        '</div>'
    )


def render_chat(chat_placeholder, messages, partial_assistant_text=None):
    chat_placeholder.markdown(build_chat_html(messages, partial_assistant_text), unsafe_allow_html=True)

    components.html(
        """
<script>
  const d = window.parent.document;
  const el = d.getElementById("falcon-chat-scroll");
  if (el) el.scrollTop = el.scrollHeight;
</script>
""",
        height=0,
    )


# ============================================================
# SIDEBAR
# ============================================================
with st.sidebar:
    st.markdown(
        f"""
<div class="sidebar-brand">
  {sidebar_logo}
  <div class="sidebar-brand-text">
    <div class="title">Falcon</div>
    <div class="sub">Legal Assistant</div>
  </div>
</div>
""",
        unsafe_allow_html=True,
    )

    if st.button("➕  Nova Conversa", use_container_width=True):
        st.session_state.chat = create_chat(st.session_state.model_name, st.session_state.temperature)
        st.session_state.messages = []
        st.session_state.uploader_key += 1
        st.session_state.draft_message = ""
        st.rerun()

    # botão/área de upload (mais discreto)
    with st.popover("📎  Importar Documentos", use_container_width=True):
        st.caption("Selecione arquivos para enviar na próxima mensagem")
        selected_files_sidebar = st.file_uploader(
            "Arquivos",
            accept_multiple_files=True,
            type=[
                "pdf",
                "png", "jpg", "jpeg", "webp", "bmp",
                "mp3", "wav", "m4a", "aac", "ogg", "flac",
                "mp4", "mov", "avi", "webm", "mkv", "mpeg",
                "txt", "md", "csv", "json", "html", "xml", "rtf",
                "docx", "xlsx", "xlsm",
            ],
            label_visibility="collapsed",
            key=f"uploader_{st.session_state.uploader_key}",
        )
        st.caption("PDF, imagens, áudio, vídeo, DOCX, XLSX e mais.")

    if st.button("🕘  Histórico", use_container_width=True):
        st.session_state.show_history = not st.session_state.show_history

    with st.popover("⚙️  Configurações", use_container_width=True):
        idx = FREE_MODELS.index(st.session_state.model_name) if st.session_state.model_name in FREE_MODELS else 0
        new_model = st.selectbox("Modelo (free)", FREE_MODELS, index=idx)
        new_temp = st.slider("Criatividade", 0.0, 1.0, float(st.session_state.temperature), 0.1)

        if st.button("Aplicar", use_container_width=True):
            st.session_state.model_name = new_model
            st.session_state.temperature = new_temp
            st.session_state.chat = create_chat(new_model, new_temp)
            st.session_state.messages = []
            st.session_state.draft_message = ""
            st.rerun()

    if st.session_state.show_history:
        st.markdown("---")
        st.caption("Sessão atual")
        user_msgs = [m["content"] for m in st.session_state.messages if m["role"] == "user"]
        if not user_msgs:
            st.caption("Sem mensagens ainda.")
        else:
            for i, txt in enumerate(user_msgs[-8:], 1):
                preview = txt.replace("\n", " ")
                if len(preview) > 40:
                    preview = preview[:40] + "..."
                st.caption(f"{i}. {preview}")

selected_files = locals().get("selected_files_sidebar") or []


# ============================================================
# TOPO
# ============================================================
st.markdown(
    f"""
<div class="top-wrap">
  <div class="top-main">
    <div class="top-left">
      {top_logo}
      <div class="top-title">My Legal Assistant</div>
    </div>
    <div class="top-avatar">👤</div>
  </div>
  <div class="top-sub">Assistente jurídico e professor particular, com anexos e resposta fluida.</div>
</div>
""",
    unsafe_allow_html=True,
)

st.markdown(
    f'<div class="top-actions"><a class="live-pill" href="{html.escape(LIVE_URL)}" target="_blank">🎙️ Falcon Live</a></div>',
    unsafe_allow_html=True,
)

# ============================================================
# CHAT
# ============================================================
chat_placeholder = st.empty()
render_chat(chat_placeholder, st.session_state.messages)

# Barra de input visual (fica logo abaixo do card, parecendo integrada)
# container "falso" para parecer dentro do card
st.markdown(
    """
<div style="
    margin-top:-58px;
    padding: 10px 12px 12px 12px;
    border-left:1px solid #dbe3ef;
    border-right:1px solid #dbe3ef;
    border-bottom:1px solid #dbe3ef;
    border-radius:0 0 14px 14px;
    background:#f8fafd;
    box-shadow:0 8px 20px rgba(15,23,42,0.05);
">
</div>
""",
    unsafe_allow_html=True,
)

# chips de anexos
if selected_files:
    chips = "".join([f'<span class="chip">📎 {html.escape(f.name)}</span>' for f in selected_files])
    st.markdown(f'<div class="chips-wrap">{chips}</div>', unsafe_allow_html=True)

# linha de input com aparência do mock
c1, c2, c3, c4 = st.columns([12, 1, 1, 1], vertical_alignment="center")

with c1:
    pergunta = st.text_input(
        "Mensagem",
        value=st.session_state.draft_message,
        key="falcon_input_text",
        placeholder="Digite sua mensagem...",
        label_visibility="collapsed",
    )
    st.session_state.draft_message = pergunta

with c2:
    st.markdown('<div class="icon-btn">', unsafe_allow_html=True)
    st.button("🎙️", key="mic_btn", help="Falcon Live (voz em tempo real)", use_container_width=True)
    st.markdown('</div>', unsafe_allow_html=True)

with c3:
    st.markdown('<div class="icon-popover">', unsafe_allow_html=True)
    with st.popover("📎", use_container_width=True):
        st.caption("Anexos já são enviados pelo menu lateral.")
        st.caption("Use “Importar Documentos” na barra esquerda.")
    st.markdown('</div>', unsafe_allow_html=True)

with c4:
    st.markdown('<div class="send-btn">', unsafe_allow_html=True)
    send_clicked = st.button("➤", key="send_btn", use_container_width=True)
    st.markdown('</div>', unsafe_allow_html=True)

# Enter para enviar (atalho)
components.html(
    """
<script>
const d = window.parent.document;
const input = d.querySelector('input[aria-label="Mensagem"]') || d.querySelector('input[type="text"]');
const sendBtns = [...d.querySelectorAll('button')].filter(b => b.innerText.trim() === '➤');
if (input && sendBtns.length) {
  const sendBtn = sendBtns[sendBtns.length-1];
  if (!input.dataset.falconEnterBound) {
    input.dataset.falconEnterBound = "1";
    input.addEventListener('keydown', function(e){
      if (e.key === 'Enter' && !e.shiftKey) {
        e.preventDefault();
        sendBtn.click();
      }
    });
  }
}
</script>
""",
    height=0,
)

# ============================================================
# ENVIO / STREAMING
# ============================================================
if send_clicked and pergunta and pergunta.strip():
    pergunta = pergunta.strip()
    st.session_state.draft_message = ""

    user_display = pergunta
    if selected_files:
        user_display += "\n\n📎 Anexos enviados: " + ", ".join([f.name for f in selected_files])

    st.session_state.messages.append({"role": "user", "content": user_display})
    render_chat(chat_placeholder, st.session_state.messages)

    try:
        refs = []
        if selected_files:
            with st.spinner("🦅 Processando anexos..."):
                refs, labels = upload_attachments(selected_files)

            st.session_state.messages.append(
                {"role": "assistant", "content": "✅ Anexos processados: " + " • ".join(labels)}
            )
            render_chat(chat_placeholder, st.session_state.messages)

        payload = [*refs, pergunta] if refs else pergunta

        chunks = []
        try:
            for chunk in st.session_state.chat.send_message_stream(payload):
                txt = getattr(chunk, "text", None)
                if txt:
                    chunks.append(txt)
                    render_chat(chat_placeholder, st.session_state.messages, "".join(chunks))
        except Exception as stream_err:
            # fallback sem streaming
            resp = st.session_state.chat.send_message(payload)
            txt = getattr(resp, "text", "") or str(resp)
            chunks = [txt]

        final_text = "".join(chunks).strip() or "Não consegui responder agora. Tenta reformular."
        st.session_state.messages.append({"role": "assistant", "content": final_text})

        # limpa anexos após envio
        st.session_state.uploader_key += 1
        render_chat(chat_placeholder, st.session_state.messages)
        st.rerun()

    except Exception as e:
        msg = str(e)
        if "NotFound" in msg or "404" in msg:
            msg = (
                "Modelo não encontrado nessa conta/API. Vai em Configurações e troca para outro modelo free "
                "(ex.: gemini-1.5-flash ou gemini-2.0-flash)."
            )
        st.session_state.messages.append({"role": "assistant", "content": f"❌ Erro: {msg}"})
        render_chat(chat_placeholder, st.session_state.messages)
