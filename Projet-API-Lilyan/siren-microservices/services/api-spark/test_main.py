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

# =============================================================================
# Constantes de test (évite les duplications détectées par SonarQube)
# =============================================================================
TEST_BASE_URL = "https://test.example.com"
OPENAPI_ENDPOINT = "/openapi.json"

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
        result = create_pagination(page=1, limit=20, total=100, base_url=TEST_BASE_URL)

        assert result["page"] == 1
        assert result["limit"] == 20
        assert result["totalItems"] == 100
        assert result["total_pages"] == 5
        assert result["has_next"] is True
        assert result["has_prev"] is False

    def test_pagination_middle_page(self):
        """Test pagination sur une page au milieu"""
        result = create_pagination(page=3, limit=20, total=100, base_url=TEST_BASE_URL)

        assert result["page"] == 3
        assert result["has_next"] is True
        assert result["has_prev"] is True

    def test_pagination_last_page(self):
        """Test pagination sur la dernière page"""
        result = create_pagination(page=5, limit=20, total=100, base_url=TEST_BASE_URL)

        assert result["page"] == 5
        assert result["has_next"] is False
        assert result["has_prev"] is True

    def test_pagination_single_page(self):
        """Test avec une seule page"""
        result = create_pagination(page=1, limit=20, total=10, base_url=TEST_BASE_URL)

        assert result["total_pages"] == 1
        assert result["has_next"] is False
        assert result["has_prev"] is False

    def test_pagination_empty_result(self):
        """Test avec aucun résultat"""
        result = create_pagination(page=1, limit=20, total=0, base_url=TEST_BASE_URL)

        assert result["total_pages"] == 1
        assert result["totalItems"] == 0

    def test_pagination_view_links(self):
        """Test des liens de vue Hydra"""
        result = create_pagination(page=2, limit=10, total=50, base_url=TEST_BASE_URL)

        assert "view" in result
        assert JSONLD_ID in result["view"]
        assert JSONLD_TYPE in result["view"]
        assert result["view"][JSONLD_TYPE] == "hydra:PartialCollectionView"

    def test_pagination_navigation_links(self):
        """Test des liens de navigation"""
        result = create_pagination(page=2, limit=10, total=50, base_url=TEST_BASE_URL)

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
        response = client.get(OPENAPI_ENDPOINT)

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
        response = client.get(OPENAPI_ENDPOINT)
        data = response.json()

        assert "components" in data
        assert "securitySchemes" in data["components"]
        assert "bearerAuth" in data["components"]["securitySchemes"]

    def test_openapi_bearer_auth_config(self):
        """Vérifie la configuration du Bearer Auth"""
        response = client.get(OPENAPI_ENDPOINT)
        data = response.json()

        bearer_auth = data["components"]["securitySchemes"]["bearerAuth"]
        assert bearer_auth["type"] == "http"
        assert bearer_auth["scheme"] == "bearer"

    def test_health_endpoint_no_security(self):
        """Vérifie que /health n'a pas de sécurité requise"""
        response = client.get(OPENAPI_ENDPOINT)
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


# =============================================================================
# Tests de verify_token
# =============================================================================
class TestVerifyToken:
    """Tests pour la fonction verify_token"""

    def test_missing_auth_header(self):
        """Test sans header Authorization"""
        response = client.get("/v1/stats/activites/count")
        assert response.status_code == 401
        assert "Missing or invalid" in response.json()["detail"]

    def test_invalid_auth_header_format(self):
        """Test avec header Authorization mal formaté"""
        response = client.get(
            "/v1/stats/activites/count",
            headers={"Authorization": "Basic invalid"}
        )
        assert response.status_code == 401

    @patch('main.httpx.AsyncClient')
    def test_invalid_token_response(self, mock_client_class):
        """Test avec token invalide (réponse 401 du serveur OAuth)"""
        mock_client = AsyncMock()
        mock_response = Mock()
        mock_response.status_code = 401
        mock_client.get = AsyncMock(return_value=mock_response)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)
        mock_client_class.return_value = mock_client

        response = client.get(
            "/v1/stats/activites/count",
            headers={"Authorization": "Bearer invalid_token"}
        )
        assert response.status_code == 401

    @patch('main.httpx.AsyncClient')
    def test_oauth_server_error(self, mock_client_class):
        """Test avec erreur de connexion au serveur OAuth"""
        import httpx
        mock_client = AsyncMock()
        mock_client.get = AsyncMock(side_effect=httpx.RequestError("Connection failed"))
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)
        mock_client_class.return_value = mock_client

        response = client.get(
            "/v1/stats/activites/count",
            headers={"Authorization": "Bearer some_token"}
        )
        assert response.status_code == 401
        assert "Token verification failed" in response.json()["detail"]


# =============================================================================
# Tests custom_openapi
# =============================================================================
class TestCustomOpenAPI:
    """Tests pour la fonction custom_openapi"""

    def test_openapi_schema_cached(self):
        """Test que le schéma OpenAPI est mis en cache"""
        from main import app, custom_openapi

        # Premier appel
        schema1 = custom_openapi()
        # Deuxième appel (doit retourner le cache)
        schema2 = custom_openapi()

        assert schema1 is schema2

    def test_openapi_has_components(self):
        """Test que le schéma a des composants"""
        response = client.get(OPENAPI_ENDPOINT)
        data = response.json()

        assert "components" in data
        assert "securitySchemes" in data["components"]

    def test_openapi_paths_have_security(self):
        """Test que les paths (sauf health) ont la sécurité"""
        response = client.get(OPENAPI_ENDPOINT)
        data = response.json()

        for path, methods in data["paths"].items():
            if "/health" not in path and path != "/redoc":
                for method, details in methods.items():
                    if isinstance(details, dict) and method in ["get", "post", "put", "delete"]:
                        # Les endpoints protégés doivent avoir security
                        if path not in ["/docs", "/openapi.json"]:
                            assert "security" in details or path == "/redoc"


# =============================================================================
# Tests des endpoints Spark avec mocks
# =============================================================================
class TestSparkEndpointsWithMocks:
    """Tests des endpoints Spark avec mocks complets"""

    @patch('main.verify_token')
    @patch('main.get_spark')
    def test_count_by_activity_success(self, mock_get_spark, mock_verify):
        """Test /v1/stats/activites/count avec succès"""
        mock_verify.return_value = {"user": "test"}

        # Mock Spark DataFrame
        mock_row = Mock()
        mock_row.activite_principale_unite_legale = "62.01Z"
        mock_row.siren_count = 1000

        mock_df = Mock()
        mock_df.count.return_value = 1
        mock_df.limit.return_value.offset.return_value.collect.return_value = [mock_row]

        mock_spark = Mock()
        mock_spark.sql.return_value = mock_df
        mock_get_spark.return_value = mock_spark

        response = client.get(
            "/v1/stats/activites/count",
            headers={"Authorization": "Bearer valid_token"}
        )

        assert response.status_code == 200
        data = response.json()
        assert JSONLD_CONTEXT in data
        assert "itemListElement" in data

    @patch('main.verify_token')
    @patch('main.get_spark')
    def test_count_by_activity_spark_error(self, mock_get_spark, mock_verify):
        """Test /v1/stats/activites/count avec erreur Spark"""
        mock_verify.return_value = {"user": "test"}
        mock_spark = Mock()
        mock_spark.sql.side_effect = Exception("Spark connection failed")
        mock_get_spark.return_value = mock_spark

        response = client.get(
            "/v1/stats/activites/count",
            headers={"Authorization": "Bearer valid_token"}
        )

        assert response.status_code == 500
        assert "Spark query failed" in response.json()["detail"]

    @patch('main.verify_token')
    @patch('main.get_spark')
    def test_filter_by_activity_success(self, mock_get_spark, mock_verify):
        """Test /v1/stats/activites/filter avec succès"""
        mock_verify.return_value = {"user": "test"}

        mock_row = Mock()
        mock_row.activite_principale_unite_legale = "62.01Z"
        mock_row.siren_count = 5000

        mock_spark = Mock()
        mock_spark.sql.return_value.collect.return_value = [mock_row]
        mock_get_spark.return_value = mock_spark

        response = client.get(
            "/v1/stats/activites/filter?code=62.01Z",
            headers={"Authorization": "Bearer valid_token"}
        )

        assert response.status_code == 200
        data = response.json()
        assert data["identifier"] == "62.01Z"
        assert data["ratingCount"] == 5000

    @patch('main.verify_token')
    @patch('main.get_spark')
    def test_filter_by_activity_not_found(self, mock_get_spark, mock_verify):
        """Test /v1/stats/activites/filter code non trouvé"""
        mock_verify.return_value = {"user": "test"}

        mock_spark = Mock()
        mock_spark.sql.return_value.collect.return_value = []
        mock_get_spark.return_value = mock_spark

        response = client.get(
            "/v1/stats/activites/filter?code=INVALID",
            headers={"Authorization": "Bearer valid_token"}
        )

        assert response.status_code == 404

    @patch('main.verify_token')
    @patch('main.get_spark')
    def test_filter_by_activity_spark_error(self, mock_get_spark, mock_verify):
        """Test /v1/stats/activites/filter avec erreur Spark"""
        mock_verify.return_value = {"user": "test"}
        mock_spark = Mock()
        mock_spark.sql.side_effect = Exception("Spark error")
        mock_get_spark.return_value = mock_spark

        response = client.get(
            "/v1/stats/activites/filter?code=62.01Z",
            headers={"Authorization": "Bearer valid_token"}
        )

        assert response.status_code == 500

    @patch('main.verify_token')
    @patch('main.get_spark')
    def test_top_activities_success(self, mock_get_spark, mock_verify):
        """Test /v1/stats/activites/top avec succès"""
        mock_verify.return_value = {"user": "test"}

        mock_row1 = Mock()
        mock_row1.activite_principale_unite_legale = "62.01Z"
        mock_row1.siren_count = 10000

        mock_row2 = Mock()
        mock_row2.activite_principale_unite_legale = "47.11Z"
        mock_row2.siren_count = 8000

        mock_spark = Mock()
        mock_spark.sql.return_value.collect.return_value = [mock_row1, mock_row2]
        mock_get_spark.return_value = mock_spark

        response = client.get(
            "/v1/stats/activites/top?limit=2",
            headers={"Authorization": "Bearer valid_token"}
        )

        assert response.status_code == 200
        data = response.json()
        assert data["numberOfItems"] == 2

    @patch('main.verify_token')
    @patch('main.get_spark')
    def test_top_activities_spark_error(self, mock_get_spark, mock_verify):
        """Test /v1/stats/activites/top avec erreur Spark"""
        mock_verify.return_value = {"user": "test"}
        mock_spark = Mock()
        mock_spark.sql.side_effect = Exception("Spark error")
        mock_get_spark.return_value = mock_spark

        response = client.get(
            "/v1/stats/activites/top",
            headers={"Authorization": "Bearer valid_token"}
        )

        assert response.status_code == 500

    @patch('main.verify_token')
    @patch('main.get_spark')
    def test_bottom_activities_success(self, mock_get_spark, mock_verify):
        """Test /v1/stats/activites/bottom avec succès"""
        mock_verify.return_value = {"user": "test"}

        mock_row = Mock()
        mock_row.activite_principale_unite_legale = "99.99Z"
        mock_row.siren_count = 1

        mock_spark = Mock()
        mock_spark.sql.return_value.collect.return_value = [mock_row]
        mock_get_spark.return_value = mock_spark

        response = client.get(
            "/v1/stats/activites/bottom?limit=1",
            headers={"Authorization": "Bearer valid_token"}
        )

        assert response.status_code == 200
        data = response.json()
        assert data["numberOfItems"] == 1

    @patch('main.verify_token')
    @patch('main.get_spark')
    def test_bottom_activities_spark_error(self, mock_get_spark, mock_verify):
        """Test /v1/stats/activites/bottom avec erreur Spark"""
        mock_verify.return_value = {"user": "test"}
        mock_spark = Mock()
        mock_spark.sql.side_effect = Exception("Spark error")
        mock_get_spark.return_value = mock_spark

        response = client.get(
            "/v1/stats/activites/bottom",
            headers={"Authorization": "Bearer valid_token"}
        )

        assert response.status_code == 500


# =============================================================================
# Tests de get_spark
# =============================================================================
class TestGetSpark:
    """Tests pour la fonction get_spark"""

    @patch('main.SparkSession')
    def test_get_spark_creates_session(self, mock_spark_session):
        """Test que get_spark crée une session"""
        from main import get_spark, _spark_session
        import main

        # Reset la session globale
        main._spark_session = None

        mock_builder = Mock()
        mock_builder.appName.return_value = mock_builder
        mock_builder.remote.return_value = mock_builder
        mock_builder.getOrCreate.return_value = Mock()
        mock_spark_session.builder = mock_builder

        result = get_spark()

        assert result is not None
        mock_builder.appName.assert_called_once_with("api-spark")


# =============================================================================
# Tests ReDoc endpoint
# =============================================================================
class TestReDocEndpoint:
    """Tests pour l'endpoint ReDoc"""

    def test_redoc_contains_required_elements(self):
        """Test que ReDoc contient les éléments requis"""
        response = client.get("/redoc")

        assert response.status_code == 200
        html = response.text

        assert "<!DOCTYPE html>" in html
        assert "redoc" in html.lower()
        assert "openapi.json" in html
        assert "redoc@2.1.3" in html

    def test_redoc_content_type(self):
        """Test que ReDoc retourne du HTML"""
        response = client.get("/redoc")

        assert "text/html" in response.headers["content-type"]


# =============================================================================
# Tests des constantes de configuration
# =============================================================================
class TestConfiguration:
    """Tests pour la configuration"""

    def test_spark_connect_host_default(self):
        """Test de la valeur par défaut de SPARK_CONNECT_HOST"""
        from main import SPARK_CONNECT_HOST
        # Soit la valeur d'env, soit la valeur par défaut
        assert SPARK_CONNECT_HOST is not None

    def test_spark_connect_port_default(self):
        """Test de la valeur par défaut de SPARK_CONNECT_PORT"""
        from main import SPARK_CONNECT_PORT
        assert SPARK_CONNECT_PORT is not None

    def test_oauth2_url_default(self):
        """Test de la valeur par défaut de OAUTH2_URL"""
        from main import OAUTH2_URL
        assert OAUTH2_URL is not None
