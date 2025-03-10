const input = document.getElementById("search-input");
const resultsDiv = document.getElementById("results");
const paginationDiv = document.getElementById("pagination");
const indexDropdown = document.getElementById("index-dropdown");

let currentPage = 1;
const pageSize = 10;

let selectedFilters = {
    taxonomies: [],
    galaxy: []
};

// Debounce function to limit API calls.
function debounce(func, delay) {
    let timeoutId;
    return function(...args) {
        clearTimeout(timeoutId);
        timeoutId = setTimeout(() => func.apply(this, args), delay);
    };
}

// Helper: Escapes regex special characters in the query.
function escapeRegex(string) {
    return string.replace(/[-\/\\^$*+?.()|[\]{}]/g, '\\$&');
}

// Helper: Recursively creates a table for a JSON object.
function createNestedTable(obj) {
    const table = document.createElement("table");
    table.className = "nested-table";
    for (const key in obj) {
        const tr = document.createElement("tr");

        const tdKey = document.createElement("td");
        tdKey.textContent = key;
        tdKey.style.fontWeight = "bold";

        const tdValue = document.createElement("td");
        tdValue.appendChild(createValueElement(obj[key]));

        tr.appendChild(tdKey);
        tr.appendChild(tdValue);
        table.appendChild(tr);
    }
    return table;
}

// Helper: Creates an element to display a given value.
function createValueElement(value) {
    if (typeof value === "string") {
        const span = document.createElement("span");
        span.innerHTML = value;
        return span;
    } else if (Array.isArray(value)) {
        const container = document.createElement("div");
        value.forEach(item => {
            if (typeof item === "object" && item !== null) {
                container.appendChild(createNestedTable(item));
            } else {
                const span = document.createElement("span");
                span.innerHTML = String(item);
                container.appendChild(span);
            }
            container.appendChild(document.createElement("br"));
        });
        return container;
    } else if (typeof value === "object" && value !== null) {
        return createNestedTable(value);
    } else {
        const span = document.createElement("span");
        span.innerHTML = String(value);
        return span;
    }
}

function updateURL() {
    const query = input.value.trim();
    const indexValue = indexDropdown.value;
    history.pushState(null, '', `/?q=${encodeURIComponent(query)}&index=${encodeURIComponent(indexValue)}&page=${currentPage}`);
}

function renderPagination(totalHits) {
    paginationDiv.innerHTML = "";
    const totalPages = Math.ceil(totalHits / pageSize);
    // Create Previous button if not on the first page.
    if (currentPage > 1) {
        const prevButton = document.createElement("button");
        prevButton.textContent = "Previous";
        prevButton.className = "btn btn-secondary";
        prevButton.addEventListener("click", () => {
            currentPage--;
            updateURL();
            performSearch();
            window.scrollTo({
                top: 0,
                left: 0,
                behavior: "instant",
            });
        });
        paginationDiv.appendChild(prevButton);
    }
    // Display current page information.
    const pageInfo = document.createElement("span");
    pageInfo.textContent = ` Page ${currentPage} of ${totalPages} `;
    paginationDiv.appendChild(pageInfo);
    // Create Next button if there are more pages.
    if (currentPage < totalPages) {
        const nextButton = document.createElement("button");
        nextButton.textContent = "Next";
        nextButton.className = "btn btn-secondary";
        nextButton.addEventListener("click", () => {
            currentPage++;
            updateURL();
            performSearch();
            window.scrollTo({
                top: 0,
                left: 0,
                behavior: "instant",
            });
        });
        paginationDiv.appendChild(nextButton);
    }
}

async function performSearch() {
    const query = input.value.trim();
    const indexValue = indexDropdown.value;

    // Build query strings for each filter category.
    const taxonomyQuery = selectedFilters.taxonomies && selectedFilters.taxonomies.length
        ? `&taxonomies=${encodeURIComponent(selectedFilters.taxonomies.join(','))}`
        : "";
    const galaxyQuery = selectedFilters.galaxy && selectedFilters.galaxy.length
        ? `&galaxy=${encodeURIComponent(selectedFilters.galaxy.join(','))}`
        : "";
    history.pushState(null, '', `/?q=${encodeURIComponent(query)}&index=${encodeURIComponent(indexValue)}&page=${currentPage}${taxonomyQuery}${galaxyQuery}`);
    try {
        const response = await fetch(
            `/search?q=${encodeURIComponent(query)}&index=${encodeURIComponent(indexValue)}&page=${currentPage}&pageSize=${pageSize}${taxonomyQuery}${galaxyQuery}`
        );
        const data = await response.json();
        resultsDiv.innerHTML = "";

        if (data.hits && data.hits.length > 0) {
            data.hits.forEach(res => {
                const { _formatted: hit } = res
                let currentIndex;
                if (indexValue === "all") {
                    currentIndex = res._federation.indexUid;
                } else {
                    currentIndex = availableIndexes[indexDropdown.value];
                }
                const hitDiv = document.createElement("div");
                hitDiv.className = "result-card";

                // Title and Follow Link Button
                const titleDiv = document.createElement("div");
                titleDiv.className = "result-title";

                const titleText = document.createElement("h2");
                // Remove highlighting: simply use the raw value.
                if (currentIndex === "misp-galaxy") {
                    titleText.innerHTML = hit.value ? hit.value : "No Title";
                } else if (currentIndex === "misp-objects") {
                    titleText.innerHTML = hit.name ? hit.name : "No Name";
                } else if (currentIndex === "misp-taxonomies") {
                    if (!hit.value) {
                        titleText.innerHTML = hit.namespace;
                    } else if (hit.predicate) {
                        title = hit.namespace + ":" + hit.predicate + "=\"" + hit.value + "\"";
                        titleText.innerHTML = title;
                    } else {
                        title = hit.namespace + ":" + hit.value;
                        titleText.innerHTML = title;
                    }
                }
                titleText.className = "h4";
                titleDiv.appendChild(titleText);

                // Tag with the galaxy for MISP-Galaxy
                if (currentIndex === "misp-galaxy") {
                    const cleanedGalaxy = (hit.galaxy || "").replace(/<\/?mark>/gi, '');

                    const galaxyTag = document.createElement("a");
                    galaxyTag.className = "badge bg-warning text-dark me-2 galaxy-tag";
                    galaxyTag.textContent = cleanedGalaxy || "Unknown Galaxy";
                    galaxyTag.href = `https://misp-galaxy.org/${encodeURIComponent(cleanedGalaxy)}/`;
                    galaxyTag.target = "_blank";

                    titleDiv.appendChild(galaxyTag);
                }

                // Button with link to MISP-Galaxy
                if (currentIndex === "misp-galaxy") {
                    const galaxyButton = document.createElement("button");
                    galaxyButton.textContent = "Visit MISP-Galaxy";
                    galaxyButton.className = "btn btn-primary link-button galaxy-button";
                    galaxyButton.onclick = function() {
                        const formattedValue = hit.value.toLowerCase().replace(/\s+/g, '-');
                        const cleanedGalaxy = (hit.galaxy || "").replace(/<\/?mark>/gi, '');
                        const cleanedValue = (formattedValue || "").replace(/<\/?mark>/gi, '');
                        window.location.href = `https://misp-galaxy.org/${encodeURIComponent(cleanedGalaxy)}/#${encodeURIComponent(cleanedValue)}`;

                    };
                    titleDiv.appendChild(galaxyButton);
                }

                // Button to contribute on GitHub
                const button = document.createElement("button");
                button.textContent = "Contribute";
                button.className = "btn btn-primary link-button contribute-button";
                button.onclick = function() {
                    if (currentIndex === "misp-galaxy") {
                        const cleanedGalaxy = (hit.galaxy || "").replace(/<\/?mark>/gi, '');
                        window.location.href = `https://github.com/MISP/misp-galaxy/edit/main/clusters/${encodeURIComponent(cleanedGalaxy)}.json`;
                    } else if (currentIndex === "misp-objects") {
                        const cleanedName = (hit.name || "").replace(/<\/?mark>/gi, '');
                        window.location.href = `https://github.com/MISP/misp-objects/edit/main/objects/${encodeURIComponent(cleanedName)}/definition.json`;
                    } else if (currentIndex === "misp-taxonomies") {
                        const cleanedNS = (hit.namespace || "").replace(/<\/?mark>/gi, '');
                        window.location.href = `https://github.com/MISP/misp-taxonomies/edit/main/${encodeURIComponent(cleanedNS)}/machinetag.json`;
                    }
                };
                titleDiv.appendChild(button);

                hitDiv.appendChild(titleDiv);

                // Description: display raw description text.
                const description = document.createElement("p");
                description.innerHTML = hit.description ? hit.description : "No Description";
                hitDiv.appendChild(description);

                // Table for additional key:value pairs.
                const table = document.createElement("table");
                table.className = "nested-table";

                for (const key in hit) {
                    if (key === "description" || key === "_federation") continue;
                    const tr = document.createElement("tr");

                    const tdKey = document.createElement("td");
                    tdKey.textContent = key;
                    tdKey.style.fontWeight = "bold";

                    const tdValue = document.createElement("td");
                    tdValue.appendChild(createValueElement(hit[key]));

                    tr.appendChild(tdKey);
                    tr.appendChild(tdValue);
                    table.appendChild(tr);
                }

                // Create a unique ID for the accordion item.
                const accordionId = "accordionCollapse" + Math.random().toString(36).substring(2, 8);

                // Build the accordion structure.
                const accordionDiv = document.createElement("div");
                accordionDiv.className = "accordion";

                const accordionItem = document.createElement("div");
                accordionItem.className = "accordion-item";

                const accordionHeader = document.createElement("h2");
                accordionHeader.className = "accordion-header";
                accordionHeader.id = "heading" + accordionId;

                const accordionButton = document.createElement("button");
                accordionButton.className = "accordion-button collapsed";
                accordionButton.type = "button";
                accordionButton.setAttribute("data-bs-toggle", "collapse");
                accordionButton.setAttribute("data-bs-target", "#collapse" + accordionId);
                accordionButton.setAttribute("aria-expanded", "false");
                accordionButton.setAttribute("aria-controls", "collapse" + accordionId);
                accordionButton.textContent = "Show Data";

                accordionHeader.appendChild(accordionButton);
                accordionItem.appendChild(accordionHeader);

                const accordionCollapse = document.createElement("div");
                accordionCollapse.id = "collapse" + accordionId;
                accordionCollapse.className = "accordion-collapse collapse";
                accordionCollapse.setAttribute("aria-labelledby", "heading" + accordionId);

                const accordionBody = document.createElement("div");
                accordionBody.className = "accordion-body";
                accordionBody.appendChild(table);

                accordionCollapse.appendChild(accordionBody);
                accordionItem.appendChild(accordionCollapse);
                accordionDiv.appendChild(accordionItem);

                hitDiv.appendChild(accordionDiv);
                resultsDiv.appendChild(hitDiv);
            });
        } else {
            resultsDiv.innerHTML = "<p>No results found</p>";
        }

        let totalHits = data.estimatedTotalHits || data.nbHits || 0;
        renderPagination(totalHits);

    } catch (error) {
        resultsDiv.innerHTML = "<p>Error retrieving search results</p>";
        console.log(error);
    }
}

async function loadGalaxyFilters() {
    try {
        // Construct a URL for a search that returns only facets.
        // For example, here we search with an empty query.
        const response = await fetch(`/search?q=&index=0&page=1&pageSize=0&facetsDistribution=["galaxy"]`);
        const data = await response.json();

        if (data.facetDistribution && data.facetDistribution.galaxy) {
            const galaxyFacets = data.facetDistribution.galaxy;
            const galaxyForm = document.getElementById("galaxyFilterForm");
            galaxyForm.innerHTML = ""; // Clear previous content

            // For each facet, create a checkbox with the galaxy name and count.
            for (const [galaxy, count] of Object.entries(galaxyFacets)) {
                const div = document.createElement("div");
                div.className = "form-check";

                const checkbox = document.createElement("input");
                checkbox.type = "checkbox";
                checkbox.className = "form-check-input";
                checkbox.value = galaxy;
                checkbox.id = "filterGalaxy_" + galaxy;
                checkbox.dataset.category = "misp-galaxy";

                const label = document.createElement("label");
                label.className = "form-check-label";
                label.setAttribute("for", checkbox.id);
                label.textContent = `${galaxy} (${count})`;

                div.appendChild(checkbox);
                div.appendChild(label);
                galaxyForm.appendChild(div);
            }
        }
    } catch (error) {
        console.error("Error loading galaxy facets:", error);
    }
}


// const debouncedSearch = debounce(performSearch, 300);
const debouncedSearch = debounce(() => {
    currentPage = 1; // Reset to page 1 when the search query changes.
    performSearch();
}, 300);
input.addEventListener("keyup", debouncedSearch);

indexDropdown.addEventListener("change", () => {
    currentPage = 1;
    performSearch();
});

document.addEventListener("DOMContentLoaded", () => {
    // Parse URL parameters.
    const params = new URLSearchParams(window.location.search);
    const q = params.get("q") || "";
    const index = params.get("index") || "all";
    const taxonomiesParam = params.get("taxonomies") || "";
    const galaxyParam = params.get("galaxy") || "";

    currentPage = parseInt(params.get("page")) || 1;

    input.value = q;
    indexDropdown.value = index;

    // Build the global filter object with separate arrays for each category.
    selectedFilters = {
        taxonomies: taxonomiesParam ? taxonomiesParam.split(",") : [],
        galaxy: galaxyParam ? galaxyParam.split(",") : []
    };

    performSearch();
});


document.addEventListener('DOMContentLoaded', function() {
    var popoverTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="popover"]'));
    var popoverList = popoverTriggerList.map(function(popoverTriggerEl) {
        return new bootstrap.Popover(popoverTriggerEl);
    });
});

document.getElementById("applyFilterBtn").addEventListener("click", function() {
    // Create objects to store selected filters by category.
    let taxonomyFilters = [];
    let galaxyFilters = [];

    // Get checked checkboxes from the taxonomy form.
    const taxonomyCheckboxes = document.querySelectorAll("#taxonomyFilterForm input[type=checkbox]:checked");
    taxonomyCheckboxes.forEach(function(checkbox) {
        taxonomyFilters.push(checkbox.value);
    });

    // Get checked checkboxes from the galaxy form.
    const galaxyCheckboxes = document.querySelectorAll("#galaxyFilterForm input[type=checkbox]:checked");
    galaxyCheckboxes.forEach(function(checkbox) {
        galaxyFilters.push(checkbox.value);
    });

    // Store the selected filters in a global variable.
    // You might choose to store them as an object for clarity.
    selectedFilters = {
        taxonomies: taxonomyFilters,
        galaxy: galaxyFilters
    };

    currentPage = 1;

    // Close the modal.
    var filterModalEl = document.getElementById('filterModal');
    var modal = bootstrap.Modal.getInstance(filterModalEl);
    modal.hide();

    performSearch();
});

document.getElementById("filterModal").addEventListener("show.bs.modal", async function() {
    await loadGalaxyFilters();
    // For taxonomy filters:
    const taxonomyCheckboxes = document.querySelectorAll("#taxonomyFilterForm input[type=checkbox]");
    taxonomyCheckboxes.forEach(function(checkbox) {
        checkbox.checked = selectedFilters.taxonomies && selectedFilters.taxonomies.includes(checkbox.value);
    });

    // For galaxy filters:
    const galaxyCheckboxes = document.querySelectorAll("#galaxyFilterForm input[type=checkbox]");
    galaxyCheckboxes.forEach(function(checkbox) {
        checkbox.checked = selectedFilters.galaxy && selectedFilters.galaxy.includes(checkbox.value);
    });
});

document.getElementById("clearFilterBtn").addEventListener("click", function() {
    selectedFilters = {
        taxonomies: [],
        galaxy: []
    };

    // Uncheck all checkboxes in the taxonomy filter form.
    const taxonomyCheckboxes = document.querySelectorAll("#taxonomyFilterForm input[type=checkbox]");
    taxonomyCheckboxes.forEach(function(checkbox) {
        checkbox.checked = false;
    });

    // Uncheck all checkboxes in the galaxy filter form.
    const galaxyCheckboxes = document.querySelectorAll("#galaxyFilterForm input[type=checkbox]");
    galaxyCheckboxes.forEach(function(checkbox) {
        checkbox.checked = false;
    });

    const filterModalEl = document.getElementById('filterModal');
    const modalInstance = bootstrap.Modal.getInstance(filterModalEl);
    if (modalInstance) {
        modalInstance.hide();
    }
    performSearch();
});
