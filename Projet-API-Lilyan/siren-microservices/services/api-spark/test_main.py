"""
Tests unitaires pour l'API Spark
"""
import pytest
from unittest.mock import Mock, patch, AsyncMock
from fastapi.testclient import TestClient
from httpx import AsyncClient
import math

# Import des modules à tester
from main import (
    app,
    to_jsonld,
    create_pagination,
    JSONLD_TYPE,
    JSONLD_ID,
    JSONLD_CONTEXT,
)

client = TestClient(app)


# =============================================================================
# Tests des constantes JSON-LD
# =============================================================================
class TestConstants:
    """Tests pour les constantes JSON-LD"""

    def test_jsonld_type_constant(self):
        """Vérifie que la constante JSONLD_TYPE est correcte"""
        assert JSONLD_TYPE == "@type"

    def test_jsonld_id_constant(self):
        """Vérifie que la constante JSONLD_ID est correcte"""
        assert JSONLD_ID == "@id"

    def test_jsonld_context_constant(self):
        """Vérifie que la constante JSONLD_CONTEXT est correcte"""
        assert JSONLD_CONTEXT == "@context"


# =============================================================================
# Tests de la fonction to_jsonld
# =============================================================================
class TestToJsonld:
    """Tests pour la fonction to_jsonld"""

    def test_to_jsonld_basic(self):
        """Test basique de conversion JSON-LD"""
        result = to_jsonld("TestType", {"key": "value"})

        assert JSONLD_CONTEXT in result
        assert JSONLD_TYPE in result
        assert result[JSONLD_TYPE] == "TestType"
        assert result["key"] == "value"

    def test_to_jsonld_with_context(self):
        """Vérifie que le contexte JSON-LD contient schema.org"""
        result = to_jsonld("TestType", {})

        assert isinstance(result[JSONLD_CONTEXT], list)
        assert "https://schema.org/" in result[JSONLD_CONTEXT]

    def test_to_jsonld_with_hydra(self):
        """Vérifie que le contexte contient Hydra"""
        result = to_jsonld("TestType", {})

        context = result[JSONLD_CONTEXT]
        hydra_context = next((c for c in context if isinstance(c, dict)), None)

        assert hydra_context is not None
        assert "hydra" in hydra_context

    def test_to_jsonld_preserves_data(self):
        """Vérifie que les données sont préservées"""
        data = {
            "name": "Test",
            "value": 123,
            "nested": {"inner": "data"}
        }
        result = to_jsonld("TestType", data)

        assert result["name"] == "Test"
        assert result["value"] == 123
        assert result["nested"]["inner"] == "data"

    def test_to_jsonld_empty_data(self):
        """Test avec données vides"""
        result = to_jsonld("EmptyType", {})

        assert result[JSONLD_TYPE] == "EmptyType"
        assert JSONLD_CONTEXT in result


# =============================================================================
# Tests de la fonction create_pagination
# =============================================================================
class TestCreatePagination:
    """Tests pour la fonction create_pagination"""

    def test_pagination_first_page(self):
        """Test pagination sur la première page"""
        result = create_pagination(page=1, limit=20, total=100, base_url="http://test.com")

        assert result["page"] == 1
        assert result["limit"] == 20
        assert result["totalItems"] == 100
        assert result["total_pages"] == 5
        assert result["has_next"] is True
        assert result["has_prev"] is False

    def test_pagination_middle_page(self):
        """Test pagination sur une page au milieu"""
        result = create_pagination(page=3, limit=20, total=100, base_url="http://test.com")

        assert result["page"] == 3
        assert result["has_next"] is True
        assert result["has_prev"] is True

    def test_pagination_last_page(self):
        """Test pagination sur la dernière page"""
        result = create_pagination(page=5, limit=20, total=100, base_url="http://test.com")

        assert result["page"] == 5
        assert result["has_next"] is False
        assert result["has_prev"] is True

    def test_pagination_single_page(self):
        """Test avec une seule page"""
        result = create_pagination(page=1, limit=20, total=10, base_url="http://test.com")

        assert result["total_pages"] == 1
        assert result["has_next"] is False
        assert result["has_prev"] is False

    def test_pagination_empty_result(self):
        """Test avec aucun résultat"""
        result = create_pagination(page=1, limit=20, total=0, base_url="http://test.com")

        assert result["total_pages"] == 1
        assert result["totalItems"] == 0

    def test_pagination_view_links(self):
        """Test des liens de vue Hydra"""
        result = create_pagination(page=2, limit=10, total=50, base_url="http://test.com")

        assert "view" in result
        assert JSONLD_ID in result["view"]
        assert JSONLD_TYPE in result["view"]
        assert result["view"][JSONLD_TYPE] == "hydra:PartialCollectionView"

    def test_pagination_navigation_links(self):
        """Test des liens de navigation"""
        result = create_pagination(page=2, limit=10, total=50, base_url="http://test.com")

        assert "first" in result["view"]
        assert "previous" in result["view"]
        assert "next" in result["view"]
        assert "last" in result["view"]

    def test_pagination_no_base_url(self):
        """Test sans base_url"""
        result = create_pagination(page=1, limit=20, total=100, base_url="")

        assert "view" not in result

    def test_pagination_total_pages_calculation(self):
        """Test du calcul du nombre total de pages"""
        # 100 items, 20 par page = 5 pages
        result = create_pagination(page=1, limit=20, total=100, base_url="")
        assert result["total_pages"] == 5

        # 101 items, 20 par page = 6 pages
        result = create_pagination(page=1, limit=20, total=101, base_url="")
        assert result["total_pages"] == 6

        # 99 items, 20 par page = 5 pages
        result = create_pagination(page=1, limit=20, total=99, base_url="")
        assert result["total_pages"] == 5


# =============================================================================
# Tests des endpoints API
# =============================================================================
class TestAPIEndpoints:
    """Tests pour les endpoints de l'API"""

    def test_redoc_endpoint(self):
        """Test de l'endpoint ReDoc"""
        response = client.get("/redoc")

        assert response.status_code == 200
        assert "text/html" in response.headers["content-type"]
        assert "redoc" in response.text.lower()

    def test_openapi_endpoint(self):
        """Test de l'endpoint OpenAPI"""
        response = client.get("/openapi.json")

        assert response.status_code == 200
        data = response.json()
        assert "openapi" in data
        assert "info" in data
        assert data["info"]["title"] == "API Spark - Statistiques SIREN"

    def test_docs_endpoint(self):
        """Test de l'endpoint Swagger docs"""
        response = client.get("/docs")

        assert response.status_code == 200
        assert "text/html" in response.headers["content-type"]

    def test_health_endpoint_structure(self):
        """Test de la structure de l'endpoint health (sans Spark)"""
        response = client.get("/v1/health")

        assert response.status_code == 200
        data = response.json()
        assert "status" in data
        assert "service" in data
        assert data["service"] == "api-spark"
        assert "version" in data

    def test_root_v1_requires_auth(self):
        """Test que /v1/ requiert une authentification"""
        response = client.get("/v1/")

        # Sans token, devrait retourner 401
        assert response.status_code == 401

    def test_stats_count_requires_auth(self):
        """Test que /v1/stats/activites/count requiert une authentification"""
        response = client.get("/v1/stats/activites/count")

        assert response.status_code == 401

    def test_stats_filter_requires_auth(self):
        """Test que /v1/stats/activites/filter requiert une authentification"""
        response = client.get("/v1/stats/activites/filter?code=62.01Z")

        assert response.status_code == 401

    def test_stats_top_requires_auth(self):
        """Test que /v1/stats/activites/top requiert une authentification"""
        response = client.get("/v1/stats/activites/top")

        assert response.status_code == 401

    def test_stats_bottom_requires_auth(self):
        """Test que /v1/stats/activites/bottom requiert une authentification"""
        response = client.get("/v1/stats/activites/bottom")

        assert response.status_code == 401


# =============================================================================
# Tests de sécurité OpenAPI
# =============================================================================
class TestOpenAPISecurity:
    """Tests pour la configuration de sécurité OpenAPI"""

    def test_openapi_has_security_schemes(self):
        """Vérifie que le schéma OpenAPI contient les schémas de sécurité"""
        response = client.get("/openapi.json")
        data = response.json()

        assert "components" in data
        assert "securitySchemes" in data["components"]
        assert "bearerAuth" in data["components"]["securitySchemes"]

    def test_openapi_bearer_auth_config(self):
        """Vérifie la configuration du Bearer Auth"""
        response = client.get("/openapi.json")
        data = response.json()

        bearer_auth = data["components"]["securitySchemes"]["bearerAuth"]
        assert bearer_auth["type"] == "http"
        assert bearer_auth["scheme"] == "bearer"

    def test_health_endpoint_no_security(self):
        """Vérifie que /health n'a pas de sécurité requise"""
        response = client.get("/openapi.json")
        data = response.json()

        health_path = data["paths"].get("/v1/health", {})
        if "get" in health_path:
            # health ne devrait pas avoir de security ou avoir une liste vide
            security = health_path["get"].get("security", [])
            assert security == [] or "security" not in health_path["get"]


# =============================================================================
# Tests d'intégration (avec mocks)
# =============================================================================
class TestIntegrationWithMocks:
    """Tests d'intégration avec mocks pour Spark et OAuth"""

    @patch('main.verify_token')
    @patch('main.get_spark')
    def test_root_v1_with_valid_token(self, mock_spark, mock_verify):
        """Test /v1/ avec un token valide"""
        mock_verify.return_value = {"user": "test"}

        response = client.get(
            "/v1/",
            headers={"Authorization": "Bearer valid_token"}
        )

        # Avec le mock, l'auth est bypassée
        assert response.status_code == 200
        data = response.json()
        assert "service" in data
        assert "endpoints" in data
