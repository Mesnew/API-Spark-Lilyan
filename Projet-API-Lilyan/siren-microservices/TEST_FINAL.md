# Test Final de l'Architecture 5 Containers

## État des Containers

```bash
docker ps
```

**Résultat attendu** : 5 containers en cours d'exécution
- siren-mysql (healthy)
- siren-oauth2 (healthy)
- siren-spark (up)
- siren-api-mysql (up/unhealthy - normal au début)
- siren-api-spark (up/unhealthy - normal au début)

## Test 1: Obtenir un token OAuth2

```bash
curl -X POST http://localhost:3000/oauth/token \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "grant_type=password" \
  -d "username=user1" \
  -d "password=DevUser1Pass2024!" \
  -d "client_id=client-app" \
  -d "client_secret=Dev_Client_Secret_2024!"
```

**Résultat** : Un JSON avec `accessToken` et `refreshToken`

## Test 2: API MySQL - Récupérer une entreprise par SIREN

```bash
TOKEN="<votre_token_ici>"

curl -X GET "http://localhost:3001/entreprises/siren/123456789" \
  -H "Authorization: Bearer $TOKEN"
```

**Résultat attendu** : JSON-LD avec les données de l'entreprise

## Test 3: API MySQL - Recherche par code activité

```bash
curl -X GET "http://localhost:3001/entreprises/activite/62.01Z?page=1&limit=5" \
  -H "Authorization: Bearer $TOKEN"
```

**Résultat** : Liste paginée des entreprises avec code 62.01Z

## Test 4: API Spark - Statistiques par code activité

```bash
curl -X GET "http://localhost:3002/stats/activites/count?limit=10" \
  -H "Authorization: Bearer $TOKEN"
```

**Résultat** : Statistiques agrégées par Spark Connect

## Test 5: API Spark - Top 5 des codes activité

```bash
curl -X GET "http://localhost:3002/stats/activites/top?limit=5" \
  -H "Authorization: Bearer $TOKEN"
```

## Vérification des formats

Tous les endpoints doivent retourner du JSON-LD avec:
- `@context`: "https://schema.org/"
- `@type`: Type approprié (Organization, ItemList, AggregateRating)
- `pagination`: Métadonnées Hydra pour les listes paginées

## Swagger UI

- OAuth2: http://localhost:3000/api-docs
- API MySQL: http://localhost:3001/docs
- API Spark: http://localhost:3002/docs
