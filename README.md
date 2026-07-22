# Creator Intelligence Studio

Creator Intelligence Studio es una aplicación de escritorio para Windows orientada al análisis inteligente de contenido audiovisual para creadores.

## Estado actual

Este repositorio está en una etapa temprana. Ya existe una base ejecutable, diagnóstica y un primer flujo vertical funcional para creadores, proyectos y videos locales usando únicamente la biblioteca estándar de Python 3.11.

Todavía no existen:

- interfaz gráfica;
- análisis audiovisual;
- PyTorch;
- CUDA Toolkit;
- FFmpeg;
- modelos descargados;
- conectores reales;
- Script & Voice Studio implementado;
- procesamiento creativo final.

## Plataforma principal

- Windows
- Python 3.11
- NVIDIA CUDA como plataforma principal futura
- procesamiento local como prioridad

AMD, ROCm, DirectML, Vulkan y macOS quedan fuera del MVP.

## Requisitos actuales

- Windows 11 recomendado para el uso final, aunque este entorno de desarrollo está en Windows 10 Pro 22H2.
- Python 3.11.9 dentro de `.venv`
- Git instalado
- No se requieren dependencias externas en esta etapa

## Estado funcional actual

La aplicación ya permite:

- crear creadores;
- listar y consultar creadores;
- archivar creadores;
- crear proyectos pertenecientes a un creador;
- listar y consultar proyectos;
- archivar proyectos;
- registrar videos locales como metadatos;
- listar y consultar videos registrados;
- verificar si un archivo sigue disponible;
- persistir toda la información en SQLite local.

## Base local

La base estructurada inicial se guarda en:

`data/creator_intelligence_studio.db`

El archivo está ignorado por Git. No debe subirse al repositorio.

Advertencia: en esta primera versión el registro conserva la ruta absoluta normalizada del archivo local. Eso es funcional para desarrollo, pero no es una estrategia portable final.

## Activar `.venv`

En PowerShell:

```powershell
.\.venv\Scripts\Activate.ps1
```

En `cmd.exe`:

```bat
.\.venv\Scripts\activate.bat
```

## Ejecutar la aplicación

```bat
scripts\run_app.bat
```

O directamente:

```bat
python -m creator_intelligence_studio
```

## Ejecutar el diagnóstico en JSON

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
python -m creator_intelligence_studio video register --project <project_id> --file "C:\ruta\video.mp4" --title "Título provisional"
python -m creator_intelligence_studio video list --project <project_id>
python -m creator_intelligence_studio video show <video_id>
python -m creator_intelligence_studio video verify <video_id>
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

- `docs/`: documentación maestra y diagnóstico inicial.
- `src/creator_intelligence_studio/`: paquete principal del proyecto.
- `tests/`: pruebas unitarias.
- `config/`: configuración por defecto.
- `scripts/`: scripts de arranque y pruebas en Windows.
- `data/`, `logs/`, `models/`, `artifacts/`: carpetas operativas locales.
- `data/creator_intelligence_studio.db`: base SQLite local estructurada.

## Script & Voice Studio

Script & Voice Studio es un módulo opcional. No es necesario para analizar videos, revisar métricas, administrar proyectos ni usar el núcleo del sistema.

## Advertencia sobre CUDA y PyTorch

CUDA Toolkit y PyTorch todavía no están instalados en este repositorio. La aplicación actual solo realiza diagnóstico básico y preparación de rutas y logging.

## Seguridad y repositorio

No subas videos, modelos, datos privados, credenciales ni la base SQLite al repositorio. Los archivos sensibles deben permanecer fuera del control de versiones.

## Borrado manual de una base de desarrollo

Si necesitas reiniciar los datos de desarrollo, borra manualmente `data/creator_intelligence_studio.db` solo cuando estés seguro de que no necesitas conservar la información. No hay borrado automático en la aplicación.
