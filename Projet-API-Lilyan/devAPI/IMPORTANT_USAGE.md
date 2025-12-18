# ⚠️ IMPORTANT - USAGE DE CE DOSSIER

## Ne pas lancer docker-compose directement depuis ce dossier !

Ce dossier `devAPI/` contient l'infrastructure backend héritée du projet professeur :
- MySQL database setup
- Spark Connect server
- Data loader (dbcli)

**Cependant, ces services NE DOIVENT PAS être lancés depuis ce dossier.**

---

## ✅ Utilisation correcte

Le projet principal **`siren-microservices/`** orchestre tous les services, y compris ceux de `devAPI/`.

### Commandes à utiliser

```bash
# Depuis la racine du projet
cd siren-microservices/

# Lancer tous les services (db, spark, oauth2, api-mysql, api-spark)
docker-compose up -d

# Voir le statut
docker-compose ps

# Voir les logs
docker-compose logs -f

# Arrêter tous les services
docker-compose down
```

---

## 🏗️ Architecture

Le fichier `siren-microservices/docker-compose.yaml` référence automatiquement les ressources de `devAPI/` :

```yaml
dbcli:
  build:
    context: ../devAPI        # ← Utilise ce dossier
    dockerfile: dbcli.Dockerfile

spark:
  build:
    context: ../devAPI        # ← Utilise ce dossier
    dockerfile: analyticcli.Dockerfile
```

---

## ⚠️ Pourquoi ne pas lancer devAPI/docker-compose.yaml ?

Si vous lancez `docker-compose up` dans ce dossier **ET** dans `siren-microservices/`, vous aurez :

1. **Conflit de port 3367** : Les deux tentent de démarrer MySQL sur le même port
2. **Duplication de services** : Spark et MySQL tournent en double
3. **Gaspillage de ressources** : RAM/CPU inutilement consommés

---

## 📁 Contenu de ce dossier

- `dbcli.Dockerfile` - Image pour charger les données CSV → MySQL
- `analyticcli.Dockerfile` - Image pour Spark Connect server
- `src/main/scala/` - Code Scala (dbcli et analyticcli)
- `data/` - Fichiers CSV (StockUniteLegale_utf8.csv)
- `my.cnf` - Configuration MySQL
- `docker-compose.yaml` - ⚠️ **NON UTILISÉ** (remplacé par siren-microservices)

---

## 🎯 Résumé

```
❌ NE PAS FAIRE : cd devAPI/ && docker-compose up
✅ À FAIRE      : cd siren-microservices/ && docker-compose up
```

---

## 📚 Documentation complète

Voir `../siren-microservices/README.md` pour la documentation complète du projet.
