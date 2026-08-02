from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Uuid

from app.database.db import Base
from app.models.base import UUIDTimestampMixin


class Capteur(UUIDTimestampMixin, Base):
    __tablename__ = "capteurs"

    entrepot_id = Column(
        Uuid(as_uuid=True),
        ForeignKey("entrepots.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    reference = Column(String(100), unique=True, nullable=False)
    topic_mqtt = Column(String(255), nullable=False)
    type_capteur = Column(String(100), nullable=False)
    statut = Column(String(30), nullable=False, default="ACTIF")
    frequence_mesure_secondes = Column(Integer, nullable=False)
    derniere_communication = Column(DateTime(timezone=True), nullable=True)
