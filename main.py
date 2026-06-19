from fastapi import FastAPI

# On ajoute "app." car TOUS tes dossiers sont à l'intérieur du dossier 'app'
from app.database.db import engine, Base

from app.models.entrepot import Entrepot
from app.models.lot import Lot
from app.models.mesure import Mesure
from app.models.alerte import Alerte

# Import des routeurs
from app.api.routes.entrepots import router as entrepot_router
from app.api.routes.lots import router as lot_router
from app.api.routes.mesures import router as mesure_router
from app.api.routes.alertes import router as alerte_router

# Création des tables dans PostgreSQL (ne bloque pas le démarrage si la BDD est indisponible)
try:
    Base.metadata.create_all(bind=engine)
except Exception as e:
    print(f"Warning: impossible de créer les tables au démarrage: {e}")

app = FastAPI(
    title="FutureKawa Backend Local",
    version="1.0.0"
)

# Configuration des routes
app.include_router(entrepot_router, prefix="/entrepots", tags=["Entrepots"])
app.include_router(lot_router, prefix="/lots", tags=["Lots"])
app.include_router(mesure_router, prefix="/mesures", tags=["Mesures"])
app.include_router(alerte_router, prefix="/alertes", tags=["Alertes"])

@app.get("/")
def root():
    return {
        "message": "FutureKawa Backend Local opérationnel"
    }