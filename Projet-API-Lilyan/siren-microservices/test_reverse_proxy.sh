#!/bin/bash

echo "=========================================="
echo "Test du Reverse Proxy Nginx"
echo "=========================================="
echo ""

echo "IMPORTANT: Assurez-vous d'avoir ajouté ces lignes à /etc/hosts :"
echo "127.0.0.1  oauth.siren.local"
echo "127.0.0.1  mysql.siren.local"
echo "127.0.0.1  spark.siren.local"
echo ""

# Test 1: OAuth2 Service
echo "=== Test 1: OAuth2 Service Health (oauth.siren.local) ==="
curl -s -H "Host: oauth.siren.local" http://localhost/v1/health | python3 -m json.tool
echo ""

# Test 2: API MySQL Health
echo "=== Test 2: API MySQL Health (mysql.siren.local) ==="
curl -s -H "Host: mysql.siren.local" http://localhost/v1/health | python3 -m json.tool
echo ""

# Test 3: API Spark Health
echo "=== Test 3: API Spark Health (spark.siren.local) ==="
curl -s -H "Host: spark.siren.local" http://localhost/v1/health | python3 -m json.tool
echo ""

echo "=== Test 4: OAuth2 - Obtenir un token ==="
TOKEN_RESPONSE=$(curl -s -X POST -H "Host: oauth.siren.local" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "grant_type=password&client_id=client-app&client_secret=Dev_Client_Secret_2024!&username=user1&password=DevUser1Pass2024!" \
  http://localhost/v1/oauth/token)

echo "$TOKEN_RESPONSE" | python3 -m json.tool

TOKEN=$(echo "$TOKEN_RESPONSE" | python3 -c "import sys, json; print(json.load(sys.stdin)['access_token'])" 2>/dev/null)

if [ -z "$TOKEN" ]; then
  echo ""
  echo "❌ Échec de l'obtention du token OAuth2"
  echo "Vérifiez que les services OAuth2 et MySQL sont correctement démarrés"
  exit 1
fi

echo ""
echo "✅ Token obtenu: $TOKEN"
echo ""

# Test 5: API MySQL - Recherche par SIREN (exemple)
echo "=== Test 5: API MySQL - Recherche par SIREN (via mysql.siren.local) ==="
curl -s -H "Host: mysql.siren.local" \
  -H "Authorization: Bearer $TOKEN" \
  http://localhost/v1/entreprises/siren/123456789 | python3 -m json.tool | head -20
echo ""

# Test 6: API Spark - Top activités
echo "=== Test 6: API Spark - Top 3 activités (via spark.siren.local) ==="
curl -s -H "Host: spark.siren.local" \
  -H "Authorization: Bearer $TOKEN" \
  "http://localhost/v1/stats/activites/top?limit=3" | python3 -m json.tool | head -30
echo ""

echo "=========================================="
echo "✅ Tous les tests du reverse proxy terminés"
echo "=========================================="
echo ""
echo "L'architecture est maintenant masquée :"
echo "  - OAuth2:     oauth.siren.local  → http://oauth2:3000"
echo "  - API MySQL:  mysql.siren.local  → http://api-mysql:3001"
echo "  - API Spark:  spark.siren.local  → http://api-spark:3002"
echo ""
echo "Tous les services sont accessibles via le port 80 uniquement !"
