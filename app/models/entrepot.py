from sqlalchemy import Column, Numeric, String

from app.database.db import Base
from app.models.base import UUIDTimestampMixin


class Entrepot(UUIDTimestampMixin, Base):
    __tablename__ = "entrepots"

    nom = Column(String(150), nullable=False)
    ville = Column(String(150), nullable=False)
    code_pays = Column(String(3), nullable=False)
    nom_responsable = Column(String(150), nullable=False)
    email_responsable = Column(String(255), nullable=False)

    temperature_min_c = Column(Numeric(5, 2), nullable=False)
    temperature_max_c = Column(Numeric(5, 2), nullable=False)
    humidite_min_pct = Column(Numeric(5, 2), nullable=False)
    humidite_max_pct = Column(Numeric(5, 2), nullable=False)
