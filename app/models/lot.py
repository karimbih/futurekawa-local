from sqlalchemy import *
from app.database.db import Base

class Lot(Base):
    __tablename__ = "lots"

    id = Column(Integer, primary_key=True)

    code_lot = Column(String(100), unique=True)

    entrepot_id = Column(
        Integer,
        ForeignKey("entrepots.id")
    )

    date_stockage = Column(Date)

    statut = Column(String(50))

    cree_le = Column(DateTime)
    mis_a_jour_le = Column(DateTime)