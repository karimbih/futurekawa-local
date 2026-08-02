-- =============================================================
-- FutureKawa - Initialisation du schéma (jeu de données de démo)
-- =============================================================
-- Ce script ne s'exécute QUE sur un volume Postgres vierge
-- (dossier /docker-entrypoint-initdb.d).
-- Le schéma reflète les modèles SQLAlchemy dans backend/app/models
-- (source de vérité pour l'API au runtime : Base.metadata.create_all).
-- =============================================================

CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- ---------- entrepots ----------
CREATE TABLE IF NOT EXISTS entrepots (
    id                   UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    nom                  VARCHAR(150) NOT NULL,
    ville                VARCHAR(150) NOT NULL,
    code_pays            VARCHAR(3)   NOT NULL,
    nom_responsable      VARCHAR(150) NOT NULL,
    email_responsable    VARCHAR(255) NOT NULL,
    temperature_min_c    NUMERIC(5,2) NOT NULL,
    temperature_max_c    NUMERIC(5,2) NOT NULL,
    humidite_min_pct     NUMERIC(5,2) NOT NULL,
    humidite_max_pct     NUMERIC(5,2) NOT NULL,
    cree_le              TIMESTAMPTZ  NOT NULL DEFAULT now(),
    mis_a_jour_le        TIMESTAMPTZ  NOT NULL DEFAULT now()
);

-- ---------- capteurs ----------
CREATE TABLE IF NOT EXISTS capteurs (
    id                        UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    entrepot_id               UUID NOT NULL REFERENCES entrepots(id) ON DELETE CASCADE,
    reference                 VARCHAR(100) NOT NULL UNIQUE,
    topic_mqtt                VARCHAR(255) NOT NULL,
    type_capteur              VARCHAR(100) NOT NULL,
    statut                    VARCHAR(30)  NOT NULL DEFAULT 'ACTIF',
    frequence_mesure_secondes INTEGER NOT NULL,
    derniere_communication    TIMESTAMPTZ,
    cree_le                   TIMESTAMPTZ NOT NULL DEFAULT now(),
    mis_a_jour_le             TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS ix_capteurs_entrepot_id ON capteurs(entrepot_id);

-- ---------- lots ----------
CREATE TABLE IF NOT EXISTS lots (
    id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    code_lot      VARCHAR(100) NOT NULL UNIQUE,
    entrepot_id   UUID NOT NULL REFERENCES entrepots(id) ON DELETE CASCADE,
    produit       VARCHAR(150) NOT NULL,
    quantite_kg   NUMERIC(12,2) NOT NULL,
    date_stockage DATE NOT NULL,
    statut        VARCHAR(30) NOT NULL DEFAULT 'EN_STOCK',
    cree_le       TIMESTAMPTZ NOT NULL DEFAULT now(),
    mis_a_jour_le TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS ix_lots_entrepot_id ON lots(entrepot_id);

-- ---------- mesures ----------
CREATE TABLE IF NOT EXISTS mesures (
    id             UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    entrepot_id    UUID NOT NULL REFERENCES entrepots(id) ON DELETE CASCADE,
    capteur_id     UUID NOT NULL REFERENCES capteurs(id) ON DELETE CASCADE,
    lot_id         UUID REFERENCES lots(id) ON DELETE SET NULL,
    source         VARCHAR(30) NOT NULL DEFAULT 'MQTT',
    topic_mqtt     VARCHAR(255) NOT NULL,
    date_mesure    TIMESTAMPTZ NOT NULL,
    date_reception TIMESTAMPTZ NOT NULL DEFAULT now(),
    temperature_c  NUMERIC(5,2) NOT NULL,
    humidite_pct   NUMERIC(5,2) NOT NULL,
    donnees_brutes JSONB,
    cree_le        TIMESTAMPTZ NOT NULL DEFAULT now(),
    mis_a_jour_le  TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS ix_mesures_entrepot_id ON mesures(entrepot_id);
CREATE INDEX IF NOT EXISTS ix_mesures_capteur_id  ON mesures(capteur_id);
CREATE INDEX IF NOT EXISTS ix_mesures_lot_id      ON mesures(lot_id);

-- ---------- alertes ----------
CREATE TABLE IF NOT EXISTS alertes (
    id                     UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    entrepot_id            UUID NOT NULL REFERENCES entrepots(id) ON DELETE CASCADE,
    lot_id                 UUID REFERENCES lots(id) ON DELETE SET NULL,
    capteur_id             UUID REFERENCES capteurs(id) ON DELETE SET NULL,
    type_alerte            VARCHAR(50) NOT NULL,
    niveau                 VARCHAR(20) NOT NULL DEFAULT 'MOYEN',
    statut                 VARCHAR(30) NOT NULL DEFAULT 'ACTIVE',
    message                TEXT NOT NULL,
    valeur_detectee        NUMERIC(10,2),
    seuil_minimum          NUMERIC(10,2),
    seuil_maximum          NUMERIC(10,2),
    date_declenchement     TIMESTAMPTZ NOT NULL DEFAULT now(),
    date_resolution        TIMESTAMPTZ,
    resolue_par            UUID,
    commentaire_resolution TEXT,
    email_envoye           BOOLEAN NOT NULL DEFAULT FALSE,
    date_email             TIMESTAMPTZ,
    cree_le                TIMESTAMPTZ NOT NULL DEFAULT now(),
    mis_a_jour_le          TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS ix_alertes_entrepot_id ON alertes(entrepot_id);
CREATE INDEX IF NOT EXISTS ix_alertes_capteur_id  ON alertes(capteur_id);
CREATE INDEX IF NOT EXISTS ix_alertes_lot_id      ON alertes(lot_id);

-- =============================================================
-- Jeu de données de démonstration
-- =============================================================
INSERT INTO entrepots (id, nom, ville, code_pays, nom_responsable, email_responsable,
                       temperature_min_c, temperature_max_c, humidite_min_pct, humidite_max_pct)
VALUES
    ('11111111-1111-1111-1111-111111111111', 'Entrepôt São Paulo', 'São Paulo', 'BRA',
     'Maria Silva', 'maria.silva@example.com', 18.0, 24.0, 40.0, 70.0),
    ('22222222-2222-2222-2222-222222222222', 'Entrepôt Ho Chi Minh', 'Hô-Chi-Minh-Ville', 'VNM',
     'Nguyen An', 'nguyen.an@example.com', 16.0, 22.0, 35.0, 65.0)
ON CONFLICT (id) DO NOTHING;

INSERT INTO capteurs (id, entrepot_id, reference, topic_mqtt, type_capteur, statut, frequence_mesure_secondes)
VALUES
    ('aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa', '11111111-1111-1111-1111-111111111111',
     'ESP32-DHT22-001', 'futurekawa/bra/esp32-dht22-001', 'TEMPERATURE_HUMIDITE', 'ACTIF', 60),
    ('bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb', '22222222-2222-2222-2222-222222222222',
     'ESP32-DHT22-002', 'futurekawa/vnm/esp32-dht22-002', 'TEMPERATURE_HUMIDITE', 'ACTIF', 30)
ON CONFLICT (id) DO NOTHING;

INSERT INTO lots (id, code_lot, entrepot_id, produit, quantite_kg, date_stockage, statut)
VALUES
    ('cccccccc-cccc-cccc-cccc-cccccccccccc', 'BRA-2026-001', '11111111-1111-1111-1111-111111111111',
     'Café Arabica - Grain vert', 12000.00, '2026-07-01', 'EN_STOCK'),
    ('dddddddd-dddd-dddd-dddd-dddddddddddd', 'VNM-2026-002', '22222222-2222-2222-2222-222222222222',
     'Café Robusta - Grain vert', 8500.50, '2026-07-15', 'EN_STOCK')
ON CONFLICT (id) DO NOTHING;
