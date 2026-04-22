# UniLiving Barcelona — AI Agent Demo

Agente de IA para residencias de estudiantes con dos canales: **chat web** (texto) y **voz** (Vapi). El agente cualifica leads, responde preguntas sobre la residencia y agenda visitas automáticamente.

---

## Qué hace el agente

- Saluda, pregunta el nombre y cualifica al estudiante (origen, estudios, fechas)
- Responde preguntas sobre habitaciones, precios y servicios
- Propone visita presencial o videollamada en el momento adecuado
- Muestra huecos reales del calendario y confirma la cita
- Guarda el lead en Google Sheets y envía email de confirmación automático
- Detecta y responde en español o inglés según el idioma del usuario

---

## Acceso a los datos

| Recurso | Enlace |
|---|---|
| **Leads captados (Google Sheets)** | [Ver hoja de leads](https://docs.google.com/spreadsheets/d/1nhMXHyYVvWp5TMFhDmqgA1U7whxvXWfHic_w6wyNmQw/edit?gid=0#gid=0) |
| **Panel ngrok (tráfico en tiempo real)** | http://127.0.0.1:4040 |
| **Documentación API de voz** | http://localhost:8001/docs |

---

## Requisitos previos

- Python 3.10 o superior
- Cuenta gratuita en [Groq](https://console.groq.com) — LLM del agente
- Cuenta gratuita en [ngrok](https://dashboard.ngrok.com/signup) — para exponer el servidor al exterior
- Cuenta en [Vapi](https://vapi.ai) — solo para el canal de voz

---

## Instalación

```bash
# 1. Clonar el repositorio
git clone <url-del-repo>
cd Demo_AI_Agent

# 2. Crear entorno virtual
python -m venv venv

# 3. Activar entorno virtual
venv\Scripts\activate        # Windows
# source venv/bin/activate   # Mac / Linux

# 4. Instalar dependencias
pip install -r requirements.txt
```

---

## Configuración del `.env`

Crea un archivo `.env` en la raíz del proyecto con estas variables:

```env
# OBLIGATORIO — LLM (obtener en https://console.groq.com/keys)
GROQ_API_KEY=gsk_xxxxxxxxxxxxxxxxxxxx

# Google Sheets — guardar leads
SPREADSHEET_ID=1nhMXHyYVvWp5TMFhDmqgA1U7whxvXWfHic_w6wyNmQw
GOOGLE_SHEETS_CREDENTIALS_FILE=credentials.json

# Email de confirmación automática
EMAIL_ENABLED=true
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=tu@gmail.com
SMTP_PASSWORD=xxxx xxxx xxxx xxxx   # App Password de Google (requiere 2FA)
EMAIL_FROM=tu@gmail.com
EMAIL_FROM_NAME=UniLiving Barcelona
```

### Dónde obtener cada clave

| Variable | Dónde obtenerla |
|---|---|
| `GROQ_API_KEY` | [console.groq.com/keys](https://console.groq.com/keys) |
| `SPREADSHEET_ID` | Es el ID de la URL de tu Google Sheet: `/d/ESTE_ID/edit` |
| `credentials.json` | [console.cloud.google.com](https://console.cloud.google.com/apis/credentials) → Cuenta de servicio → Descargar JSON |
| `SMTP_PASSWORD` | [myaccount.google.com/apppasswords](https://myaccount.google.com/apppasswords) (requiere 2FA activo) |

---

## Arrancar la demo — paso a paso

Necesitas **3 terminales** abiertas simultáneamente.

### Terminal 1 — Chat de texto

```bash
chainlit run app.py
```

Acceso local: **http://localhost:8000**

### Terminal 2 — Servidor de voz (API para Vapi)

```bash
uvicorn vapi_server:app --host 0.0.0.0 --port 8001 --reload
```

### Terminal 3 — ngrok (expone ambos servidores al exterior)

Primero configura tu authtoken (solo la primera vez):
```bash
ngrok-temp\ngrok.exe config add-authtoken TU_AUTHTOKEN
```
Obtén tu authtoken en: [dashboard.ngrok.com/get-started/your-authtoken](https://dashboard.ngrok.com/get-started/your-authtoken)

Luego lanza los túneles. **Opción A — un túnel a la vez** (plan gratuito):

```bash
# Para compartir el chat de texto con el cliente:
ngrok-temp\ngrok.exe http 8000

# Para conectar Vapi al servidor de voz:
ngrok-temp\ngrok.exe http 8001
```

Copia la URL pública que aparece (ejemplo: `https://abc123.ngrok-free.app`) y envíasela al cliente.

---

## Configurar el asistente de voz en Vapi

1. Entra en [vapi.ai](https://vapi.ai) → **Assistants → Create Assistant**
2. Pega el contenido de `vapi_prompt.txt` como **System Prompt**
3. En **Tools**, añade dos funciones con la URL de ngrok del puerto 8001:

| Tool name | Método | URL |
|---|---|---|
| `get_available_slots` | POST | `https://TU-URL-NGROK/tools/get-available-slots` |
| `book_visit` | POST | `https://TU-URL-NGROK/tools/book-visit` |

4. Selecciona una voz (recomendado: **ElevenLabs** para baja latencia)
5. Activa el **widget web** para probarlo en el navegador

---

## Compartir la demo con el cliente

1. Arranca las 3 terminales según los pasos de arriba
2. Lanza ngrok sobre el puerto 8000 y copia la URL pública
3. Envía esa URL al cliente — puede abrir el chat desde cualquier dispositivo sin instalar nada
4. Los leads quedan registrados automáticamente en [Google Sheets](https://docs.google.com/spreadsheets/d/1nhMXHyYVvWp5TMFhDmqgA1U7whxvXWfHic_w6wyNmQw/edit?gid=0#gid=0)

---

## Verificar que todo funciona

```bash
# Probar Google Sheets
python test_sheets.py

# Probar envío de email
python test_email.py

# Probar endpoints de voz
python test_vapi_webhook.py
python test_voice_api.py
```

---

## Estructura del proyecto

```
Demo_AI_Agent/
├── app.py               # Chat web — Chainlit
├── vapi_server.py       # API de voz — FastAPI + endpoints Vapi
├── booking_service.py   # Orquestación: reserva + Sheets + email
├── calendar_utils.py    # Gestión de slots de visita (calendar.json)
├── email_utils.py       # Envío de confirmaciones por SMTP
├── sheets_utils.py      # Guardado de leads en Google Sheets
├── prompt.txt           # Prompt del agente de texto
├── vapi_prompt.txt      # Prompt del agente de voz
├── calendar.json        # Calendario de slots (se genera automáticamente)
├── credentials.json     # Credenciales Google (no subir a git)
├── requirements.txt     # Dependencias Python
└── .env                 # Variables de entorno (no subir a git)
```

---

## Flujo conversacional

```
1. Saludo → pregunta nombre
2. Cualificación → origen, estudios, fechas de estancia
3. Responde dudas → precios, habitaciones, servicios, ubicación
4. Detecta interés → propone visita presencial o videollamada
5. Muestra slots → 3 huecos reales del calendario
6. Recoge contacto → nombre completo, email, teléfono
7. Confirma cita → bloquea slot, envía email, guarda lead en Sheets
```
