import chainlit as cl
from openai import AsyncOpenAI
import json
import os
from dotenv import load_dotenv
from calendar_utils import get_available_slots, book_slot  # Lo crearemos en el Hito 1

load_dotenv()

client = AsyncOpenAI(
    api_key=os.getenv("GEMINI_API_KEY"),
    base_url="https://generativelanguage.googleapis.com/v1beta/openai/"
)

with open("prompt.txt", "r", encoding="utf-8") as f:
    SYSTEM_PROMPT = f.read()

# Definición de herramientas (tools) para el modelo
TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "get_available_slots",
            "description": "Obtiene los horarios disponibles del calendario para agendar visitas",
            "parameters": {
                "type": "object",
                "properties": {
                    "modalidad": {
                        "type": "string",
                        "enum": ["presencial", "videollamada", "cualquiera"],
                        "description": "Tipo de visita"
                    }
                },
                "required": []
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "book_slot",
            "description": "Reserva un slot concreto del calendario con los datos del usuario",
            "parameters": {
                "type": "object",
                "properties": {
                    "fecha": {"type": "string", "description": "YYYY-MM-DD"},
                    "hora": {"type": "string", "description": "HH:MM"},
                    "modalidad": {"type": "string", "enum": ["presencial", "videollamada"]},
                    "nombre": {"type": "string"},
                    "email": {"type": "string"},
                    "telefono": {"type": "string"},
                    "pais_origen": {"type": "string"},
                    "estudios": {"type": "string"},
                    "fecha_estancia": {"type": "string"}
                },
                "required": ["fecha", "hora", "modalidad", "nombre", "email", "telefono"]
            }
        }
    }
]

@cl.on_chat_start
async def start():
    cl.user_session.set("history", [
        {"role": "system", "content": SYSTEM_PROMPT}
    ])
    await cl.Message(
        content="¡Hola! 👋 Soy Alex, de UniLiving Madrid. Ayudo a estudiantes como tú a encontrar su sitio perfecto para este curso. ¿Cómo te llamas?"
    ).send()

@cl.on_message
async def main(message: cl.Message):
    history = cl.user_session.get("history")
    history.append({"role": "user", "content": message.content})
    
    # Loop para manejar tool calls
    max_iterations = 5
    for _ in range(max_iterations):
        response = await client.chat.completions.create(
            model="gemini-2.0-flash-lite",
            messages=history,
            tools=TOOLS,
            temperature=0.7
        )
        
        msg = response.choices[0].message
        
        # ¿El modelo quiere usar una tool?
        if msg.tool_calls:
            history.append({
                "role": "assistant",
                "content": msg.content or "",
                "tool_calls": [
                    {
                        "id": tc.id,
                        "type": "function",
                        "function": {
                            "name": tc.function.name,
                            "arguments": tc.function.arguments,
                        },
                    }
                    for tc in msg.tool_calls
                ],
            })

            for tool_call in msg.tool_calls:
                func_name = tool_call.function.name
                args = json.loads(tool_call.function.arguments)
                
                # Ejecutar la función correspondiente
                if func_name == "get_available_slots":
                    result = get_available_slots(**args)
                elif func_name == "book_slot":
                    result = book_slot(**args)
                else:
                    result = {"error": "función desconocida"}
                
                history.append({
                    "role": "tool",
                    "tool_call_id": tool_call.id,
                    "content": json.dumps(result, ensure_ascii=False)
                })
            
            # Volver a llamar al modelo con el resultado de la tool
            continue
        
        # Respuesta final al usuario
        reply = msg.content
        history.append({"role": "assistant", "content": reply})
        cl.user_session.set("history", history)
        await cl.Message(content=reply).send()
        break