from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Numeric, String, Text, Uuid, func

from app.database.db import Base
from app.models.base import UUIDTimestampMixin


class Alerte(UUIDTimestampMixin, Base):
    __tablename__ = "alertes"

    entrepot_id = Column(
        Uuid(as_uuid=True),
        ForeignKey("entrepots.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    lot_id = Column(
        Uuid(as_uuid=True),
        ForeignKey("lots.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    capteur_id = Column(
        Uuid(as_uuid=True),
        ForeignKey("capteurs.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    type_alerte = Column(String(50), nullable=False)
    niveau = Column(String(20), nullable=False, default="MOYEN")
    statut = Column(String(30), nullable=False, default="ACTIVE")
    message = Column(Text, nullable=False)
    valeur_detectee = Column(Numeric(10, 2), nullable=True)
    seuil_minimum = Column(Numeric(10, 2), nullable=True)
    seuil_maximum = Column(Numeric(10, 2), nullable=True)
    date_declenchement = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    date_resolution = Column(DateTime(timezone=True), nullable=True)
    resolue_par = Column(Uuid(as_uuid=True), nullable=True)
    commentaire_resolution = Column(Text, nullable=True)
    email_envoye = Column(Boolean, nullable=False, default=False)
    date_email = Column(DateTime(timezone=True), nullable=True)
