#!/bin/bash
set -e

host="$1"
port="$2"
shift 2
cmd="$@"

echo "⏳ Attente de la disponibilité de MongoDB sur $host:$port..."

until mongosh --quiet --eval "db.runCommand({ ping: 1 }).ok" "mongodb://$host:$port" > /dev/null 2>&1; do
  echo "🔁 MongoDB pas encore prêt à $host:$port, nouvelle tentative dans 5s..."
  sleep 5
done

echo "✅ MongoDB prêt, exécution du script Python..."
exec $cmd