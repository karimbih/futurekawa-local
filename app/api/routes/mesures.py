import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional
from app.database.db import get_db
from app.models.mesure import Mesure
from app.models.entrepot import Entrepot
from app.models.alerte import Alerte
from dotenv import load_dotenv

load_dotenv()

router = APIRouter(prefix="/mesures", tags=["Mesures"])

class MesureCreate(BaseModel):
    entrepot_id: int
    lot_id: Optional[int] = None
    source: str
    temperature_c: float
    humidite_pct: float

# --- FONCTION D'ENVOI DE MAIL EN PRODUCTION ---
def send_real_email(to_email: str, subject: str, body: str) -> bool:
    """Se connecte au serveur SMTP et envoie un vrai e-mail"""
    smtp_server = os.getenv("SMTP_SERVER")
    smtp_port = int(os.getenv("SMTP_PORT"))
    smtp_username = os.getenv("SMTP_USERNAME")
    smtp_password = os.getenv("SMTP_PASSWORD")

    if not smtp_username or not smtp_password:
        print("❌ Erreur Production : Identifiants SMTP manquants dans l'environnement.")
        return False

    try:
        msg = MIMEMultipart()
        msg['From'] = smtp_username
        msg['To'] = to_email
        msg['Subject'] = subject
        msg.attach(MIMEText(body, 'plain'))

        # Connexion sécurisée TLS
        server = smtplib.SMTP(smtp_server, smtp_port)
        server.starttls()
        server.login(smtp_username, smtp_password)
        server.sendmail(smtp_username, to_email, msg.as_string())
        server.quit()
        
        print(f"✅ E-mail envoyé avec succès à {to_email}")
        return True
    except Exception as e:
        print(f"❌ Échec de l'envoi de l'e-mail : {str(e)}")
        return False


@router.post("/", status_code=status.HTTP_201_CREATED)
def receive_mesure(mesure: MesureCreate, db: Session = Depends(get_db)):
    # 1. Vérifier si l'entrepôt existe pour récupérer ses seuils cibles
    entrepot = db.query(Entrepot).filter(Entrepot.id == mesure.entrepot_id).first()
    if not entrepot:
        raise HTTPException(status_code=404, detail="Entrepôt introuvable")
        
    # 2. Sauvegarder la mesure IoT en base PostgreSQL
    db_mesure = Mesure(**mesure.dict())
    db.add(db_mesure)
    db.commit()
    db.refresh(db_mesure)
    
    # 3. Logique de détection d'anomalie (Seuils climatiques)
    if db_mesure.temperature_c > entrepot.target_temp_c:
        
        # Préparation du contenu de l'e-mail avec tes variables d'entrepôt
        sujet_mail = f"⚠️ ALERTE CRITIQUE - Température hors norme : {entrepot.nom}"
        corps_mail = (
            f"Bonjour {entrepot.nom_responsable},\n\n"
            f"Le système a détecté une anomalie thermique dans votre entrepôt {entrepot.nom} ({entrepot.ville}).\n\n"
            f"Détails de l'incident :\n"
            f"- Température enregistrée : {db_mesure.temperature_c}°C\n"
            f"- Seuil maximal autorisé : {entrepot.target_temp_c}°C\n\n"
            f"Veuillez agir au plus vite.\n"
            f"Cordialement,\nL'équipe FutureKahwa."
        )
        
        # Envoi effectif de l'e-mail au responsable
        email_envoye = send_real_email(
            to_email=entrepot.email_responsable, 
            subject=sujet_mail, 
            body=corps_mail
        )
        
        # Création de l'alerte en BDD avec le vrai statut de l'envoi du mail
        nouvelle_alerte = Alerte(
            entrepot_id=entrepot.id,
            lot_id=mesure.lot_id,
            mesure_id=db_mesure.id,
            type_alerte="CLIMAT_HORS_NORME",
            message=f"Température critique : {db_mesure.temperature_c}°C mesurés (Seuil max : {entrepot.target_temp_c}°C).",
            statut="Active",
            email_status="SENT" if email_envoye else "FAILED"
        )
        db.add(nouvelle_alerte)
        db.commit()

    return {"status": "Mesure traitée", "mesure_id": db_mesure.id}


@router.get("/")
def list_mesures(db: Session = Depends(get_db)):
    return db.query(Mesure).order_by(Mesure.date_mesure.desc()).all()