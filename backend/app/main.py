from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.routers import analisis

app = FastAPI(title="Analizador de etiquetado de Tequila")

# En desarrollo local permitimos al frontend; restringir en producción.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://127.0.0.1:5500", "http://localhost:5500"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(analisis.router)


@app.get("/salud")
def salud():
    return {"estado": "ok"}
