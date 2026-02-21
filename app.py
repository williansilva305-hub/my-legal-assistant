import streamlit as st
import google.generativeai as genai

# --- 1. CONFIGURAÇÃO DA PÁGINA ---
st.set_page_config(
    page_title="My Legal Assistant", 
    page_icon="⚖️", 
    layout="centered"
)

# Estilo CSS para deixar o visual mais moderno
st.markdown("""
    <style>
    .stChatMessage { border-radius: 15px; margin-bottom: 10px; }
    .main { background-color: #f8f9fa; }
    </style>
    """, unsafe_allow_config=True)

# --- 2. BARRA LATERAL (SIDEBAR) ---
with st.sidebar:
    st.title("⚖️ Menu do Assistente")
    st.info("Este é o seu mentor jurídico particular, rodando direto do seu Vostro!")
    
    # Botão para limpar o histórico e começar do zero
    if st.button("Limpar Histórico de Conversa"):
        st.session_state.messages = []
        if "chat" in st.session_state:
            del st.session_state.chat
        st.rerun()

# --- 3. CONEXÃO SEGURA COM A IA ---
st.title("⚖️ My Legal Assistant")
st.caption("Mentor Jurídico e Professor Particular")

def carregar_ia():
    try:
        # Busca a chave nos Secrets do Streamlit
        api_key = st.secrets.get("GEMINI_API_KEY")
        
        if not api_key or api_key == "SUA_CHAVE_AQUI":
            st.error("⚠️ Chave API não configurada! Vá em Settings > Secrets no Streamlit.")
            st.stop()
            
        genai.configure(api_key=api_key)
        return True
    except Exception as e:
        st.error(f"❌ Erro de configuração: {e}")
        return False

if carregar_ia():
    # Personalidade do Professor
    instrucao_mestra = """
    Você é o meu Assistente Pessoal, Jurídico e Professor Particular. 
    Seu tom deve ser amigável, encorajador e altamente didático.
    Explique conceitos de forma clara, use exemplos práticos e, se eu quiser aprender algo novo, 
    use o método socrático: faça perguntas para me fazer pensar.
    """

    # Configura o modelo (1.5-flash é o mais estável para contas gratuitas)
    if "model" not in st.session_state:
        st.session_state.model = genai.GenerativeModel(
            model_name="gemini-1.5-flash",
            system_instruction=instrucao_mestra
        )

    # Inicializa a memória da conversa
    if "messages" not in st.session_state:
        st.session_state.messages = []

    if "chat" not in st.session_state:
        st.session_state.chat = st.session_state.model.start_chat(history=[])

    # Exibe as mensagens na tela
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    # --- 4. ÁREA DE INTERAÇÃO ---
    pergunta = st.chat_input("Digite sua dúvida jurídica ou peça uma explicação...")

    if pergunta:
        # Mostra a pergunta do usuário
        st.session_state.messages.append({"role": "user", "content": pergunta})
        with st.chat_message("user"):
            st.markdown(pergunta)

        # Gera a resposta com tratamento de erro (Proteção contra o "Erro Vermelho")
        with st.chat_message("assistant"):
            try:
                with st.spinner("O Mestre está elaborando a resposta..."):
                    resposta = st.session_state.chat.send_message(pergunta)
                    st.markdown(resposta.text)
                    st.session_state.messages.append({"role": "assistant", "content": resposta.text})
            except Exception as e:
                # Aqui está o segredo: se der erro, ele avisa de forma elegante
                if "429" in str(e) or "ResourceExhausted" in str(e):
                    st.warning("☕ O Google atingiu o limite de uso gratuito por agora. Aguarde 60 segundos e tente novamente.")
                elif "NotFound" in str(e):
                    st.error("🔍 Chave não encontrada. Verifique se clicou em 'Save' nos Secrets do Streamlit.")
                else:
                    st.error(f"🤔 Ocorreu um imprevisto: {e}")
