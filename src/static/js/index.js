const input = document.getElementById("search-input");
const resultsDiv = document.getElementById("results");

// Debounce function to limit API calls.
function debounce(func, delay) {
  let timeoutId;
  return function(...args) {
    clearTimeout(timeoutId);
    timeoutId = setTimeout(() => func.apply(this, args), delay);
  };
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
  if (Array.isArray(value)) {
    const container = document.createElement("div");
    value.forEach(item => {
      if (typeof item === "object" && item !== null) {
        container.appendChild(createNestedTable(item));
      } else {
        const span = document.createElement("span");
        span.textContent = item;
        container.appendChild(span);
      }
      container.appendChild(document.createElement("br"));
    });
    return container;
  } else if (typeof value === "object" && value !== null) {
    return createNestedTable(value);
  } else {
    return document.createTextNode(value);
  }
}

async function performSearch() {
  const query = input.value;
  try {
    const response = await fetch(`/search?q=${encodeURIComponent(query)}`);
    const data = await response.json();
    resultsDiv.innerHTML = "";

    if (data.hits && data.hits.length > 0) {
      data.hits.forEach(hit => {
        const hitDiv = document.createElement("div");
        hitDiv.className = "result-card";

        // Title and Follow Link Button
        const titleDiv = document.createElement("div");
        titleDiv.className = "result-title";

        const titleText = document.createElement("h2");
        titleText.textContent = hit.value || "No Title";
        titleText.className = "h4";
        titleDiv.appendChild(titleText);

        if (hit.value) {
          const button = document.createElement("button");
          button.textContent = "Go to MISP-Galaxy";
          button.className = "btn btn-primary link-button";
          button.onclick = function() {
            const formattedValue = hit.value.toLowerCase().replace(/\s+/g, '-');
            window.location.href = `https://misp-galaxy.org/${encodeURIComponent(hit.galaxy || "")}/#${encodeURIComponent(formattedValue)}`;
          };
          titleDiv.appendChild(button);
        }
        hitDiv.appendChild(titleDiv);

        // Description
        const description = document.createElement("p");
        description.textContent = hit.description || "No Description";
        hitDiv.appendChild(description);

        // Table for additional key:value pairs.
        const table = document.createElement("table");
        table.className = "nested-table";

        for (const key in hit) {
          if (key === "value" || key === "description") continue;
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
        hitDiv.appendChild(table);
        resultsDiv.appendChild(hitDiv);
      });
    } else {
      resultsDiv.innerHTML = "<p>No results found</p>";
    }
  } catch (error) {
    resultsDiv.innerHTML = "<p>Error retrieving search results</p>";
  }
}

const debouncedSearch = debounce(performSearch, 300);
input.addEventListener("keyup", debouncedSearch);

document.addEventListener("DOMContentLoaded", performSearch);
