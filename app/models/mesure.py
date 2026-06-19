from sqlalchemy import *
from app.database.db import Base

class Mesure(Base):
    __tablename__ = "mesures"

    id = Column(Integer, primary_key=True)

    entrepot_id = Column(
        Integer,
        ForeignKey("entrepots.id")
    )

    lot_id = Column(
        Integer,
        ForeignKey("lots.id")
    )

    source = Column(String(50))

    date_mesure = Column(DateTime)

    temperature_c = Column(Float)

    humidite_pct = Column(Float)

    cree_le = Column(DateTime)