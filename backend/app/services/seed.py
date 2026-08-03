"""Initialisation de la configuration pays locale (conditions idéales + contact)."""

from sqlalchemy.orm import Session

from app.models.pays import Pays

# Conditions idéales de conservation du café vert (cahier des charges) :
#   Brésil 29°C / 55% · Équateur 31°C / 60% · Colombie 26°C / 80%
# Tolérance acceptable : ±3 °C et ±2 %.
PAYS_DEFAULTS = [
    {
        "code_iso": "BRA",
        "nom": "Brésil",
        "temperature_cible_c": 29.0,
        "humidite_cible_pct": 55.0,
        "tolerance_temperature_c": 3.0,
        "tolerance_humidite_pct": 2.0,
        "responsable_exploitation_nom": "Ana Oliveira",
        "responsable_exploitation_email": "responsable.exploitation.bra@example.com",
    },
    {
        "code_iso": "ECU",
        "nom": "Équateur",
        "temperature_cible_c": 31.0,
        "humidite_cible_pct": 60.0,
        "tolerance_temperature_c": 3.0,
        "tolerance_humidite_pct": 2.0,
        "responsable_exploitation_nom": "Carlos Mendoza",
        "responsable_exploitation_email": "responsable.exploitation.ecu@example.com",
    },
    {
        "code_iso": "COL",
        "nom": "Colombie",
        "temperature_cible_c": 26.0,
        "humidite_cible_pct": 80.0,
        "tolerance_temperature_c": 3.0,
        "tolerance_humidite_pct": 2.0,
        "responsable_exploitation_nom": "Laura Gómez",
        "responsable_exploitation_email": "responsable.exploitation.col@example.com",
    },
]


def seed_pays(db: Session) -> None:
    """Insère les configurations pays par défaut si la table est vide."""
    if db.query(Pays).count() > 0:
        return
    for valeurs in PAYS_DEFAULTS:
        db.add(Pays(**valeurs))
    db.commit()
    print(f"Table 'pays' initialisée avec {len(PAYS_DEFAULTS)} configurations.")
