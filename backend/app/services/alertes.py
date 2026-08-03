"""Dispositif d'alerte local.

Règles métier (cf. cahier des charges, §III.4) :
  1. Conditions non idéales : température/humidité hors bande acceptable du pays
     (cible ± tolérance : Brésil 29±3 °C / 55±2 %, Équateur 31±3 °C / 60±2 %,
      Colombie 26±3 °C / 80±2 %).
  2. Lot trop ancien : lot dépassant 365 jours de stockage.
En cas d'alerte, un e-mail est envoyé au responsable d'exploitation du pays concerné.
"""

import asyncio
import os
import smtplib
from datetime import datetime, timedelta, timezone
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Optional

from dotenv import load_dotenv
from sqlalchemy.orm import Session

from app.database.db import SessionLocal
from app.models.alerte import Alerte
from app.models.capteur import Capteur
from app.models.entrepot import Entrepot
from app.models.lot import Lot
from app.models.pays import Pays

load_dotenv()


# ---------------- Envoi d'e-mail ----------------

def send_real_email(to_email: str, subject: str, body: str) -> bool:
    """Se connecte au serveur SMTP et envoie un e-mail d'alerte.

    Compatible MailHog (démo locale, sans STARTTLS ni authentification)
    et un vrai serveur SMTP (STARTTLS + login si identifiants fournis).
    """
    smtp_server = os.getenv("SMTP_SERVER")
    smtp_port = os.getenv("SMTP_PORT")
    smtp_username = os.getenv("SMTP_USERNAME")
    smtp_password = os.getenv("SMTP_PASSWORD")
    smtp_from = os.getenv("SMTP_FROM", "noreply@futurekawa.com")

    if not smtp_server or not smtp_port:
        print("SMTP non configuré (SMTP_SERVER/SMTP_PORT manquants), envoi d'e-mail ignoré.")
        return False
    if not smtp_username or not smtp_password:
        print("Identifiants SMTP manquants (SMTP_USERNAME/SMTP_PASSWORD), envoi d'e-mail ignoré.")
        return False

    try:
        msg = MIMEMultipart()
        msg["From"] = smtp_from
        msg["To"] = to_email
        msg["Subject"] = subject
        msg.attach(MIMEText(body, "plain"))

        server = smtplib.SMTP(smtp_server, int(smtp_port))
        try:
            server.starttls()
        except Exception:
            # Serveur sans STARTTLS (ex: relais SMTP locaux)
            pass
        server.login(smtp_username, smtp_password)
        server.sendmail(smtp_from, to_email, msg.as_string())
        server.quit()
        print(f"E-mail envoyé avec succès à {to_email}")
        return True
    except Exception as e:
        print(f"Échec de l'envoi de l'e-mail : {e}")
        return False


# ---------------- Configuration pays ----------------

def get_pays_config(db: Session, code_pays: str) -> Optional[Pays]:
    return db.query(Pays).filter(Pays.code_iso == code_pays).first()


def get_bande_pays(db: Session, code_pays: str) -> Optional[dict]:
    """Bande idéale du pays : cible ± tolérance. None si non configuré."""
    pays = get_pays_config(db, code_pays)
    if not pays:
        return None
    return {
        "t_min": float(pays.temperature_cible_c - pays.tolerance_temperature_c),
        "t_max": float(pays.temperature_cible_c + pays.tolerance_temperature_c),
        "h_min": float(pays.humidite_cible_pct - pays.tolerance_humidite_pct),
        "h_max": float(pays.humidite_cible_pct + pays.tolerance_humidite_pct),
    }


def _destinataire_alerte(db: Session, entrepot: Entrepot) -> tuple[str, str]:
    """Destinataire prioritaire : responsable d'exploitation du pays (PDF §III.4),
    repli sur le responsable d'entrepôt si la config pays est absente."""
    pays = get_pays_config(db, entrepot.code_pays)
    if pays:
        return pays.responsable_exploitation_email, pays.responsable_exploitation_nom
    return entrepot.email_responsable, entrepot.nom_responsable


# ---------------- Création d'une alerte ----------------

def creer_alerte(
    db: Session,
    *,
    entrepot: Entrepot,
    capteur: Optional[Capteur],
    lot: Optional[Lot],
    type_alerte: str,
    niveau: str,
    message: str,
    valeur_detectee: Optional[float],
    seuil_minimum: Optional[float],
    seuil_maximum: Optional[float],
) -> None:
    """Crée une alerte et tente l'envoi de l'e-mail au responsable d'exploitation."""
    destinataire, nom_destinataire = _destinataire_alerte(db, entrepot)

    sujet = f"ALERTE {niveau} - {type_alerte} : {entrepot.nom}"
    corps = (
        f"Bonjour {nom_destinataire},\n\n"
        f"Une anomalie a été détectée dans l'entrepôt {entrepot.nom} "
        f"({entrepot.ville}, {entrepot.code_pays}).\n\n"
        f"Détails : {message}\n"
        f"Valeur détectée : {valeur_detectee}\n"
        f"Seuils : min={seuil_minimum}, max={seuil_maximum}\n\n"
        f"Cordialement,\nL'équipe FutureKawa."
    )
    email_envoye = send_real_email(
        to_email=destinataire,
        subject=sujet,
        body=corps,
    )

    db.add(
        Alerte(
            entrepot_id=entrepot.id,
            lot_id=lot.id if lot else None,
            capteur_id=capteur.id if capteur else None,
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


def detecter_anomalies_conditions(
    db: Session,
    *,
    entrepot: Entrepot,
    capteur: Capteur,
    lot: Optional[Lot],
    temperature: float,
    humidite: float,
) -> None:
    """Vérifie temp/humidité par rapport à la bande idéale du PAYS (cible ± tolérance).

    Repli sur la bande de l'entrepôt si aucune config pays n'est enregistrée.
    """
    bande = get_bande_pays(db, entrepot.code_pays)
    if bande is None:
        t_min, t_max = float(entrepot.temperature_min_c), float(entrepot.temperature_max_c)
        h_min, h_max = float(entrepot.humidite_min_pct), float(entrepot.humidite_max_pct)
        reference = f"bande de l'entrepôt"
    else:
        t_min, t_max = bande["t_min"], bande["t_max"]
        h_min, h_max = bande["h_min"], bande["h_max"]
        reference = f"bande idéale du pays {entrepot.code_pays}"

    if temperature > t_max:
        creer_alerte(
            db,
            entrepot=entrepot,
            capteur=capteur,
            lot=lot,
            type_alerte="TEMPERATURE_ELEVEE",
            niveau="ELEVE",
            message=(
                f"Température hors {reference} : {temperature}°C mesurés "
                f"(Bande : {t_min}–{t_max}°C)."
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
                f"Température sous {reference} : {temperature}°C mesurés "
                f"(Bande : {t_min}–{t_max}°C)."
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
                f"Humidité hors {reference} : {humidite}% mesurés "
                f"(Bande : {h_min}–{h_max}%)."
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
                f"Humidité sous {reference} : {humidite}% mesurés "
                f"(Bande : {h_min}–{h_max}%)."
            ),
            valeur_detectee=humidite,
            seuil_minimum=h_min,
            seuil_maximum=h_max,
        )


# ---------------- Lots trop anciens (> 365 jours) ----------------

def verifier_lots_anciens(db: Session) -> int:
    """Crée une alerte LOT_TROP_ANCIEN pour chaque lot > 365 jours de stockage.

    Idempotent : un lot déjà sous alerte ACTIVE / PRISE_EN_COMPTE est ignoré.
    Un lot EN_STOCK trop ancien passe au statut PERIME.
    Retourne le nombre d'alertes créées.
    """
    seuil_date = datetime.now(timezone.utc).date() - timedelta(days=365)
    lots = (
        db.query(Lot)
        .filter(
            Lot.date_stockage <= seuil_date,
            Lot.statut.in_(["EN_STOCK", "EN_ALERTE"]),
        )
        .all()
    )

    crees = 0
    maintenant = datetime.now(timezone.utc)
    for lot in lots:
        existante = (
            db.query(Alerte)
            .filter(
                Alerte.lot_id == lot.id,
                Alerte.type_alerte == "LOT_TROP_ANCIEN",
                Alerte.statut.in_(["ACTIVE", "PRISE_EN_COMPTE"]),
            )
            .first()
        )
        if existante:
            continue

        entrepot = db.get(Entrepot, lot.entrepot_id)
        if not entrepot:
            continue

        jours = (maintenant.date() - lot.date_stockage).days
        destinataire, nom_destinataire = _destinataire_alerte(db, entrepot)

        sujet = f"ALERTE MOYEN - LOT_TROP_ANCIEN : {lot.code_lot}"
        corps = (
            f"Bonjour {nom_destinataire},\n\n"
            f"Le lot {lot.code_lot} ({lot.produit}) stocké dans l'entrepôt "
            f"{entrepot.nom} ({entrepot.ville}) depuis le {lot.date_stockage} dépasse "
            f"1 an de stockage ({jours} jours).\n\n"
            f"Rappel : un lot au-delà de 365 jours de stockage doit être contrôlé "
            f"avant expédition (rotation FIFO).\n\n"
            f"Cordialement,\nL'équipe FutureKawa."
        )
        email_envoye = send_real_email(
            to_email=destinataire,
            subject=sujet,
            body=corps,
        )

        db.add(
            Alerte(
                entrepot_id=lot.entrepot_id,
                lot_id=lot.id,
                capteur_id=None,
                type_alerte="LOT_TROP_ANCIEN",
                niveau="MOYEN",
                statut="ACTIVE",
                message=(
                    f"Lot stocké depuis {jours} jours ({lot.date_stockage}), "
                    f"seuil de 365 jours dépassé."
                ),
                valeur_detectee=jours,
                seuil_minimum=365,
                seuil_maximum=None,
                email_envoye=email_envoye,
                date_email=maintenant if email_envoye else None,
            )
        )
        if lot.statut == "EN_STOCK":
            lot.statut = "PERIME"

        crees += 1
    return crees


def run_verification_lots_anciens() -> None:
    db = SessionLocal()
    try:
        n = verifier_lots_anciens(db)
        db.commit()
        if n:
            print(f"Alertes LOT_TROP_ANCIEN créées : {n}")
    except Exception as e:
        db.rollback()
        print(f"Erreur lors de la vérification des lots anciens : {e}")
    finally:
        db.close()


async def boucle_verification_lots_anciens() -> None:
    """Surveillance périodique des lots trop anciens (démarrée au lancement de l'API)."""
    intervalle = int(os.getenv("ALERTE_LOTS_INTERVAL_SECONDS", "3600"))
    print(f"Surveillance des lots anciens démarrée (toutes les {intervalle}s).")
    while True:
        await asyncio.sleep(intervalle)
        try:
            await asyncio.to_thread(run_verification_lots_anciens)
        except Exception as e:
            print(f"Erreur dans la boucle de surveillance des lots anciens : {e}")
