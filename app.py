import io
import os
import time
import tempfile
from pathlib import Path

import streamlit as st
from google import genai
from google.genai import types
from docx import Document
from openpyxl import load_workbook

# ============================================================
# CONFIG DA PÁGINA
# ============================================================
st.set_page_config(
    page_title="Falcão Jurídico",
    page_icon="🦅",
    layout="centered"
)

# CSS clean (estilo chat moderno)
st.markdown("""
<style>
#MainMenu {visibility: hidden;}
footer {visibility: hidden;}
header {visibility: hidden;}

.block-container {
    max-width: 900px;
    padding-top: 1.0rem;
    padding-bottom: 5rem;
}

.app-title {
    font-size: 1.35rem;
    font-weight: 700;
    margin-bottom: 0.15rem;
}

.app-subtitle {
    color: #6b7280;
    font-size: 0.92rem;
    margin-bottom: 0.8rem;
}

.toolbar-wrap {
    border: 1px solid rgba(128,128,128,0.25);
    border-radius: 14px;
    padding: 8px 10px;
    margin-bottom: 10px;
    background: rgba(255,255,255,0.02);
}

.chips-wrap {
    display: flex;
    flex-wrap: wrap;
    gap: 6px;
    margin-top: 4px;
    margin-bottom: 8px;
}
.chip {
    border: 1px solid rgba(128,128,128,0.35);
    border-radius: 999px;
    padding: 4px 10px;
    font-size: 0.82rem;
    color: #374151;
    background: rgba(0,0,0,0.02);
}

.small-muted {
    color: #6b7280;
    font-size: 0.82rem;
}
</style>
""", unsafe_allow_html=True)

# ============================================================
# HEADER
# ============================================================
st.markdown('<div class="app-title">🦅 Falcão Jurídico</div>', unsafe_allow_html=True)
st.markdown(
    '<div class="app-subtitle">Assistente jurídico e professor particular com análise de anexos e conversa fluida.</div>',
    unsafe_allow_html=True
)

# ============================================================
# SECRETS / CHAVE
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
# CONFIGS DO ASSISTENTE
# ============================================================
DEFAULT_MODEL = "gemini-2.5-flash-lite"  # free
DEFAULT_TEMP = 0.6

INSTRUCAO_MESTRA = """
Você é o meu Assistente Pessoal, Jurídico e Professor Particular.

ESTILO:
- Fale em português do Brasil.
- Responda de forma natural, fluida e humana, como um chat moderno.
- Evite tom robótico ou formal demais.
- Só use listas quando realmente ajudarem.
- Em temas jurídicos, explique de forma didática, clara e prática.
- Se eu enviar documentos, imagens, áudio ou vídeo, analise o conteúdo com organização.
- Quando for útil, organize em: fatos, questões jurídicas, riscos e estratégia.

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
        )
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

if "last_response" not in st.session_state:
    st.session_state.last_response = ""

if "uploader_key" not in st.session_state:
    st.session_state.uploader_key = 0

# ============================================================
# UTILITÁRIOS DE CONVERSÃO (DOCX / XLSX -> TEXTO)
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
    """
    Converte alguns formatos localmente (DOCX/XLSX -> TXT)
    e devolve um arquivo temporário pronto para upload no Gemini Files API.
    """
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

    # PDF, imagem, áudio, vídeo, txt etc.
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
# STREAM DE RESPOSTA
# ============================================================
def stream_response(chat, user_text: str, file_refs=None):
    file_refs = file_refs or []
    st.session_state.last_response = ""

    payload = [*file_refs, user_text] if file_refs else user_text
    chunks = []

    for chunk in chat.send_message_stream(payload):
        txt = getattr(chunk, "text", None)
        if txt:
            chunks.append(txt)
            yield txt

    st.session_state.last_response = "".join(chunks).strip()

# ============================================================
# TOOLBAR (IMPORTAR / CONFIG / LIVE)
# ============================================================
st.markdown('<div class="toolbar-wrap">', unsafe_allow_html=True)
col_a, col_b, col_c, col_d = st.columns([1.2, 0.8, 1.3, 2.7])

with col_a:
    with st.popover("📎 Importar", use_container_width=True):
        st.markdown("**Anexar arquivos**")
        st.caption("Documentos, imagens, áudio, vídeo e outros")
        selected_files = st.file_uploader(
            "Anexar",
            accept_multiple_files=True,
            type=[
                "pdf",
                "png", "jpg", "jpeg", "webp", "bmp",
                "mp3", "wav", "m4a", "aac", "ogg", "flac",
                "mp4", "mov", "avi", "webm", "mkv", "mpeg",
                "txt", "md", "csv", "json", "html", "xml", "rtf",
                "docx", "xlsx", "xlsm"
            ],
            label_visibility="collapsed",
            key=f"uploader_{st.session_state.uploader_key}"
        )
        st.caption("Os anexos serão enviados com a próxima mensagem.")

with col_b:
    with st.popover("⚙️", use_container_width=True):
        new_model = st.selectbox(
            "Modelo",
            ["gemini-2.5-flash-lite", "gemini-2.5-flash"],
            index=0 if st.session_state.model_name == "gemini-2.5-flash-lite" else 1
        )
        new_temp = st.slider("Criatividade", 0.0, 1.0, float(st.session_state.temperature), 0.1)

        if st.button("Aplicar e reiniciar", use_container_width=True):
            st.session_state.model_name = new_model
            st.session_state.temperature = new_temp
            st.session_state.chat = create_chat(new_model, new_temp)
            st.session_state.messages = []
            st.session_state.last_response = ""
            st.rerun()

        if st.button("Limpar conversa", use_container_width=True):
            st.session_state.chat = create_chat(st.session_state.model_name, st.session_state.temperature)
            st.session_state.messages = []
            st.session_state.last_response = ""
            st.rerun()

with col_c:
    st.link_button("🎙️ Falcão Live", LIVE_URL, use_container_width=True)

with col_d:
    st.markdown('<div class="small-muted">Visão, precisão e estratégia para seus casos.</div>', unsafe_allow_html=True)

st.markdown('</div>', unsafe_allow_html=True)

selected_files = locals().get("selected_files") or []

# Chips dos anexos
if selected_files:
    chips = "".join([f'<span class="chip">📄 {f.name}</span>' for f in selected_files])
    st.markdown(f'<div class="chips-wrap">{chips}</div>', unsafe_allow_html=True)

# ============================================================
# HISTÓRICO
# ============================================================
if not st.session_state.messages:
    st.info("Posso analisar documentos, imagens, áudios e vídeos. Me diga o que você precisa.")

for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

# ============================================================
# INPUT + RESPOSTA
# ============================================================
pergunta = st.chat_input("Pergunte algo jurídico ou peça para analisar os anexos...")

if pergunta:
    user_display = pergunta
    if selected_files:
        user_display += "\n\n📎 **Anexos enviados:** " + ", ".join([f.name for f in selected_files])

    st.session_state.messages.append({"role": "user", "content": user_display})

    with st.chat_message("user"):
        st.markdown(user_display)

    with st.chat_message("assistant"):
        try:
            refs = []
            if selected_files:
                with st.spinner("🦅 Lendo anexos..."):
                    refs, labels = upload_attachments(selected_files)
                st.caption("✅ " + " • ".join(labels))

            st.write_stream(stream_response(st.session_state.chat, pergunta, refs))

            final_text = st.session_state.last_response or "Não consegui responder agora. Tenta reformular."
            st.session_state.messages.append({"role": "assistant", "content": final_text})

            # limpa anexos após envio
            st.session_state.uploader_key += 1
            st.rerun()

        except Exception as e:
            st.error(f"❌ Erro: {e}")
