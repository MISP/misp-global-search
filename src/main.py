import json
from starlette.applications import Starlette
from starlette.responses import JSONResponse
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

TAXONOMIES_INDEX = 'misp-taxonomies'

async def homepage(request):
    ms_indexes = admin.get_indexes()
    indexes = [index.uid for index in ms_indexes["results"]]
    return templates.TemplateResponse(
        "index.html", {"request": request, "indexes": indexes}
    )


async def get_paging_params(request):
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
    return page, page_size, offset


def perform_multisearch(index_list, query, page_size, offset, filter_string):
    request = []
    for index in index_list:
        if index != TAXONOMIES_INDEX:
            request.append(
                {
                    "indexUid": index,
                    "q": query,
                    "attributesToHighlight": ["*"],
                    "highlightPreTag": "<mark>",
                    "highlightPostTag": "</mark>",
                }
            )
        else:
            request.append(
                {
                    "indexUid": index,
                    "q": query,
                    "attributesToHighlight": ["*"],
                    "highlightPreTag": "<mark>",
                    "highlightPostTag": "</mark>",
                    "filter": filter_string
                }
            )

    multisearch_options = {"limit": page_size, "offset": offset}
    return client.multi_search(request, multisearch_options)


def perform_singlesearch(index_list, query, search_options, index_param):
    try:
        index_position = int(index_param)
    except ValueError:
        index_position = 0
    index_position = max(0, min(index_position, len(index_list) - 1))
    selected_index = index_list[index_position]
    if selected_index != TAXONOMIES_INDEX and 'filter' in search_options:
        del search_options['filter'] 
    return client.index(selected_index).search(query, search_options)


def build_search_options(page_size, offset, filter_string=None):
    options = {
        "limit": page_size,
        "offset": offset,
        "attributesToHighlight": ["*"],
        "highlightPreTag": "<mark>",
        "highlightPostTag": "</mark>",
    }
    if filter_string:
        options["filter"] = filter_string
    return options


def build_filter_query(filters):
    filter_string = ''
    if not filters:
        return None
    else:
        if "namespace" in filters:
            expression = 'version EXISTS' 
            if len(filter_string) == 0:
                filter_string += f'{expression}'
            else:
                filter_string += f' OR {expression}'
        if "predicates" in filters:
            expression = '((namespace EXISTS) AND (NOT version EXISTS) AND (NOT predicate EXISTS))' 
            if len(filter_string) == 0:
                filter_string += f'{expression}'
            else:
                filter_string += f' OR {expression}'
        if "values" in filters:
            expression = 'predicate EXISTS' 
            if len(filter_string) == 0:
                filter_string += f'{expression}'
            else:
                filter_string += f' OR {expression}'
    return filter_string


async def search(request):
    query = request.query_params.get("q", "")
    index_param = request.query_params.get("index", "0")

    filters = request.query_params.get("filters", None)
    page, page_size, offset = await get_paging_params(request)

    ms_indexes = admin.get_indexes()
    index_list = [index.uid for index in ms_indexes["results"]]

    filter_string = build_filter_query(filters)
    search_options = build_search_options(page_size, offset, filter_string)

    if not index_list:
        return JSONResponse({"hits": []})

    if index_param == "all":
        results = perform_multisearch(index_list, query, page_size, offset, filter_string)
    else:
        results = perform_singlesearch(index_list, query, search_options, index_param)

    return JSONResponse(results)


routes = [Route("/", homepage), Route("/search", search)]

app = Starlette(debug=True, routes=routes)
app.mount("/static", StaticFiles(directory="static"), name="static")

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8001)
