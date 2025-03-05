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
MEILI_ADMIN_API_KEY = config.get("MEILI_ADMIN_API_KEY")
MEILI_API_KEY = config.get("MEILI_API_KEY")

admin = meilisearch.Client(MEILI_URL, MEILI_ADMIN_API_KEY)
client = meilisearch.Client(MEILI_URL, MEILI_API_KEY)

templates = Jinja2Templates(directory="templates")


async def homepage(request):
    ms_indexes = admin.get_indexes()
    indexes = [index.uid for index in ms_indexes["results"]]
    return templates.TemplateResponse(
        "index.html", {"request": request, "indexes": indexes}
    )


async def search(request):
    query = request.query_params.get("q", "")
    index_param = request.query_params.get("index", "0")

    try:
        page = int(request.query_params.get("page", "1"))
    except ValueError:
        page = 1
    page = max(page, 1)

    try:
        page_size = int(request.query_params.get("pageSize", "10"))
    except ValueError:
        page_size = 10
    page_size = max(page_size, 1)
    offset = (page - 1) * page_size
    
    ms_indexes = admin.get_indexes()
    index_list = [index.uid for index in ms_indexes["results"]]

    if not index_list:
        return JSONResponse({"hits": []})

    if index_param == "all":
        request = []
        for index in index_list:
            request.append(
                {
                    "indexUid": index,
                    "q": query,
                    "attributesToHighlight": ["*"],
                    "highlightPreTag": "<mark>",
                    "highlightPostTag": "</mark>",
                }
            )
        results = client.multi_search(
            request,
            {
                "limit": page_size,
                "offset": offset,
            },
        )
        return JSONResponse(results)
    else:
        try:
            index_position = int(index_param)
        except ValueError:
            index_position = 0
        index_position = max(0, min(index_position, len(index_list) - 1))
        selected_index = index_list[index_position]
        results = client.index(selected_index).search(
            query,
            {
                "attributesToHighlight": ["*"],
                "highlightPreTag": "<mark>",
                "highlightPostTag": "</mark>",
                "limit": page_size,
                "offset": offset,
            },
        )
        return JSONResponse(results)


routes = [Route("/", homepage), Route("/search", search)]

app = Starlette(debug=True, routes=routes)
app.mount("/static", StaticFiles(directory="static"), name="static")

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8001)
