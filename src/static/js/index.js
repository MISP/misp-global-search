const input = document.getElementById("search-input");
const resultsDiv = document.getElementById("results");
const indexDropdown = document.getElementById("index-dropdown");

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
// Instead of highlighting, we simply display the value as plain text.
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
                span.textContent = String(item);
                container.appendChild(span);
            }
            container.appendChild(document.createElement("br"));
        });
        return container;
    } else if (typeof value === "object" && value !== null) {
        return createNestedTable(value);
    } else {
        const span = document.createElement("span");
        span.textContent = String(value);
        return span;
    }
}

async function performSearch() {
    const query = input.value.trim();
    const indexValue = indexDropdown.value;
    history.pushState(null, '', `/?q=${encodeURIComponent(query)}&index=${encodeURIComponent(indexValue)}`);
    try {
        const response = await fetch(`/search?q=${encodeURIComponent(query)}&index=${encodeURIComponent(indexValue)}`);
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

                // Button with link to MISP-Galaxy
                if (currentIndex === "misp-galaxy") {
                    const galaxyButton = document.createElement("button");
                    galaxyButton.textContent = "Visit MISP-Galaxy";
                    galaxyButton.className = "btn btn-primary link-button galaxy-button";
                    galaxyButton.onclick = function() {
                        const formattedValue = hit.value.toLowerCase().replace(/\s+/g, '-');
                        window.location.href = `https://misp-galaxy.org/${encodeURIComponent(hit.galaxy || "")}/#${encodeURIComponent(formattedValue)}`;
                    };
                    titleDiv.appendChild(galaxyButton);
                }

                // Button to contribute on GitHub
                const button = document.createElement("button");
                button.textContent = "Contribute";
                button.className = "btn btn-primary link-button contribute-button";
                button.onclick = function() {
                    if (currentIndex === "misp-galaxy") {
                        window.location.href = `https://github.com/MISP/misp-galaxy/edit/main/clusters/${encodeURIComponent(hit.galaxy || "")}.json`;
                    } else if (currentIndex === "misp-objects") {
                        window.location.href = `https://github.com/MISP/misp-objects/edit/main/objects/${encodeURIComponent(hit.name || "")}/definition.json`;
                    } else if (currentIndex === "misp-taxonomies") {
                        window.location.href = `https://github.com/MISP/misp-taxonomies/edit/main/${encodeURIComponent(hit.namespace || "")}/machinetag.json`;
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
    } catch (error) {
        resultsDiv.innerHTML = "<p>Error retrieving search results</p>";
        console.log(error);
    }
}

const debouncedSearch = debounce(performSearch, 300);
input.addEventListener("keyup", debouncedSearch);

indexDropdown.addEventListener("change", performSearch);

document.addEventListener("DOMContentLoaded", () => {
    // Parse URL parameters
    const params = new URLSearchParams(window.location.search);
    const q = params.get("q") || "";
    const index = params.get("index") || "all";

    // Set the search input and dropdown to the URL values.
    input.value = q;
    indexDropdown.value = index;

    // Then trigger the search.
    performSearch();
});

