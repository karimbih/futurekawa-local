from datetime import datetime, timezone
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
from app.models.lot import Lot
from app.models.mesure import Mesure
from app.services.alertes import detecter_anomalies_conditions

router = APIRouter(dependencies=[Depends(require_api_key)])


class MesureCreate(BaseModel):
    capteur_id: Optional[UUID] = None
    topic_mqtt: Optional[str] = None
    entrepot_id: Optional[UUID] = None
    lot_id: Optional[UUID] = None
    source: str = "MQTT"
    date_mesure: Optional[datetime] = None
    temperature_c: float
    humidite_pct: float
    donnees_brutes: Optional[dict] = None


class MesureUpdate(BaseModel):
    lot_id: Optional[UUID] = None


@router.post("/", status_code=status.HTTP_201_CREATED)
def receive_mesure(mesure: MesureCreate, db: Session = Depends(get_db)):
    # 1. Résolution du capteur (par id ou par topic MQTT)
    capteur = None
    if mesure.capteur_id is not None:
        capteur = db.get(Capteur, mesure.capteur_id)
    elif mesure.topic_mqtt:
        capteur = (
            db.query(Capteur)
            .filter(Capteur.topic_mqtt == mesure.topic_mqtt)
            .first()
        )
    if not capteur:
        raise HTTPException(
            status_code=404,
            detail="Capteur introuvable (fournir capteur_id ou un topic_mqtt connu)",
        )

    # 2. Vérification de l'entrepôt cible
    entrepot = db.get(Entrepot, capteur.entrepot_id)
    if not entrepot:
        raise HTTPException(status_code=404, detail="Entrepôt associé introuvable")
    if mesure.entrepot_id is not None and mesure.entrepot_id != entrepot.id:
        raise HTTPException(
            status_code=400,
            detail="entrepot_id incohérent avec le capteur fourni",
        )

    # 3. Vérification du lot optionnel
    lot = None
    if mesure.lot_id is not None:
        lot = db.get(Lot, mesure.lot_id)
        if not lot:
            raise HTTPException(status_code=404, detail="Lot introuvable")

    # 4. Persistance de la mesure
    db_mesure = Mesure(
        entrepot_id=entrepot.id,
        capteur_id=capteur.id,
        lot_id=lot.id if lot else None,
        source=mesure.source,
        topic_mqtt=capteur.topic_mqtt,
        date_mesure=mesure.date_mesure or datetime.now(timezone.utc),
        date_reception=datetime.now(timezone.utc),
        temperature_c=mesure.temperature_c,
        humidite_pct=mesure.humidite_pct,
        donnees_brutes=mesure.donnees_brutes,
    )
    db.add(db_mesure)

    # 5. Mise à jour de la dernière communication du capteur
    capteur.derniere_communication = datetime.now(timezone.utc)
    db.add(capteur)

    # 6. Détection d'anomalies par rapport à la bande idéale du pays (cible ± tolérance)
    detecter_anomalies_conditions(
        db,
        entrepot=entrepot,
        capteur=capteur,
        lot=lot,
        temperature=float(mesure.temperature_c),
        humidite=float(mesure.humidite_pct),
    )

    db.commit()
    db.refresh(db_mesure)
    return {"status": "Mesure traitée", "mesure_id": str(db_mesure.id)}


@router.get("/")
def list_mesures(
    entrepot_id: Optional[UUID] = None,
    capteur_id: Optional[UUID] = None,
    lot_id: Optional[UUID] = None,
    date_mesure_depuis: Optional[datetime] = None,
    date_mesure_jusqua: Optional[datetime] = None,
    mis_a_jour_depuis: Optional[datetime] = None,
    limit: Optional[int] = None,
    offset: Optional[int] = None,
    db: Session = Depends(get_db),
):
    limit, offset = get_pagination(limit, offset)
    query = db.query(Mesure)
    if entrepot_id is not None:
        query = query.filter(Mesure.entrepot_id == entrepot_id)
    if capteur_id is not None:
        query = query.filter(Mesure.capteur_id == capteur_id)
    if lot_id is not None:
        query = query.filter(Mesure.lot_id == lot_id)
    if date_mesure_depuis is not None:
        query = query.filter(Mesure.date_mesure >= date_mesure_depuis)
    if date_mesure_jusqua is not None:
        query = query.filter(Mesure.date_mesure <= date_mesure_jusqua)
    if mis_a_jour_depuis is not None:
        query = query.filter(Mesure.mis_a_jour_le > mis_a_jour_depuis)
    total = query.count()
    items = (
        query.order_by(Mesure.date_mesure.desc())
        .offset(offset)
        .limit(limit)
        .all()
    )
    return paginated_response(items, total, limit, offset)


@router.get("/{mesure_id}")
def get_mesure(mesure_id: UUID, db: Session = Depends(get_db)):
    mesure = db.get(Mesure, mesure_id)
    if not mesure:
        raise HTTPException(status_code=404, detail="Mesure introuvable")
    return mesure


@router.put("/{mesure_id}")
def update_mesure(
    mesure_id: UUID,
    payload: MesureUpdate,
    db: Session = Depends(get_db),
):
    mesure = db.get(Mesure, mesure_id)
    if not mesure:
        raise HTTPException(status_code=404, detail="Mesure introuvable")
    if payload.lot_id is not None:
        if not db.get(Lot, payload.lot_id):
            raise HTTPException(status_code=404, detail="Lot introuvable")
        mesure.lot_id = payload.lot_id
        db.commit()
        db.refresh(mesure)
    return mesure
