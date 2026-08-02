from sqlalchemy import Column, Date, ForeignKey, Numeric, String, Uuid

from app.database.db import Base
from app.models.base import UUIDTimestampMixin


class Lot(UUIDTimestampMixin, Base):
    __tablename__ = "lots"

    code_lot = Column(String(100), unique=True, nullable=False)
    entrepot_id = Column(
        Uuid(as_uuid=True),
        ForeignKey("entrepots.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    produit = Column(String(150), nullable=False)
    quantite_kg = Column(Numeric(12, 2), nullable=False)
    date_stockage = Column(Date, nullable=False)
    statut = Column(String(30), nullable=False, default="EN_STOCK")
