import io
import os
import time
import html
import base64
import tempfile
from pathlib import Path

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
# HELPERS VISUAIS
# ============================================================
def get_logo_data_uri() -> str | None:
    """
    Procura o logo em caminhos comuns do projeto e devolve data URI.
    Esperado: assets/falcon_logo.png
    """
    candidates = [
        Path("assets/falcon_logo.png"),
        Path("falcon_logo.png"),
        Path("assets/logo.png"),
    ]
    for p in candidates:
        if p.exists() and p.is_file():
            mime = "image/png"
            if p.suffix.lower() in [".jpg", ".jpeg"]:
                mime = "image/jpeg"
            raw = p.read_bytes()
            b64 = base64.b64encode(raw).decode("utf-8")
            return f"data:{mime};base64,{b64}"
    return None


LOGO_URI = get_logo_data_uri()


# ============================================================
# CSS (estilo mock)
# ============================================================
logo_html_sidebar = (
    f'<img src="{LOGO_URI}" class="falcon-logo-img" />'
    if LOGO_URI
    else '<div class="falcon-logo-fallback">🦅</div>'
)

logo_html_top = (
    f'<img src="{LOGO_URI}" class="top-logo-img" />'
    if LOGO_URI
    else '<div class="top-logo-fallback">⚖️</div>'
)

st.markdown(
    f"""
<style>
/* Esconde elementos padrão */
#MainMenu, footer, header {{
    visibility: hidden;
}}
[data-testid="collapsedControl"] {{
    display: none;
}}

/* Fundo geral */
[data-testid="stAppViewContainer"] {{
    background: #f2f4f8;
}}

/* Margens gerais */
.block-container {{
    padding-top: 0.6rem !important;
    padding-bottom: 0.6rem !important;
}}

/* ========== SIDEBAR (escura) ========== */
[data-testid="stSidebar"] {{
    background:
      radial-gradient(circle at 15% 10%, rgba(255,191,82,0.10) 0%, rgba(255,191,82,0.00) 35%),
      linear-gradient(180deg, #101826 0%, #0b1018 100%);
    border-right: 1px solid rgba(255,255,255,0.05);
}}
[data-testid="stSidebar"] * {{
    color: #f3f4f6 !important;
}}

.sidebar-brand {{
    display: flex;
    align-items: center;
    gap: 10px;
    padding: 6px 4px 8px 4px;
    margin-bottom: 8px;
}}
.falcon-logo-img {{
    width: 38px;
    height: 38px;
    object-fit: contain;
    border-radius: 10px;
    background: rgba(255,255,255,0.02);
}}
.falcon-logo-fallback {{
    width: 38px;
    height: 38px;
    border-radius: 10px;
    display: flex;
    align-items: center;
    justify-content: center;
    background: rgba(255,255,255,0.05);
    font-size: 20px;
}}
.sidebar-brand-text {{
    display: flex;
    flex-direction: column;
    line-height: 1.1;
}}
.sidebar-brand-text .title {{
    font-weight: 700;
    font-size: 1rem;
    color: #fff;
}}
.sidebar-brand-text .sub {{
    font-size: .75rem;
    color: #9aa5b5;
}}

[data-testid="stSidebar"] .stButton > button,
[data-testid="stSidebar"] .stLinkButton > a,
[data-testid="stSidebar"] .stPopover > button {{
    width: 100%;
    justify-content: flex-start;
    border-radius: 12px;
    border: 1px solid rgba(255,255,255,0.08);
    background: rgba(255,255,255,0.03);
    color: #f9fafb !important;
    padding: 0.65rem 0.85rem;
    box-shadow: none !important;
}}
[data-testid="stSidebar"] .stButton > button:hover,
[data-testid="stSidebar"] .stLinkButton > a:hover,
[data-testid="stSidebar"] .stPopover > button:hover {{
    background: rgba(255,255,255,0.06);
    border-color: rgba(255,255,255,0.16);
}}

/* ========== TOPO AZUL ========== */
.falcon-topbar {{
    background: linear-gradient(90deg, #0f2f7e 0%, #0d43b4 100%);
    border-radius: 12px 12px 0 0;
    padding: 12px 16px;
    display: flex;
    align-items: center;
    justify-content: space-between;
    box-shadow: 0 8px 18px rgba(15,47,126,0.18);
}}
.falcon-topbar-left {{
    display: flex;
    align-items: center;
    gap: 10px;
}}
.top-logo-img {{
    width: 28px;
    height: 28px;
    object-fit: contain;
}}
.top-logo-fallback {{
    width: 28px;
    height: 28px;
    display: flex;
    align-items: center;
    justify-content: center;
    color: white;
    font-size: 18px;
}}
.falcon-topbar-title {{
    color: #fff;
    font-weight: 700;
    font-size: 0.98rem;
}}
.falcon-avatar {{
    width: 32px;
    height: 32px;
    border-radius: 999px;
    background: rgba(255,255,255,0.25);
    border: 1px solid rgba(255,255,255,0.35);
    display: flex;
    align-items: center;
    justify-content: center;
    color: white;
    font-size: 15px;
}}

.falcon-subbar {{
    background: #eef1f5;
    color: #4b5563;
    border: 1px solid #dfe5ee;
    border-top: none;
    border-radius: 0 0 12px 12px;
    padding: 8px 14px;
    margin-bottom: 12px;
    font-size: 0.86rem;
}}

/* ========== CHAT CARD ========== */
.chat-card {{
    background: #ffffff;
    border: 1px solid #dfe5ee;
    border-radius: 14px;
    box-shadow: 0 8px 24px rgba(15,23,42,0.06);
    padding: 12px;
}}

.chat-scroll {{
    height: calc(100vh - 355px);
    min-height: 320px;
    max-height: calc(100vh - 355px);
    overflow-y: auto;
    padding: 4px 4px 8px 4px;
    scroll-behavior: smooth;
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
    line-height: 1.42;
    font-size: 0.96rem;
    white-space: pre-wrap;
    word-wrap: break-word;
}}
.bubble.user {{
    background: linear-gradient(180deg, #0d4aa5 0%, #0a3781 100%);
    color: #fff;
    border: 1px solid rgba(255,255,255,0.16);
    box-shadow: 0 4px 12px rgba(10,55,129,0.18);
}}
.bubble.assistant {{
    background: #eceff4;
    color: #111827;
    border: 1px solid #e3e8ef;
}}
.bubble .label {{
    font-weight: 700;
    margin-bottom: 4px;
    color: #111827;
}}

.empty-state {{
    color: #6b7280;
    text-align: center;
    padding-top: 80px;
    font-size: 0.95rem;
}}

/* Chips anexos */
.chips-wrap {{
    display: flex;
    gap: 6px;
    flex-wrap: wrap;
    margin: 8px 2px 10px 2px;
}}
.chip {{
    border-radius: 999px;
    border: 1px solid #d9e1ea;
    background: #f9fbfd;
    color: #334155;
    padding: 4px 10px;
    font-size: 0.8rem;
}}

/* Top actions (Live) */
.top-actions {{
    display: flex;
    justify-content: flex-end;
    margin-bottom: 8px;
}}
.live-pill {{
    display: inline-flex;
    align-items: center;
    gap: 6px;
    border-radius: 999px;
    border: 1px solid #d9e1ea;
    background: #ffffff;
    color: #0f172a;
    text-decoration: none;
    padding: 8px 12px;
    font-size: 0.88rem;
}}
.live-pill:hover {{
    background: #f8fafc;
    border-color: #cdd7e3;
}}

/* Chat input (mantém estável e bonito) */
[data-testid="stChatInput"] {{
    margin-top: 8px;
}}
[data-testid="stChatInput"] textarea {{
    border-radius: 12px !important;
    border: 1px solid #d9e1ea !important;
    background: #ffffff !important;
    box-shadow: 0 4px 16px rgba(15,23,42,0.06) !important;
    min-height: 44px !important;
}}
[data-testid="stChatInput"] button {{
    border-radius: 10px !important;
}}

/* Responsivo */
@media (max-width: 900px) {{
    .chat-scroll {{
        height: calc(100vh - 395px);
        max-height: calc(100vh - 395px);
    }}
    .falcon-subbar {{
        font-size: 0.8rem;
    }}
}}
</style>
""",
    unsafe_allow_html=True,
)


# ============================================================
# GEMINI (FREE)
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

DEFAULT_MODEL = "gemini-2.5-flash-lite"  # modelo free
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


# ============================================================
# UTILIDADES DE ARQUIVOS
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
# CHAT HTML (fixo + scroll)
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
            label = '<div class="label">Falcão:</div>' if role == "assistant" else ""

            rows.append(
                f'<div class="msg-row {role}">'
                f'  <div class="bubble {role}">{label}{safe}</div>'
                f'</div>'
            )

        if partial_assistant_text:
            safe = html.escape(partial_assistant_text).replace("\n", "<br>")
            rows.append(
                '<div class="msg-row assistant">'
                '  <div class="bubble assistant"><div class="label">Falcão:</div>'
                f'  {safe}</div>'
                '</div>'
            )

    return (
        '<div class="chat-card">'
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

    # Auto-scroll no painel interno
    components.html(
        """
<script>
  const d = window.parent.document;
  const el = d.getElementById("falcon-chat-scroll");
  if (el) { el.scrollTop = el.scrollHeight; }
</script>
""",
        height=0,
    )


# ============================================================
# SIDEBAR (estilo mock)
# ============================================================
with st.sidebar:
    st.markdown(
        f"""
<div class="sidebar-brand">
  {logo_html_sidebar}
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
        st.rerun()

    with st.popover("📎  Importar Documentos", use_container_width=True):
        st.caption("Anexe arquivos para a próxima mensagem")
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
        st.caption("Os anexos aparecem em chips acima do campo de mensagem.")

    if st.button("🕘  Histórico", use_container_width=True):
        st.session_state.show_history = not st.session_state.show_history

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

    if st.session_state.show_history:
        st.markdown("---")
        st.caption("Sessão atual")
        user_msgs = [m["content"] for m in st.session_state.messages if m["role"] == "user"]
        if not user_msgs:
            st.caption("Sem mensagens ainda.")
        else:
            for i, txt in enumerate(user_msgs[-8:], 1):
                preview = txt.replace("\n", " ")
                if len(preview) > 42:
                    preview = preview[:42] + "..."
                st.caption(f"{i}. {preview}")

selected_files = locals().get("selected_files_sidebar") or []


# ============================================================
# TOPO (igual ao mock)
# ============================================================
st.markdown(
    f"""
<div class="falcon-topbar">
  <div class="falcon-topbar-left">
    {logo_html_top}
    <div class="falcon-topbar-title">My Legal Assistant</div>
  </div>
  <div class="falcon-avatar">👤</div>
</div>
<div class="falcon-subbar">Assistente jurídico e professor particular, com anexos e resposta fluida.</div>
""",
    unsafe_allow_html=True,
)

# botão Falcon Live (estilo pill no topo do chat)
st.markdown(
    f'<div class="top-actions"><a class="live-pill" href="{html.escape(LIVE_URL)}" target="_blank">🎙️ Falcon Live</a></div>',
    unsafe_allow_html=True,
)

# chat
chat_placeholder = st.empty()
render_chat(chat_placeholder, st.session_state.messages)

# chips de anexos
if selected_files:
    chips = "".join([f'<span class="chip">📎 {html.escape(f.name)}</span>' for f in selected_files])
    st.markdown(f'<div class="chips-wrap">{chips}</div>', unsafe_allow_html=True)

# campo de digitar (estável)
pergunta = st.chat_input("Digite sua mensagem...")


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
            with st.spinner("🦅 Processando anexos..."):
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

        # limpa anexos depois do envio
        st.session_state.uploader_key += 1

        render_chat(chat_placeholder, st.session_state.messages)
        st.rerun()

    except Exception as e:
        err = f"❌ Erro: {e}"
        st.session_state.messages.append({"role": "assistant", "content": err})
        render_chat(chat_placeholder, st.session_state.messages)
