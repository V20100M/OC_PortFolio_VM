import pandas as pd
import numpy as np

DATASET_YEAR = 2016
MULTI_USE_THRESHOLD = 0.9

def build_features(payload: dict) -> pd.DataFrame:
    df = pd.DataFrame([payload])

    # Gestion des divisions par zéro
    gfa_total = df["PropertyGFATotal"].replace(0, np.nan)
    nb_buildings = df["NumberofBuildings"].replace(0, np.nan)

    # Ratios de surface
    df["GFA_Building_Ratio"] = (
        (df["PropertyGFATotal"] - df["PropertyGFAParking"]) / gfa_total
    )

    df["GFA_Parking_Ratio"] = df["PropertyGFAParking"] / gfa_total

    # Log surface totale
    df["Log_PropertyGFATotal"] = np.log1p(df["PropertyGFATotal"])

    # Temporalité
    df["Building_Age"] = DATASET_YEAR - df["YearBuilt"]
    df["YearBuilt_Decade"] = (df["YearBuilt"] // 10 * 10).astype("Int64")

    # Structure
    df["Floors_per_Building"] = df["NumberofFloors"] / nb_buildings

    df["Floors_Class"] = pd.cut(
        df["NumberofFloors"],
        bins=[0, 2, 5, 10, 20, np.inf],
        labels=["1-2", "3-5", "6-10", "11-20", "20+"]
    )

    # Usage
    df["LargestUse_GFA_Ratio"] = (
        df["LargestPropertyUseTypeGFA"] / gfa_total
    )

    df["Is_MultiUse"] = (df["LargestUse_GFA_Ratio"] < MULTI_USE_THRESHOLD).astype("Int64")

    # Nettoyage final
    df.replace([np.inf, -np.inf], np.nan, inplace=True)

    return df