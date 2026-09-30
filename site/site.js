"use strict";
for (const overlay of document.querySelectorAll(".overlay")) {
  const range = overlay.querySelector("input");
  range.addEventListener("input", () => {
    overlay.querySelector(".overlay-render").style.opacity =
      Number(range.value) / 100;
    overlay.querySelector("output").value = `${range.value}%`;
  });
}
for (const filter of document.querySelectorAll("[data-filter]")) {
  const rows = [...document.querySelectorAll("tbody tr")];
  const count = document.querySelector("[data-count]");
  const update = () => {
    const query = filter.value.trim().toLocaleLowerCase();
    let visible = 0;
    for (const row of rows) {
      row.hidden = !row.textContent.toLocaleLowerCase().includes(query);
      if (!row.hidden) visible++;
    }
    count.textContent = `${visible} of ${rows.length} documents`;
  };
  filter.addEventListener("input", update);
  update();
}

for (const toggle of document.querySelectorAll("[data-full-canvas]")) {
  toggle.addEventListener("change", () => {
    for (const image of document.querySelectorAll("img[data-focus]")) {
      image.src = toggle.checked ? image.dataset.full : image.dataset.focus;
    }
  });
}

for (const comparison of document.querySelectorAll("[data-output-comparison]")) {
  const toggle = comparison.querySelector("[data-contact-diffs]");
  if (!toggle) continue;
  comparison.querySelector("[data-diff-control]").hidden = false;
  const update = () => {
    for (const view of comparison.querySelectorAll("[data-render-view]")) {
      view.hidden = toggle.checked;
    }
    for (const view of comparison.querySelectorAll("[data-diff-view]")) {
      view.hidden = !toggle.checked;
    }
  };
  toggle.addEventListener("change", update);
  update();
}

for (const table of document.querySelectorAll("table[data-sortable]")) {
  for (const [column, heading] of [...table.tHead.rows[0].cells].entries()) {
    const button = document.createElement("button");
    button.type = "button";
    button.textContent = heading.textContent;
    heading.replaceChildren(button);
    button.addEventListener("click", () => {
      const ascending = heading.getAttribute("aria-sort") !== "ascending";
      for (const cell of table.tHead.rows[0].cells) cell.removeAttribute("aria-sort");
      heading.setAttribute("aria-sort", ascending ? "ascending" : "descending");
      const value = row => {
        const text = row.cells[column].textContent.trim();
        return /^\d+(\.\d+)?(\s*(µs|ms|MiB))?$/.test(text) ? Number.parseFloat(text) : text;
      };
      const rows = [...table.tBodies[0].rows];
      rows.sort((a, b) => {
        const x = value(a), y = value(b);
        if (typeof x === "number" && typeof y !== "number") return -1;
        if (typeof y === "number" && typeof x !== "number") return 1;
        const order = typeof x === "number" ? x - y : x.localeCompare(y, undefined, {numeric: true});
        return ascending ? order : -order;
      });
      table.tBodies[0].append(...rows);
    });
  }
}
