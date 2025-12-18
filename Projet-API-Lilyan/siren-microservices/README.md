# Architecture Microservices SIREN

Architecture conteneurisée de **5 containers Docker** combinant l'infrastructure devAPI (MySQL + Spark) avec 3 APIs REST pour la gestion et l'analyse des données SIREN (entreprises françaises).

## 🚀 Installation Rapide

```bash
# 1. Cloner le repository
git clone git@github.com:Mesnew/API-Spark-Lilyan.git
cd API-Spark-Lilyan/Projet-API-Lilyan

# 2. Configurer les variables d'environnement
cd siren-microservices
cp .env.example .env

# 3. Télécharger les données SIREN (optionnel pour tester, obligatoire pour production)
cd ../devAPI/data
wget https://object.files.data.gouv.fr/data-pipeline-open/siren/stock/StockUniteLegale_utf8.zip
unzip StockUniteLegale_utf8.zip
cd ../../devAPI

# 4. Démarrer l'infrastructure (MySQL + Spark)
docker-compose up -d

# Attendre que les services devAPI soient prêts (~5-10 minutes au premier démarrage)
docker-compose logs -f

# 5. Dans un autre terminal, démarrer les APIs
cd ../siren-microservices
docker-compose up -d

# 6. (Optionnel) Configurer le reverse proxy avec sous-domaines
sudo nano /etc/hosts
# Ajouter ces lignes :
# 127.0.0.1  oauth.siren.local
# 127.0.0.1  mysql.siren.local
# 127.0.0.1  spark.siren.local

# 7. Tester
./test_reverse_proxy.sh
```

**Accès aux services :**
- OAuth2 (Swagger): http://localhost:3000/api-docs ou http://oauth.siren.local/docs
- API MySQL (Swagger): http://localhost:3001/docs ou http://mysql.siren.local/docs
- API Spark (Swagger): http://localhost:3002/docs ou http://spark.siren.local/docs

## Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                      ARCHITECTURE GLOBALE (5 Containers)             │
└─────────────────────────────────────────────────────────────────────┘

                        ┌─────────────────┐
                        │   Client        │
                        │  (Postman/etc.) │
                        └────────┬────────┘
                                 │
                    ┌────────────┼────────────┐
                    │            │            │
                    v            v            v
        ┌───────────────┐  ┌──────────┐  ┌─────────────┐
        │  API OAuth2   │  │API MySQL │  │ API Spark   │
        │ (Express.js)  │  │(FastAPI) │  │ (FastAPI)   │
        │  Port: 3000   │  │Port: 3001│  │ Port: 3002  │
        │               │  │          │  │             │
        │  - Auth       │  │- SIREN   │  │ - Stats     │
        │  - Tokens     │  │- Nom     │  │ - Top/Flop  │
        │  - Swagger    │  │- Filtres │  │ - Agrég.    │
        └───────────────┘  └────┬─────┘  └──────┬──────┘
                                │                │
                         ┌──────┴───────┐        │
                         │              │        │
                         v              │        v
                  ┌──────────┐          │  ┌─────────────────┐
                  │  MySQL   │◄─────────┘  │ Spark Connect   │
                  │  Port:   │             │ Port: 15002     │
                  │  3367    │◄────────────┤ (Scala)         │
                  │          │             │                 │
                  └─────▲────┘             └─────────────────┘
                        │
                  ┌─────┴─────┐
                  │  DB CLI   │
                  │ (Scala)   │
                  │ Load data │
                  └───────────┘
```

## Services

### 1. Infrastructure Backend (depuis devAPI)

#### MySQL Database
**Port:** 3367
**Image:** mysql:8.0
**Fonction:** Base de données transactionnelle SIREN

#### DB CLI
**Technologie:** Scala
**Fonction:** Chargement des données SIREN depuis CSV vers MySQL (s'exécute une fois)

#### Spark Connect Server
**Port:** 15002
**Technologie:** Scala + Apache Spark 3.5
**Fonction:** Serveur Spark Connect pour l'analyse analytique des données

### 2. API OAuth2 (Node.js + Express)
**Port:** 3000
**Technologie:** Node.js, Express, express-oauth-server

**Endpoints:**
- `POST /oauth/token` - Obtenir un token
- `GET /secure` - Route protégée exemple
- `GET /me` - Informations utilisateur
- `GET /users` - Liste des utilisateurs
- `GET /health` - Santé du service

**Documentation:** http://localhost:3000/api-docs

### 3. API MySQL (Python + FastAPI)
**Port:** 3001
**Technologie:** Python 3.11, FastAPI, SQLAlchemy, MySQL

**Endpoints:**
- `GET /entreprises/siren/{siren}` - Entreprise par SIREN
- `GET /entreprises/activite/{code}` - Entreprises par code activité
- `GET /entreprises/search?nom=...` - Recherche par nom
- `GET /entreprises/filter?nom=...&activite=...` - Recherche avec filtres combinés
- `GET /health` - Santé du service

**Fonctionnalités:**
- Pagination (20 par défaut, paramétrable)
- Format JSON-LD avec Hydra
- Documentation Swagger automatique
- Protection OAuth2

**Documentation:** http://localhost:3001/docs

### 4. API Spark (Python + FastAPI + Spark Connect)
**Port:** 3002
**Technologie:** Python 3.11, FastAPI, PySpark 3.5, Spark Connect

**Endpoints:**
- `GET /stats/activites/count` - Nombre d'entreprises par code activité (paginé)
- `GET /stats/activites/filter?code=...` - Nombre pour un code spécifique
- `GET /stats/activites/top` - Codes activité les plus représentés
- `GET /stats/activites/bottom` - Codes activité les moins représentés
- `GET /health` - Santé du service

**Fonctionnalités:**
- Utilise Spark Connect pour l'analyse analytique
- Pagination (20 par défaut, paramétrable)
- Format JSON-LD avec Hydra
- Documentation Swagger automatique
- Protection OAuth2

**Documentation:** http://localhost:3002/docs

## Exigences respectées

### Architecture de service conteneurisée
- [x] **3 services API** : OAuth2, API MySQL, API Spark
- [x] **5 containers Docker** : db, dbcli, spark, oauth2, api-mysql, api-spark
- [x] **Conteneurisation complète** : Docker Compose orchestration

### API OAuth2
- [x] Autorise les 2 autres APIs (MySQL et Spark)
- [x] Génère des tokens Bearer
- [x] Documentation Swagger

### API MySQL (Transactionnel)
- [x] Entreprises par SIREN
- [x] Entreprises par code activité
- [x] Entreprises avec filtre par nom
- [x] Entreprises avec filtres combinés (nom + code activité)

### API Spark (Analytique)
- [x] Nombre d'entreprises par code activité
- [x] Nombre d'entreprises avec filtre par code activité
- [x] Codes activité les plus représentés
- [x] Codes activité les moins représentés
- [x] Utilise **réellement Spark Connect** (pas MySQL direct)

### Exigences techniques
- [x] Pagination par défaut de 20 entrées (paramétrable)
- [x] Toutes les APIs conteneurisées
- [x] Documentation Swagger sur chaque API
- [x] Format JSON-LD/Hydra pour toutes les réponses
- [x] Testable dans Pytest, Postman, curl, etc.
- [x] Technologies variées : Node.js (OAuth2), Python (MySQL, Spark), Scala (Backend)
- [x] Basé sur devAPI existant (https://github.com/St-Michel-IT/devAPI)

## Installation

### Prérequis

- Docker & Docker Compose
- Au minimum 8 GB RAM disponible (pour Spark)
- Fichier de données SIREN

### Étape 1: Téléchargement des données

Les données SIREN doivent être placées dans le dossier `../devAPI/data/` :

```bash
cd ../devAPI/data
wget https://object.files.data.gouv.fr/data-pipeline-open/siren/stock/StockUniteLegale_utf8.zip
unzip StockUniteLegale_utf8.zip
cd ../../siren-microservices
```

### Étape 2: Configuration (Déjà faite)

Le fichier `.env` est déjà configuré avec les valeurs de développement. Pour la production, modifiez :
- `MYSQL_ROOT_PASSWORD`
- `MYSQL_PASSWORD`
- `OAUTH2_CLIENT_SECRET`
- `OAUTH2_USER1` et `OAUTH2_USER2`

**⚠️ ATTENTION:**
- **JAMAIS** committer le fichier `.env` dans git (déjà dans `.gitignore`)
- Utiliser des mots de passe forts en production

### Étape 3: Démarrage

```bash
# Depuis le dossier siren-microservices/
docker-compose up -d

# Voir les logs de tous les services
docker-compose logs -f

# Voir les logs d'un service spécifique
docker-compose logs -f api-spark
docker-compose logs -f spark

# Arrêter tous les services
docker-compose down
```

### Ordre de démarrage automatique

Le docker-compose gère automatiquement l'ordre de démarrage :

1. **db** (MySQL) - Démarre en premier
2. **dbcli** - Charge les données SIREN dans MySQL (attend que db soit healthy)
3. **spark** - Démarre le serveur Spark Connect (attend dbcli)
4. **oauth2** - Démarre le serveur OAuth2
5. **api-mysql** - Démarre l'API transactionnelle (attend db et oauth2)
6. **api-spark** - Démarre l'API analytique (attend spark et oauth2)

⏱️ **Premier démarrage** : Compter ~5-10 minutes pour le chargement des données et le démarrage de Spark.

## Utilisation

### 1. Obtenir un token OAuth2

```bash
curl -X POST http://localhost:3000/oauth/token \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "grant_type=password" \
  -d "username=user1" \
  -d "password=DevUser1Pass2024!" \
  -d "client_id=client-app" \
  -d "client_secret=Dev_Client_Secret_2024!"
```

**Réponse :**
```json
{
  "accessToken": "...",
  "accessTokenExpiresAt": "...",
  "refreshToken": "...",
  "refreshTokenExpiresAt": "...",
  "client": {...},
  "user": {...}
}
```

### 2. Utiliser l'API MySQL (Transactionnel)

```bash
# Récupérer une entreprise par SIREN
curl -X GET "http://localhost:3001/entreprises/siren/123456789" \
  -H "Authorization: Bearer YOUR_TOKEN"

# Rechercher par code activité
curl -X GET "http://localhost:3001/entreprises/activite/62.01Z?page=1&limit=10" \
  -H "Authorization: Bearer YOUR_TOKEN"

# Rechercher par nom
curl -X GET "http://localhost:3001/entreprises/search?nom=ENTREPRISE&page=1&limit=20" \
  -H "Authorization: Bearer YOUR_TOKEN"

# Recherche combinée (nom + code activité)
curl -X GET "http://localhost:3001/entreprises/filter?nom=TEST&activite=62.01Z" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

### 3. Utiliser l'API Spark (Analytique)

```bash
# Nombre d'entreprises par code activité (paginé)
curl -X GET "http://localhost:3002/stats/activites/count?page=1&limit=20" \
  -H "Authorization: Bearer YOUR_TOKEN"

# Filtrer par un code activité spécifique
curl -X GET "http://localhost:3002/stats/activites/filter?code=62.01Z" \
  -H "Authorization: Bearer YOUR_TOKEN"

# Top 10 des codes activité les plus représentés
curl -X GET "http://localhost:3002/stats/activites/top?limit=10" \
  -H "Authorization: Bearer YOUR_TOKEN"

# Top 10 des codes activité les moins représentés
curl -X GET "http://localhost:3002/stats/activites/bottom?limit=10" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

### 4. Documentation Swagger interactive

- **OAuth2**: http://localhost:3000/api-docs
- **API MySQL**: http://localhost:3001/docs
- **API Spark**: http://localhost:3002/docs

Dans Swagger UI, utilisez le bouton "Authorize" et collez votre token Bearer.

## Credentials de développement

**⚠️ Ces credentials sont définis dans le fichier `.env`**

**Valeurs par défaut (fichier .env fourni):**
- **Client ID:** `client-app`
- **Client Secret:** `Dev_Client_Secret_2024!`
- **User1:** `user1` / `DevUser1Pass2024!`
- **User2:** `user2` / `DevUser2Pass2024!`

**🔒 Pour la production:**
- Modifier TOUS les mots de passe dans `.env`
- Ne JAMAIS utiliser les valeurs par défaut en production
- Utiliser un gestionnaire de secrets sécurisé

## Structure du projet

```
Projet-API-Lilyan/
├── devAPI/                     # Infrastructure backend (NE PAS MODIFIER)
│   ├── docker-compose.yaml     # [Non utilisé - on utilise celui de siren-microservices]
│   ├── dbcli.Dockerfile        # Build du chargeur de données
│   ├── analyticcli.Dockerfile  # Build du serveur Spark Connect
│   ├── my.cnf                  # Configuration MySQL
│   ├── data/                   # Données SIREN (à télécharger)
│   │   └── StockUniteLegale_utf8.csv
│   └── src/main/scala/
│       ├── dbcli.scala         # Script de chargement des données
│       └── analyticcli.scala   # Serveur Spark Connect
│
└── siren-microservices/        # APIs REST (Projet principal)
    ├── docker-compose.yaml     # ⭐ Orchestration des 5 containers
    ├── .env                    # Variables d'environnement
    ├── .env.example            # Template de configuration
    ├── README.md               # Ce fichier
    └── services/
        ├── oauth2/             # API OAuth2 (Node.js + Express)
        │   ├── Dockerfile
        │   ├── package.json
        │   ├── app.js
        │   ├── model.js
        │   └── swagger.js
        ├── api-mysql/          # API MySQL (Python + FastAPI)
        │   ├── Dockerfile
        │   ├── requirements.txt
        │   ├── main.py
        │   ├── models.py
        │   ├── schemas.py
        │   ├── database.py
        │   └── auth.py
        └── api-spark/          # API Spark (Python + FastAPI + Spark Connect)
            ├── Dockerfile
            ├── requirements.txt
            └── main.py
```

**Points importants :**
- Le dossier `devAPI/` contient l'infrastructure Scala/Spark (ne pas modifier)
- Le dossier `siren-microservices/` contient les 3 APIs REST
- Le `docker-compose.yaml` dans `siren-microservices/` orchestre TOUT (5 containers)
- Les données CSV doivent être dans `devAPI/data/`

## JSON-LD Format

Toutes les réponses des APIs suivent le format JSON-LD avec contexte :

```json
{
  "@context": "https://schema.org/",
  "@type": "Organization",
  "@id": "siren:123456789",
  "identifier": "123456789",
  "name": "ENTREPRISE EXEMPLE",
  "address": {...}
}
```

## Pagination

Tous les endpoints supportent la pagination :

```
GET /entreprises/search?nom=test&page=1&limit=50
```

- `page`: Numéro de page (défaut: 1)
- `limit`: Nombre d'éléments (défaut: 20, max: 100)

## Développement

### Ajouter un nouveau service

1. Créer un dossier dans `services/`
2. Ajouter un `Dockerfile`
3. Configurer dans `docker-compose.yml`
4. Implémenter l'authentification OAuth2
5. Ajouter la documentation Swagger
6. Implémenter JSON-LD

### Tests

```bash
# Lancer les tests
docker-compose exec api-mysql pytest
```

## Monitoring

- Logs: `docker-compose logs -f [service]`
- Health checks: Endpoint `/health` sur chaque service
- Métriques: TODO (Prometheus + Grafana)

## Sécurité

- Tous les endpoints (sauf OAuth2) sont protégés par tokens
- HTTPS recommandé en production
- Rate limiting à implémenter
- Secrets à externaliser (.env, vault)

## Licence

ISC
