from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from pydantic import BaseModel
from datetime import datetime
from app.database.db import get_db
from app.models.entrepot import Entrepot

router = APIRouter()

# Schéma de validation Pydantic pour l'entrée
class EntrepotCreate(BaseModel):
    nom: str
    ville: str
    code_pays: str
    nom_responsable: str
    email_responsable: str
    target_temp_c: float
    target_humidity_pct: float

@router.post("/", status_code=status.HTTP_201_CREATED)
def create_entrepot(entrepot: EntrepotCreate, db: Session = Depends(get_db)):
    db_entrepot = Entrepot(**entrepot.dict())
    db.add(db_entrepot)
    db.commit()
    db.refresh(db_entrepot)
    return {"message": "Entrepôt créé avec succès", "id": db_entrepot.id}

@router.get("/")
def list_entrepots(db: Session = Depends(get_db)):
    return db.query(Entrepot).all()
