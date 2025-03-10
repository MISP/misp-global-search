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
GALAXY_INDEX = 'misp-galaxy'  

async def homepage(request):
    ms_indexes = admin.get_indexes()
    # Exclude indexes ending with "_new"
    indexes = [index.uid for index in ms_indexes["results"] if not index.uid.endswith("_new")]
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

def build_filter_query(taxonomy_filters, galaxy_filters):
    taxonomy_filter_string = None
    if taxonomy_filters:
        taxonomy_options = taxonomy_filters.split(',')
        expressions = []
        if "namespaces" in taxonomy_options:
            expressions.append("version EXISTS")
        if "predicates" in taxonomy_options:
            expressions.append("((namespace EXISTS) AND (NOT version EXISTS) AND (NOT predicate EXISTS))")
        if "values" in taxonomy_options:
            expressions.append("predicate EXISTS")
        if expressions:
            taxonomy_filter_string = " OR ".join(expressions)

    galaxy_filter_string = None
    if galaxy_filters:
        galaxy_options = galaxy_filters.split(',')
        expressions = []
        for option in galaxy_options:
            option = option.strip()
            if option:
                expressions.append(f"galaxy = '{option}'")
        if expressions:
            galaxy_filter_string = " OR ".join(expressions)

    return taxonomy_filter_string, galaxy_filter_string

def build_search_options(page_size, offset, facets_param=None):
    options = {
        "limit": page_size,
        "offset": offset,
        "attributesToHighlight": ["*"],
        "highlightPreTag": "<mark>",
        "highlightPostTag": "</mark>",
    }
    if facets_param:
        options["facets"] = facets_param
    return options

def perform_multisearch(index_list, query, page_size, offset, taxonomy_filter_string, galaxy_filter_string):
    request_payload = []
    for index in index_list:
        base_query = {
            "indexUid": index,
            "q": query,
            "attributesToHighlight": ["*"],
            "highlightPreTag": "<mark>",
            "highlightPostTag": "</mark>",
        }
        if index == TAXONOMIES_INDEX:
            base_query["filter"] = taxonomy_filter_string
        elif index == GALAXY_INDEX:
            base_query["filter"] = galaxy_filter_string
        request_payload.append(base_query)
    multisearch_options = {"limit": page_size, "offset": offset}
    return client.multi_search(request_payload, multisearch_options)

def perform_singlesearch(index_list, query, search_options, index_param, taxonomy_filter_string, galaxy_filter_string):
    try:
        index_position = int(index_param)
    except ValueError:
        index_position = 0
    index_position = max(0, min(index_position, len(index_list) - 1))
    selected_index = index_list[index_position]
    if selected_index == TAXONOMIES_INDEX:
        search_options["filter"] = taxonomy_filter_string
    elif selected_index == GALAXY_INDEX:
        search_options["filter"] = galaxy_filter_string
    return client.index(selected_index).search(query, search_options)

async def search(request):
    query = request.query_params.get("q", "")
    index_param = request.query_params.get("index", "0")
    taxonomies_param = request.query_params.get("taxonomies", None)
    galaxy_param = request.query_params.get("galaxy", None)
    page, page_size, offset = await get_paging_params(request)

    facets_param = request.query_params.get("facetsDistribution", None)
    if facets_param:
        try:
            facets_param = json.loads(facets_param)
        except json.JSONDecodeError:
            facets_param = facets_param.split(',')

    ms_indexes = admin.get_indexes()
    index_list = [index.uid for index in ms_indexes["results"] if not index.uid.endswith("_new")]

    taxonomy_filter_string, galaxy_filter_string = build_filter_query(taxonomies_param, galaxy_param)
    search_options = build_search_options(page_size, offset, facets_param)

    if not index_list:
        return JSONResponse({"hits": []})
    
    if index_param == "all":
        results = perform_multisearch(index_list, query, page_size, offset, taxonomy_filter_string, galaxy_filter_string)
    else:
        results = perform_singlesearch(index_list, query, search_options, index_param, taxonomy_filter_string, galaxy_filter_string)

    return JSONResponse(results)

routes = [
    Route("/", homepage),
    Route("/search", search)
]

app = Starlette(debug=True, routes=routes)
app.mount("/static", StaticFiles(directory="static"), name="static")

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8001)

