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

// Helper: Escapes regex special characters in the query.
function escapeRegex(string) {
  return string.replace(/[-\/\\^$*+?.()|[\]{}]/g, '\\$&');
}

// Helper: Wraps matching text in <mark> tags.
function highlightText(text, query) {
  if (!query) return text;
  // Split the query by whitespace and filter out empty words.
  const words = query.split(/\s+/).filter(w => w);
  if (words.length === 0) return text;
  // Build a regex that matches any of the words (case-insensitive)
  const regex = new RegExp(`(${words.map(escapeRegex).join('|')})`, 'gi');
  return text.replace(regex, '<mark>$1</mark>');
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

// Helper: Creates an element to display a given value with highlighting.
function createValueElement(value) {
  // If the value is a string, highlight matches.
  if (typeof value === "string") {
    const span = document.createElement("span");
    const query = input.value.trim();
    // Set innerHTML so that <mark> tags are rendered.
    span.innerHTML = highlightText(value, query);
    return span;
  } else if (Array.isArray(value)) {
    const container = document.createElement("div");
    value.forEach(item => {
      if (typeof item === "object" && item !== null) {
        container.appendChild(createNestedTable(item));
      } else {
        const span = document.createElement("span");
        span.innerHTML = highlightText(String(item), input.value.trim());
        container.appendChild(span);
      }
      container.appendChild(document.createElement("br"));
    });
    return container;
  } else if (typeof value === "object" && value !== null) {
    return createNestedTable(value);
  } else {
    // For numbers or other primitives, convert to string.
    const span = document.createElement("span");
    span.innerHTML = highlightText(String(value), input.value.trim());
    return span;
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

        const titleDiv = document.createElement("div");
        titleDiv.className = "result-title";

        const titleText = document.createElement("h2");
        titleText.innerHTML = hit.value ? highlightText(hit.value, query) : "No Title";
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
        description.innerHTML = hit.description ? highlightText(hit.description, query) : "No Description";
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

