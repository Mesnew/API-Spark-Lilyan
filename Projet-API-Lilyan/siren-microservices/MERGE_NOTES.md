# Notes de Merge - Infrastructure Prof + APIs Étudiantes

**Date** : 2024-12-17
**Type** : Merge de l'infrastructure Scala/Spark du professeur avec les 3 APIs existantes

---

## 🔄 Changements effectués

### Infrastructure ajoutée (depuis prof)

1. **dbcli** (Dockerfile: `dbcli.Dockerfile`)
   - Conteneur Scala qui charge automatiquement les données CSV dans MySQL
   - Exécute `feedDB.scala` pour créer les tables et importer les données
   - Se termine après avoir chargé les données (`condition: service_completed_successfully`)

2. **spark** (Dockerfile: `analyticcli.Dockerfile`)
   - Serveur Spark Connect sur le port 15002
   - Permet les analyses distribuées via Spark
   - Exécute `analyticcli.scala`

3. **Fichiers d'infrastructure**
   - `build.sbt` : Configuration du projet Scala
   - `project/` : Configuration SBT
   - `src/main/scala/` : Code source Scala
   - `my.cnf` : Configuration MySQL optimisée

### Services conservés (APIs étudiantes)

1. **oauth2** (Port 3000)
   - API OAuth2 (Node.js + Express)
   - Authentification pour les 2 autres APIs

2. **api-mysql** (Port 3001)
   - API de recherche d'entreprises (Python FastAPI)
   - Endpoints : SIREN, code activité, nom

3. **api-spark** (Port 3002)
   - API de statistiques (Node.js + Express)
   - **NOUVEAU** : Variable d'environnement `SPARK_CONNECT_URL` ajoutée
   - Peut maintenant se connecter au vrai Spark Connect

---

## 📊 Architecture finale

```
┌─────────────────────────────────────────────────────────────┐
│                    ARCHITECTURE COMPLÈTE                     │
└─────────────────────────────────────────────────────────────┘

         Client (Postman / Browser)
                    │
        ┌───────────┴───────────┐
        │                       │
        v                       v
   ┌─────────┐           ┌─────────────┐
   │ OAuth2  │           │  API MySQL  │
   │ :3000   │───────────│  :3001      │
   └─────────┘           └──────┬──────┘
        │                       │
        │                       │
   ┌────────────┐               │
   │ API Spark  │               │
   │ :3002      │               │
   └─────┬──────┘               │
         │                      │
         │                      │
    ┌────┴──────────────────────┴────┐
    │                                 │
    v                                 v
┌─────────┐                     ┌─────────┐
│  Spark  │◄────────────────────│  MySQL  │
│ :15002  │                     │ :3367   │
└─────────┘                     └────┬────┘
    ▲                                │
    │                                │
    │           ┌────────────────────┘
    │           │
    │       ┌───▼────┐
    │       │ dbcli  │ (one-shot: loads CSV data)
    │       └────────┘
    │
    └─── analyticcli (Spark Connect Server)
```

---

## 🔧 Changements dans docker-compose.yaml

### Ordre de démarrage

1. **db** (MySQL) - Démarre en premier
2. **dbcli** - Charge les données une fois MySQL prêt
3. **spark** - Démarre après dbcli (données chargées)
4. **oauth2** - Démarre après dbcli
5. **api-mysql** - Démarre après db + dbcli + oauth2
6. **api-spark** - Démarre après db + dbcli + spark + oauth2

### Dépendances ajoutées

- Tous les services attendent `dbcli: condition: service_completed_successfully`
- `api-spark` dépend maintenant de `spark: condition: service_started`

---

## 🔑 Changements dans .env

**Ancien (développement)** :
```
MYSQL_ROOT_PASSWORD=Dev_Root_Pass_2024!
MYSQL_PASSWORD=Dev_Siren_Pass_2024!
MYSQL_PORT=3366
```

**Nouveau (compatibilité prof)** :
```
MYSQL_ROOT_PASSWORD=12345678
MYSQL_PASSWORD=12345678
MYSQL_HOST=db
MYSQL_PORT=3306
```

**⚠️ IMPORTANT** : Les credentials ont été simplifiés pour correspondre à ceux du prof.

---

## 📦 Données

Le projet utilise maintenant **deux méthodes** de chargement :

1. **init-db.sql** (ancienne méthode)
   - Fichier SQL avec 20 entreprises de test
   - Utilisé manuellement si besoin

2. **dbcli + feedDB.scala** (nouvelle méthode - AUTOMATIQUE)
   - Charge automatiquement le fichier CSV complet
   - Exécuté au démarrage du conteneur
   - Fichier attendu : `data/StockUniteLegale_utf8.csv`

### Télécharger les données

```bash
cd data
wget https://object.files.data.gouv.fr/data-pipeline-open/siren/stock/StockUniteLegale_utf8.zip
unzip StockUniteLegale_utf8.zip
```

---

## 🚀 Démarrage

```bash
# Télécharger les données (si pas déjà fait)
cd data
wget https://object.files.data.gouv.fr/data-pipeline-open/siren/stock/StockUniteLegale_utf8.zip
unzip StockUniteLegale_utf8.zip
cd ..

# Lancer tous les services
docker-compose build
docker-compose up

# Voir les logs
docker-compose logs -f

# Vérifier que tout fonctionne
docker ps
```

---

## 🧪 Tests

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

### 2. Tester les APIs

```bash
TOKEN="votre_token_ici"

# API MySQL
curl -H "Authorization: Bearer $TOKEN" \
  http://localhost:3001/entreprises/siren/123456789

# API Spark (statistiques)
curl -H "Authorization: Bearer $TOKEN" \
  "http://localhost:3002/stats/activites/count?page=1&limit=5"
```

### 3. Vérifier Spark Connect

```bash
# Logs du serveur Spark
docker logs spark

# Le port 15002 doit être accessible
nc -zv localhost 15002
```

---

## 📝 TODO pour api-spark

L'API Spark peut maintenant se connecter au vrai Spark Connect via `SPARK_CONNECT_URL=spark:15002`.

**Modifications suggérées dans `services/api-spark/app.js`** :

```javascript
// Remplacer les requêtes MySQL directes par Spark Connect
// Exemple avec spark-connect-client (à installer)

const { SparkSession } = require('@apache/spark-connect');

const spark = SparkSession.builder()
  .remote(process.env.SPARK_CONNECT_URL || 'localhost:15002')
  .build();

// Lire depuis MySQL via Spark
const df = spark.read
  .format('jdbc')
  .option('url', `jdbc:mysql://${process.env.MYSQL_HOST}:3306/${process.env.MYSQL_DATABASE}`)
  .option('driver', 'com.mysql.cj.jdbc.Driver')
  .option('dbtable', 'unite_legale')
  .option('user', process.env.MYSQL_USER)
  .option('password', process.env.MYSQL_PASSWORD)
  .load();

// Effectuer des analyses distribuées
const stats = df.groupBy('activite_principale_unite_legale')
  .count()
  .orderBy('count', { ascending: false });
```

---

## 🔗 Liens utiles

- **OAuth2 Swagger** : http://localhost:3000/api-docs
- **API MySQL Swagger** : http://localhost:3001/docs
- **API Spark Swagger** : http://localhost:3002/api-docs
- **Spark Connect** : localhost:15002

---

## 🎯 Résumé

**Avant** : 3 APIs + MySQL (données chargées manuellement)
**Après** : 3 APIs + MySQL + Spark Connect + chargement automatique des données

**Avantages** :
- ✅ Chargement automatique des données CSV
- ✅ Infrastructure Spark Connect disponible
- ✅ Toutes les APIs conservées et fonctionnelles
- ✅ Architecture complète et conteneurisée

**Prochaines étapes** :
- [ ] Modifier `api-spark` pour utiliser Spark Connect au lieu de MySQL
- [ ] Tester les performances avec le dataset complet
- [ ] Implémenter des analyses distribuées avec Spark
