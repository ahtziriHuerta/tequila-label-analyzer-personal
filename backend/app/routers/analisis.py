from fastapi import APIRouter, UploadFile, File

router = APIRouter(prefix="/analisis", tags=["analisis"])


@router.post("/")
def crear_analisis():
    """RF-01: crear un análisis (una botella). TODO: guardar en BD."""
    return {"id_analisis": 1, "estado_general": "en_proceso"}


@router.post("/{id_analisis}/imagenes")
async def agregar_imagen(id_analisis: int, tipo_vista: str, archivo: UploadFile = File(...)):
    """RF-02/RF-03: adjuntar foto y su vista (frontal, posterior, lote...). TODO: validar y guardar."""
    return {"id_analisis": id_analisis, "tipo_vista": tipo_vista, "archivo": archivo.filename}
