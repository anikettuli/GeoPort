// Location Search with Autocomplete & Direct Coordinate Parsing
let searchDebounceTimer = null;

function initSearch() {
  const searchInput = document.getElementById("searchInput");
  const searchDropdown = document.getElementById("searchDropdown");

  if (!searchInput || !searchDropdown) return;

  searchInput.addEventListener("input", (e) => {
    const query = e.target.value.trim();
    clearTimeout(searchDebounceTimer);

    if (query.length < 2) {
      searchDropdown.innerHTML = "";
      searchDropdown.classList.remove("active");
      return;
    }

    searchDebounceTimer = setTimeout(() => {
      performSearch(query);
    }, 280);
  });

  searchInput.addEventListener("keydown", (e) => {
    if (e.key === "Enter") {
      const firstItem = searchDropdown.querySelector(".search-item");
      if (firstItem) {
        firstItem.click();
      }
    } else if (e.key === "Escape") {
      searchDropdown.classList.remove("active");
    }
  });

  // Hide dropdown on outside click
  document.addEventListener("click", (e) => {
    if (!searchInput.contains(e.target) && !searchDropdown.contains(e.target)) {
      searchDropdown.classList.remove("active");
    }
  });
}

async function performSearch(query) {
  const searchDropdown = document.getElementById("searchDropdown");
  try {
    const res = await fetch(`/api/search?q=${encodeURIComponent(query)}`);
    if (!res.ok) return;

    const results = await res.json();
    searchDropdown.innerHTML = "";

    if (!results || results.length === 0) {
      searchDropdown.innerHTML = `<div class="search-item" style="color: var(--text-muted); cursor: default;">No locations found</div>`;
      searchDropdown.classList.add("active");
      return;
    }

    results.forEach((item) => {
      const el = document.createElement("div");
      el.className = "search-item";
      el.innerHTML = `
        <div class="search-item-title">${escapeHtml(item.title)}</div>
        ${item.subtitle ? `<div class="search-item-sub">${escapeHtml(item.subtitle)}</div>` : ""}
      `;

      el.addEventListener("click", () => {
        setMarkerLocation(item.latitude, item.longitude, true);
        searchDropdown.classList.remove("active");
        document.getElementById("searchInput").value = item.title;
        showToast(`Selected: ${item.title}`);
      });

      searchDropdown.appendChild(el);
    });

    searchDropdown.classList.add("active");
  } catch (err) {
    console.error("Search error:", err);
  }
}

function escapeHtml(text) {
  if (!text) return "";
  const div = document.createElement("div");
  div.innerText = text;
  return div.innerHTML;
}
