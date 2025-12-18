"""
API Spark pour les statistiques SIREN
FastAPI avec Spark Connect, Swagger, JSON-LD et OAuth2
"""
from fastapi import FastAPI, Depends, APIRouter, HTTPException, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from pyspark.sql import SparkSession
from typing import List, Optional
import httpx
import math
import os

# Configuration
SPARK_CONNECT_HOST = os.getenv("SPARK_CONNECT_HOST", "spark")
SPARK_CONNECT_PORT = os.getenv("SPARK_CONNECT_PORT", "15002")
OAUTH2_URL = os.getenv("OAUTH2_URL", "http://oauth2:3000")

# Spark session (lazy initialization)
_spark_session = None

def get_spark():
    """Get or create Spark session (lazy initialization)"""
    global _spark_session
    if _spark_session is None:
        _spark_session = SparkSession.builder \
            .appName("api-spark") \
            .remote(f"sc://{SPARK_CONNECT_HOST}:{SPARK_CONNECT_PORT}") \
            .getOrCreate()
    return _spark_session


# OAuth2 Verification
async def verify_token(request: Request):
    """Vérifie le token OAuth2 auprès du service OAuth2"""
    auth_header = request.headers.get("Authorization")

    if not auth_header or not auth_header.startswith("Bearer "):
        raise HTTPException(
            status_code=401,
            detail="Missing or invalid Authorization header"
        )

    token = auth_header.split(" ")[1]

    try:
        # Note: express-oauth-server a des problèmes avec le header Bearer,
        # donc on utilise le query parameter access_token
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{OAUTH2_URL}/v1/secure?access_token={token}"
            )

            if response.status_code != 200:
                raise HTTPException(status_code=401, detail="Invalid token")

            return response.json()
    except Exception as e:
        raise HTTPException(status_code=401, detail=f"Token verification failed: {str(e)}")


def to_jsonld(type_name: str, data: dict) -> dict:
    """Convertit les données en JSON-LD avec contexte Hydra"""
    return {
        "@context": [
            "https://schema.org/",
            {
                "hydra": "http://www.w3.org/ns/hydra/core#",
                "view": "hydra:view",
                "first": "hydra:first",
                "last": "hydra:last",
                "next": "hydra:next",
                "previous": "hydra:previous",
                "totalItems": "hydra:totalItems"
            }
        ],
        "@type": type_name,
        **data
    }


def create_pagination(page: int, limit: int, total: int, base_url: str) -> dict:
    """Crée les métadonnées de pagination avec Hydra"""
    total_pages = math.ceil(total / limit) if total > 0 else 1

    pagination = {
        "page": page,
        "limit": limit,
        "totalItems": total,
        "total_pages": total_pages,
        "has_next": page < total_pages,
        "has_prev": page > 1
    }

    if base_url:
        pagination["view"] = {
            "@id": f"{base_url}?page={page}&limit={limit}",
            "@type": "hydra:PartialCollectionView"
        }

        if page > 1:
            pagination["view"]["first"] = f"{base_url}?page=1&limit={limit}"
            pagination["view"]["previous"] = f"{base_url}?page={page - 1}&limit={limit}"

        if page < total_pages:
            pagination["view"]["next"] = f"{base_url}?page={page + 1}&limit={limit}"
            pagination["view"]["last"] = f"{base_url}?page={total_pages}&limit={limit}"

    return pagination


# Créer l'application FastAPI
app = FastAPI(
    title="API Spark - Statistiques SIREN",
    description="""
    API REST pour analyser les données SIREN via Apache Spark Connect.

    ## Fonctionnalités

    * **Statistiques par activité**: Nombre d'entreprises groupées par code NAF/APE
    * **Filtrage**: Statistiques pour un code activité spécifique
    * **Top/Bottom**: Codes activité les plus et moins représentés
    * **Pagination**: Toutes les listes sont paginées (20 par défaut, paramétrable)
    * **Format JSON-LD**: Toutes les réponses suivent le standard JSON-LD avec Hydra
    * **Authentification OAuth2**: Endpoints protégés par token Bearer

    ## Authentification

    Tous les endpoints (sauf `/health`) nécessitent un token OAuth2 valide.

    1. Obtenir un token depuis l'API OAuth2: `POST http://localhost:3000/oauth/token`
    2. Utiliser le token dans le header: `Authorization: Bearer <token>`

    ## Technologie

    Cette API utilise Apache Spark Connect pour l'analyse analytique des données SIREN.
    """,
    version="1.0.0",
    contact={
        "name": "API Support",
        "email": "support@example.com"
    },
    license_info={
        "name": "ISC",
    },
    docs_url="/docs",
    redoc_url="/redoc"
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Router pour API v1
v1_router = APIRouter(prefix="/v1", tags=["v1"])

@app.on_event("startup")
async def startup():
    """Événement au démarrage"""
    print("=" * 50)
    print("API Spark démarrée")
    print(f"Spark Connect: {SPARK_CONNECT_HOST}:{SPARK_CONNECT_PORT}")
    print("Documentation: http://localhost:3002/docs")
    print("=" * 50)


@app.on_event("shutdown")
async def shutdown():
    """Événement à l'arrêt"""
    get_spark().stop()


@v1_router.get(
    "/health",
    tags=["Health"],
    summary="Vérifier la santé du service"
)
async def health_check():
    """
    Vérifie que le service et Spark Connect fonctionnent correctement.

    **Pas d'authentification requise pour ce endpoint.**
    """
    try:
        # Tester la connexion à Spark
        get_spark().sql("SELECT 1").collect()
        spark_status = "connected"
    except Exception as e:
        spark_status = f"error: {str(e)}"

    return {
        "status": "OK",
        "service": "api-spark",
        "version": "v1",
        "spark_connect": f"{SPARK_CONNECT_HOST}:{SPARK_CONNECT_PORT}",
        "spark_status": spark_status
    }


@v1_router.get(
    "/stats/activites/count",
    tags=["Statistiques"],
    summary="Nombre d'entreprises par code activité",
    responses={
        200: {"description": "Liste des statistiques par activité"},
        401: {"description": "Non authentifié"}
    }
)
async def count_by_activity(
    request: Request,
    page: int = Query(1, ge=1, description="Numéro de page"),
    limit: int = Query(20, ge=1, le=100, description="Nombre d'éléments par page"),
    token_data: dict = Depends(verify_token)
):
    """
    Retourne le nombre d'entreprises groupées par code d'activité principale.

    - **page**: Numéro de page (défaut: 1)
    - **limit**: Nombre d'éléments par page (défaut: 20, max: 100)
    - **Authorization**: Token Bearer OAuth2 requis

    Utilise Spark Connect pour l'agrégation analytique.
    """
    try:
        # Utiliser la vue Spark créée par analyticcli.scala
        df = get_spark().sql("""
            SELECT activite_principale_unite_legale, siren_count
            FROM global_temp.activity
            WHERE activite_principale_unite_legale IS NOT NULL
            ORDER BY siren_count DESC
        """)

        # Compter le total
        total = df.count()

        # Pagination
        offset = (page - 1) * limit
        results = df.limit(limit).offset(offset).collect()

        # Convertir en JSON-LD
        items = [
            {
                "@type": "AggregateRating",
                "@id": f"activity:{row.activite_principale_unite_legale}",
                "identifier": row.activite_principale_unite_legale,
                "ratingCount": int(row.siren_count)
            }
            for row in results
        ]

        base_url = f"{request.url.scheme}://{request.url.netloc}/stats/activites/count"
        pagination = create_pagination(page, limit, total, base_url)

        return to_jsonld("ItemList", {
            "numberOfItems": len(items),
            "itemListElement": items,
            "totalItems": total,
            "pagination": pagination
        })

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Spark query failed: {str(e)}")


@v1_router.get(
    "/stats/activites/filter",
    tags=["Statistiques"],
    summary="Filtrer par code activité",
    responses={
        200: {"description": "Statistique pour le code activité"},
        400: {"description": "Paramètre manquant"},
        401: {"description": "Non authentifié"},
        404: {"description": "Code activité non trouvé"}
    }
)
async def filter_by_activity(
    code: str = Query(..., description="Code d'activité (ex: 62.01Z)"),
    token_data: dict = Depends(verify_token)
):
    """
    Retourne le nombre d'entreprises pour un code d'activité spécifique.

    - **code**: Code d'activité principale (NAF/APE)
    - **Authorization**: Token Bearer OAuth2 requis
    """
    try:
        result = get_spark().sql(f"""
            SELECT activite_principale_unite_legale, siren_count
            FROM global_temp.activity
            WHERE activite_principale_unite_legale = '{code}'
        """).collect()

        if not result:
            raise HTTPException(
                status_code=404,
                detail=f"No data found for activity code: {code}"
            )

        row = result[0]

        return to_jsonld("AggregateRating", {
            "@id": f"activity:{row.activite_principale_unite_legale}",
            "identifier": row.activite_principale_unite_legale,
            "ratingCount": int(row.siren_count)
        })

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Spark query failed: {str(e)}")


@v1_router.get(
    "/stats/activites/top",
    tags=["Statistiques"],
    summary="Codes activité les plus représentés",
    responses={
        200: {"description": "Top des codes activité"},
        401: {"description": "Non authentifié"}
    }
)
async def top_activities(
    limit: int = Query(20, ge=1, le=100, description="Nombre de résultats"),
    token_data: dict = Depends(verify_token)
):
    """
    Retourne les codes d'activité avec le plus grand nombre d'entreprises.

    - **limit**: Nombre de résultats (défaut: 20, max: 100)
    - **Authorization**: Token Bearer OAuth2 requis
    """
    try:
        results = get_spark().sql(f"""
            SELECT activite_principale_unite_legale, siren_count
            FROM global_temp.activity
            WHERE activite_principale_unite_legale IS NOT NULL
            ORDER BY siren_count DESC
            LIMIT {limit}
        """).collect()

        items = [
            {
                "@type": "AggregateRating",
                "@id": f"activity:{row.activite_principale_unite_legale}",
                "identifier": row.activite_principale_unite_legale,
                "ratingCount": int(row.siren_count)
            }
            for row in results
        ]

        return to_jsonld("ItemList", {
            "numberOfItems": len(items),
            "totalItems": len(items),
            "itemListElement": items
        })

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Spark query failed: {str(e)}")


@v1_router.get(
    "/stats/activites/bottom",
    tags=["Statistiques"],
    summary="Codes activité les moins représentés",
    responses={
        200: {"description": "Codes activité les moins représentés"},
        401: {"description": "Non authentifié"}
    }
)
async def bottom_activities(
    limit: int = Query(20, ge=1, le=100, description="Nombre de résultats"),
    token_data: dict = Depends(verify_token)
):
    """
    Retourne les codes d'activité avec le plus petit nombre d'entreprises.

    - **limit**: Nombre de résultats (défaut: 20, max: 100)
    - **Authorization**: Token Bearer OAuth2 requis
    """
    try:
        results = get_spark().sql(f"""
            SELECT activite_principale_unite_legale, siren_count
            FROM global_temp.activity
            WHERE activite_principale_unite_legale IS NOT NULL
            ORDER BY siren_count ASC
            LIMIT {limit}
        """).collect()

        items = [
            {
                "@type": "AggregateRating",
                "@id": f"activity:{row.activite_principale_unite_legale}",
                "identifier": row.activite_principale_unite_legale,
                "ratingCount": int(row.siren_count)
            }
            for row in results
        ]

        return to_jsonld("ItemList", {
            "numberOfItems": len(items),
            "totalItems": len(items),
            "itemListElement": items
        })

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Spark query failed: {str(e)}")


@v1_router.get(
    "/",
    tags=["Info"],
    summary="Information sur l'API"
)
async def root():
    """
    Informations générales sur l'API
    """
    return {
        "service": "API Spark - Statistiques SIREN",
        "version": "v1",
        "technology": "Apache Spark Connect",
        "documentation": "/docs",
        "health": "/v1/health",
        "endpoints": {
            "count_by_activity": "/stats/activites/count",
            "filter_by_activity": "/stats/activites/filter?code={code}",
            "top_activities": "/stats/activites/top",
            "bottom_activities": "/stats/activites/bottom"
        }
    }


# Monter le router v1
app.include_router(v1_router)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=3002)
