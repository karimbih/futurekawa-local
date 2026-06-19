from sqlalchemy import Column, Integer, String, Float, DateTime
from app.database.db import Base
from datetime import datetime

class Entrepot(Base):
    __tablename__ = "entrepots"

    id = Column(Integer, primary_key=True)
    nom = Column(String(100))
    ville = Column(String(100))
    code_pays = Column(String(10))

    nom_responsable = Column(String(100))
    email_responsable = Column(String(255))

    target_temp_c = Column(Float)
    target_humidity_pct = Column(Float)

    cree_le = Column(DateTime, default=datetime.utcnow)
    mis_a_jour_le = Column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow
    )