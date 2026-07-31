function buildSearchIndex() {
  const index = [];
  document
    .querySelectorAll('script.search-data[type="application/json"]')
    .forEach((el) => {
      index.push({
        url: el.dataset.url || "",
        title: el.dataset.title || "",
        excerpt: el.dataset.excerpt || "",
      });
    });
  return index;
}

function escapeRegExp(text) {
  return text.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
}

function highlight(text, term) {
  if (!term) return text;
  const regex = new RegExp(`(${escapeRegExp(term)})`, "ig");
  return text.replace(regex, "<mark>$1</mark>");
}

function initSearch() {
  const input = document.getElementById("search-input");
  const suggestions = document.getElementById("search-suggestions");
  if (!input || !suggestions) return;

  const index = buildSearchIndex();
  let activeIdx = -1;

  function query(raw) {
    const q = raw.trim().toLowerCase();
    if (!q) return [];

    return index
      .map((item) => {
        const title = item.title.toLowerCase();
        const excerpt = item.excerpt.toLowerCase();
        let score = 0;

        if (title.includes(q)) score += 3;
        if (excerpt.includes(q)) score += 1;

        return { ...item, score };
      })
      .filter((item) => item.score > 0)
      .sort((a, b) => b.score - a.score)
      .slice(0, 8);
  }

  function clear() {
    suggestions.hidden = true;
    suggestions.innerHTML = "";
    activeIdx = -1;
  }

  function render(results, q) {
    if (!q || !results.length) {
      clear();
      return;
    }

    suggestions.innerHTML = results
      .map(
        (result, i) => `
          <li class="suggestion-item" role="option" aria-selected="${i === activeIdx}" data-url="${result.url}">
            <strong>${highlight(result.title, q)}</strong>
            <span>${highlight(result.excerpt.slice(0, 110), q)}...</span>
          </li>
        `,
      )
      .join("");

    suggestions.hidden = false;

    suggestions.querySelectorAll(".suggestion-item").forEach((item) => {
      item.addEventListener("mousedown", (event) => {
        event.preventDefault();
        const url = item.dataset.url;
        if (url) window.location.href = url;
      });
    });
  }

  input.addEventListener("input", () => {
    activeIdx = -1;
    render(query(input.value), input.value.trim());
  });

  input.addEventListener("keydown", (event) => {
    const items = suggestions.querySelectorAll(".suggestion-item");
    if (!items.length) return;

    if (event.key === "ArrowDown") {
      event.preventDefault();
      activeIdx = Math.min(activeIdx + 1, items.length - 1);
    } else if (event.key === "ArrowUp") {
      event.preventDefault();
      activeIdx = Math.max(activeIdx - 1, 0);
    } else if (event.key === "Enter") {
      event.preventDefault();
      const target = items[activeIdx >= 0 ? activeIdx : 0];
      if (target && target.dataset.url) window.location.href = target.dataset.url;
      return;
    } else if (event.key === "Escape") {
      clear();
      return;
    } else {
      return;
    }

    items.forEach((item, i) => {
      item.setAttribute("aria-selected", String(i === activeIdx));
    });
    if (items[activeIdx]) {
      items[activeIdx].scrollIntoView({ block: "nearest" });
    }
  });

  input.addEventListener("focus", () => {
    if (input.value.trim()) {
      render(query(input.value), input.value.trim());
    }
  });

  document.addEventListener("click", (event) => {
    if (!event.target.closest(".search-wrap")) {
      clear();
    }
  });
}

document.addEventListener("DOMContentLoaded", initSearch);
