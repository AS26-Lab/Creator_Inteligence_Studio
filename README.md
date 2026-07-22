# Creator Intelligence Studio

Creator Intelligence Studio es una aplicación de escritorio para Windows orientada al análisis inteligente de contenido audiovisual para creadores.

## Estado actual

Este repositorio está en una etapa muy temprana. En esta misión solo se creó la cimentación ejecutable y comprobable del proyecto usando únicamente la biblioteca estándar de Python 3.11.

Todavía no existen:

- interfaz gráfica;
- base de datos;
- análisis audiovisual;
- PyTorch;
- CUDA Toolkit;
- FFmpeg;
- modelos descargados;
- conectores reales;
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

## Script & Voice Studio

Script & Voice Studio es un módulo opcional. No es necesario para analizar videos, revisar métricas, administrar proyectos ni usar el núcleo del sistema.

## Advertencia sobre CUDA y PyTorch

CUDA Toolkit y PyTorch todavía no están instalados en este repositorio. La aplicación actual solo realiza diagnóstico básico y preparación de rutas y logging.

## Seguridad y repositorio

No subas videos, modelos, datos privados ni credenciales al repositorio. Los archivos sensibles deben permanecer fuera del control de versiones.

