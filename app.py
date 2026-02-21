# ============================================================
# 8) ENTRADA DO USUÁRIO (AGORA FLUIDA / STREAMING)
# ============================================================
pergunta = st.chat_input("Digite a sua pergunta jurídica...")

if pergunta:
    # Mostra a sua pergunta imediatamente
    st.session_state.messages.append({"role": "user", "content": pergunta})
    with st.chat_message("user"):
        st.markdown(pergunta)

    # Gera resposta fluida (chunk por chunk)
    with st.chat_message("assistant"):
        # Criamos um espaço vazio que vamos preencher aos poucos
        placeholder = st.empty()
        texto_completo = ""
        
        try:
            # O comando agora é send_message_stream
            for chunk in client.chats.send_message_stream(pergunta):
                texto_completo += chunk.text
                # Atualiza o texto na tela em tempo real
                placeholder.markdown(texto_completo + "▌") 
            
            # Remove o cursor (▌) no final
            placeholder.markdown(texto_completo)
            st.session_state.messages.append({"role": "assistant", "content": texto_completo})

        except Exception as e:
            st.error(f"❌ Erro ao chamar o Gemini: {e}")
