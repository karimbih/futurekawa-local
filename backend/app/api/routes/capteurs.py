from datetime import datetime
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.security import require_api_key
from app.core.utils import get_pagination, paginated_response
from app.database.db import get_db
from app.models.capteur import Capteur
from app.models.entrepot import Entrepot

router = APIRouter(dependencies=[Depends(require_api_key)])


class CapteurCreate(BaseModel):
    entrepot_id: UUID
    reference: str
    topic_mqtt: str
    type_capteur: str
    statut: str = "ACTIF"
    frequence_mesure_secondes: int


class CapteurUpdate(BaseModel):
    entrepot_id: Optional[UUID] = None
    reference: Optional[str] = None
    topic_mqtt: Optional[str] = None
    type_capteur: Optional[str] = None
    statut: Optional[str] = None
    frequence_mesure_secondes: Optional[int] = None


@router.post("/", status_code=status.HTTP_201_CREATED)
def create_capteur(capteur: CapteurCreate, db: Session = Depends(get_db)):
    entrepot = db.get(Entrepot, capteur.entrepot_id)
    if not entrepot:
        raise HTTPException(status_code=404, detail="Entrepôt introuvable")
    db_capteur = Capteur(**capteur.model_dump())
    db.add(db_capteur)
    db.commit()
    db.refresh(db_capteur)
    return db_capteur


@router.get("/")
def list_capteurs(
    entrepot_id: Optional[UUID] = None,
    statut: Optional[str] = None,
    mis_a_jour_depuis: Optional[datetime] = None,
    limit: Optional[int] = None,
    offset: Optional[int] = None,
    db: Session = Depends(get_db),
):
    limit, offset = get_pagination(limit, offset)
    query = db.query(Capteur)
    if entrepot_id is not None:
        query = query.filter(Capteur.entrepot_id == entrepot_id)
    if statut is not None:
        query = query.filter(Capteur.statut == statut)
    if mis_a_jour_depuis is not None:
        query = query.filter(Capteur.mis_a_jour_le > mis_a_jour_depuis)
    total = query.count()
    items = (
        query.order_by(Capteur.mis_a_jour_le.asc())
        .offset(offset)
        .limit(limit)
        .all()
    )
    return paginated_response(items, total, limit, offset)


@router.get("/{capteur_id}")
def get_capteur(capteur_id: UUID, db: Session = Depends(get_db)):
    capteur = db.get(Capteur, capteur_id)
    if not capteur:
        raise HTTPException(status_code=404, detail="Capteur introuvable")
    return capteur


@router.put("/{capteur_id}")
def update_capteur(
    capteur_id: UUID,
    payload: CapteurUpdate,
    db: Session = Depends(get_db),
):
    capteur = db.get(Capteur, capteur_id)
    if not capteur:
        raise HTTPException(status_code=404, detail="Capteur introuvable")
    if payload.entrepot_id is not None and payload.entrepot_id != capteur.entrepot_id:
        if not db.get(Entrepot, payload.entrepot_id):
            raise HTTPException(status_code=404, detail="Entrepôt introuvable")
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(capteur, field, value)
    db.commit()
    db.refresh(capteur)
    return capteur


@router.delete("/{capteur_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_capteur(capteur_id: UUID, db: Session = Depends(get_db)):
    capteur = db.get(Capteur, capteur_id)
    if not capteur:
        raise HTTPException(status_code=404, detail="Capteur introuvable")
    db.delete(capteur)
    db.commit()
