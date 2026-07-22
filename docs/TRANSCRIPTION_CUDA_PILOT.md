# Transcription CUDA Pilot

Fecha: 2026-07-22

## Resumen Ejecutivo

Se instalo un conjunto minimo y oficial de bibliotecas NVIDIA dentro de `.venv` y se valido `faster-whisper` con CUDA en dos procesos limpios.

Resultado:

- `faster-whisper` instalo correctamente.
- CTranslate2 detecta una GPU CUDA y soporta `int8_float16`.
- `WhisperModel("small", device="cuda", compute_type="int8_float16")` cargo correctamente.
- La transcripcion CUDA completo con exito.
- La prueba se repitio en un segundo proceso limpio y volvio a funcionar.
- La ruta CPU `small` + `int8` tambien funciono como fallback y comparacion.

Decision:

- `GO` para la ruta CUDA con runtimes oficiales NVIDIA dentro de `.venv`.
- `GO` para fallback CPU.

## Entorno

| Dato | Valor |
| --- | --- |
| Sistema operativo | Windows 10 Pro 22H2 build 19045 |
| Python | 3.11.9 64-bit |
| Intérprete | `H:\ALEJANDRO_2\CreatorIntelligenceStudio\.venv\Scripts\python.exe` |
| pip | 25.1.1 |
| GPU | NVIDIA GeForce RTX 2080 |
| VRAM total | 8192 MiB |
| Driver NVIDIA | 576.52 |
| CUDA reportada por driver | 12.9 |
| CUDA Toolkit global | No detectado |
| `nvcc` | No disponible |
| cuDNN global | No detectado |
| PyTorch | No instalado |

### Auditoria previa

- Suite existente antes de instalar: `53` pruebas, `52` aprobadas, `1` omitida.
- VRAM libre en el arranque del piloto CUDA: entre `1.90 GB` y `2.24 GB`, segun el momento de la medicion.
- RAM disponible al inicio: aproximadamente `6.2 GB` a `6.9 GB`.
- Disco libre en `H:\`: aproximadamente `1.23 TB`.

Aviso:

- La VRAM libre fue inferior a 4 GB durante el piloto, asi que la ejecucion era posible pero ajustada.

## Respaldo Reversible

Se guardaron fuera del commit:

- `C:\Users\CHarro\AppData\Local\Temp\creator_intelligence_studio_pip_freeze_before_faster_whisper.txt`
- `C:\Users\CHarro\AppData\Local\Temp\creator_intelligence_studio_pip_list_before_faster_whisper.txt`
- ruta del interprete: `H:\ALEJANDRO_2\CreatorIntelligenceStudio\.venv\Scripts\python.exe`
- ruta de site-packages: `H:\ALEJANDRO_2\CreatorIntelligenceStudio\.venv\Lib\site-packages`

## Instalacion Oficial

Instalado dentro de `.venv`:

- `nvidia-cublas-cu12==12.9.2.10`
- `nvidia-cuda-runtime-cu12==12.9.79`
- `nvidia-cuda-nvrtc-cu12==12.9.86`
- `nvidia-cudnn-cu12==9.25.0.15`

Tambien presentes por el piloto previo:

- `faster-whisper==1.2.1`
- `ctranslate2==4.8.1`
- `av==18.0.0`
- `tokenizers==0.23.1`
- `huggingface-hub==1.24.0`
- `onnxruntime==1.27.0`
- `numpy==2.4.6`
- `pyyaml==6.0.3`
- `protobuf==7.35.1`
- `tqdm==4.69.0`

No se instalo:

- PyTorch
- Transformers
- openai-whisper
- CUDA Toolkit global
- nvcc
- diarizacion

## DLL Reales

Rutas reales dentro de `.venv`:

- `H:\ALEJANDRO_2\CreatorIntelligenceStudio\.venv\Lib\site-packages\nvidia\cuda_runtime\bin`
  - `cudart64_12.dll`
- `H:\ALEJANDRO_2\CreatorIntelligenceStudio\.venv\Lib\site-packages\nvidia\cublas\bin`
  - `cublas64_12.dll`
  - `cublasLt64_12.dll`
  - `nvblas64_12.dll`
- `H:\ALEJANDRO_2\CreatorIntelligenceStudio\.venv\Lib\site-packages\nvidia\cuda_nvrtc\bin`
  - `nvrtc64_120_0.dll`
  - `nvrtc64_120_0.alt.dll`
  - `nvrtc-builtins64_129.dll`
- `H:\ALEJANDRO_2\CreatorIntelligenceStudio\.venv\Lib\site-packages\nvidia\cudnn\bin`
  - `cudnn64_9.dll`
  - `cudnn_adv64_9.dll`
  - `cudnn_cnn64_9.dll`
  - `cudnn_engines_precompiled64_9.dll`
  - `cudnn_engines_runtime_compiled64_9.dll`
  - `cudnn_engines_tensor_ir64_9.dll`
  - `cudnn_ext64_9.dll`
  - `cudnn_graph64_9.dll`
  - `cudnn_heuristic64_9.dll`
  - `cudnn_ops64_9.dll`

## Estrategia DLL del Proceso

En los procesos del piloto se hizo lo siguiente, sin alterar el PATH global:

1. Registrar las carpetas reales con `os.add_dll_directory(...)`.
2. Prependear las mismas rutas a `PATH` solo para el proceso actual.
3. Mantener vivos los handles devueltos por `os.add_dll_directory` durante toda la ejecucion.
4. Ejecutar el modelo en un proceso nuevo para validar que no dependiera de DLL cargadas accidentalmente por una corrida previa.

## Modelo y Caché

### Ruta de caché controlada

- `H:\ALEJANDRO_2\CreatorIntelligenceStudio\temp\transcription_pilot\model_cache`

### Modelo descargado

- `small` de `Systran/faster-whisper-small`

### Tamaño observado

- `486,213,474` bytes
- aproximadamente `463.6 MiB`

### Observaciones de descarga

- HF Hub aviso sobre symlinks no soportados en esta ruta.
- La caché siguio funcionando correctamente.
- Se uso descarga anónima, sin token.

## Prueba CUDA

### Configuracion

- Modelo: `small`
- Device: `cuda`
- Compute type: `int8_float16`
- `beam_size = 5`
- `language = es`
- `word_timestamps = false`
- `vad_filter = false`

### Verificacion del backend

- `ctranslate2.__version__ = 4.8.1`
- `get_cuda_device_count() = 1`
- `get_supported_compute_types("cuda")` incluyo `int8_float16`

### Resultado del primer proceso limpio

- Carga del modelo: `5.97 s`
- Transcripcion: `6.25 s`
- Real-time factor: `0.19`
- Idioma detectado: `es`
- Probabilidad de idioma: `1.0`
- Segmentos: `5`

### Resultado del segundo proceso limpio

- Carga del modelo: `7.96 s`
- Transcripcion: `2.01 s`
- Real-time factor: `0.06`
- Idioma detectado: `es`
- Probabilidad de idioma: `1.0`
- Segmentos: `5`

### Texto completo obtenido

```text
Hola. Esta es una prueba local de transcripción para Creador Inteligencia Estudio. Queremos verificar que el modelo detecte español, genere segmentos con tiempos, y mantenga el texto completo. La voz debe sonar natural, con pausas cortas, números simples, y algunas palabras de prueba como CUDA, RTX, audio, video y cache. Si esta grabación sirve, continuaremos con la integración modular en la siguiente fase. Gracias por revisar esta prueba piloto.
```

### Segmentos observados

| Inicio | Fin | Texto |
| --- | --- | --- |
| 0.0 | 6.2 | Hola. Esta es una prueba local de transcripción para Creador Inteligencia Estudio. |
| 6.2 | 13.7 | Queremos verificar que el modelo detecte español, genere segmentos con tiempos, y mantenga el texto completo. |
| 13.7 | 24.4 | La voz debe sonar natural, con pausas cortas, números simples, y algunas palabras de prueba como CUDA, RTX, audio, video y cache. |
| 24.4 | 30.1 | Si esta grabación sirve, continuaremos con la integración modular en la siguiente fase. |
| 30.1 | 33.1 | Gracias por revisar esta prueba piloto. |

### Uso de GPU observado

En `nvidia-smi` el proceso Python aparecio durante la ejecucion, y se observaron variaciones de uso de GPU y memoria compatibles con inferencia real.

### Memoria

Primer proceso CUDA:

- VRAM usada antes: `6122 MiB`
- VRAM usada pico: `6273 MiB`
- VRAM usada despues: `6176 MiB`
- RAM disponible antes: `6965374976`
- RAM disponible despues: `5376512000`

Segundo proceso CUDA:

- VRAM usada antes: `5947 MiB`
- VRAM usada pico: `6469 MiB`
- VRAM usada despues: `6373 MiB`
- RAM disponible antes: `6673465344`
- RAM disponible despues: `5092376576`

## Prueba CPU

### Configuracion

- Modelo: `small`
- Device: `cpu`
- Compute type: `int8`
- `beam_size = 5`
- `language = es`
- `word_timestamps = false`
- `vad_filter = false`

### Resultado

- Carga del modelo: `1.83 s`
- Transcripcion: `7.29 s`
- Real-time factor: `0.22`
- Idioma detectado: `es`
- Probabilidad de idioma: `1.0`
- Segmentos: `5`

### Comparacion resumida

| Aspecto | CUDA 1 | CUDA 2 | CPU |
| --- | --- | --- | --- |
| Carga | `5.97 s` | `7.96 s` | `1.83 s` |
| Transcripcion | `6.25 s` | `2.01 s` | `7.29 s` |
| RTF | `0.19` | `0.06` | `0.22` |
| Idioma | `es` | `es` | `es` |
| Segmentos | `5` | `5` | `5` |
| Texto | Coherente | Coherente | Coherente |

## Calidad Observada

Evaluacion cualitativa:

- Omisiones: no se observaron omisiones graves.
- Inventadas: no se observaron inventos relevantes.
- Puntuacion: aceptable.
- Nombres propios o marcas: `Creator Intelligence Studio` se transcribio como `Creador Inteligencia Estudio`.
- Timestamps: consistentes.

## Bibliotecas CUDA Requeridas

Validadas:

- `cublas64_12.dll`
- `cudart64_12.dll`
- `cudnn64_9.dll`
- `nvrtc64_120_0.dll`

## Errores

No hubo error de DLL durante la transcripcion final.

La unica incidencia previa fue el fallo inicial por `cublas64_12.dll` ausente, resuelto al instalar las bibliotecas oficiales NVIDIA dentro de `.venv` y registrar sus rutas con `os.add_dll_directory`.

## Decision Go / No-Go

### Go

- `faster-whisper` importa correctamente.
- `int8_float16` fue aceptado.
- La transcripcion CUDA termino con exito.
- El proceso nuevo y limpio tambien funciono.
- La GPU se observo activa en `nvidia-smi`.

### Go para fallback CPU

- CPU `int8` funciono como respaldo.

## Rollback

Para retirar solo los paquetes NVIDIA oficiales, sin tocar `faster-whisper`, PySide6 ni otras dependencias:

```bat
.venv\Scripts\python.exe -m pip uninstall nvidia-cudnn-cu12 nvidia-cuda-runtime-cu12 nvidia-cublas-cu12 nvidia-cuda-nvrtc-cu12
```

Para limpiar la caché del piloto:

```bat
Remove-Item -Recurse -Force H:\ALEJANDRO_2\CreatorIntelligenceStudio\temp\transcription_pilot
```

## Recomendacion para Integracion

1. Encapsular la deteccion y registro de DLL en infraestructura formal.
2. Mantener `os.add_dll_directory` solo en el arranque del backend.
3. Preservar `small` + `int8_float16` como perfil inicial CUDA.
4. Mantener `small` + `int8` como fallback CPU.
5. Integrar solo despues la capa de dominio, CLI, SQLite y GUI.

## Comandos Ejecutados y Resultados Resumidos

### Auditoria previa

- `git status --short` -> habia dos documentos de plan/piloto sin commitear.
- `python -m pip freeze` -> sin paquetes NVIDIA al inicio.
- `nvidia-smi` -> RTX 2080, driver `576.52`, CUDA `12.9`, VRAM total `8192 MiB`.
- `python -m unittest discover -s tests -p "test_*.py"` -> `53` pruebas, `52` aprobadas, `1` omitida.

### Instalacion

- `python -m pip install nvidia-cublas-cu12 nvidia-cuda-runtime-cu12 nvidia-cudnn-cu12` -> exitosa dentro de `.venv`.
- Dependencia transitiva adicional instalada: `nvidia-cuda-nvrtc-cu12==12.9.86`.

### Verificacion CUDA

- `WhisperModel("small", device="cuda", compute_type="int8_float16")` -> carga exitosa.
- `WhisperModel.transcribe(...)` -> exitosa en dos procesos limpios.

### Verificacion CPU

- `WhisperModel("small", device="cpu", compute_type="int8")` -> exitosa.

## Nota de Cierre

El piloto CUDA fue la validacion tecnica previa.
La integracion formal ya usa la ruta permanente de modelos en `models/transcription/faster-whisper/` y exportaciones controladas en `cache/transcriptions/`.
