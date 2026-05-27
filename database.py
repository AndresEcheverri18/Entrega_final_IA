from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime, text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from datetime import datetime

# Crea el archivo de base de datos en la misma carpeta
engine = create_engine("sqlite:///solardata.db", echo=False)
Base = declarative_base()
SessionLocal = sessionmaker(bind=engine)

class Factura(Base):
    __tablename__ = "facturas"

    id                    = Column(Integer, primary_key=True, autoincrement=True)
    archivo               = Column(String, nullable=False)
    consumo_promedio_kwh  = Column(Float, nullable=True)
    estrato_socioeconomico= Column(Integer, nullable=True)
    referencia_transformador = Column(String, nullable=True)
    direccion             = Column(String, nullable=True)
    numero_contrato       = Column(String, nullable=True)
    fecha_procesado       = Column(DateTime, default=datetime.now)
    hash_archivo          = Column(String, nullable=True)

def crear_tablas():
    Base.metadata.create_all(engine)

def guardar_factura(datos: dict, hash_archivo: str = None) -> dict:
    """Guarda una extracción en la base de datos."""
    db = SessionLocal()
    try:
        factura = Factura(
            archivo                  = datos.get("archivo", ""),
            consumo_promedio_kwh     = datos.get("consumo_promedio_kwh"),
            estrato_socioeconomico   = datos.get("estrato_socioeconomico"),
            referencia_transformador = datos.get("referencia_transformador"),
            direccion                = datos.get("direccion"),
            numero_contrato          = datos.get("numero_contrato"),
            hash_archivo             = hash_archivo,
            fecha_procesado          = datetime.now()
        )
        db.add(factura)
        db.commit()
        db.refresh(factura)
        return {"id": factura.id, "fecha": factura.fecha_procesado.isoformat()}
    finally:
        db.close()

def ya_fue_procesada(hash_archivo: str) -> dict | None:
    """Revisa si ya procesamos este archivo antes (por hash)."""
    db = SessionLocal()
    try:
        factura = db.query(Factura).filter(Factura.hash_archivo == hash_archivo).first()
        if factura:
            return {
                "archivo": factura.archivo,
                "consumo_promedio_kwh": factura.consumo_promedio_kwh,
                "estrato_socioeconomico": factura.estrato_socioeconomico,
                "referencia_transformador": factura.referencia_transformador,
                "direccion": factura.direccion,
                "numero_contrato": factura.numero_contrato,
                "desde_cache": True,
                "fecha_procesado": factura.fecha_procesado.isoformat()
            }
        return None
    finally:
        db.close()

def obtener_historial(limite: int = 100) -> list:
    """Retorna las últimas N facturas procesadas."""
    db = SessionLocal()
    try:
        facturas = db.query(Factura).order_by(Factura.fecha_procesado.desc()).limit(limite).all()
        return [
            {
                "id": f.id,
                "archivo": f.archivo,
                "consumo_promedio_kwh": f.consumo_promedio_kwh,
                "estrato_socioeconomico": f.estrato_socioeconomico,
                "referencia_transformador": f.referencia_transformador,
                "direccion": f.direccion,
                "numero_contrato": f.numero_contrato,
                "fecha_procesado": f.fecha_procesado.isoformat()
            }
            for f in facturas
        ]
    finally:
        db.close()

def eliminar_factura(id: int) -> bool:
    """Elimina una factura del historial por ID."""
    db = SessionLocal()
    try:
        factura = db.query(Factura).filter(Factura.id == id).first()
        if factura:
            db.delete(factura)
            db.commit()
            return True
        return False
    finally:
        db.close()

# Crea las tablas al importar el módulo
crear_tablas()