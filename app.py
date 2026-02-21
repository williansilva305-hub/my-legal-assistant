import io
import os
import time
import html
import tempfile
from pathlib import Path

import streamlit as st
import streamlit.components.v1 as components
from google import genai
from google.genai import types
from docx import Document
from openpyxl import load_workbook

# ============================================================
# CONFIG DA PÁGINA
# ============================================================
st.set_page_config(
    page_title="Falcon",
    page_icon="🦅",
    layout="wide"
)

# ============================================================
# CSS (premium + estável)
# ============================================================
st.markdown(
    """
<style>
#MainMenu {visibility: hidden;}
footer {visibility: hidden;}
header {visibility: hidden;}

[data-testid="stAppViewContainer"] {
    background: linear-gradient(180deg, #f4f6f9 0%, #eef1f5 100%);
}

/* Sidebar */
[data-testid="stSidebar"] {
    background:
      radial-gradient(circle at 20% 20%, rgba(255,177,64,0.10) 0%, rgba(255,177,64,0.00) 35%),
      linear-gradient(180deg, #0b1118 0%, #0f1722 100%);
    border-right: 1px solid rgba(255,255,255,0.06);
}
[data-testid="stSidebar"] * {
    color: #f3f4f6 !important;
}
[data-testid="stSidebar"] .stButton > button,
[data-testid="stSidebar"] .stLinkButton > a {
    width: 100%;
    justify-content: flex-start;
    border-radius: 12px;
    border: 1px solid rgba(255,255,255,0.08);
    background: rgba(255,255,255,0.02);
    color: #f9fafb !important;
    padding: 0.6rem 0.8rem;
}
[data-testid="stSidebar"] .stButton > button:hover,
[data-testid="stSidebar"] .stLinkButton > a:hover {
    border-color: rgba(255,255,255,0.18);
    background: rgba(255,255,255,0.05);
}

/* Marca sidebar */
.brand-wrap {
    display:flex;
    align-items:center;
    gap:10px;
    margin-top: 4px;
    margin-bottom: 14px;
}
.brand-icon {
    width: 42px;
    height: 42px;
    border-radius: 12px;
    border: 1px solid rgba(255,193,77,0.35);
    background: rgba(255,193,77,0.08);
    display:flex;
    align-items:center;
    justify-content:center;
    font-size: 22px;
}
.brand-text {
    display:flex;
    flex-direction:column;
    line-height:1.1;
}
.brand-text .name {
    font-weight:700;
    color:#f8fafc;
    font-size: 1.05rem;
}
.brand-text .sub {
    color:#94a3b8;
    font-size: .75rem;
}

/* Área central */
.main-title {
    font-weight: 700;
    color: #0f172a;
    font-size: 1.05rem;
    margin-bottom: 4px;
}
.main-subtitle {
    color: #64748b;
    font-size: 0.86rem;
    margin-bottom: 10px;
}

/* Ações topo */
.top-actions {
    display: flex;
    justify-content: flex-end;
    margin-bottom: 8px;
}
.live-pill {
    display: inline-flex;
    align-items: center;
    gap: 6px;
    border-radius: 999px;
    border: 1px solid rgba(15,23,42,0.10);
    background: rgba(255,255,255,0.92);
    color: #0f172a;
    text-decoration: none;
    padding: 8px 12px;
    font-size: 0.9rem;
}
.live-pill:hover {
    border-color: rgba(15,23,42,0.20);
    background: #fff;
}

/* Painel do chat */
.chat-shell {
    border: 1px solid rgba(15,23,42,0.08);
    background: rgba(255,255,255,0.55);
    border-radius: 16px;
    padding: 10px;
    box-shadow: 0 8px 30px rgba(15,23,42,0.05);
}
.chat-scroll {
    height: calc(100vh - 320px);
    min-height: 340px;
    max-height: calc(100vh - 320px);
    overflow-y: auto;
    padding: 4px 4px 8px 4px;
    scroll-behavior: smooth;
}

/* Bolhas */
.msg-row {
    display: flex;
    margin: 10px 0;
    width: 100%;
}
.msg-row.user {
    justify-content: flex-end;
}
.msg-row.assistant {
    justify-content: flex-start;
}
.bubble {
    max-width: 78%;
    border-radius: 14px;
    padding: 12px 14px;
    line-height: 1.45;
    font-size: 0.97rem;
    box-shadow: 0 4px 14px rgba(0,0,0,0.08);
    white-space: pre-wrap;
    word-wrap: break-word;
}
.bubble.user {
    background: linear-gradient(180deg, #083b7a 0%, #072f63 100%);
    color: #ffffff;
    border: 1px solid rgba(255,255,255,0.08);
}
.bubble.assistant {
    background: #ffffff;
    color: #111827;
    border: 1px solid rgba(15,23,42,0.08);
}
.bubble .label {
    font-weight: 700;
    margin-bottom: 4px;
}

/* Estado vazio */
.empty-state {
    margin-top: 80px;
    text-align: center;
    color: #6b7280;
    font-size: 0.95rem;
}

/* Chips anexos */
.chips-wrap {
    display: flex;
    flex-wrap: wrap;
    gap: 6px;
    margin: 8px 0 6px 0;
}
.chip {
    border: 1px solid rgba(15,23,42,0.12);
    border-radius: 999px;
    padding: 5px 10px;
    font-size: 0.82rem;
    background: rgba(255,255,255,0.90);
    color: #374151;
    box-shadow: 0 2px 10px rgba(0,0,0,0.04);
}

/* st.chat_input */
[data-testid="stChatInput"] {
    background: transparent !important;
}
[data-testid="stChatInput"] textarea {
    border-radius: 14px !important;
    border: 1px solid rgba(15,23,42,0.10) !important;
    background: rgba(255,255,255,0.95) !important;
    box-shadow: 0 6px 24px rgba(15,23,42,0.08) !important;
}

/* Responsivo */
@media (max-width: 900px) {
    .chat-scroll {
        height: calc(100vh - 360px);
        max-height: calc(100vh - 360px);
    }
}
</style>
""",
    unsafe_allow_html=True,
)

# ============================================================
# API / CLIENTE
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

# ============================================================
# CONFIG ASSISTENTE
# ============================================================
DEFAULT_MODEL = "gemini-2.5-flash-lite"  # free
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
# SESSION STATE
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


# ============================================================
# UTILITÁRIOS (DOCX/XLSX -> TEXTO)
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
# RENDER DO CHAT + AUTO-SCROLL
# ============================================================
def build_chat_html(messages, partial_assistant_text=None):
    rows = []

    if not messages and not partial_assistant_text:
        rows.append(
            '<div class="empty-state">'
            'Posso analisar documentos, imagens, áudios e vídeos.<br>'
            'Pergunte algo ao Mestre ou envie anexos para análise.'
            '</div>'
        )
    else:
        for msg in messages:
            role = msg["role"]
            content = msg["content"]
            safe = html.escape(content).replace("\n", "<br>")
            label = '<div class="label">Mestre:</div>' if role == "assistant" else ""

            rows.append(
                f'<div class="msg-row {role}">'
                f'  <div class="bubble {role}">{label}{safe}</div>'
                f'</div>'
            )

        if partial_assistant_text:
            safe = html.escape(partial_assistant_text).replace("\n", "<br>")
            rows.append(
                '<div class="msg-row assistant">'
                '  <div class="bubble assistant"><div class="label">Mestre:</div>'
                f'  {safe}</div>'
                '</div>'
            )

    return (
        '<div class="chat-shell">'
        '<div id="falcon-chat-scroll" class="chat-scroll">'
        + "".join(rows)
        + '<div id="falcon-chat-bottom"></div>'
        '</div>'
        '</div>'
    )


def render_chat(chat_placeholder, messages, partial_assistant_text=None):
    chat_placeholder.markdown(
        build_chat_html(messages, partial_assistant_text),
        unsafe_allow_html=True,
    )

    # força scroll para o fim dentro do painel
    components.html(
        """
<script>
  const d = window.parent.document;
  const el = d.getElementById("falcon-chat-scroll");
  if (el) {
    el.scrollTop = el.scrollHeight;
  }
</script>
""",
        height=0,
    )


# ============================================================
# SIDEBAR
# ============================================================
with st.sidebar:
    st.markdown(
        """
<div class="brand-wrap">
  <div class="brand-icon">🦅</div>
  <div class="brand-text">
    <div class="name">Falcon</div>
    <div class="sub">Assistente Jurídico</div>
  </div>
</div>
""",
        unsafe_allow_html=True,
    )

    if st.button("➕  Nova Conversa", use_container_width=True):
        st.session_state.chat = create_chat(st.session_state.model_name, st.session_state.temperature)
        st.session_state.messages = []
        st.rerun()

    if st.button("🕘  Histórico", use_container_width=True):
        st.session_state.show_history = not st.session_state.show_history

    with st.popover("📄  Documentos", use_container_width=True):
        st.caption("Importe anexos para a próxima mensagem")
        selected_files_sidebar = st.file_uploader(
            "Anexar",
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
        st.caption("Os anexos ficam prontos para envio no chat.")

    with st.popover("⚙️  Configurações", use_container_width=True):
        new_model = st.selectbox(
            "Modelo",
            ["gemini-2.5-flash-lite", "gemini-2.5-flash"],
            index=0 if st.session_state.model_name == "gemini-2.5-flash-lite" else 1,
        )
        new_temp = st.slider("Criatividade", 0.0, 1.0, float(st.session_state.temperature), 0.1)

        if st.button("Aplicar", use_container_width=True):
            st.session_state.model_name = new_model
            st.session_state.temperature = new_temp
            st.session_state.chat = create_chat(new_model, new_temp)
            st.session_state.messages = []
            st.rerun()

    st.link_button("🎙️  Falcon Live", LIVE_URL, use_container_width=True)

    if st.session_state.show_history:
        st.markdown("---")
        st.caption("Histórico (sessão atual)")
        user_msgs = [m["content"] for m in st.session_state.messages if m["role"] == "user"]
        if not user_msgs:
            st.caption("Sem mensagens ainda.")
        else:
            for i, txt in enumerate(user_msgs[-8:], 1):
                preview = txt.replace("\n", " ")
                if len(preview) > 45:
                    preview = preview[:45] + "..."
                st.caption(f"{i}. {preview}")

selected_files = locals().get("selected_files_sidebar") or []

# ============================================================
# MAIN
# ============================================================
st.markdown('<div class="main-title">Falcon</div>', unsafe_allow_html=True)
st.markdown(
    '<div class="main-subtitle">Visão, precisão e estratégia para seus casos.</div>',
    unsafe_allow_html=True,
)

st.markdown(
    f'<div class="top-actions"><a class="live-pill" href="{html.escape(LIVE_URL)}" target="_blank">🎙️ Falcon Live</a></div>',
    unsafe_allow_html=True,
)

chat_placeholder = st.empty()
render_chat(chat_placeholder, st.session_state.messages)

if selected_files:
    chips = "".join([f'<span class="chip">📎 {html.escape(f.name)}</span>' for f in selected_files])
    st.markdown(f'<div class="chips-wrap">{chips}</div>', unsafe_allow_html=True)

# Input sempre visível
pergunta = st.chat_input("Pergunte algo ao Mestre...")

# ============================================================
# ENVIO / STREAMING
# ============================================================
if pergunta and pergunta.strip():
    pergunta = pergunta.strip()

    user_display = pergunta
    if selected_files:
        user_display += "\n\n📎 Anexos enviados: " + ", ".join([f.name for f in selected_files])

    # mensagem do usuário
    st.session_state.messages.append({"role": "user", "content": user_display})
    render_chat(chat_placeholder, st.session_state.messages)

    try:
        refs = []
        if selected_files:
            with st.spinner("🦅 Lendo anexos..."):
                refs, labels = upload_attachments(selected_files)

            info_txt = "✅ Anexos processados: " + " • ".join(labels)
            st.session_state.messages.append({"role": "assistant", "content": info_txt})
            render_chat(chat_placeholder, st.session_state.messages)

        payload = [*refs, pergunta] if refs else pergunta

        chunks = []
        for chunk in st.session_state.chat.send_message_stream(payload):
            txt = getattr(chunk, "text", None)
            if txt:
                chunks.append(txt)
                parcial = "".join(chunks)
                render_chat(chat_placeholder, st.session_state.messages, partial_assistant_text=parcial)

        final_text = "".join(chunks).strip() or "Não consegui responder agora. Tenta reformular."
        st.session_state.messages.append({"role": "assistant", "content": final_text})

        # limpa anexos após envio
        st.session_state.uploader_key += 1

        render_chat(chat_placeholder, st.session_state.messages)
        st.rerun()

    except Exception as e:
        err = f"❌ Erro: {e}"
        st.session_state.messages.append({"role": "assistant", "content": err})
        render_chat(chat_placeholder, st.session_state.messages)
