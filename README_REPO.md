# Cortinillas AI

Sistema automatizado de detección de cortinillas en audio de televisión usando Deepgram API.

## 🚀 Características

- **Procesamiento Automatizado**: Ejecuta cada hora vía Windows Task Scheduler
- **Multi-Canal**: Procesa múltiples canales de TV simultáneamente  
- **Detección Inteligente**: Usa Deepgram API para reconocimiento de voz preciso
- **Filtrado de Solapamiento**: Elimina contenido duplicado entre segmentos consecutivos
- **Reportes Profesionales**: Genera reportes en Excel y JSON con estilos profesionales
- **Manejo de Errores**: Sistema robusto de recuperación y logging

## 📋 Requisitos

- Python 3.8+
- Windows 10/11 (para Task Scheduler)
- Deepgram API Key
- Acceso a API de TV

## ⚡ Instalación Rápida

1. **Clonar el repositorio**:
   ```bash
   git clone <repository-url>
   cd cortinillas-ai
   ```

2. **Instalar dependencias**:
   ```bash
   pip install -r requirements.txt
   ```

3. **Configurar variables de entorno**:
   ```bash
   copy config\env.template .env
   # Editar .env con tu Deepgram API key
   ```

4. **Configurar canales**:
   - Editar `config/caracol.json` y `config/rcn.json` según tus necesidades

5. **Probar el sistema**:
   ```bash
   python src\main.py --validate-only
   ```

6. **Configurar tarea programada**:
   ```powershell
   powershell -ExecutionPolicy Bypass -File scripts\create_scheduled_task.ps1
   ```

## 🏗️ Estructura del Proyecto

```
cortinillas-ai/
├── src/                    # Código fuente
│   ├── main.py            # Controlador principal
│   ├── cortinilla_detector.py  # Detección de cortinillas
│   ├── audio_extractor.py      # Extracción de audio
│   ├── overlap_detector.py     # Detección de solapamiento
│   └── report_generator.py     # Generación de reportes
├── config/                 # Configuraciones
│   ├── caracol.json       # Config canal Caracol
│   └── rcn.json          # Config canal RCN
├── scripts/               # Scripts de utilidad
├── tests/                 # Pruebas unitarias
├── docs/                  # Documentación
└── data/                  # Reportes generados
```

## 🔧 Uso

### Ejecución Manual
```bash
# Procesamiento normal
python src\main.py

# Solo validación
python src\main.py --validate-only

# Logging detallado
python src\main.py --verbose
```

### Ejecución Automatizada
El sistema se ejecuta automáticamente cada hora vía Windows Task Scheduler una vez configurado.

## 📊 Reportes

El sistema genera reportes en dos formatos:

- **Excel** (`data/{canal}_results.xlsx`): Reportes profesionales con múltiples hojas
- **JSON** (`data/{canal}_results.json`): Datos estructurados para integración

### Hojas del Excel:
- **Resumen**: Estadísticas generales
- **Detalles por Hora**: Resultados detallados por ejecución
- **Desglose Cortinillas**: Análisis por tipo de cortinilla
- **Logs y Errores**: Registro de eventos importantes

## 🔍 Monitoreo

- **Logs**: `logs/cortinillas_ai_YYYYMMDD.log`
- **Reportes**: `data/{canal}_results.xlsx` y `.json`
- **Cache**: `data/transcript_cache/` (para detección de solapamiento)

## ⚙️ Configuración

### Variables de Entorno (.env)
```env
DEEPGRAM_API_KEY=tu_api_key_aqui
```

### Configuración de Canal (config/{canal}.json)
```json
{
  "channel_name": "caracol",
  "idemisora": 3,
  "idprograma": 6,
  "cortinillas": ["buenos días", "buenas tardes", ...],
  "deepgram_config": {
    "language": "multi",
    "model": "nova-3",
    "smart_format": true
  },
  "api_config": {
    "base_url": "https://tu-api.com",
    "cookie_sid": "tu_session_id"
  }
}
```

## 🧪 Pruebas

```bash
# Ejecutar todas las pruebas
python -m pytest tests/

# Pruebas con cobertura
python -m pytest tests/ --cov=src

# Validar configuración
python scripts\validate_config.py
```

## 📝 Logs

El sistema mantiene logs detallados en:
- `logs/cortinillas_ai_YYYYMMDD.log`: Log principal
- Reportes Excel incluyen hoja de "Logs y Errores"
- JSON incluye sección `logs_and_errors`

## 🔒 Seguridad

- Las API keys se almacenan en `.env` (no incluido en el repositorio)
- Los archivos de configuración pueden contener información sensible
- Se recomienda usar variables de entorno para datos sensibles

## 📞 Soporte

Para problemas o preguntas:
1. Revisar logs en `logs/`
2. Ejecutar `python src\main.py --validate-only`
3. Verificar configuración con `python scripts\validate_config.py`

## 📄 Licencia

Proyecto propietario para detección automatizada de cortinillas en TV.