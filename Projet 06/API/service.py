import bentoml
import pandas as pd

from preprocessing import build_features
from schemas import BuildingInput, PredictionOutput

# Chargement du modèle entraîné
model_ref = bentoml.sklearn.get("seattle_energy_model:latest")
model = model_ref.load_model()

# Définition du service
@bentoml.service(name="seattle_energy_service")
class SeattleEnergyService:
    
    @bentoml.api
    def predict(self, input_data: BuildingInput) -> PredictionOutput:
        
        # Construction des features exactement comme en entraînement
        payload = input_data.model_dump()
        df = build_features(payload)
        
        # Prédit la consommation énergétique à partir des données d'entrée
        prediction = model.predict(df)
        
        if prediction is None or len(prediction) == 0:
            raise ValueError("Erreur lors de la prédiction du modèle.")

        return PredictionOutput(
            site_energy_use_kbtu=float(prediction[0][0]),
            total_ghg_emissions=float(prediction[0][1])
        )
