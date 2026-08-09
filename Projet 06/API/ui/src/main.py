from fastapi import FastAPI, Request, Form
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

import requests

from .config import BENTO_URL, HTTP_TIMEOUT

app = FastAPI()
templates=Jinja2Templates(directory="templates")

@app.get("/", response_class=HTMLResponse)
def show_from(request: Request):
    return templates.TemplateResponse(
        "form.html", 
        {
            "request": request,
            "form": {},
            "prediction": None,
            "error": None,
        }
    )

@app.post("/predict/", response_class=HTMLResponse)
def predict(
    request: Request,
    property_gfa_total: float = Form(...),
    property_gfa_parking: float = Form(...),
    year_built: int = Form(...),
    number_of_floors: int = Form(...),
    number_of_buildings: int = Form(...),
    primary_property_type: str = Form(...),
    largest_property_use_type: str = Form(...),
    neighborhood: str = Form(...),
    largest_property_use_gfa: float = Form(...),
    latitude: float = Form(...),
    longitude: float = Form(...)
):
    
    payload = {
        "PropertyGFATotal": property_gfa_total,
        "PropertyGFAParking": property_gfa_parking,
        "YearBuilt": year_built,
        "NumberofFloors": number_of_floors,
        "NumberofBuildings": number_of_buildings,
        "PrimaryPropertyType": primary_property_type,
        "LargestPropertyUseType": largest_property_use_type,
        "Neighborhood": neighborhood,
        "LargestPropertyUseTypeGFA": largest_property_use_gfa,
        "Latitude": latitude,
        "Longitude": longitude,
    }
    
    try:
        response = requests.post(BENTO_URL, json={"input_data": payload}, timeout=HTTP_TIMEOUT)
    except requests.exceptions.RequestException:
        return templates.TemplateResponse(
            "form.html", 
            {
                "request": request,
                "form": payload,
                "prediction": None,
                "error": "Service de prédiction indisponible (BentoML inaccessible). Veuillez réessayer plus tard.",
            }, 
            status_code=503,
        )

    if response.status_code != 200:
        return templates.TemplateResponse(
            "form.html", 
            {
                "request": request,
                "form": payload,
                "prediction": None,
                "error": response.text,
            },
            status_code=400
        )

    result = response.json()

    return templates.TemplateResponse(
        "form.html",
        {
            "request": request,
            "form": payload,
            "prediction": result,
            "error": None,
        },
        status_code=200
    )