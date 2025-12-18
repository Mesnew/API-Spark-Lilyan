"""
Schémas Pydantic pour la validation et sérialisation
Format JSON-LD intégré
"""
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field
from datetime import date


class EntrepriseBase(BaseModel):
    """
    Schéma de base pour une entreprise - Compatible devAPI
    """
    siren: str = Field(..., description="Numéro SIREN (9 chiffres)")
    denomination_unite_legale: Optional[str] = Field(None, description="Dénomination")
    activite_principale_unite_legale: Optional[str] = Field(None, description="Code NAF/APE")
    nomenclature_activite_principale_unite_legale: Optional[str] = Field(None, description="Nomenclature activité")

    class Config:
        from_attributes = True


class EntrepriseJSONLD(BaseModel):
    """
    Entreprise au format JSON-LD avec Hydra
    """
    context: Any = Field(
        default=[
            "https://schema.org/",
            {
                "hydra": "http://www.w3.org/ns/hydra/core#"
            }
        ],
        alias="@context"
    )
    type: str = Field(default="Organization", alias="@type")
    id: str = Field(..., alias="@id", description="URI unique de l'entreprise")
    identifier: str = Field(..., description="Numéro SIREN")
    name: Optional[str] = Field(None, description="Nom de l'entreprise")
    legalName: Optional[str] = Field(None, description="Dénomination légale")
    alternativeName: Optional[str] = Field(None, description="Sigle")
    foundingDate: Optional[str] = Field(None, description="Date de création")
    naics: Optional[str] = Field(None, description="Code activité principale (NAF)")
    numberOfEmployees: Optional[str] = Field(None, description="Tranche d'effectifs")
    legalForm: Optional[str] = Field(None, description="Forme juridique")
    additionalType: Optional[str] = Field(None, description="Catégorie entreprise")
    socialEnterprise: bool = Field(False, description="Entreprise sociale et solidaire")
    isEmployer: bool = Field(False, description="Caractère employeur")

    class Config:
        populate_by_name = True

    @staticmethod
    def from_entreprise(entreprise: EntrepriseBase) -> "EntrepriseJSONLD":
        """
        Convertir une entreprise en format JSON-LD
        """
        return EntrepriseJSONLD(
            **{
                "@id": f"siren:{entreprise.siren}",
                "identifier": entreprise.siren,
                "name": entreprise.denomination_unite_legale,
                "legalName": entreprise.denomination_unite_legale,
                "alternativeName": None,
                "foundingDate": None,
                "naics": entreprise.activite_principale_unite_legale,
                "numberOfEmployees": None,
                "legalForm": None,
                "additionalType": None,
                "socialEnterprise": False,
                "isEmployer": False
            }
        )


class HydraView(BaseModel):
    """
    Vue Hydra pour la pagination
    """
    id: str = Field(..., alias="@id", description="URL de la page actuelle")
    type: str = Field(default="hydra:PartialCollectionView", alias="@type")
    first: Optional[str] = Field(None, description="Première page")
    previous: Optional[str] = Field(None, description="Page précédente")
    next: Optional[str] = Field(None, description="Page suivante")
    last: Optional[str] = Field(None, description="Dernière page")

    class Config:
        populate_by_name = True


class PaginationMeta(BaseModel):
    """
    Métadonnées de pagination avec Hydra
    """
    page: int = Field(..., description="Numéro de page actuelle")
    limit: int = Field(..., description="Nombre d'éléments par page")
    totalItems: int = Field(..., description="Nombre total d'éléments")
    total_pages: int = Field(..., description="Nombre total de pages")
    has_next: bool = Field(..., description="Existence d'une page suivante")
    has_prev: bool = Field(..., description="Existence d'une page précédente")
    view: Optional[HydraView] = Field(None, description="Vue Hydra pour navigation")


class EntrepriseListJSONLD(BaseModel):
    """
    Liste paginée d'entreprises au format JSON-LD avec Hydra
    """
    context: Any = Field(
        default=[
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
        alias="@context"
    )
    type: str = Field(default="ItemList", alias="@type")
    numberOfItems: int = Field(..., description="Nombre d'éléments dans la page")
    totalItems: int = Field(..., description="Nombre total d'éléments")
    itemListElement: List[EntrepriseJSONLD] = Field(..., description="Liste des entreprises")
    pagination: PaginationMeta = Field(..., description="Métadonnées de pagination")

    class Config:
        populate_by_name = True


class HealthResponse(BaseModel):
    """
    Réponse du endpoint health
    """
    status: str = Field(..., example="OK")
    service: str = Field(..., example="api-mysql")
    version: str = Field(..., example="1.0.0")
    database: str = Field(..., example="connected")


class ErrorResponse(BaseModel):
    """
    Réponse d'erreur
    """
    detail: str = Field(..., description="Description de l'erreur")
    status_code: int = Field(..., description="Code HTTP")
