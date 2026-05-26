from google import genai
from google.genai import types
import base64
import json
from pathlib import Path
from pdf2image import convert_from_path
from dotenv import load_dotenv
import os
import io

load_dotenv()

client = genai.Client(api_key=os.getenv("GOOGLE_API_KEY"))

def imagen_a_bytes(ruta_imagen: str) -> tuple[bytes, str]:
    with open(ruta_imagen, "rb") as f:
        datos = f.read()
    extension = Path(ruta_imagen).suffix.lower()
    tipos = {".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".png": "image/png"}
    media_type = tipos.get(extension, "image/jpeg")
    return datos, media_type

def pdf_a_bytes(ruta_pdf: str) -> list:
    paginas = convert_from_path(
        ruta_pdf,
        dpi=200,
        poppler_path=r"poppler-26.02.0\Library\bin"
    )
    imagenes = []
    for pagina in paginas:
        buffer = io.BytesIO()
        pagina.save(buffer, format="JPEG", quality=90)
        imagenes.append(buffer.getvalue())
    return imagenes

def extraer_datos_factura(ruta_archivo: str) -> dict:
    extension = Path(ruta_archivo).suffix.lower()

    if extension == ".pdf":
        imagenes = pdf_a_bytes(ruta_archivo)
    else:
        datos_img, media_type = imagen_a_bytes(ruta_archivo)
        imagenes = [datos_img]

    prompt = """Eres un experto extrayendo datos de facturas de energía eléctrica colombianas.
    Analiza TODAS las páginas. La factura puede ser de EPM, CELSIA, QI Energy u otro comercializador.

    Responde ÚNICAMENTE con un objeto JSON, sin texto adicional, sin markdown, sin explicaciones:

    {
    "consumo_promedio_kwh": <número entero o null>,
    "estrato_socioeconomico": <número 1-6 o null>,
    "referencia_transformador": <string o null>,
    "direccion": <string o null>,
    "numero_contrato": <string o null>
    }

    ════════════════════════════════════════════
    CAMPO 1 — consumo_promedio_kwh
    ════════════════════════════════════════════
    Busca el PROMEDIO histórico de consumo de ENERGÍA ELÉCTRICA en kWh.
    NUNCA uses valores de agua (m3), alcantarillado, pesos ($), mora ni cargos fijos.

    A) FACTURAS EPM con gráfico de barras (residencial y comercial):
    - Busca la sección "Histórico de consumos (kWh) y promedio"
    - Hay una fila de números encima de las barras del gráfico — el ÚLTIMO número de esa fila es el PROM
    - Ejemplo: "1142 1071 802 1180 1418 903 779 995 1026" → PROM = 1026
    - Ejemplo: "11703 11244 11751 12778 11248 11640 12336 11699 11833" → PROM = 11833
    - Si la factura tiene múltiples servicios (agua + energía), usa SOLO el PROM del gráfico
        que diga "(kWh)" — ignora completamente los gráficos que digan "(m3)"

    B) FACTURAS EPM industrial / gran consumo (con tabla histórica):
    - Busca "Activa Promedio" seguido de un número
    - Ejemplo: "Activa Promedio  72.032,29" → devuelve 72032

    C) FACTURAS CELSIA:
    - Busca tabla "Consumos históricos", fila "Energía activa kWh-mes"
    - El promedio es el ÚLTIMO número de esa fila (columna "Promedio")
    - Ejemplo: "201.408  212.570  200.711  194.964  200.086  202.007  201.958" → 201958

    D) FACTURAS QI ENERGY:
    - Busca tabla "Consumo Historicos de Energia Activa y Reactiva"
    - Busca la columna "Consumo Promedio" — toma ese valor específico
    - Ejemplo: "6,470.88  6,607" → el promedio es 6607 (NO 6470)

    Conversión de números: elimina puntos de miles y comas decimales → entero.
    "11.833"→11833 | "72.032,29"→72032 | "201.958"→201958 | "6,607"→6607 | "1.026"→1026

    ════════════════════════════════════════════
    CAMPO 2 — estrato_socioeconomico
    ════════════════════════════════════════════
    - Busca "Estrato" seguido de un número del 1 al 6
    - SOLO aplica a personas naturales con CC en servicio residencial
    - Si el cliente tiene NIT → null
    - Si es empresa, hotel, industria, bomba, o servicio comercial → null
    - Si "Estrato:" aparece en blanco o sin número → null

    ════════════════════════════════════════════
    CAMPO 3 — referencia_transformador
    ════════════════════════════════════════════
    A) FACTURAS EPM (cualquier tipo):
    - Busca en la sección "Informacion tecnica" el texto "Transfor.:"
    - Copia el número que está INMEDIATAMENTE después de "Transfor.:" hasta el siguiente " - "
    - Ejemplo: "Transfor.: 206870 - Grupo: 32" → "206870"
    - Ejemplo: "Transfor.: 087920 - Grupo:" → "087920"

    B) FACTURAS CELSIA:
    - Busca la línea que contiene simultáneamente "Transformador:" Y "Circuito:" Y "Grupo:"
    - Copia el código entre "Transformador:" y "Circuito:"
    - Ejemplo: "Transformador: 104C6V0000   Circuito:0   Grupo: 12" → "104C6V0000"

    C) FACTURAS QI ENERGY:
    - Busca "Código Transformador" en la tabla de calidad del servicio
    - Si el valor está vacío → null

    ════════════════════════════════════════════
    CAMPO 4 — direccion
    ════════════════════════════════════════════
    Busca en este orden:
    1. "Dirección prestación servicio:" → copia hasta fin de línea
    2. "Dirección del servicio:" → copia hasta fin de línea
    3. "Dirección de cobro:" → copia hasta fin de línea
    4. "Dirección:" al inicio del documento

    Devuelve SOLO: calle/carrera + número + municipio + departamento.
    NO incluyas: estrato, ciclo, NIU, códigos de más de 10 dígitos.

    ════════════════════════════════════════════
    CAMPO 5 — numero_contrato
    ════════════════════════════════════════════
    A) FACTURAS EPM RESIDENCIAL/COMERCIAL:
    - En la página 2, busca "Contrato" seguido de un número de 7-8 dígitos
    - IMPORTANTE: el número que buscas está en la sección de resumen de pago
    - Ejemplo: "Contrato 10206177" → "10206177" | "Contrato 7186550" → "7186550"
    - NUNCA uses: "N° DEE..." (esos son números de documento electrónico, no contrato)
    - NUNCA uses: "Referente de pago", "Producto:", "NIU", ni CUDE

    B) FACTURAS EPM INDUSTRIAL:
    - En la primera página busca "Contrato:" cerca del nombre del cliente
    - Ejemplo: "Contrato: 192535" → "192535"

    C) FACTURAS CELSIA:
    - Busca "Contrato:" en los datos del cliente
    - Ejemplo: "Contrato: AV-095-23" → "AV-095-23"

    D) FACTURAS QI ENERGY:
    - Busca "Codigo QI ENERGY" o "Código QI Energy"
    - Ejemplo: "Código QI Energy  QIE00167" → "QIE00167"
    - NUNCA uses "Referencia de Pago" ni el número "00000166"

    ════════════════════════════════════════════
    VALORES ESPERADOS DE REFERENCIA
    ════════════════════════════════════════════
    Usa estos como guía para validar tu extracción:
    - Facturas EPM residencial: contrato es número de 8 dígitos (ej: 10206177, 7186550)
    - Facturas EPM industrial: contrato es número de 5-6 dígitos (ej: 192535)
    - Facturas CELSIA: contrato tiene letras y guiones (ej: AV-095-23)
    - Facturas QI Energy: contrato empieza con QIE (ej: QIE00167)"""

    contenido = []
    for img in imagenes:
        contenido.append(types.Part.from_bytes(data=img, mime_type="image/jpeg"))
    contenido.append(prompt)

    respuesta = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=contenido
    )

    texto = respuesta.text.strip()
    texto = texto.replace("```json", "").replace("```", "").strip()
    return json.loads(texto)

# ── Punto de entrada ──────────────────────────────────────────
if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("Uso: python extractor.py <ruta_de_la_factura>")
        print("Ejemplo: python extractor.py factura.pdf")
        sys.exit(1)

    ruta = sys.argv[1]
    print(f"\n📄 Procesando: {ruta}")
    print("⏳ Extrayendo datos...\n")

    resultado = extraer_datos_factura(ruta)

    print("✅ Datos extraídos:")
    print(json.dumps(resultado, indent=2, ensure_ascii=False))