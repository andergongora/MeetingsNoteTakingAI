# Meeting AI System

Sistema completo de IA para reuniones que graba, transcribe y analiza automáticamente usando Whisper local y Gemini.

## ✨ Características

🎙️ **Grabación** - Captura micrófono + audio del sistema simultáneamente
📝 **Transcripción** - Convierte audio a texto con **Whisper local** (sin API, gratis)
🤖 **Análisis IA** - Extrae notas, tareas y resumen con Gemini
📁 **Organización** - Guarda todo estructuradamente
🔒 **Privacidad** - Transcripción 100% local, sin enviar audio a internet

## 🚀 Inicio Rápido

### Opción 1: Scripts de Windows (MÁS FÁCIL) ⭐

**Primera vez:**
1. **Doble clic en `SETUP.bat`** - Configura todo (FFmpeg, .env, dependencias)
2. **Doble clic en `RUN.bat`** - Ejecuta la aplicación

**Después:**
- Solo ejecuta `RUN.bat` cada vez que quieras grabar una reunión

> **Nota**: Los scripts solo funcionan en **Windows nativo**. WSL y Docker NO soportan grabación de audio (limitación de PyAudioWPatch/WASAPI).

### Opción 2: Instalación Manual

#### 1. Instalar Dependencias

```bash
pip install PyAudioWPatch numpy openai-whisper torch google-generativeai python-dotenv
```

> **Nota GPU**: Si tienes GPU NVIDIA, Whisper usará CUDA automáticamente para transcribir más rápido.

### 2. Instalar FFmpeg (Requerido)

Whisper necesita ffmpeg para procesar audio:

```bash
# Windows (con winget)
winget install ffmpeg

# O descarga desde: https://ffmpeg.org/download.html
```

### 3. Configurar API Key de Gemini

```bash
# Copiar template
copy .env.template .env

# Editar .env y agregar tu API key de Gemini
```

Solo necesitas:
- ✅ **Gemini API Key** (gratis) - https://makersuite.google.com/app/apikey
- ❌ ~~OpenAI API Key~~ (ya no necesaria - Whisper local)

**Ejemplo `.env`:**
```env
GEMINI_API_KEY=AIza...tu_key_aqui
WHISPER_MODEL=base
```

### 4. Ejecutar

```bash
python main.py
```

El sistema:
1. 🎤 Graba la reunión (Ctrl+C para detener)
2. 📝 Transcribe localmente con Whisper
3. 🤖 Analiza con Gemini cloud
4. 💾 Guarda todo en `outputs/`

## 📁 Estructura del Proyecto

```
MeetingsNoteTakingAI/
├── src/
│   ├── recorder.py       # Grabación de audio
│   ├── transcriber.py    # Transcripción con Whisper LOCAL
│   ├── analyzer.py       # Análisis con Gemini
│   └── config.py         # Configuración
├── prompts/
│   └── meeting_analysis.txt  # Prompt para Gemini
├── outputs/
│   ├── recordings/       # Archivos WAV
│   ├── transcripts/      # Transcripciones TXT
│   └── summaries/        # Análisis (JSON + MD)
├── SETUP.bat             # ⭐ Configuración inicial (primera vez)
├── RUN.bat               # ⭐ Ejecutar aplicación
├── main.py               # Aplicación principal
├── requirements.txt      # Dependencias pip
└── .env                  # Solo Gemini API key
```

## ⚠️ Importante: WSL y Docker

**La grabación de audio NO funciona en WSL ni Docker** porque el proyecto usa `PyAudioWPatch`, que requiere acceso directo a WASAPI (Windows Audio Session API).

- ✅ **Windows nativo** - Funciona completamente
- ❌ **WSL** - NO graba audio (limitación técnica de acceso a hardware)
- ❌ **Docker** - NO graba audio (contenedores no tienen acceso a dispositivos de audio)

**Solución**: Ejecuta desde Windows nativo usando los scripts `.bat` o PowerShell.

## ⚙️ Modelos de Whisper

Puedes configurar el tamaño del modelo en `.env`:

| Modelo | Tamaño | RAM | Velocidad | Precisión | Recomendado para |
|--------|--------|-----|-----------|-----------|------------------|
| `tiny` | ~75MB | ~1GB | Muy rápida | Básica | Pruebas rápidas |
| `base` | ~145MB | ~1GB | Rápida | Buena | **Uso general** ⭐ |
| `small` | ~483MB | ~2GB | Media | Muy buena | Calidad > velocidad |
| `medium` | ~1.5GB | ~5GB | Lenta | Excelente | GPU recomendada |
| `large` | ~3GB | ~10GB | Muy lenta | Máxima | Solo con GPU potente |

**Configuración en `.env`:**
```env
WHISPER_MODEL=base  # Recomendado
```

La primera vez que uses un modelo, se descargará automáticamente.

## 📊 Salida del Análisis

Cada reunión genera:

### 📝 Transcripción (`outputs/transcripts/`)
Texto completo de la reunión

### 📋 Resumen Markdown (`outputs/summaries/*.md`)
```markdown
# Resumen de Reunión

## 📋 Resumen Ejecutivo
Resumen conciso de la reunión...

## 📝 Notas Clave
- Punto importante 1
- Punto importante 2

## ✅ Tareas para Ander
- [ ] Tarea 1
- [ ] Tarea 2
```

### 🗂️ JSON Estructurado (`outputs/summaries/*.json`)
```json
{
  "notas": [...],
  "tareas_para_ander": [...],
  "resumen": "..."
}
```

## 🚀 Rendimiento

### Transcripción (Whisper local)

| Hardware | Modelo | Tiempo (por 1h audio) |
|----------|--------|-----------------------|
| CPU i7 | base | ~15 min |
| CPU i7 | small | ~30 min |
| GPU RTX 3060 | base | ~3 min ⚡ |
| GPU RTX 3060 | medium | ~7 min ⚡ |

> El modelo `base` es el mejor balance velocidad/calidad para CPU.

## � Costos

| Componente | Costo |
|------------|-------|
| **Grabación** | Gratis |
| **Transcripción (Whisper)** | **GRATIS** ✅ (local) |
| **Análisis (Gemini)** | Gratis (plan free) |

**Total: 100% GRATIS** 🎉

## 🔧 Solución de Problemas

### Error: "ffmpeg not found"

Instala ffmpeg:
```bash
winget install ffmpeg
```

O descarga de https://ffmpeg.org/download.html y agrega al PATH.

### Whisper muy lento

1. **Usar modelo más pequeño**:
   ```env
   WHISPER_MODEL=tiny
   ```

2. **Habilitar GPU** (si tienes NVIDIA):
   - Instala CUDA: https://developer.nvidia.com/cuda-downloads
   - Whisper detectará y usará GPU automáticamente

### Error de memoria (OOM)

Usar modelo más pequeño:
```env
WHISPER_MODEL=tiny  # o base
```

### Error de API Key

Solo necesitas Gemini:
```env
GEMINI_API_KEY=AIza...
```

## 🔒 Privacidad

| Componente | ¿Datos enviados a internet? |
|------------|------------------------------|
| Grabación | ❌ No - 100% local |
| Transcripción | ❌ No - 100% local (Whisper) |
| Análisis | ✅ Sí - Texto enviado a Gemini |

**El audio NUNCA sale de tu computadora** - solo se envía el texto transcrito a Gemini para análisis.

## ⚙️ Configuración Avanzada

### Editar Prompt de Gemini

Modifica `prompts/meeting_analysis.txt` para cambiar cómo Gemini analiza las reuniones.

### Forzar uso de CPU

Si Whisper no detecta tu GPU correctamente, puedes forzar CPU editando `src/transcriber.py`:
```python
device = "cpu"  # Forzar CPU
```

## 🛠️ Scripts de Utilidad

```bash
python disp.py              # Ver dispositivos de audio
python find_loopback.py     # Diagnosticar loopback
python check_rates.py       # Verificar sample rates
```

## 📝 Ejemplo de Uso Completo

```bash
$ python main.py

======================================================================
 MEETING AI SYSTEM
 Grabación → Transcripción → Análisis con IA
======================================================================

PASO 1/3: GRABACIÓN
----------------------------------------------------------------------

🔍 Buscando dispositivos de audio...
✓ Audio del Sistema: Speakers (Focusrite) [Loopback]
✓ Micrófono: Microphone (USB)

======================================================================
✓ GRABACIÓN INICIADA
======================================================================
⏱️  05:30
```

*(Presionar Ctrl+C)*

```
¿Continuar con transcripción y análisis? (s/n): s

PASO 2/3: TRANSCRIPCIÓN
----------------------------------------------------------------------

📥 Cargando modelo Whisper 'base'...
   ✓ GPU detectada - usando aceleración CUDA
   ✓ Modelo cargado correctamente

📝 TRANSCRIBIENDO AUDIO
⏳ Transcribiendo...
✓ Transcripción completada (2543 caracteres)

PASO 3/3: ANÁLISIS CON IA
----------------------------------------------------------------------

🤖 ANALIZANDO CON GEMINI
✓ Análisis completado

✅ PROCESO COMPLETADO
```

## 🎯 Ventajas vs API de OpenAI

| Aspecto | Whisper Local | Whisper API |
|---------|---------------|-------------|
| **Costo** | Gratis ✅ | ~$0.36/hora |
| **Privacidad** | 100% local ✅ | Audio enviado a internet |
| **Internet** | Solo para Gemini | Requerido siempre |
| **Velocidad** | Depende de HW | Rápida consistente |
| **Setup** | Requiere ffmpeg | Solo API key |

---

**¿Problemas?** Abre un issue o revisa la documentación completa en los artifacts.
