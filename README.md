# Creator Intelligence Studio

Creator Intelligence Studio es una aplicacion de escritorio para Windows orientada al analisis inteligente de contenido audiovisual para creadores.

## Estado actual

El proyecto ya dispone de:

- base ejecutable con Python 3.11;
- catalogo de creadores, proyectos y videos locales;
- GUI con PySide6;
- diagnostico del entorno;
- persistencia SQLite;
- inspeccion tecnica local de videos con `ffprobe`;
- miniatura tecnica inicial en caché local con `ffmpeg` cuando esta disponible.

Todavia no existen:

- analisis audiovisual con IA;
- PyTorch;
- CUDA Toolkit;
- modelos descargados;
- conectores reales;
- Script & Voice Studio como flujo obligatorio.

## Plataforma principal

- Windows
- Python 3.11
- NVIDIA CUDA como plataforma principal futura
- procesamiento local como prioridad

AMD, ROCm, DirectML, Vulkan y macOS quedan fuera del MVP.

## Requisitos actuales

- Windows 11 recomendado para uso final, aunque este entorno de desarrollo esta en Windows 10 Pro 22H2.
- Python 3.11.9 dentro de `.venv`
- PySide6 instalado en el entorno virtual
- Git instalado
- `ffprobe` requerido para la inspeccion tecnica
- `ffmpeg` opcional para miniaturas tecnicas iniciales

La localizacion de herramientas multimedia puede configurarse mas adelante con
`ffmpeg_path`, `ffprobe_path` o `ffmpeg_bin_directory`, o mediante las
variables `CIS_FFMPEG_PATH`, `CIS_FFPROBE_PATH` y `CIS_FFMPEG_BIN_DIRECTORY`.

## Arranque de la GUI

```bat
scripts\run_gui.bat
```

O directamente:

```bat
python -m creator_intelligence_studio --gui
```

## Estado funcional actual

La aplicacion ya permite:

- crear creadores;
- listar y consultar creadores;
- archivar creadores;
- crear proyectos pertenecientes a un creador;
- listar y consultar proyectos;
- archivar proyectos;
- registrar videos locales como metadatos;
- listar y consultar videos registrados;
- verificar si un archivo sigue disponible;
- inspeccionar tecnicamente un video registrado;
- guardar un resumen tecnico real de `ffprobe`;
- generar una miniatura tecnica inicial en caché local cuando `ffmpeg` esta disponible;
- abrir una interfaz de escritorio funcional con navegacion, inspector y diagnostico del sistema;
- persistir toda la informacion en SQLite local.

## Base local

La base estructurada inicial se guarda en:

`data/creator_intelligence_studio.db`

El archivo esta ignorado por Git. No debe subirse al repositorio.

Advertencia: en esta primera version el registro conserva la ruta absoluta normalizada del archivo local. Eso es funcional para desarrollo, pero no es una estrategia portable final.

La inspeccion tecnica escribe artefactos derivados en `cache/videos/<video-id>/inspection/` y `cache/videos/<video-id>/thumbnails/`. Ese caché permanece local y no debe subirse.

## Activar `.venv`

En PowerShell:

```powershell
.\.venv\Scripts\Activate.ps1
```

En `cmd.exe`:

```bat
.\.venv\Scripts\activate.bat
```

## Ejecutar la aplicacion

```bat
scripts\run_app.bat
```

O directamente:

```bat
python -m creator_intelligence_studio
```

## Ejecutar el diagnostico en JSON

```bat
python -m creator_intelligence_studio --diagnostic-json
```

## Comandos de creadores

```bat
python -m creator_intelligence_studio creator create --name "Heybermu"
python -m creator_intelligence_studio creator list
python -m creator_intelligence_studio creator show <creator_id_or_slug>
python -m creator_intelligence_studio creator archive <creator_id_or_slug>
```

## Comandos de proyectos

```bat
python -m creator_intelligence_studio project create --creator <creator_id_or_slug> --name "Video principal" --type long_form
python -m creator_intelligence_studio project list --creator <creator_id_or_slug>
python -m creator_intelligence_studio project show <project_id>
python -m creator_intelligence_studio project archive <project_id>
```

## Comandos de videos

```bat
python -m creator_intelligence_studio video register --project <project_id> --file "C:\ruta\video.mp4" --title "Titulo provisional"
python -m creator_intelligence_studio video list --project <project_id>
python -m creator_intelligence_studio video show <video_id>
python -m creator_intelligence_studio video verify <video_id>
```

## Comandos de medios

```bat
python -m creator_intelligence_studio media tools
python -m creator_intelligence_studio media tools --json
python -m creator_intelligence_studio media inspect --video-id <video_id>
python -m creator_intelligence_studio media inspect --video-id <video_id> --force
python -m creator_intelligence_studio media show --video-id <video_id>
python -m creator_intelligence_studio media show --video-id <video_id> --json
```

## Ejecutar pruebas

```bat
scripts\run_tests.bat
```

O directamente:

```bat
python -m unittest discover -s tests -p "test_*.py"
```

## Estructura principal

- `docs/`: documentacion maestra y diagnósticos.
- `src/creator_intelligence_studio/`: paquete principal del proyecto.
- `tests/`: pruebas unitarias.
- `config/`: configuracion por defecto.
- `scripts/`: scripts de arranque y pruebas en Windows.
- `data/`, `logs/`, `models/`, `artifacts/`, `cache/`: carpetas operativas locales.
- `data/creator_intelligence_studio.db`: base SQLite local estructurada.

## Script & Voice Studio

Script & Voice Studio es un modulo opcional. No es necesario para analizar videos, revisar metricas, administrar proyectos ni usar el nucleo del sistema.

## Advertencia sobre CUDA y PyTorch

CUDA Toolkit y PyTorch todavia no estan instalados en este repositorio. La aplicacion actual solo realiza diagnostico basico, catalogo, inspeccion tecnica local con herramientas externas si existen, preparacion de rutas, logging e interfaz.

`ffprobe` es la herramienta requerida para la inspeccion tecnica. `ffmpeg` solo se usa para la miniatura inicial. El video original nunca se copia ni se modifica.

## Seguridad y repositorio

No subas videos, modelos, datos privados, credenciales ni la base SQLite al repositorio. Los archivos sensibles deben permanecer fuera del control de versiones.

## Borrado manual de una base de desarrollo

Si necesitas reiniciar los datos de desarrollo, borra manualmente `data/creator_intelligence_studio.db` solo cuando estes seguro de que no necesitas conservar la informacion. No hay borrado automatico en la aplicacion.
