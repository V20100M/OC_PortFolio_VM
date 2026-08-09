from pydantic import BaseModel, Field, validator

class BuildingInput(BaseModel):
    PropertyGFATotal: float = Field(..., gt=0)
    PropertyGFAParking: float = Field(..., ge=0)
    YearBuilt: int = Field(..., ge=1800)
    NumberofFloors: int = Field(..., ge=0)
    NumberofBuildings: int = Field(..., ge=1)
    
    PrimaryPropertyType: str
    LargestPropertyUseType: str
    Neighborhood: str
    
    LargestPropertyUseTypeGFA: float = Field(..., gt=0)
    
    Latitude: float = Field(..., ge=47.0, le=48.0)
    Longitude: float = Field(..., ge=-123.0, le=-121.0)
    
    @validator("LargestPropertyUseTypeGFA")
    def check_gfa_coherence(cls, v, values):
        if "PropertyGFATotal" in values and v > values["PropertyGFATotal"]:
            raise ValueError("LargestPropertyUseTypeGFA ne peut pas être supérieur à PropertyGFATotal")
        return v
    
    class Config:
        extra = "forbid"
        
class PredictionOutput(BaseModel):
	site_energy_use_kbtu: float = Field(..., gt=0)
	total_ghg_emissions: float = Field(..., ge=0)