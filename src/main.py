import json
from starlette.applications import Starlette
from starlette.responses import HTMLResponse, JSONResponse
from starlette.routing import Route
from starlette.templating import Jinja2Templates
from starlette.staticfiles import StaticFiles
import uvicorn
import meilisearch

with open("config.json", "r") as config_file:
    config = json.load(config_file)

MEILI_URL = config.get("MEILI_URL", "http://localhost:7700")
MEILI_API_KEY = config.get("MEILI_API_KEY", "masterKey")
INDEX_NAME = config.get("INDEX_NAME", "your_index_name")

client = meilisearch.Client(MEILI_URL, MEILI_API_KEY)

templates = Jinja2Templates(directory="templates")

async def homepage(request):
    return templates.TemplateResponse("index.html", {"request": request})

async def search(request):
    query = request.query_params.get('q', '')
    index = client.index(INDEX_NAME)
    results = index.search(query)
    return JSONResponse(results)

routes = [
    Route("/", homepage),
    Route("/search", search)
]

app = Starlette(debug=True, routes=routes)

app.mount('/static', StaticFiles(directory='static'), name='static')

if __name__ == '__main__':
    uvicorn.run(app, host="0.0.0.0", port=8000)

