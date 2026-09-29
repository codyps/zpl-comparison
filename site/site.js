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
