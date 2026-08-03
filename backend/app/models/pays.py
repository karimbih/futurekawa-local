from sqlalchemy import Column, Numeric, String

from app.database.db import Base
from app.models.base import UUIDTimestampMixin


class Pays(UUIDTimestampMixin, Base):
    """Configuration locale du pays : conditions idéales de conservation
    (cible ± tolérance, cf. cahier des charges) + contact responsable d'exploitation
    destinataire des e-mails d'alerte."""

    __tablename__ = "pays"

    code_iso = Column(String(3), unique=True, nullable=False)
    nom = Column(String(100), nullable=False)
    temperature_cible_c = Column(Numeric(5, 2), nullable=False)
    humidite_cible_pct = Column(Numeric(5, 2), nullable=False)
    tolerance_temperature_c = Column(Numeric(5, 2), nullable=False)
    tolerance_humidite_pct = Column(Numeric(5, 2), nullable=False)
    responsable_exploitation_nom = Column(String(150), nullable=False)
    responsable_exploitation_email = Column(String(255), nullable=False)
