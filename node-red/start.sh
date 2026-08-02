#!/bin/sh
# Démarrage Node-RED : installe les dépendances déclarées dans /data/package.json
# si elles ne sont pas déjà présentes, puis lance Node-RED normalement.

cd /data || exit 1

if [ -f package.json ] && [ ! -d node_modules ]; then
    echo "Installation des dépendances Node-RED (package.json)..."
    npm install --only=prod --no-audit --no-fund --unsafe-perm
    echo "Dépendances installées."
fi

cd /usr/src/node-red || exit 1
exec /usr/src/node-red/entrypoint.sh "$@"
