from fastapi import FastAPI, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
import shutil, os, uuid, hashlib
from pathlib import Path
from extractor import extraer_datos_factura
from database import guardar_factura, ya_fue_procesada, obtener_historial, eliminar_factura

app = FastAPI(title="SolarData API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

TEMP_DIR = Path("temp_uploads")
TEMP_DIR.mkdir(exist_ok=True)

@app.get("/")
def raiz():
    return FileResponse("index.html")

@app.post("/extraer")
async def extraer(file: UploadFile = File(...)):
    ext = Path(file.filename).suffix
    ruta_temp = TEMP_DIR / f"{uuid.uuid4()}{ext}"

    try:
        contenido = await file.read()

        # Calcula hash para detectar duplicados
        hash_archivo = hashlib.md5(contenido).hexdigest()

        # Revisa si ya fue procesada antes
        cached = ya_fue_procesada(hash_archivo)
        if cached:
            print(f"✅ Desde caché: {file.filename}")
            cached["archivo"] = file.filename
            return cached

        # Guarda el archivo temporalmente
        with open(ruta_temp, "wb") as f:
            f.write(contenido)

        # Extrae los datos
        resultado = extraer_datos_factura(str(ruta_temp))
        resultado["archivo"] = file.filename

        # Guarda en base de datos
        info = guardar_factura(resultado, hash_archivo)
        resultado["id_db"] = info["id"]
        resultado["fecha_procesado"] = info["fecha"]
        resultado["desde_cache"] = False

        return resultado

    except Exception as e:
        return {"error": str(e), "archivo": file.filename}

    finally:
        if ruta_temp.exists():
            os.remove(ruta_temp)

@app.get("/historial")
def historial(limite: int = 100):
    """Retorna el historial de facturas procesadas."""
    return obtener_historial(limite)

@app.delete("/historial/{id}")
def borrar(id: int):
    """Elimina una factura del historial."""
    ok = eliminar_factura(id)
    return {"eliminado": ok}

@app.get("/health")
def health():
    return {"status": "ok", "mensaje": "SolarData API funcionando"}