# FutureKawa - Backend local par pays

Backend FastAPI d'un pays, qui alimente le backend central avec les données
d'entrepôts, capteurs, lots, mesures et alertes. L'infrastructure locale tourne
entièrement sous Docker Compose.

## Services (`compose.yaml`)

| Service  | Rôle                                           | Ports hôte            |
| -------- | ---------------------------------------------- | --------------------- |
| api      | Backend FastAPI du pays                         | 8000:8000             |
| postgres | Base PostgreSQL locale                          | 5432:5432 (dev)       |
| mosquitto| Broker MQTT pour les ESP32                      | 1883:1883             |
| nodered  | Visualisation IoT optionnelle                   | 1880:1880             |

## Démarrage

```bash
cp .env.example .env      # si .env absent, adapter les valeurs
docker compose up -d --build
```

- API : http://localhost:8000  (docs : http://localhost:8000/docs)
- Node-RED : http://localhost:1880  (dashboard : http://localhost:1880/ui)
- MQTT broker : localhost:1883

Arrêt : `docker compose down`

## Structure

```
├── compose.yaml
├── .env.example
├── backend/
│   ├── Dockerfile
│   ├── requirements.txt
│   ├── main.py
│   └── app/                 # modèles SQLAlchemy + routes FastAPI
├── mosquitto/
│   └── mosquitto.conf
├── node-red/
│   ├── start.sh              # installe les dépendances puis démarre Node-RED
│   └── data/                 # flows.json + settings.js versionnés (portable)
└── database/
    └── init/                 # schéma + seed (volume Postgres vierge uniquement)
```

## API

Toutes les routes nécessitent l'en-tête `X-API-Key` (variable `API_KEY`).

Ressources : `entrepots`, `capteurs`, `lots`, `mesures`, `alertes`.

Chaque liste accepte un filtre de synchro incrémentale `mis_a_jour_depuis`
et une pagination `limit` / `offset` :

```bash
curl -H "X-API-Key: dev-local-api-key-change-me" \
     "http://localhost:8000/mesures/?mis_a_jour_depuis=2026-08-01T00:00:00Z&limit=100&offset=0"
```

Endpoints notables :

| Méthode | Chemin                  | Description                                  |
| ------- | ----------------------- | -------------------------------------------- |
| POST    | `/mesures/`             | Réception d'une mesure MQTT (capteur_id ou topic_mqtt), détection d'anomalies + alerte e-mail |
| GET     | `/alertes/actives`      | Alertes en cours (dashboard)                 |
| GET     | `/alertes/historique`   | Historique complet                           |
| GET     | `/lots/fifo`            | Lots triés FIFO par date de stockage         |

## E-mails d'alerte

Les alertes sont envoyées via **Brevo** (relais SMTP `smtp-relay.brevo.com`,
port 587, STARTTLS). Renseignez dans `.env` :

- `SMTP_USERNAME` / `SMTP_PASSWORD` : la clé SMTP Brevo (`xkeysib-...`) est
  utilisée **à la fois** comme identifiant et comme mot de passe.
- `SMTP_FROM` : expéditeur **vérifié** dans Brevo (sinon l'envoi échoue, code 503).

Sans identifiants valides, l'alerte est quand même créée en base avec
`email_envoye=false`.

## Base de données

- Volume **géré par compose** (portable) : créé automatiquement sur toute
  machine. Un volume vierge est initialisé par `database/init/01_init.sql`
  (schéma + données de démo).
- Identifiants par défaut : user `futurekawa` / mdp `futurekawa` / bdd `futurekawa_local`.
- Les timestamps (`cree_le`, `mis_a_jour_le`) sont en UTC (`TIMESTAMPTZ`).
- Identifiants UUID générés localement, adaptés à la synchro incrémentale.
