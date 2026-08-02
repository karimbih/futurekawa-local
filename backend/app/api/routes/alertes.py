from datetime import datetime
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.security import require_api_key
from app.core.utils import get_pagination, paginated_response
from app.database.db import get_db
from app.models.alerte import Alerte

router = APIRouter(dependencies=[Depends(require_api_key)])


class AlerteUpdate(BaseModel):
    statut: Optional[str] = None
    commentaire_resolution: Optional[str] = None
    resolue_par: Optional[UUID] = None


@router.get("/")
def list_alertes(
    statut: Optional[str] = None,
    entrepot_id: Optional[UUID] = None,
    type_alerte: Optional[str] = None,
    mis_a_jour_depuis: Optional[datetime] = None,
    limit: Optional[int] = None,
    offset: Optional[int] = None,
    db: Session = Depends(get_db),
):
    limit, offset = get_pagination(limit, offset)
    query = db.query(Alerte)
    if statut is not None:
        query = query.filter(Alerte.statut == statut)
    if entrepot_id is not None:
        query = query.filter(Alerte.entrepot_id == entrepot_id)
    if type_alerte is not None:
        query = query.filter(Alerte.type_alerte == type_alerte)
    if mis_a_jour_depuis is not None:
        query = query.filter(Alerte.mis_a_jour_le > mis_a_jour_depuis)
    total = query.count()
    items = (
        query.order_by(Alerte.date_declenchement.desc())
        .offset(offset)
        .limit(limit)
        .all()
    )
    return paginated_response(items, total, limit, offset)


@router.get("/actives")
def list_active_alerts(db: Session = Depends(get_db)):
    """Alertes en cours (non résolues) pour le dashboard local."""
    return db.query(Alerte).filter(Alerte.statut == "ACTIVE").order_by(
        Alerte.date_declenchement.desc()
    ).all()


@router.get("/historique")
def list_all_alerts(db: Session = Depends(get_db)):
    """Historique complet pour l'auditabilité."""
    return db.query(Alerte).order_by(Alerte.date_declenchement.desc()).all()


@router.get("/{alerte_id}")
def get_alerte(alerte_id: UUID, db: Session = Depends(get_db)):
    alerte = db.get(Alerte, alerte_id)
    if not alerte:
        raise HTTPException(status_code=404, detail="Alerte introuvable")
    return alerte


@router.put("/{alerte_id}")
def update_alerte(
    alerte_id: UUID,
    payload: AlerteUpdate,
    db: Session = Depends(get_db),
):
    alerte = db.get(Alerte, alerte_id)
    if not alerte:
        raise HTTPException(status_code=404, detail="Alerte introuvable")

    data = payload.model_dump(exclude_unset=True)
    if "statut" in data:
        nouveau_statut = data["statut"].upper()
        if nouveau_statut not in {"ACTIVE", "PRISE_EN_COMPTE", "RESOLUE", "IGNOREE"}:
            raise HTTPException(
                status_code=400,
                detail="Statut invalide (ACTIVE, PRISE_EN_COMPTE, RESOLUE, IGNOREE)",
            )
        data["statut"] = nouveau_statut
        if nouveau_statut in {"RESOLUE", "IGNOREE"}:
            data["date_resolution"] = datetime.utcnow()

    for field, value in data.items():
        setattr(alerte, field, value)

    db.commit()
    db.refresh(alerte)
    return alerte
