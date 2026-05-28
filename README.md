# Extractor de Facturas de Energía 

Extrae automáticamente los 5 campos clave de facturas EPM, CELSIA y QI Energy
usando visión por computador con Gemini 2.5 Flash.

---

## Estructura del proyecto

```
Entrega_final_IA-main/
├── extractor.py        ← extrae datos de una sola factura
├── procesar_PDF.py     ← procesa una carpeta y genera Excel
├── server.py           ← servidor FastAPI (conecta el HTML con el extractor)
├── index.html          ← interfaz web
├── .env       ← tu API key (debes crearlo tú)
├──  notebooks/
├──  01 EDA
├──  02 OCR
├──  03 NER
├──  04 EVALUATION
└── README.md
```

---

## Requisitos previos

### Mac
```bash
brew install poppler
```
> Si no tienes Homebrew: https://brew.sh

### Windows
Descarga poppler para Windows y descomprímelo en la carpeta del proyecto:
> https://github.com/oschwartz10612/poppler-windows/releases

La carpeta debe quedar así:
```
Entrega_final_IA-main/
└── poppler-26.02.0/
    └── Library/
        └── bin/
```

---

## Instalación

```bash
pip install google-genai pdf2image openpyxl python-dotenv fastapi uvicorn python-multipart
```

---

## Configuración

Crea un archivo llamado `.env` en la carpeta del proyecto con tu API key de Google:

```
GOOGLE_API_KEY=tu_api_key_aqui
```

> Consigue tu key gratis en https://aistudio.google.com → *Get API key*

---

## Ejecución

### Opción A — Interfaz web (recomendado)

**Paso 1:** Abre una terminal en la carpeta del proyecto y arranca el servidor:

```bash
python server.py
```

Deberías ver:
```
INFO: Uvicorn running on http://0.0.0.0:8000
INFO: Application startup complete.
```

**Paso 2:** Sin cerrar esa terminal, abre `index.html` en el navegador.

**Paso 3:** Arrastra tus facturas y haz clic en **Procesar facturas**.

**Paso 4:** Cuando terminen, usa los botones **Exportar JSON** o **Descargar Excel (CSV)**.

---

### Opción B — Una sola factura por terminal

```bash
python extractor.py ruta/a/factura.pdf
```

Ejemplo:
```bash
python extractor.py facturas/factura_epm.pdf
```

Salida esperada:
```json
{
  "consumo_promedio_kwh": 1026,
  "estrato_socioeconomico": 3,
  "referencia_transformador": "206870",
  "direccion": "CL 45 # 32-10, Medellín - Antioquia",
  "numero_contrato": "10206177"
}
```

---

### Opción C — Carpeta entera con exportación a Excel

```bash
python procesar_PDF.py ruta/a/carpeta/
```

Ejemplo:
```bash
python procesar_PDF.py facturas/
```

Genera automáticamente un archivo `resultados_2026-05-27_14-30.xlsx` en la misma carpeta.

---

## Formatos soportados

| Formato | Soportado |
|---------|-----------|
| PDF     | ✅        |
| JPG     | ✅        |
| PNG     | ✅        |

## Comercializadores soportados

| Empresa   | Soportado |
|-----------|-----------|
| EPM       | ✅        |
| CELSIA    | ✅        |
| QI Energy | ✅        |
| Otros     | ⚠️ resultados pueden variar |

---

## Campos extraídos

| Campo                    | Descripción                          |
|--------------------------|--------------------------------------|
| `consumo_promedio_kwh`   | Promedio histórico de consumo en kWh |
| `estrato_socioeconomico` | Estrato 1–6 (null si no aplica)      |
| `referencia_transformador` | Código del transformador           |
| `direccion`              | Dirección del predio                 |
| `numero_contrato`        | Número de contrato del cliente       |

---

## Solución de problemas

**`ModuleNotFoundError`** → corre `pip install` del módulo que falta

**`Load failed` en el HTML** → el servidor no está corriendo; ejecuta `python server.py` primero

**Campos vacíos en los resultados** → la factura puede ser de baja calidad o de un comercializador no soportado; intenta con una foto más nítida

**Error de poppler en Windows** → verifica que la carpeta `poppler-26.02.0/Library/bin` esté dentro del proyecto
