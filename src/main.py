import json
from starlette.applications import Starlette
from starlette.responses import HTMLResponse, JSONResponse
from starlette.routing import Route
from starlette.templating import Jinja2Templates
from starlette.staticfiles import StaticFiles
import uvicorn
import meilisearch

# Load configuration
with open("config.json", "r") as config_file:
    config = json.load(config_file)

MEILI_URL = config.get("MEILI_URL", "http://localhost:7700")
MEILI_API_KEY = config.get("MEILI_API_KEY", "masterKey")

client = meilisearch.Client(MEILI_URL, MEILI_API_KEY)

templates = Jinja2Templates(directory="templates")

async def homepage(request):
    ms_indexes = client.get_indexes()
    # Iterate over the "results" list from the returned dictionary.
    indexes = [index.uid for index in ms_indexes["results"]]
    return templates.TemplateResponse("index.html", {"request": request, "indexes": indexes})

async def search(request):
    query = request.query_params.get('q', '')
    slider_value = request.query_params.get('index', '0')
    try:
        slider_value = int(slider_value)
    except ValueError:
        slider_value = 0

    ms_indexes = client.get_indexes()
    index_list = [index.uid for index in ms_indexes["results"]]

    if not index_list:
        return JSONResponse({"hits": []})

    slider_value = max(0, min(slider_value, len(index_list) - 1))
    selected_index = index_list[slider_value]
    index = client.index(selected_index)
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

