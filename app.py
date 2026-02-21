import streamlit as st
from google import genai
from google.genai import types

# ============================================================
# 1) CONFIGURAÇÃO DA PÁGINA
# ============================================================
st.set_page_config(
    page_title="My Legal Assistant",
    page_icon="⚖️",
    layout="centered"
)

st.title("⚖️ My Legal Assistant")
st.markdown("O seu assistente jurídico, mentor e professor particular.")

# ============================================================
# 2) CHAVE DA API (STREAMLIT SECRETS)
# ============================================================
API_KEY = st.secrets.get("GEMINI_API_KEY")

if not API_KEY:
    st.error("❌ Falta configurar a chave `GEMINI_API_KEY` no Streamlit Secrets.")
    st.info(
        "No Streamlit Cloud: Settings → Secrets → adicione:\n\n"
        "GEMINI_API_KEY = \"SUA_CHAVE_AQUI\""
    )
    st.stop()

# ============================================================
# 3) MODELO (FREE)
#    Opções free recomendadas:
#    - gemini-2.5-flash-lite (mais leve)
#    - gemini-2.5-flash (melhor qualidade)
# ============================================================
MODEL_NAME = "gemini-2.5-flash-lite"

# ============================================================
# 4) PROMPT / PERSONALIDADE
# ============================================================
INSTRUCAO_MESTRA = """
Você é o meu Assistente Pessoal, Jurídico e Professor Particular.
Seu tom deve ser amigável, encorajador e altamente didático, conversando de forma fluida e natural.
Quando eu fizer uma pergunta jurídica ou pedir para analisar um caso, explique os conceitos de forma clara,
como se estivesse a dar uma aula, usando exemplos práticos.
Se eu pedir para aprender algo novo, use o método socrático: faça perguntas para testar o meu raciocínio
em vez de apenas dar a resposta pronta.
"""

# ============================================================
# 5) CLIENTE GEMINI (SDK NOVO)
# ============================================================
@st.cache_resource
def get_client():
    return genai.Client(api_key=API_KEY)

client = get_client()

# ============================================================
# 6) ESTADO DA SESSÃO (CHAT + HISTÓRICO VISUAL)
# ============================================================
def iniciar_chat():
    return client.chats.create(
        model=MODEL_NAME,
        config=types.GenerateContentConfig(
            system_instruction=INSTRUCAO_MESTRA,
            temperature=0.4
        )
    )

if "chat" not in st.session_state:
    st.session_state.chat = iniciar_chat()

if "messages" not in st.session_state:
    st.session_state.messages = []

# Botão para limpar conversa
col1, col2 = st.columns([1, 1])
with col2:
    if st.button("🗑️ Limpar conversa", use_container_width=True):
        st.session_state.chat = iniciar_chat()
        st.session_state.messages = []
        st.rerun()

# ============================================================
# 7) MOSTRAR HISTÓRICO
# ============================================================
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

# ============================================================
# 8) ENTRADA DO USUÁRIO
# ============================================================
pergunta = st.chat_input("Digite a sua pergunta jurídica ou peça para analisar um caso...")

if pergunta:
    # Mostra pergunta
    st.session_state.messages.append({"role": "user", "content": pergunta})
    with st.chat_message("user"):
        st.markdown(pergunta)

    # Gera resposta
    with st.chat_message("assistant"):
        try:
            with st.spinner("Pensando..."):
                resposta = st.session_state.chat.send_message(pergunta)

            # Alguns retornos podem vir sem .text pronto
            texto_resposta = getattr(resposta, "text", None)

            if not texto_resposta:
                texto_resposta = (
                    "Não consegui gerar uma resposta em texto agora. "
                    "Tenta reformular a pergunta."
                )

            st.markdown(texto_resposta)
            st.session_state.messages.append({"role": "assistant", "content": texto_resposta})

        except Exception as e:
            erro = str(e)

            # Mensagens mais amigáveis para erros comuns
            if "API key" in erro.lower() or "unauthorized" in erro.lower() or "permission" in erro.lower():
                st.error("❌ Erro de autenticação. Verifica a tua `GEMINI_API_KEY` no Streamlit Secrets.")
            elif "not found" in erro.lower():
                st.error("❌ Modelo não encontrado. Verifica o nome do modelo configurado.")
            else:
                st.error(f"❌ Erro ao chamar o Gemini: {erro}")
