from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from pydantic import BaseModel
from datetime import datetime
from app.database.db import get_db
from app.models.lot import Lot
from app.models.entrepot import Entrepot

router = APIRouter()

class LotCreate(BaseModel):
    code_lot: str
    entrepot_id: int
    date_stockage: datetime
    statut: str = "Conforme"

@router.post("/", status_code=status.HTTP_201_CREATED)
def create_lot(lot: LotCreate, db: Session = Depends(get_db)):
    # Vérifier si l'entrepôt existe
    entrepot = db.query(Entrepot).filter(Entrepot.id == lot.entrepot_id).first()
    if not entrepot:
        raise HTTPException(status_code=404, detail="Entrepôt non trouvé")
        
    db_lot = Lot(**lot.dict())
    db.add(db_lot)
    db.commit()
    db.refresh(db_lot)
    return {"message": "Lot enregistré avec succès", "id": db_lot.id}

# Route demandée par le client : Tri FIFO (First In, First Out)
@router.get("/fifo")
def get_lots_fifo(db: Session = Depends(get_db)):
    # Tri par ordre croissant de la date de stockage (le plus ancien en premier)
    return db.query(LotDB).order_by(LotDB.date_stockage.asc()).all()