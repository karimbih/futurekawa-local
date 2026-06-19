from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey
from datetime import datetime
from app.database.db import Base

class Alerte(Base):
    __tablename__ = "alertes"

    id = Column(Integer, primary_key=True, autoincrement=True, index=True)

    # Clés étrangères (avec comportement de suppression en cascade si nécessaire)
    entrepot_id = Column(Integer, ForeignKey("entrepots.id", ondelete="CASCADE"), nullable=False)
    lot_id = Column(Integer, ForeignKey("lots.id", ondelete="SET NULL"), nullable=True)
    mesure_id = Column(Integer, ForeignKey("mesures.id", ondelete="SET NULL"), nullable=True)

    type_alerte = Column(String(50), nullable=False)
    message = Column(Text, nullable=False)
    statut = Column(String(30), default="Active")

    # Champs de suivi pour l'envoi d'emails (exigence du projet)
    email_status = Column(String(30), default="PENDING")
    email_error_message = Column(Text, nullable=True)

    # Remplissage automatique de la date au moment du déclenchement
    declenchee_le = Column(DateTime, default=datetime.utcnow)
    resolue_le = Column(DateTime, nullable=True)