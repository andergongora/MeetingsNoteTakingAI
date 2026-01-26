# Audio Recorder - Guía Técnica Completa

## 📋 Tabla de Contenidos

1. [Resumen General](#resumen-general)
2. [Arquitectura del Sistema](#arquitectura-del-sistema)
3. [Componentes Principales](#componentes-principales)
4. [Flujo de Grabación](#flujo-de-grabación)
5. [Detalles Técnicos](#detalles-técnicos)

---

## Resumen General

El `AudioRecorder` es un sistema de grabación de audio que captura simultáneamente:
- 🎤 **Micrófono**: Tu voz
- 🔊 **Audio del sistema** (loopback): Audio del ordenador

**Características clave:**
- ✅ Funciona solo con micrófono si no hay audio del PC
- ✅ Mezcla ambas fuentes cuando ambas están disponibles
- ✅ Ctrl+C responde inmediatamente (gracias al threading)
- ✅ Duración precisa (tiempo real = audio grabado)
- ✅ Display en tiempo real del progreso

---

## Arquitectura del Sistema

```
┌─────────────────────────────────────────────────────────────┐
│                    MAIN THREAD                              │
│  - Inicia grabación                                        │
│  - Muestra progreso en tiempo real                         │
│  - Escucha Ctrl+C                                          │
└──────────────┬──────────────────────────────────────────────┘
               │
               │ crea y monitorea
               ▼
┌─────────────────────────────────────────────────────────────┐
│                   WORKER THREAD                             │
│  - Lee audio del micrófono (bloqueante)                    │
│  - Lee audio del loopback (condicional)                    │
│  - Mezcla ambos streams                                    │
│  - Escribe al archivo WAV                                  │
│  - Actualiza contador de samples                           │
└─────────────────────────────────────────────────────────────┘
```

**¿Por qué threading?**
- El **main thread** puede responder a Ctrl+C inmediatamente
- El **worker thread** puede bloquearse en las lecturas de audio sin problemas
- Comunicación thread-safe mediante `_lock` para el contador

---

## Componentes Principales

### 1. **Inicialización (`__init__`)**

```python
self._samples_written = 0    # Contador thread-safe
self._lock = threading.Lock()  # Sincronización
self._stop_event = threading.Event()  # Señal de parada
```

- `_samples_written`: Contador compartido entre threads
- `_lock`: Protege el acceso al contador (evita race conditions)
- `_stop_event`: Señal para detener el worker thread limpiamente

### 2. **Detección de Dispositivos (`find_devices`)**

**Estrategia de búsqueda:**

#### Loopback (audio del sistema):
1. Busca dispositivo WASAPI de salida predeterminado
2. Busca loopback asociado a ese dispositivo
3. Fallback: Cualquier dispositivo con `[loopback]` en el nombre

#### Micrófono:
1. Prioridad: Micrófono USB
2. Fallback: Primer dispositivo de entrada disponible
3. Ignora dispositivos loopback

**Robustez:**
- Múltiples fallbacks para encontrar dispositivos
- Manejo de excepciones en cada paso
- Mensajes claros de qué se encontró

### 3. **Mezcla de Audio (`_mix_and_clip`)**

**Entrada:** Dos buffers de bytes (mic y loopback)

**Proceso:**

```python
# 1. Convertir a arrays numpy (int16)
mic_array = np.frombuffer(mic_bytes, dtype=np.int16)
loop_array = np.frombuffer(loop_bytes, dtype=np.int16)

# 2. Encontrar longitud mínima
min_len = min(len(mic_array), len(loop_array))

# 3. Mezclar con int32 (evita overflow)
mic32 = mic_array[:min_len].astype(np.int32)
loop32 = loop_array[:min_len].astype(np.int32)
mixed32 = mic32 + loop32

# 4. Clip a rango int16 y convertir
mixed32 = np.clip(mixed32, -32768, 32767)
mixed16 = mixed32.astype(np.int16)
```

**Casos especiales:**
- Si uno está vacío → Retorna el otro
- Si ambos vacíos → Retorna buffer de silencio
- Si tienen diferentes longitudes → Usa la mínima

**¿Por qué int32?**
- `int16 + int16` puede causar overflow
- `int32` tiene rango suficiente para la suma
- Luego se hace clip de vuelta a int16

### 4. **Worker Thread (`_record_worker`)**

**Responsabilidades:**
1. Leer audio continuamente
2. Mezclar streams
3. Escribir al archivo WAV
4. Actualizar contador de progreso

**Estrategia de lectura:**

```python
# Micrófono: SIEMPRE bloqueante
mic_data = mic_stream.read(CHUNK, exception_on_overflow=False)

# Loopback: CONDICIONAL
loop_available = loop_stream.get_read_available()

if loop_available >= CHUNK:
    # Hay audio del PC → leer
    loop_data = loop_stream.read(CHUNK, exception_on_overflow=False)
else:
    # No hay audio del PC → usar silencio
    loop_data = silence_bytes
```

**¿Por qué esta estrategia?**
- **Micrófono bloqueante**: Marca el ritmo real de grabación
- **Loopback condicional**: No bloquea si no hay audio del PC
- **Resultado**: Funciona en ambos escenarios (con/sin audio PC)

**Actualización del contador:**

```python
# Actualizar cada 0.5 segundos
if now - last_update >= 0.5:
    with self._lock:
        self._samples_written = local_samples
```

- Reduce contención del lock
- Actualización visible frecuente (cada 0.5s)

### 5. **Grabación Principal (`record`)**

**Flujo completo:**

```
1. Crear output path
2. Abrir streams de audio
   ├─ Micrófono (CHUNK=256)
   └─ Loopback (CHUNK=256)
3. Crear archivo WAV
4. Mostrar mensaje de inicio
5. Iniciar worker thread
6. Loop de monitoreo:
   ├─ Leer contador (thread-safe)
   ├─ Calcular duración
   ├─ Mostrar progreso cada segundo
   └─ Capturar Ctrl+C
7. Al detener:
   ├─ Señalar stop al worker
   ├─ Esperar a que termine
   ├─ Cerrar streams y archivo
   └─ Mostrar estadísticas finales
```

**Display en tiempo real:**

```python
# Cada segundo muestra:
⏱️  Tiempo real: 00:15 | Audio grabado: 00:14
```

- `Tiempo real`: Tiempo transcurrido desde inicio
- `Audio grabado`: Duración real del audio capturado

**Estadísticas finales:**

```
⏰ Tiempo real total: 00:21 (21.45s)
⏱️  Audio grabado:    00:21 (21.12s)
📊 Samples: 1,863,168 | Rate: 44100Hz | Channels: 2
✓ Diferencia: 0.33s (excelente sincronización)
📁 Guardado en: reunion_20260126.wav
💾 Tamaño: 7.32 MB
```

---

## Flujo de Grabación

### Escenario A: Solo Micrófono (Sin audio del PC)

```
[Micrófono] ──► read(CHUNK) [BLOQUEA hasta tener datos]
                     │
                     ▼
              [mic_data: 1024 bytes]

[Loopback]  ──► get_read_available() → 0 frames
                     │
                     ▼
              [loop_data: silence_bytes]

         ┌─────────────────┐
         │  _mix_and_clip  │
         └─────────────────┘
                  │
                  ▼
         [mixed: solo audio del mic]
                  │
                  ▼
           wf.writeframes()
```

**Resultado:** Graba solo tu voz a velocidad normal

### Escenario B: Micrófono + Audio del PC

```
[Micrófono] ──► read(CHUNK) [BLOQUEA hasta tener datos]
                     │
                     ▼
              [mic_data: 1024 bytes]

[Loopback]  ──► get_read_available() → 512 frames
                     │
                     ▼
              read(CHUNK)
                     │
                     ▼
              [loop_data: 1024 bytes]

         ┌─────────────────┐
         │  _mix_and_clip  │
         │  mic + loop     │
         │  clip overflow  │
         └─────────────────┘
                  │
                  ▼
         [mixed: ambos mezclados]
                  │
                  ▼
           wf.writeframes()
```

**Resultado:** Graba ambas fuentes mezcladas

---

## Detalles Técnicos

### Configuración de Audio

```python
CHUNK = 256              # Frames por lectura
SAMPLE_RATE = 44100      # Hz (calidad CD)
CHANNELS = 2             # Stereo
FORMAT = paInt16         # 16-bit signed integer
```

**¿Por qué CHUNK=256?**
- **Pequeño**: Baja latencia, Ctrl+C responsive
- **No muy pequeño**: Evita overhead excesivo
- **256 frames** ≈ 5.8ms @ 44100Hz

### Cálculo de Duración

```python
# Samples escritos (int16 values)
samples = 1,863,168

# Conversión a segundos
duration = samples / (SAMPLE_RATE * CHANNELS)
         = 1,863,168 / (44100 * 2)
         = 21.12 segundos
```

**Importante:**
- `samples` = número de valores int16 individuales
- Para stereo: 2 samples = 1 frame
- Duración precisa al sample

### Thread Safety

**Problema:** Dos threads acceden al mismo contador

```python
# Worker thread escribe:
local_samples += n_samples
with self._lock:
    self._samples_written = local_samples

# Main thread lee:
with self._lock:
    current = self._samples_written
```

**Solución:** `threading.Lock()`
- Garantiza que solo un thread accede a la vez
- Previene race conditions
- Actualizaciones cada 0.5s minimizan contención

### Manejo de Errores

**IOError (Buffer overflow/underflow):**
```python
except IOError:
    continue  # Skip chunk and continue
```
- Común cuando el CPU está ocupado
- No es crítico, solo omite ese chunk

**Otras excepciones:**
```python
except Exception as e:
    print(f"❌ Error: {e}")
    break  # Stop recording
```
- Errores inesperados detienen la grabación
- El cleanup siempre se ejecuta (finally block)

### Sincronización con Ctrl+C

**Problema:** Lecturas bloqueantes no responden a Ctrl+C

**Solución 1: Threading**
```python
# Main thread SOLO monitorea
while worker.is_alive():
    time.sleep(0.1)  # Pequeño sleep
    # Ctrl+C interrumpe aquí (KeyboardInterrupt)
```

**Solución 2: Stop streams**
```python
except KeyboardInterrupt:
    self._stop_event.set()  # Señal al worker
    mic_stream.stop_stream()  # Desbloquea read()
    loop_stream.stop_stream()
```

---

## Mejores Prácticas Aplicadas

1. **Separation of Concerns**
   - Worker: Solo lectura y escritura
   - Main: Solo monitoreo y UI

2. **Thread Safety**
   - Lock para datos compartidos
   - Event para señalización limpia

3. **Robustez**
   - Múltiples fallbacks en detección
   - Manejo de excepciones en cada punto crítico
   - Cleanup garantizado (finally blocks)

4. **User Experience**
   - Display en tiempo real
   - Feedback claro (emoji + números)
   - Estadísticas detalladas al finalizar

5. **Eficiencia**
   - Buffer pequeño (baja latencia)
   - Actualizaciones periódicas (no constantes)
   - Mezcla optimizada con numpy

---

## Troubleshooting Común

### "No se encontraron dispositivos"
- **Causa**: WASAPI no disponible o permisos
- **Solución**: Verificar permisos de micrófono en Windows

### "Duración no coincide con tiempo real"
- **Causa**: Problemas con el loopback o CPU
- **Solución**: Verificar que hay audio reproduciéndose

### "Ctrl+C no responde"
- **Causa**: El worker thread está bloqueado
- **Solución**: Ya implementado con `stop_stream()`

### "Audio con carraspeo/glitches"
- **Causa**: Mezcla incorrecta o silence padding
- **Solución**: Ya solucionado con estrategia condicional

---

## Conclusión

El `AudioRecorder` es un sistema robusto que:

✅ **Funciona en múltiples escenarios** (mic solo, mic+PC)
✅ **Responde inmediatamente** a interrupciones del usuario
✅ **Sincroniza perfectamente** tiempo real con audio
✅ **Maneja errores gracefully** sin crashes
✅ **Proporciona feedback claro** al usuario

**Arquitectura clave:** Threading + Estado compartido thread-safe + Estrategia de lectura híbrida (bloqueante mic + condicional loopback)
