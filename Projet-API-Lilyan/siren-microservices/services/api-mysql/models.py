"""
Modèles SQLAlchemy pour la base de données SIREN
"""
from sqlalchemy import Column, String, Integer, Date
from database import Base


class UniteLegale(Base):
    """
    Table des unités légales (entreprises) - Schéma compatible devAPI
    """
    __tablename__ = "unite_legale"

    # Colonnes du schéma devAPI (version simplifiée)
    siren = Column(String(9), primary_key=True, index=True)
    denomination_unite_legale = Column(String(100), index=True)
    activite_principale_unite_legale = Column(String(6), index=True)
    nomenclature_activite_principale_unite_legale = Column(String(8))

    def to_dict(self):
        """
        Convertir en dictionnaire
        """
        return {
            "siren": self.siren,
            "denomination": self.denomination_unite_legale,
            "activite_principale": self.activite_principale_unite_legale,
            "nomenclature_activite": self.nomenclature_activite_principale_unite_legale
        }
