#!/bin/bash
set -e

# ----- CONFIG -----
APP_NAME="terraform-generator-api"
IMAGE_NAME="terraform-generator-api:latest"
CONTAINER_NAME="terraform-api"
ORACLE_MIGRATION="./migrations/01_create_status_table.sql"
ENV_FILE=".env"

# ----- BUILD -----
echo "➡️  Construction de l'image Docker..."
docker build -t $IMAGE_NAME .

# ----- ORACLE MIGRATION -----
echo "➡️  Application des migrations Oracle si besoin..."
if [ -f "$ORACLE_MIGRATION" ]; then
  # Utilisation de sqlplus (nécessite que le client sqlplus soit installé)
  echo "Connexion à Oracle pour appliquer la migration (nécessite SQL*Plus) :"
  read -p "User : " ORA_USER
  read -s -p "Password : " ORA_PASS
  echo
  read -p "TNS (exemple : //host:1521/service) : " ORA_TNS

  echo "SET DEFINE OFF;" > tmp_migration.sql
  cat "$ORACLE_MIGRATION" >> tmp_migration.sql

  sqlplus "$ORA_USER/$ORA_PASS@$ORA_TNS" @tmp_migration.sql || echo "⚠️  Migration Oracle non appliquée (passez à la main si besoin)"
  rm -f tmp_migration.sql
else
  echo "Aucune migration Oracle trouvée."
fi

# ----- STOP & REMOVE CONTAINER -----
if docker ps -a --format '{{.Names}}' | grep -Eq "^$CONTAINER_NAME\$"; then
  echo "➡️  Arrêt et suppression du conteneur existant..."
  docker stop $CONTAINER_NAME || true
  docker rm $CONTAINER_NAME || true
fi

# ----- START CONTAINER -----
echo "➡️  Lancement du conteneur Docker..."
docker run -d --name $CONTAINER_NAME \
  --env-file $ENV_FILE \
  -p 5000:5000 \
  $IMAGE_NAME

echo "✅ Déploiement terminé. Accès API : http://localhost:5000"
