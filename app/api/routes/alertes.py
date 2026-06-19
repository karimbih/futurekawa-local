from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.database.db import get_db
from app.models.alerte import Alerte
from app.models.entrepot import Entrepot

router = APIRouter()

# Récupérer uniquement les alertes en cours (Non résolues) pour l'affichage de votre Dashboard
@router.get("/actives")
def list_active_alerts(db: Session = Depends(get_db)):
    return db.query(Alerte).filter(Alerte.statut == "Active").all()

# Récupérer tout l'historique (Exigence d'auditabilité du jury)
@router.get("/historique")
def list_all_alerts(db: Session = Depends(get_db)):
    return db.query(Alerte).order_by(Alerte.declenchee_le.desc()).all()