import uvicorn
import requests
import io
import os
from fastapi import FastAPI, UploadFile, File, HTTPException, Query # Added Query
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.openapi.utils import get_openapi
from PIL import Image
from ultralytics import YOLO

app = FastAPI(docs_url=None, redoc_url=None, openapi_url=None)

# 1. DYNAMIC OPENAPI ROUTE (Must be above app.mount)
@app.get("/assets/openapi.json", include_in_schema=False)
async def get_openapi_json():
    return JSONResponse(get_openapi(
        title="Herkenbaar API",
        version="0.2.0",
        description="API voor het bepalen of er op een afbeelding mensen zijn te herkennen (i.v.m. portretrecht).",
        routes=app.routes,
    ))

# 2. STATIC ASSETS
os.makedirs("assets", exist_ok=True)
app.mount("/assets", StaticFiles(directory="assets"), name="assets")

model = YOLO("yolo26n-pose.pt")

def process_image(img_pil: Image.Image):
    MAX_SIZE = 1280
    if max(img_pil.size) > MAX_SIZE:
        img_pil.thumbnail((MAX_SIZE, MAX_SIZE), Image.Resampling.LANCZOS)
    
    results = model(img_pil, verbose=False)[0]
    recognized = "nee"
    max_conf = 0.0
    
    if len(results.boxes) > 0:
        for i, box in enumerate(results.boxes):
            conf = float(box.conf[0])
            max_conf = max(max_conf, conf)
            kpts = results.keypoints.conf[i][:5]
            visible_face_points = (kpts > 0.5).sum()
            if conf > 0.6 and visible_face_points >= 3:
                recognized = "ja"
                break
                
    return {"herkenbaar": recognized, "betrouwbaarheid": round(max_conf, 4)}

# --- API Endpoints ---

@app.post("/herken-img", summary="Herken in afbeelding via uplaod", description="Upload een afbeelding om te controleren of er herkenbare personen op staan.")
async def herken_img(file: UploadFile = File(...)):
    try:
        data = await file.read()
        img = Image.open(io.BytesIO(data)).convert("RGB")
        return process_image(img)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Ongeldige afbeelding: {str(e)}")

@app.get("/herken-url", summary="Herken in afbeelding via URL", description="Geef een URL van een onlien afbeelding om te controleren of er herkenbare personen op staan.")
async def herken_url(
    url: str = Query(
        ...,
        description="URL van de afbeelding uit het archief",
        openapi_examples={
            "Voorbeeld 1": {
                "summary": "Buurtfoto (SAMH 0440. 58443) > ja",
                "value": "https://webservices.memorix.nl/mediabank/media/1b385bf0-1f1a-5a9d-30ae-2e0e9b3a203b/downloadoriginal/43fb2d11-6ba5-3809-b9e1-c7e96f910b64?apiKey=192a1d7b-4a05-45c3-bd2c-366cbb8ec880"
            },
            "Voorbeeld 2": {
                "summary": "Mensen in de verte (SAMH 0440. 28420) > nee",
                "value": "https://webservices.memorix.nl/mediabank/media/7af4bbd0-c697-893c-a698-82331ba98964/downloadoriginal/347ec52f-a92a-d6a1-7b47-b7be4f308a3a?apiKey=192a1d7b-4a05-45c3-bd2c-366cbb8ec880"
            },
            "Voorbeeld 3": {
                "summary": "Muzikanten (SAMH 0440. 65597) > ja",
                "value": "https://webservices.memorix.nl/mediabank/media/18f11261-fb82-1eac-10c1-42024b4d7d18/downloadoriginal/70abac34-1e49-d885-55bb-50f24d02f482?apiKey=192a1d7b-4a05-45c3-bd2c-366cbb8ec880"
            },
            "Voorbeeld 4": {
                "summary": "Straatbeeld 1 (SAMH 0440. 72109) > nee",
                "value": "https://webservices.memorix.nl/mediabank/media/df124bbe-f1a3-2f3a-af27-1d6211390a3f/downloadoriginal/91cd9556-c1ab-15b2-c86c-af842862c89d?apiKey=192a1d7b-4a05-45c3-bd2c-366cbb8ec880"
            },
            "Voorbeeld 5": {
                "summary": "Bijeenkomst (SAMH 0440. 86696) > ja",
                "value": "https://webservices.memorix.nl/mediabank/media/666c5fe6-7c91-c51c-8593-0ff004085692/downloadoriginal/7c9cdd3e-07ac-ff25-76aa-e29948d247da?apiKey=192a1d7b-4a05-45c3-bd2c-366cbb8ec880"
            },
            "Voorbeeld 6": {
                "summary": "Gevellijst (SAMH 0440. 3118) > nee",
                "value": "https://webservices.memorix.nl/mediabank/media/90cc13a9-ba1f-575d-c27c-cb8b19c1c3e2/downloadoriginal/180ff8d5-5f16-fa95-f025-91b54fb7f168?apiKey=192a1d7b-4a05-45c3-bd2c-366cbb8ec880"
            },
            "Voorbeeld 7": {
                "summary": "Straatbeeld 2 (SAMH 0440. 61155) > nee",
                "value": "https://webservices.memorix.nl/mediabank/media/0332b9b3-68b1-7e64-d3ae-8ba231dc440a/downloadoriginal/e6029902-fbd7-3800-66e3-f8f7441450ae?apiKey=192a1d7b-4a05-45c3-bd2c-366cbb8ec880"
            },
        }
    )
):
    try:
        response = requests.get(url, timeout=10)
        img = Image.open(io.BytesIO(response.content)).convert("RGB")
        return process_image(img)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Ongeldige URL: {str(e)}")


@app.get("/", response_class=HTMLResponse, include_in_schema=False)
async def custom_swagger_ui():
    return """
    <!DOCTYPE html><html lang="nl">
    <head>
      <meta charset="UTF-8">
      <title>Herkenbaar API</title>
      <link rel="stylesheet" type="text/css" href="assets/swagger-ui.css">
      <link rel="stylesheet" type="text/css" href="assets/style.css">
    </head>
    <body>
      <div id="swagger-ui"></div>
      <script src="assets/swagger-ui-standalone-preset.js"></script>
      <script src="assets/swagger-ui-bundle.js"></script>
      <script>
        window.onload = function () {
          const ui = SwaggerUIBundle({
            url: "assets/openapi.json",
            dom_id: '#swagger-ui',
            deepLinking: true,
            presets: [
              SwaggerUIBundle.presets.apis,
              SwaggerUIStandalonePreset
            ],
            layout: "StandaloneLayout"
          })
          window.ui = ui
        }
      </script>
    </body>
    </html>
    """

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=4050)

     