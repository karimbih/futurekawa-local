from uuid import uuid4

from sqlalchemy import Column, DateTime, Uuid, func

from app.database.db import Base


class UUIDTimestampMixin:
    """Identifiant UUID généré localement + horodatage UTC pour la synchro."""

    id = Column(Uuid(as_uuid=True), primary_key=True, default=uuid4)

    cree_le = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    mis_a_jour_le = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )
