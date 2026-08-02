import os
import smtplib
from datetime import datetime, timezone
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Optional
from uuid import UUID

from dotenv import load_dotenv
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.security import require_api_key
from app.core.utils import get_pagination, paginated_response
from app.database.db import get_db
from app.models.alerte import Alerte
from app.models.capteur import Capteur
from app.models.entrepot import Entrepot
from app.models.lot import Lot
from app.models.mesure import Mesure

load_dotenv()

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


def send_real_email(to_email: str, subject: str, body: str) -> bool:
    """Se connecte au serveur SMTP et envoie un e-mail d'alerte."""
    smtp_server = os.getenv("SMTP_SERVER")
    smtp_port = os.getenv("SMTP_PORT")
    smtp_username = os.getenv("SMTP_USERNAME")
    smtp_password = os.getenv("SMTP_PASSWORD")

    if not smtp_server or not smtp_port or not smtp_username or not smtp_password:
        print("SMTP non configuré, envoi d'e-mail ignoré.")
        return False

    try:
        msg = MIMEMultipart()
        msg["From"] = smtp_username
        msg["To"] = to_email
        msg["Subject"] = subject
        msg.attach(MIMEText(body, "plain"))

        server = smtplib.SMTP(smtp_server, int(smtp_port))
        server.starttls()
        server.login(smtp_username, smtp_password)
        server.sendmail(smtp_username, to_email, msg.as_string())
        server.quit()
        print(f"E-mail envoyé avec succès à {to_email}")
        return True
    except Exception as e:
        print(f"Échec de l'envoi de l'e-mail : {e}")
        return False


def creer_alerte(
    db: Session,
    *,
    entrepot: Entrepot,
    capteur: Capteur,
    lot: Optional[Lot],
    type_alerte: str,
    niveau: str,
    message: str,
    valeur_detectee: float,
    seuil_minimum: Optional[float],
    seuil_maximum: Optional[float],
) -> None:
    """Crée une alerte et tente l'envoi de l'e-mail au responsable."""
    sujet = f"ALERTE {niveau} - {type_alerte} : {entrepot.nom}"
    corps = (
        f"Bonjour {entrepot.nom_responsable},\n\n"
        f"Le capteur {capteur.reference} a détecté une anomalie "
        f"dans l'entrepôt {entrepot.nom} ({entrepot.ville}).\n\n"
        f"Détails : {message}\n"
        f"Valeur détectée : {valeur_detectee}\n"
        f"Seuils : min={seuil_minimum}, max={seuil_maximum}\n\n"
        f"Cordialement,\nL'équipe FutureKawa."
    )
    email_envoye = send_real_email(
        to_email=entrepot.email_responsable,
        subject=sujet,
        body=corps,
    )

    db.add(
        Alerte(
            entrepot_id=entrepot.id,
            lot_id=lot.id if lot else None,
            capteur_id=capteur.id,
            type_alerte=type_alerte,
            niveau=niveau,
            statut="ACTIVE",
            message=message,
            valeur_detectee=valeur_detectee,
            seuil_minimum=seuil_minimum,
            seuil_maximum=seuil_maximum,
            email_envoye=email_envoye,
            date_email=datetime.now(timezone.utc) if email_envoye else None,
        )
    )


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

    # 6. Détection d'anomalies par rapport aux seuils de l'entrepôt
    temperature = float(mesure.temperature_c)
    humidite = float(mesure.humidite_pct)
    t_min, t_max = float(entrepot.temperature_min_c), float(entrepot.temperature_max_c)
    h_min, h_max = float(entrepot.humidite_min_pct), float(entrepot.humidite_max_pct)

    if temperature > t_max:
        creer_alerte(
            db,
            entrepot=entrepot,
            capteur=capteur,
            lot=lot,
            type_alerte="TEMPERATURE_ELEVEE",
            niveau="ELEVE",
            message=(
                f"Température critique : {temperature}°C mesurés "
                f"(Seuil max : {t_max}°C)."
            ),
            valeur_detectee=temperature,
            seuil_minimum=t_min,
            seuil_maximum=t_max,
        )
    elif temperature < t_min:
        creer_alerte(
            db,
            entrepot=entrepot,
            capteur=capteur,
            lot=lot,
            type_alerte="TEMPERATURE_BASSE",
            niveau="MOYEN",
            message=(
                f"Température trop basse : {temperature}°C mesurés "
                f"(Seuil min : {t_min}°C)."
            ),
            valeur_detectee=temperature,
            seuil_minimum=t_min,
            seuil_maximum=t_max,
        )

    if humidite > h_max:
        creer_alerte(
            db,
            entrepot=entrepot,
            capteur=capteur,
            lot=lot,
            type_alerte="HUMIDITE_ELEVEE",
            niveau="ELEVE",
            message=(
                f"Humidité critique : {humidite}% mesurés "
                f"(Seuil max : {h_max}%)."
            ),
            valeur_detectee=humidite,
            seuil_minimum=h_min,
            seuil_maximum=h_max,
        )
    elif humidite < h_min:
        creer_alerte(
            db,
            entrepot=entrepot,
            capteur=capteur,
            lot=lot,
            type_alerte="HUMIDITE_BASSE",
            niveau="MOYEN",
            message=(
                f"Humidité trop basse : {humidite}% mesurés "
                f"(Seuil min : {h_min}%)."
            ),
            valeur_detectee=humidite,
            seuil_minimum=h_min,
            seuil_maximum=h_max,
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
