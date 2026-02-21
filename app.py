import io
import time
import mimetypes
from pathlib import Path

import streamlit as st
from google import genai
from google.genai import types
from docx import Document
from openpyxl import load_workbook

# ============================================================
# 1) CONFIGURAÇÃO DA PÁGINA
# ============================================================
st.set_page_config(
    page_title="My Legal Assistant",
    page_icon="⚖️",
    layout="wide"
)

st.title("⚖️ My Legal Assistant")
st.markdown("Assistente jurídico + professor particular, com suporte a anexos (PDF, imagem, áudio, vídeo, documentos).")

# ============================================================
# 2) CHAVE DA API
# ============================================================
API_KEY = st.secrets.get("GEMINI_API_KEY")
if not API_KEY:
    st.error("❌ Falta configurar `GEMINI_API_KEY` no Streamlit Secrets.")
    st.info('No Streamlit Cloud → Settings → Secrets:\n\nGEMINI_API_KEY = "SUA_CHAVE_AQUI"')
    st.stop()

# ============================================================
# 3) CLIENTE GEMINI
# ============================================================
@st.cache_resource
def get_client(api_key: str):
    return genai.Client(api_key=api_key)

client = get_client(API_KEY)

# ============================================================
# 4) SIDEBAR (MODELO / AJUSTES)
# ============================================================
with st.sidebar:
    st.subheader("⚙️ Configurações")
    model_name = st.selectbox(
        "Modelo",
        ["gemini-2.5-flash-lite", "gemini-2.5-flash"],
        index=0
    )
    temperatura = st.slider("Temperatura", 0.0, 1.0, 0.6, 0.1)
    st.caption("Flash-Lite = mais leve / Flash = respostas mais caprichadas")

    st.markdown("---")
    st.subheader("📎 Anexos suportados")
    st.markdown(
        "- PDF\n"
        "- Imagens (jpg/png/webp/bmp)\n"
        "- Áudio (mp3/wav/m4a/ogg/flac)\n"
        "- Vídeo (mp4/mov/webm/mkv etc.)\n"
        "- Texto / JSON / CSV / HTML / XML / RTF\n"
        "- DOCX (convertido para texto)\n"
        "- XLSX/XLSM (convertido para texto)\n"
    )
    st.caption("Arquivos enviados ao Gemini Files API são temporários (expiram).")

# ============================================================
# 5) PROMPT (ESTILO FLUIDO)
# ============================================================
INSTRUCAO_MESTRA = """
Você é o meu Assistente Pessoal, Jurídico e Professor Particular.

ESTILO:
- Fale em português do Brasil.
- Responda de forma natural, fluida, humana e didática.
- Evite respostas robóticas e repetitivas.
- Use listas só quando elas ajudarem de verdade.
- Quando eu trouxer documentos/anexos, analise o conteúdo com clareza e organização.
- Se for tema jurídico, explique como professor particular, com exemplos práticos.
- Se eu estiver estudando, pode usar método socrático (uma pergunta por vez).
- Se eu pedir análise de caso, organize em: fatos, pontos jurídicos, riscos e estratégia.

CUIDADOS JURÍDICOS:
- Não invente lei, artigo, súmula ou precedente.
- Se estiver em dúvida, diga que precisa confirmar.
- Diferencie explicação educativa de orientação profissional definitiva.
"""

# ============================================================
# 6) ESTADO DA SESSÃO
# ============================================================
def iniciar_chat(selected_model: str):
    return client.chats.create(
        model=selected_model,
        config=types.GenerateContentConfig(
            system_instruction=INSTRUCAO_MESTRA,
            temperature=temperatura,
            top_p=0.95,
            max_output_tokens=4096
        )
    )

if "selected_model" not in st.session_state:
    st.session_state.selected_model = model_name

if "chat" not in st.session_state or st.session_state.selected_model != model_name:
    st.session_state.selected_model = model_name
    st.session_state.chat = iniciar_chat(model_name)
    st.session_state.messages = []
    st.session_state.last_response = ""

if "messages" not in st.session_state:
    st.session_state.messages = []

if "last_response" not in st.session_state:
    st.session_state.last_response = ""

# ============================================================
# 7) UTILITÁRIOS DE DOCUMENTOS
# ============================================================
def guess_mime(uploaded_file) -> str:
    # Streamlit normalmente preenche .type, mas nem sempre
    mime = getattr(uploaded_file, "type", None) or ""
    if mime:
        return mime
    guessed, _ = mimetypes.guess_type(uploaded_file.name)
    return guessed or "application/octet-stream"


def docx_to_text(file_bytes: bytes) -> str:
    doc = Document(io.BytesIO(file_bytes))
    parts = []
    for p in doc.paragraphs:
        txt = (p.text or "").strip()
        if txt:
            parts.append(txt)

    # Também tenta capturar tabelas
    for table in doc.tables:
        parts.append("\n[TABELA]")
        for row in table.rows:
            vals = []
            for cell in row.cells:
                vals.append((cell.text or "").replace("\n", " ").strip())
            parts.append(" | ".join(vals))

    return "\n".join(parts).strip()


def xlsx_to_text(file_bytes: bytes, max_rows_per_sheet: int = 200, max_cols: int = 20) -> str:
    wb = load_workbook(io.BytesIO(file_bytes), data_only=True)
    chunks = []

    for ws in wb.worksheets:
        chunks.append(f"\n### PLANILHA: {ws.title}\n")
        row_count = 0

        for row in ws.iter_rows(values_only=True):
            if row_count >= max_rows_per_sheet:
                chunks.append("[... linhas adicionais omitidas ...]")
                break

            vals = []
            for cell in row[:max_cols]:
                vals.append("" if cell is None else str(cell))
            # ignora linhas totalmente vazias
            if any(v.strip() for v in vals):
                chunks.append(" | ".join(vals))
                row_count += 1

    return "\n".join(chunks).strip()


def normalize_for_upload(uploaded_file):
    """
    Retorna (bytes_io, mime_type, display_name, note)
    Alguns formatos são convertidos localmente para texto.
    """
    raw = uploaded_file.getvalue()
    name = uploaded_file.name
    ext = Path(name).suffix.lower()
    mime = guess_mime(uploaded_file)

    # DOCX -> texto
    if ext == ".docx":
        text = docx_to_text(raw)
        if not text:
            text = "[Documento DOCX sem texto extraível]"
        bio = io.BytesIO(text.encode("utf-8"))
        bio.seek(0)
        return bio, "text/plain", f"{name}.txt", "DOCX convertido para texto"

    # XLSX / XLSM -> texto tabular
    if ext in [".xlsx", ".xlsm"]:
        text = xlsx_to_text(raw)
        if not text:
            text = "[Planilha sem conteúdo legível]"
        bio = io.BytesIO(text.encode("utf-8"))
        bio.seek(0)
        return bio, "text/plain", f"{name}.txt", "Planilha convertida para texto"

    # DOC antigo não é suportado nativamente aqui
    if ext == ".doc":
        raise ValueError(
            f"O arquivo {name} é .doc (formato antigo). "
            "Converta para .docx ou PDF e tente novamente."
        )

    # Demais arquivos: envia como estão
    bio = io.BytesIO(raw)
    bio.seek(0)
    return bio, mime, name, None


def wait_until_active(file_obj, timeout_seconds: int = 300):
    """
    Alguns arquivos (especialmente áudio/vídeo) passam por processamento.
    Espera até ficar ACTIVE.
    """
    start = time.time()
    while True:
        info = client.files.get(name=file_obj.name)
        state = getattr(info, "state", None)

        # Estado pode vir como string ou enum
        state_str = getattr(state, "name", None) or str(state)

        if "ACTIVE" in state_str:
            return info

        if "FAILED" in state_str:
            msg = getattr(getattr(info, "error", None), "message", None) or "Falha no processamento do arquivo."
            raise RuntimeError(msg)

        if time.time() - start > timeout_seconds:
            raise TimeoutError("Tempo limite ao processar arquivo (especialmente comum em vídeos grandes).")

        time.sleep(2)


def upload_files_to_gemini(uploaded_files):
    """
    Faz upload dos anexos para o Gemini Files API e devolve:
    - lista de objetos File (pra usar no prompt)
    - lista de descrições (pra exibir no chat)
    """
    gemini_files = []
    labels = []

    for uf in uploaded_files:
        bio, mime, display_name, note = normalize_for_upload(uf)

        # Upload (Files API)
        uploaded = client.files.upload(
            file=bio,
            config={
                "mime_type": mime,
                "display_name": display_name
            }
        )

        # Aguarda processamento ficar ativo (recomendado para mídia)
        uploaded = wait_until_active(uploaded)

        gemini_files.append(uploaded)

        label = f"{uf.name}"
        if note:
            label += f" ({note})"
        labels.append(label)

    return gemini_files, labels


# ============================================================
# 8) STREAM DE RESPOSTA
# ============================================================
def stream_chat_response(chat, user_text: str, attached_gemini_files=None):
    attached_gemini_files = attached_gemini_files or []
    st.session_state.last_response = ""

    # Se houver arquivos, envia junto com o texto
    payload = [*attached_gemini_files, user_text] if attached_gemini_files else user_text

    chunks_acc = []
    for chunk in chat.send_message_stream(payload):
        txt = getattr(chunk, "text", None)
        if txt:
            chunks_acc.append(txt)
            yield txt

    st.session_state.last_response = "".join(chunks_acc).strip()


# ============================================================
# 9) BARRA DE AÇÕES
# ============================================================
c1, c2 = st.columns([1, 1])
with c2:
    if st.button("🗑️ Limpar conversa", use_container_width=True):
        st.session_state.chat = iniciar_chat(model_name)
        st.session_state.messages = []
        st.session_state.last_response = ""
        st.rerun()

# ============================================================
# 10) ÁREA DE ANEXOS
# ============================================================
st.markdown("### 📎 Anexar arquivos para a próxima mensagem")
uploaded_files = st.file_uploader(
    "Você pode enviar vários arquivos de uma vez (PDF, imagens, áudio, vídeo, DOCX, XLSX, etc.)",
    accept_multiple_files=True,
    type=[
        "pdf",
        "png", "jpg", "jpeg", "webp", "bmp",
        "mp3", "wav", "m4a", "aac", "ogg", "flac",
        "mp4", "mov", "avi", "webm", "mkv", "mpeg",
        "txt", "md", "csv", "json", "html", "xml", "rtf",
        "docx",
        "xlsx", "xlsm"
    ],
    help="Os anexos selecionados serão enviados com a próxima mensagem."
)

if uploaded_files:
    st.caption("Anexos prontos para envio:")
    st.write([f.name for f in uploaded_files])

# ============================================================
# 11) HISTÓRICO DO CHAT
# ============================================================
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

# ============================================================
# 12) INPUT + ENVIO
# ============================================================
pergunta = st.chat_input("Digite sua pergunta jurídica ou peça análise dos anexos...")

if pergunta:
    # Mostra a mensagem do usuário (com nomes dos anexos)
    user_display = pergunta
    if uploaded_files:
        nomes = ", ".join([f.name for f in uploaded_files])
        user_display += f"\n\n📎 **Anexos enviados:** {nomes}"

    st.session_state.messages.append({"role": "user", "content": user_display})
    with st.chat_message("user"):
        st.markdown(user_display)

    # Resposta
    with st.chat_message("assistant"):
        try:
            attached_refs = []
            if uploaded_files:
                with st.spinner("Enviando e processando anexos..."):
                    attached_refs, labels = upload_files_to_gemini(uploaded_files)

                # Mostra confirmação dos anexos processados
                st.caption("✅ Anexos processados: " + " • ".join(labels))

            # Streaming da resposta
            stream_output = st.write_stream(
                stream_chat_response(
                    st.session_state.chat,
                    pergunta,
                    attached_gemini_files=attached_refs
                )
            )

            # st.write_stream costuma retornar string final quando recebe chunks de texto
            texto_final = st.session_state.last_response or (stream_output if isinstance(stream_output, str) else "")
            if not texto_final:
                texto_final = "Não consegui gerar resposta agora. Tenta reformular a pergunta."

            st.session_state.messages.append({"role": "assistant", "content": texto_final})

        except Exception as e:
            erro = str(e).lower()

            if "api key" in erro or "unauthorized" in erro or "permission" in erro:
                st.error("❌ Erro de autenticação. Verifica a `GEMINI_API_KEY` no Streamlit Secrets.")
            elif "not found" in erro:
                st.error("❌ Recurso não encontrado (modelo ou arquivo). Verifica a configuração.")
            elif "timeout" in erro:
                st.error("⏳ O processamento do arquivo demorou demais (muito comum em vídeo grande). Tenta reduzir o arquivo.")
            else:
                st.error(f"❌ Erro: {e}")
