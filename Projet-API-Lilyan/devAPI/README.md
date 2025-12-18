# Conception et développement d'API

2 backends, un avec MySQL pour le transactionnel et un avec Spark pour l'annalytique.

Développé 2 service d'API REST sur ces deux backends.

Chaque service d'API est protégé par OAuth2.

## Jeu de données

Télécharger https://object.files.data.gouv.fr/data-pipeline-open/siren/stock/StockUniteLegale_utf8.zip et décompresser
le fichier `StockUniteLegale_utf8.csv` dans le dossier `data/`.

## Build dans Docker

```bash
docker compose build
docker compose up
```