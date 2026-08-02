from datetime import datetime
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.security import require_api_key
from app.core.utils import get_pagination, paginated_response
from app.database.db import get_db
from app.models.entrepot import Entrepot

router = APIRouter(dependencies=[Depends(require_api_key)])


class EntrepotCreate(BaseModel):
    nom: str
    ville: str
    code_pays: str
    nom_responsable: str
    email_responsable: str
    temperature_min_c: float
    temperature_max_c: float
    humidite_min_pct: float
    humidite_max_pct: float


class EntrepotUpdate(BaseModel):
    nom: Optional[str] = None
    ville: Optional[str] = None
    code_pays: Optional[str] = None
    nom_responsable: Optional[str] = None
    email_responsable: Optional[str] = None
    temperature_min_c: Optional[float] = None
    temperature_max_c: Optional[float] = None
    humidite_min_pct: Optional[float] = None
    humidite_max_pct: Optional[float] = None


@router.post("/", status_code=status.HTTP_201_CREATED)
def create_entrepot(entrepot: EntrepotCreate, db: Session = Depends(get_db)):
    db_entrepot = Entrepot(**entrepot.model_dump())
    db.add(db_entrepot)
    db.commit()
    db.refresh(db_entrepot)
    return db_entrepot


@router.get("/")
def list_entrepots(
    mis_a_jour_depuis: Optional[datetime] = None,
    limit: Optional[int] = None,
    offset: Optional[int] = None,
    db: Session = Depends(get_db),
):
    limit, offset = get_pagination(limit, offset)
    query = db.query(Entrepot)
    if mis_a_jour_depuis is not None:
        query = query.filter(Entrepot.mis_a_jour_le > mis_a_jour_depuis)
    total = query.count()
    items = (
        query.order_by(Entrepot.mis_a_jour_le.asc())
        .offset(offset)
        .limit(limit)
        .all()
    )
    return paginated_response(items, total, limit, offset)


@router.get("/{entrepot_id}")
def get_entrepot(entrepot_id: UUID, db: Session = Depends(get_db)):
    entrepot = db.get(Entrepot, entrepot_id)
    if not entrepot:
        raise HTTPException(status_code=404, detail="Entrepôt introuvable")
    return entrepot


@router.put("/{entrepot_id}")
def update_entrepot(
    entrepot_id: UUID,
    payload: EntrepotUpdate,
    db: Session = Depends(get_db),
):
    entrepot = db.get(Entrepot, entrepot_id)
    if not entrepot:
        raise HTTPException(status_code=404, detail="Entrepôt introuvable")
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(entrepot, field, value)
    db.commit()
    db.refresh(entrepot)
    return entrepot


@router.delete("/{entrepot_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_entrepot(entrepot_id: UUID, db: Session = Depends(get_db)):
    entrepot = db.get(Entrepot, entrepot_id)
    if not entrepot:
        raise HTTPException(status_code=404, detail="Entrepôt introuvable")
    db.delete(entrepot)
    db.commit()
