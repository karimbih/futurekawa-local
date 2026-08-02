from sqlalchemy import Column, DateTime, ForeignKey, Numeric, String, Uuid, func
from sqlalchemy.dialects.postgresql import JSONB

from app.database.db import Base
from app.models.base import UUIDTimestampMixin


class Mesure(UUIDTimestampMixin, Base):
    __tablename__ = "mesures"

    entrepot_id = Column(
        Uuid(as_uuid=True),
        ForeignKey("entrepots.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    capteur_id = Column(
        Uuid(as_uuid=True),
        ForeignKey("capteurs.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    lot_id = Column(
        Uuid(as_uuid=True),
        ForeignKey("lots.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    source = Column(String(30), nullable=False, default="MQTT")
    topic_mqtt = Column(String(255), nullable=False)
    date_mesure = Column(DateTime(timezone=True), nullable=False)
    date_reception = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    temperature_c = Column(Numeric(5, 2), nullable=False)
    humidite_pct = Column(Numeric(5, 2), nullable=False)
    donnees_brutes = Column(JSONB, nullable=True)
