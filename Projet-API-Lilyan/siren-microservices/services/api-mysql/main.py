"""
API MySQL pour les entreprises SIREN
FastAPI avec Swagger, JSON-LD et OAuth2
"""
from fastapi import FastAPI, Depends, HTTPException, Query, Request, APIRouter
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from sqlalchemy import func, or_
from typing import List, Optional
import math

from database import get_db, engine
from models import UniteLegale
import schemas
from auth import verify_token


def create_hydra_view(base_url: str, page: int, limit: int, total_pages: int) -> Optional[schemas.HydraView]:
    """
    Crée une vue Hydra pour la pagination
    """
    if total_pages <= 0:
        return None

    view = schemas.HydraView(
        **{
            "@id": f"{base_url}?page={page}&limit={limit}",
            "@type": "hydra:PartialCollectionView"
        }
    )

    # Ajouter les liens de navigation
    if page > 1:
        view.first = f"{base_url}?page=1&limit={limit}"
        view.previous = f"{base_url}?page={page - 1}&limit={limit}"

    if page < total_pages:
        view.next = f"{base_url}?page={page + 1}&limit={limit}"
        view.last = f"{base_url}?page={total_pages}&limit={limit}"

    return view

# Créer l'application FastAPI
app = FastAPI(
    title="API MySQL - Entreprises SIREN",
    description="""
    API REST pour interroger la base de données SIREN des entreprises françaises.

    ## Fonctionnalités

    * **Recherche par SIREN**: Récupérer une entreprise par son numéro SIREN
    * **Recherche par activité**: Trouver les entreprises par code NAF/APE
    * **Recherche par nom**: Rechercher des entreprises par nom ou dénomination
    * **Pagination**: Toutes les listes sont paginées (20 par défaut, paramétrable)
    * **Format JSON-LD**: Toutes les réponses suivent le standard JSON-LD
    * **Authentification OAuth2**: Endpoints protégés par token Bearer

    ## Authentification

    Tous les endpoints (sauf `/health`) nécessitent un token OAuth2 valide.

    1. Obtenir un token depuis l'API OAuth2: `POST http://localhost:3000/oauth/token`
    2. Utiliser le token dans le header: `Authorization: Bearer <token>`

    ## Pagination

    Les endpoints de liste supportent la pagination:
    - `page`: Numéro de page (défaut: 1)
    - `limit`: Nombre d'éléments par page (défaut: 20, max: 100)

    ## Format JSON-LD

    Les réponses utilisent le contexte Schema.org pour une interopérabilité maximale.
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
    print("API MySQL démarrée (v1)")
    print("Documentation: http://localhost:3001/docs")
    print("Endpoints: http://localhost:3001/v1/")
    print("=" * 50)


@v1_router.get(
    "/health",
    response_model=schemas.HealthResponse,
    tags=["Health"],
    summary="Vérifier la santé du service"
)
async def health_check(db: Session = Depends(get_db)):
    """
    Vérifie que le service et la base de données fonctionnent correctement.

    **Pas d'authentification requise pour ce endpoint.**
    """
    try:
        # Tester la connexion à la DB
        db.execute("SELECT 1")
        db_status = "connected"
    except Exception as e:
        db_status = f"error: {str(e)}"

    return {
        "status": "OK",
        "service": "api-mysql",
        "version": "1.0.0",
        "database": db_status
    }


@v1_router.get(
    "/entreprises/siren/{siren}",
    response_model=schemas.EntrepriseJSONLD,
    tags=["Entreprises"],
    summary="Récupérer une entreprise par SIREN",
    responses={
        200: {"description": "Entreprise trouvée"},
        401: {"description": "Non authentifié"},
        404: {"description": "Entreprise non trouvée"}
    }
)
async def get_entreprise_by_siren(
    siren: str,
    token_data: dict = Depends(verify_token),
    db: Session = Depends(get_db)
):
    """
    Récupère une entreprise par son numéro SIREN.

    - **siren**: Numéro SIREN à 9 chiffres
    - **Authorization**: Token Bearer OAuth2 requis
    """
    # Valider le format SIREN
    if len(siren) != 9 or not siren.isdigit():
        raise HTTPException(status_code=400, detail="SIREN must be 9 digits")

    # Rechercher l'entreprise
    entreprise = db.query(UniteLegale).filter(UniteLegale.siren == siren).first()

    if not entreprise:
        raise HTTPException(status_code=404, detail="Entreprise not found")

    # Convertir en format JSON-LD
    entreprise_data = schemas.EntrepriseBase.from_orm(entreprise)
    return schemas.EntrepriseJSONLD.from_entreprise(entreprise_data)


@v1_router.get(
    "/entreprises/activite/{code}",
    response_model=schemas.EntrepriseListJSONLD,
    tags=["Entreprises"],
    summary="Rechercher par code activité",
    responses={
        200: {"description": "Liste des entreprises"},
        401: {"description": "Non authentifié"}
    }
)
async def get_entreprises_by_activite(
    request: Request,
    code: str,
    page: int = Query(1, ge=1, description="Numéro de page"),
    limit: int = Query(20, ge=1, le=100, description="Nombre d'éléments par page"),
    token_data: dict = Depends(verify_token),
    db: Session = Depends(get_db)
):
    """
    Récupère toutes les entreprises ayant un code activité donné (NAF/APE).

    - **code**: Code activité principale (ex: "62.01Z", "47.11F")
    - **page**: Numéro de page (défaut: 1)
    - **limit**: Nombre d'éléments par page (défaut: 20, max: 100)
    - **Authorization**: Token Bearer OAuth2 requis

    La réponse est paginée et au format JSON-LD.
    """
    # Calculer l'offset
    offset = (page - 1) * limit

    # Compter le total
    total = db.query(func.count(UniteLegale.siren)).filter(
        UniteLegale.activite_principale_unite_legale == code
    ).scalar()

    # Récupérer les entreprises
    entreprises = db.query(UniteLegale).filter(
        UniteLegale.activite_principale_unite_legale == code
    ).offset(offset).limit(limit).all()

    # Convertir en JSON-LD
    entreprises_jsonld = [
        schemas.EntrepriseJSONLD.from_entreprise(schemas.EntrepriseBase.from_orm(e))
        for e in entreprises
    ]

    # Calculer les métadonnées de pagination
    total_pages = math.ceil(total / limit) if total > 0 else 1
    base_url = f"{request.url.scheme}://{request.url.netloc}/entreprises/activite/{code}"

    hydra_view = create_hydra_view(base_url, page, limit, total_pages)

    pagination = schemas.PaginationMeta(
        page=page,
        limit=limit,
        totalItems=total,
        total_pages=total_pages,
        has_next=page < total_pages,
        has_prev=page > 1,
        view=hydra_view
    )

    return schemas.EntrepriseListJSONLD(
        **{
            "numberOfItems": len(entreprises_jsonld),
            "totalItems": total,
            "itemListElement": entreprises_jsonld,
            "pagination": pagination
        }
    )


@v1_router.get(
    "/entreprises/search",
    response_model=schemas.EntrepriseListJSONLD,
    tags=["Entreprises"],
    summary="Rechercher par nom",
    responses={
        200: {"description": "Liste des entreprises"},
        401: {"description": "Non authentifié"},
        400: {"description": "Paramètre manquant"}
    }
)
async def search_entreprises_by_name(
    request: Request,
    nom: str = Query(..., min_length=3, description="Nom ou dénomination à rechercher (min 3 caractères)"),
    page: int = Query(1, ge=1, description="Numéro de page"),
    limit: int = Query(20, ge=1, le=100, description="Nombre d'éléments par page"),
    token_data: dict = Depends(verify_token),
    db: Session = Depends(get_db)
):
    """
    Recherche des entreprises par nom ou dénomination.

    La recherche est effectuée sur:
    - Le nom de l'unité légale
    - La dénomination

    - **nom**: Terme de recherche (minimum 3 caractères)
    - **page**: Numéro de page (défaut: 1)
    - **limit**: Nombre d'éléments par page (défaut: 20, max: 100)
    - **Authorization**: Token Bearer OAuth2 requis

    La recherche est insensible à la casse et supporte les correspondances partielles.
    """
    # Calculer l'offset
    offset = (page - 1) * limit

    # Pattern de recherche (LIKE avec wildcards)
    search_pattern = f"%{nom}%"

    # Compter le total
    total = db.query(func.count(UniteLegale.siren)).filter(
        UniteLegale.denomination_unite_legale.ilike(search_pattern)
    ).scalar()

    # Récupérer les entreprises
    entreprises = db.query(UniteLegale).filter(
        UniteLegale.denomination_unite_legale.ilike(search_pattern)
    ).offset(offset).limit(limit).all()

    # Convertir en JSON-LD
    entreprises_jsonld = [
        schemas.EntrepriseJSONLD.from_entreprise(schemas.EntrepriseBase.from_orm(e))
        for e in entreprises
    ]

    # Calculer les métadonnées de pagination
    total_pages = math.ceil(total / limit) if total > 0 else 1
    base_url = f"{request.url.scheme}://{request.url.netloc}/entreprises/search"

    hydra_view = create_hydra_view(f"{base_url}?nom={nom}", page, limit, total_pages)

    pagination = schemas.PaginationMeta(
        page=page,
        limit=limit,
        totalItems=total,
        total_pages=total_pages,
        has_next=page < total_pages,
        has_prev=page > 1,
        view=hydra_view
    )

    return schemas.EntrepriseListJSONLD(
        **{
            "numberOfItems": len(entreprises_jsonld),
            "totalItems": total,
            "itemListElement": entreprises_jsonld,
            "pagination": pagination
        }
    )


@v1_router.get(
    "/entreprises/filter",
    response_model=schemas.EntrepriseListJSONLD,
    tags=["Entreprises"],
    summary="Rechercher avec filtres multiples",
    responses={
        200: {"description": "Liste des entreprises"},
        401: {"description": "Non authentifié"},
        400: {"description": "Au moins un paramètre requis"}
    }
)
async def filter_entreprises(
    request: Request,
    nom: Optional[str] = Query(None, min_length=3, description="Nom ou dénomination à rechercher (min 3 caractères)"),
    activite: Optional[str] = Query(None, description="Code d'activité principale"),
    page: int = Query(1, ge=1, description="Numéro de page"),
    limit: int = Query(20, ge=1, le=100, description="Nombre d'éléments par page"),
    token_data: dict = Depends(verify_token),
    db: Session = Depends(get_db)
):
    """
    Recherche des entreprises avec filtres combinables.

    Permet de combiner plusieurs critères de recherche:
    - **nom**: Terme de recherche sur le nom/dénomination (minimum 3 caractères)
    - **activite**: Code d'activité principale (NAF/APE)
    - **page**: Numéro de page (défaut: 1)
    - **limit**: Nombre d'éléments par page (défaut: 20, max: 100)
    - **Authorization**: Token Bearer OAuth2 requis

    Au moins un des paramètres 'nom' ou 'activite' doit être fourni.
    """
    # Valider qu'au moins un filtre est fourni
    if not nom and not activite:
        raise HTTPException(
            status_code=400,
            detail="At least one filter parameter (nom or activite) is required"
        )

    # Calculer l'offset
    offset = (page - 1) * limit

    # Construire la requête dynamiquement
    query = db.query(UniteLegale)
    filters = []

    if nom:
        search_pattern = f"%{nom}%"
        filters.append(UniteLegale.denomination_unite_legale.ilike(search_pattern))

    if activite:
        filters.append(UniteLegale.activite_principale_unite_legale == activite)

    # Appliquer tous les filtres
    if filters:
        query = query.filter(*filters)

    # Compter le total
    total = query.count()

    # Récupérer les entreprises
    entreprises = query.offset(offset).limit(limit).all()

    # Convertir en JSON-LD
    entreprises_jsonld = [
        schemas.EntrepriseJSONLD.from_entreprise(schemas.EntrepriseBase.from_orm(e))
        for e in entreprises
    ]

    # Calculer les métadonnées de pagination
    total_pages = math.ceil(total / limit) if total > 0 else 1

    # Construire l'URL de base avec les paramètres
    params = []
    if nom:
        params.append(f"nom={nom}")
    if activite:
        params.append(f"activite={activite}")
    base_url = f"{request.url.scheme}://{request.url.netloc}/entreprises/filter"
    base_url_with_params = f"{base_url}?{'&'.join(params)}" if params else base_url

    hydra_view = create_hydra_view(base_url_with_params, page, limit, total_pages)

    pagination = schemas.PaginationMeta(
        page=page,
        limit=limit,
        totalItems=total,
        total_pages=total_pages,
        has_next=page < total_pages,
        has_prev=page > 1,
        view=hydra_view
    )

    return schemas.EntrepriseListJSONLD(
        **{
            "numberOfItems": len(entreprises_jsonld),
            "totalItems": total,
            "itemListElement": entreprises_jsonld,
            "pagination": pagination
        }
    )


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
        "service": "API MySQL - Entreprises SIREN",
        "version": "v1",
        "documentation": "/docs",
        "health": "/v1/health",
        "endpoints": {
            "by_siren": "/v1/entreprises/siren/{siren}",
            "by_activite": "/v1/entreprises/activite/{code}",
            "search": "/v1/entreprises/search?nom={term}",
            "filter": "/v1/entreprises/filter?nom={term}&activite={code}"
        }
    }


# Monter le router v1
app.include_router(v1_router)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=3001)
