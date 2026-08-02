from datetime import date, datetime
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.security import require_api_key
from app.core.utils import get_pagination, paginated_response
from app.database.db import get_db
from app.models.entrepot import Entrepot
from app.models.lot import Lot

router = APIRouter(dependencies=[Depends(require_api_key)])


class LotCreate(BaseModel):
    code_lot: str
    entrepot_id: UUID
    produit: str
    quantite_kg: float
    date_stockage: date
    statut: str = "EN_STOCK"


class LotUpdate(BaseModel):
    code_lot: Optional[str] = None
    entrepot_id: Optional[UUID] = None
    produit: Optional[str] = None
    quantite_kg: Optional[float] = None
    date_stockage: Optional[date] = None
    statut: Optional[str] = None


@router.post("/", status_code=status.HTTP_201_CREATED)
def create_lot(lot: LotCreate, db: Session = Depends(get_db)):
    entrepot = db.get(Entrepot, lot.entrepot_id)
    if not entrepot:
        raise HTTPException(status_code=404, detail="Entrepôt non trouvé")
    db_lot = Lot(**lot.model_dump())
    db.add(db_lot)
    db.commit()
    db.refresh(db_lot)
    return db_lot


@router.get("/")
def list_lots(
    entrepot_id: Optional[UUID] = None,
    statut: Optional[str] = None,
    mis_a_jour_depuis: Optional[datetime] = None,
    limit: Optional[int] = None,
    offset: Optional[int] = None,
    db: Session = Depends(get_db),
):
    limit, offset = get_pagination(limit, offset)
    query = db.query(Lot)
    if entrepot_id is not None:
        query = query.filter(Lot.entrepot_id == entrepot_id)
    if statut is not None:
        query = query.filter(Lot.statut == statut)
    if mis_a_jour_depuis is not None:
        query = query.filter(Lot.mis_a_jour_le > mis_a_jour_depuis)
    total = query.count()
    items = (
        query.order_by(Lot.mis_a_jour_le.asc())
        .offset(offset)
        .limit(limit)
        .all()
    )
    return paginated_response(items, total, limit, offset)


@router.get("/fifo")
def get_lots_fifo(db: Session = Depends(get_db)):
    """Tri FIFO (First In, First Out) : les lots les plus anciens d'abord."""
    return db.query(Lot).order_by(Lot.date_stockage.asc()).all()


@router.get("/{lot_id}")
def get_lot(lot_id: UUID, db: Session = Depends(get_db)):
    lot = db.get(Lot, lot_id)
    if not lot:
        raise HTTPException(status_code=404, detail="Lot introuvable")
    return lot


@router.put("/{lot_id}")
def update_lot(
    lot_id: UUID,
    payload: LotUpdate,
    db: Session = Depends(get_db),
):
    lot = db.get(Lot, lot_id)
    if not lot:
        raise HTTPException(status_code=404, detail="Lot introuvable")
    if payload.entrepot_id is not None and payload.entrepot_id != lot.entrepot_id:
        if not db.get(Entrepot, payload.entrepot_id):
            raise HTTPException(status_code=404, detail="Entrepôt non trouvé")
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(lot, field, value)
    db.commit()
    db.refresh(lot)
    return lot


@router.delete("/{lot_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_lot(lot_id: UUID, db: Session = Depends(get_db)):
    lot = db.get(Lot, lot_id)
    if not lot:
        raise HTTPException(status_code=404, detail="Lot introuvable")
    db.delete(lot)
    db.commit()
