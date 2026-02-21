import asyncio
import json
import threading
from pathlib import Path

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from google import genai
from google.genai import types

# ============================================================
# CONFIG
# ============================================================
BASE_DIR = Path(__file__).resolve().parent
STATIC_DIR = BASE_DIR / "static"

app = FastAPI(title="Falcão Live")

if STATIC_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

# IMPORTANTE:
# Em produção (Render/Railway), configure GEMINI_API_KEY como variável de ambiente.
import os
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

if not GEMINI_API_KEY:
    print("⚠️ GEMINI_API_KEY não encontrada no ambiente.")

client = genai.Client(api_key=GEMINI_API_KEY) if GEMINI_API_KEY else None

MODEL_NAME = os.getenv("FALCAO_LIVE_MODEL", "gemini-2.5-flash-lite")

SYSTEM_INSTRUCTION = """
Você é o Falcão Live, um assistente jurídico por voz.
Fale em português do Brasil de forma natural, fluida e objetiva.
Explique temas jurídicos de forma didática.
Não invente leis ou precedentes; se estiver em dúvida, avise.
Responda como em uma conversa por voz: claro, direto e humano.
"""

@app.get("/")
def root():
    return JSONResponse({"ok": True, "name": "Falcão Live", "route": "/live"})

@app.get("/live")
def live_page():
    return FileResponse(STATIC_DIR / "falcao_live.html")

@app.websocket("/ws/live")
async def ws_live(ws: WebSocket):
    await ws.accept()

    if client is None:
        await ws.send_text(json.dumps({
            "type": "error",
            "message": "GEMINI_API_KEY não configurada no servidor Live."
        }))
        await ws.close()
        return

    chat = client.chats.create(
        model=MODEL_NAME,
        config=types.GenerateContentConfig(
            system_instruction=SYSTEM_INSTRUCTION,
            temperature=0.6,
            top_p=0.95,
            max_output_tokens=2048,
        )
    )

    current_task = None
    current_stop_event = None

    async def cancel_current_generation():
        nonlocal current_task, current_stop_event
        if current_stop_event:
            current_stop_event.set()
        if current_task and not current_task.done():
            current_task.cancel()
            try:
                await current_task
            except Exception:
                pass
        current_task = None
        current_stop_event = None

    async def generate_stream_to_browser(user_text: str):
        """
        Gera resposta em stream (texto) e envia chunks ao navegador.
        Usa thread interna porque o SDK expõe iterador síncrono.
        """
        loop = asyncio.get_running_loop()
        queue = asyncio.Queue()
        stop_event = threading.Event()

        def worker():
            try:
                for chunk in chat.send_message_stream(user_text):
                    if stop_event.is_set():
                        break
                    txt = getattr(chunk, "text", None)
                    if txt:
                        asyncio.run_coroutine_threadsafe(
                            queue.put({"type": "assistant_chunk", "text": txt}),
                            loop
                        )
                asyncio.run_coroutine_threadsafe(
                    queue.put({"type": "assistant_done"}),
                    loop
                )
            except Exception as e:
                asyncio.run_coroutine_threadsafe(
                    queue.put({"type": "error", "message": str(e)}),
                    loop
                )

        thread = threading.Thread(target=worker, daemon=True)
        thread.start()

        # expõe stop_event para a função de cancelamento
        nonlocal current_stop_event
        current_stop_event = stop_event

        while True:
            event = await queue.get()
            await ws.send_text(json.dumps(event))

            if event["type"] in ("assistant_done", "error"):
                break

    try:
        await ws.send_text(json.dumps({"type": "status", "value": "connected"}))

        while True:
            raw = await ws.receive_text()
            data = json.loads(raw)
            event_type = data.get("type")

            if event_type == "ping":
                await ws.send_text(json.dumps({"type": "pong"}))

            elif event_type == "interrupt":
                await cancel_current_generation()
                await ws.send_text(json.dumps({"type": "status", "value": "interrupted"}))

            elif event_type == "reset":
                await cancel_current_generation()
                chat = client.chats.create(
                    model=MODEL_NAME,
                    config=types.GenerateContentConfig(
                        system_instruction=SYSTEM_INSTRUCTION,
                        temperature=0.6,
                        top_p=0.95,
                        max_output_tokens=2048,
                    )
                )
                await ws.send_text(json.dumps({"type": "status", "value": "reset"}))

            elif event_type == "user_text":
                user_text = (data.get("text") or "").strip()
                if not user_text:
                    continue

                # interrompe resposta anterior, se houver
                await cancel_current_generation()

                await ws.send_text(json.dumps({"type": "status", "value": "thinking"}))

                async def task_runner():
                    try:
                        await generate_stream_to_browser(user_text)
                    except asyncio.CancelledError:
                        pass

                current_task = asyncio.create_task(task_runner())

            else:
                await ws.send_text(json.dumps({
                    "type": "error",
                    "message": f"Evento desconhecido: {event_type}"
                }))

    except WebSocketDisconnect:
        pass
    except Exception as e:
        try:
            await ws.send_text(json.dumps({"type": "error", "message": str(e)}))
        except Exception:
            pass
    finally:
        try:
            await cancel_current_generation()
        except Exception:
            pass
