import streamlit as st
import google.generativeai as genai

# 1. Configuração do Layout do Site
st.set_page_config(page_title="My Legal Assistant", page_icon="⚖️", layout="centered")

# Título da página
st.title("⚖️ My Legal Assistant")
st.markdown("O seu assistente jurídico, mentor e professor particular.")

# 2. Conectando a Chave Secreta (O Motor)
# Quando colocarmos o site online, ele vai puxar a chave que guardou no "Meus acessos"
API_KEY = st.secrets.get("GEMINI_API_KEY", "SUA_CHAVE_AQUI")
genai.configure(api_key=API_KEY)

# 3. Criando a Personalidade (O Prompt do Professor)
instrucao_mestra = """
Você é o meu Assistente Pessoal, Jurídico e Professor Particular. 
Seu tom deve ser amigável, encorajador e altamente didático, conversando de forma fluida e natural. 
Quando eu fizer uma pergunta jurídica ou pedir para analisar um caso, explique os conceitos de forma clara, como se estivesse a dar uma aula, usando exemplos práticos. 
Se eu pedir para aprender algo novo, use o método socrático: faça perguntas para testar o meu raciocínio em vez de apenas dar a resposta pronta.
"""

# Configurar a IA com a personalidade acima
modelo = genai.GenerativeModel(
    model_name="gemini-2.0-flash",
    system_instruction=instrucao_mestra
)

# 4. Criando a Memória da Conversa
if "chat" not in st.session_state:
    st.session_state.chat = modelo.start_chat(history=[])

# Mostrar as mensagens antigas no ecrã
for mensagem in st.session_state.chat.history:
    papel = "user" if mensagem.role == "user" else "assistant"
    with st.chat_message(papel):
        st.markdown(mensagem.parts[0].text)

# 5. A Caixa de Conversa (Onde você digita)
pergunta = st.chat_input("Digite a sua pergunta jurídica ou peça para analisar um caso...")

if pergunta:
    # Mostra a sua pergunta no ecrã
    with st.chat_message("user"):
        st.markdown(pergunta)
    
    # Mostra a resposta do Assistente
    with st.chat_message("assistant"):
        resposta = st.session_state.chat.send_message(pergunta)
        st.markdown(resposta.text)
        
        # Nota: As "ondas" animadas e a voz (edge-tts) serão adicionadas no passo seguinte, 
        # assim que o site estiver no ar para não sobrecarregar o seu computador local!
