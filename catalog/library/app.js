import { createZip } from "./zip.js";

const github = "https://github.com/TheOutlandsDev/outlands-public-tools";
const byId = (id) => document.getElementById(id);
const search = byId("tool-search");
const family = byId("tool-family");
const availability = byId("tool-availability");
const grid = byId("tool-grid");
const previous = byId("page-prev");
const next = byId("page-next");
const bundleDownload = byId("bundle-download");
const bundleClear = byId("bundle-clear");
const bundleStatus = byId("bundle-status");
const storageKey = "outlands-library-selection-v1";
const pageSize = 24;
const params = new URLSearchParams(window.location.search);
const selection = new Set();
let page = 0;
let directTool = params.get("tool");
let busy = false;
let catalog;
let tools;
let indexedTools;
let families;

function element(tag, content, className) {
  const node = document.createElement(tag);
  if (content) node.textContent = content;
  if (className) node.className = className;
  return node;
}

function link(label, href, className = "text-link") {
  const node = element("a", label, className);
  const url = new URL(href, window.location.href);
  if (url.origin === window.location.origin || url.protocol === "https:") node.href = url.href;
  return node;
}

function button(label, className, action) {
  const node = element("button", label, className);
  node.type = "button";
  node.addEventListener("click", action);
  return node;
}

function releaseUrl({ tag, filename }) {
  return `${github}/releases/download/${encodeURIComponent(tag)}/${encodeURIComponent(filename)}`;
}

function docs(path) {
  return `${github}/blob/main/${path}`;
}

function toolkitArchive(tool) {
  return tool.released ? catalog.downloads.find((item) => item.id === tool.package) : null;
}

function hasArchive(tool) {
  return Boolean(tool.wheel_package || tool.windows_release || tool.focused_release || tool.standalone_release
    || tool.source_bundle || toolkitArchive(tool));
}

function matchesAvailability(tool, format) {
  if (format === "wheel") return Boolean(tool.wheel_package || tool.standalone_release?.download?.kind === "wheel");
  if (format === "download") return hasArchive(tool);
  if (format === "source") return !hasArchive(tool);
  return true;
}

function sourceLabel(tool) {
  if (tool.wheel_package || tool.standalone_release?.download?.kind === "wheel") return "Python wheel";
  if (tool.windows_release) return "Windows portable";
  if (tool.focused_release || tool.standalone_release?.download) return "Source ZIP";
  if (tool.standalone_release) return "Standalone release";
  if (tool.source_bundle) return "Group source ZIP";
  if (toolkitArchive(tool)) return "Toolkit source ZIP";
  return "Public source";
}

function appendDetails(article, tool) {
  const details = element("details", null, "tool-details");
  const summary = element("summary", "Requirements, examples and source");
  const refs = element("div", null, "tool-references");
  refs.append(
    link("Documentation", tool.guide),
    link("Source files", `${github}/tree/main/${tool.path}`),
    link("Example", docs(tool.examples[0])),
    link("Validation", docs(tool.validation)),
  );
  if (tool.wheel_package) {
    refs.append(
      link("Python API and install guide", docs(tool.wheel_package.guide)),
      link("Original wheel download", releaseUrl(tool.wheel_package)),
      link("Wheel checksums", releaseUrl({ ...tool.wheel_package, filename: "SHA256SUMS.txt" })),
    );
  }
  if (tool.focused_release && tool.windows_release) {
    refs.append(link("Tool source ZIP", releaseUrl(tool.focused_release)));
  }
  if (tool.source_bundle && (tool.wheel_package || tool.windows_release || tool.focused_release || tool.standalone_release)) {
    refs.append(link("Group source ZIP", releaseUrl(tool.source_bundle)));
  }
  const standalone = tool.standalone_release?.download;
  if (standalone) {
    if (tool.wheel_package || tool.windows_release) {
      refs.append(link(standalone.kind === "wheel" ? "Standalone Python wheel" : "Standalone source ZIP", standalone.url));
    }
    refs.append(
      link("Release guide", standalone.guide_url),
      link("SHA-256 checksums", standalone.checksums_url),
      link("Release validation", standalone.validation_url),
    );
  }
  if (tool.standalone_release && (standalone || tool.wheel_package || tool.windows_release || tool.focused_release)) {
    refs.append(link("Standalone release", tool.standalone_release.url));
  }
  const archive = toolkitArchive(tool);
  if (archive && (tool.wheel_package || tool.windows_release || tool.focused_release
    || tool.standalone_release || tool.source_bundle)) {
    refs.append(link("Toolkit source ZIP", archive.url));
  }
  const permalink = new URL(window.location.pathname, window.location.href);
  permalink.searchParams.set("tool", tool.id);
  refs.append(link("Link to this tool", permalink));
  details.append(summary, element("p", tool.requirements), refs);
  article.append(details);
  if (directTool === tool.id) details.open = true;
}

function renderCard(tool) {
  const card = element("li", null, "tool-card");
  card.id = `tool-${tool.id}`;
  const article = element("article");
  const meta = element("p", null, "tool-category");
  meta.append(element("span", families.get(tool.group)), element("span", sourceLabel(tool), "tool-format"));
  const actions = element("div", null, "tool-actions");
  const primary = "button button-primary";
  if (tool.wheel_package) {
    const selected = selection.has(tool.id);
    const toggle = button(selected ? "Added" : "Add to bundle", "button button-secondary bundle-toggle", () => toggleSelection(tool.id));
    toggle.dataset.toolId = tool.id;
    toggle.disabled = busy;
    toggle.setAttribute("aria-pressed", selected);
    toggle.setAttribute("aria-label", `Add ${tool.title} to bundle`);
    const filename = tool.wheel_package.filename;
    const download = link("Download wheel", `wheels/${encodeURIComponent(filename)}`, primary);
    download.download = filename;
    actions.append(download, toggle);
  } else if (tool.windows_release) {
    actions.append(link("Download Windows ZIP", releaseUrl(tool.windows_release), primary));
  } else if (tool.standalone_release?.download) {
    const { kind, url } = tool.standalone_release.download;
    actions.append(link(kind === "wheel" ? "Download Python wheel" : "Download source ZIP", url, primary));
  } else if (tool.focused_release) {
    actions.append(link("Download source ZIP", releaseUrl(tool.focused_release), primary));
  } else if (tool.standalone_release) {
    actions.append(link("Release downloads", tool.standalone_release.url, primary));
  } else if (tool.source_bundle) {
    actions.append(link("Download group ZIP", releaseUrl(tool.source_bundle), primary));
  } else if (toolkitArchive(tool)) {
    actions.append(link("Download Toolkit ZIP", toolkitArchive(tool).url, primary));
  } else {
    actions.append(link("View source", `${github}/tree/main/${tool.path}`, primary));
  }
  article.append(meta, element("h3", tool.title), element("p", tool.purpose, "tool-description"), actions);
  appendDetails(article, tool);
  card.append(article);
  return card;
}

function renderCatalog({ focusPagination = false } = {}) {
  const words = search.value.trim().toLowerCase().split(/\s+/).filter(Boolean);
  const results = tools.filter((tool) =>
    (!directTool || tool.id === directTool)
    && (family.value === "all" || family.value === tool.group)
    && matchesAvailability(tool, availability.value)
    && words.every((word) => indexedTools.get(tool.id).includes(word)),
  );
  const pageCount = Math.max(1, Math.ceil(results.length / pageSize));
  page = Math.min(page, pageCount - 1);
  const start = page * pageSize;
  const slice = results.slice(start, start + pageSize);
  const result = byId("tool-result");
  result.textContent = slice.length
    ? `Showing ${start + 1}–${start + slice.length} of ${results.length} entries`
    : "0 entries";
  byId("tool-empty").hidden = slice.length > 0;
  byId("page-status").textContent = `Page ${page + 1} of ${pageCount}`;
  previous.disabled = page === 0;
  next.disabled = page >= pageCount - 1;
  grid.replaceChildren(...slice.map(renderCard));
  if (focusPagination) result.focus();
}

function updateFilters() {
  directTool = null;
  page = 0;
  const url = new URL(window.location.href);
  url.searchParams.delete("tool");
  for (const [key, value] of [["q", search.value.trim()], ["category", family.value], ["availability", availability.value]]) {
    if (value && value !== "all") url.searchParams.set(key, value);
    else url.searchParams.delete(key);
  }
  window.history.replaceState(null, "", url);
  renderCatalog();
}

function toggleSelection(id, focusBundle = false) {
  if (busy) return;
  if (selection.has(id)) selection.delete(id);
  else selection.add(id);
  storeSelection();
  bundleStatus.textContent = "";
  renderBundle();
  if (focusBundle) {
    const target = byId("bundle-list").querySelector("button") || byId("bundle-count");
    target.focus();
  }
}

function storeSelection() {
  try {
    localStorage.setItem(storageKey, JSON.stringify([...selection]));
  } catch {
    // The current page still works when browser storage is disabled.
  }
}

function selectedTools() {
  return tools.filter((tool) => selection.has(tool.id));
}

function renderBundle() {
  const picked = selectedTools();
  byId("bundle-count").textContent = `${picked.length} selected`;
  bundleDownload.disabled = busy || !picked.length;
  bundleClear.disabled = busy || !picked.length;
  const list = byId("bundle-list");
  const entries = picked.map((tool) => {
    const item = element("li");
    const remove = button("Remove", "bundle-remove", () => toggleSelection(tool.id, true));
    remove.disabled = busy;
    remove.setAttribute("aria-label", `Remove ${tool.title} from bundle`);
    item.append(element("span", tool.title), remove);
    return item;
  });
  if (!picked.length) entries.push(element("li", "Add Python tools from the catalog.", "bundle-empty"));
  list.replaceChildren(...entries);
  grid.querySelectorAll(".bundle-toggle").forEach((node) => {
    const selected = selection.has(node.dataset.toolId);
    node.disabled = busy;
    node.textContent = selected ? "Added" : "Add to bundle";
    node.setAttribute("aria-pressed", selected);
  });
}

function readSelection() {
  try {
    const ids = JSON.parse(localStorage.getItem(storageKey) || "[]");
    if (Array.isArray(ids)) {
      for (const tool of tools) {
        if (tool.wheel_package && ids.includes(tool.id)) selection.add(tool.id);
      }
    }
  } catch {
    // An invalid or unavailable saved selection starts empty.
  }
}

function renderCollections() {
  const list = byId("collection-grid");
  for (const bundle of catalog.installable_bundles) {
    const item = element("li");
    item.append(
      element("h3", bundle.title),
      element("p", `Offline install ZIP · ${bundle.runtime}`),
      link("Download ZIP", releaseUrl(bundle)),
      link("Install guide", docs(bundle.guide)),
      link("SHA-256", releaseUrl({ tag: bundle.tag, filename: "SHA256SUMS.txt" })),
    );
    list.append(item);
  }
  for (const archive of catalog.downloads) {
    const item = element("li");
    item.append(
      element("h3", archive.title),
      element("p", `Toolkit ${catalog.release.version} · ${archive.components} components · source ZIP`),
      link("Download source ZIP", archive.url),
      link("Verification guide", docs("packages/README.md")),
    );
    list.append(item);
  }
  for (const group of catalog.installable_collections) {
    const item = element("li");
    const guidePath = group.plan.replace(/\/[^/]+$/, "/README.md");
    item.append(
      element("h3", group.title),
      element("p", `${group.tools.length} tools · ${group.runtime}`),
      link("Download collection wheel", releaseUrl({ tag: group.tag, filename: group.collection_filename })),
      link("Group release", `${github}/releases/tag/${encodeURIComponent(group.tag)}`),
      link("SHA-256", releaseUrl({ tag: group.tag, filename: "SHA256SUMS.txt" })),
      link("Install guide and APIs", docs(guidePath)),
    );
    list.append(item);
  }
}

async function fetchFile(path) {
  const response = await fetch(path);
  if (!response.ok) throw new Error(`Could not download ${path}.`);
  return new Uint8Array(await response.arrayBuffer());
}

async function fetchWheel(tool) {
  const { filename, sha256 } = tool.wheel_package;
  if (!/^[a-zA-Z0-9_.-]+\.whl$/.test(filename) || !/^[a-f0-9]{64}$/.test(sha256)) {
    throw new Error(`Invalid release metadata for ${tool.title}.`);
  }
  const bytes = await fetchFile(`wheels/${encodeURIComponent(filename)}`);
  const digest = new Uint8Array(await crypto.subtle.digest("SHA-256", bytes));
  const actual = Array.from(digest, (byte) => byte.toString(16).padStart(2, "0")).join("");
  if (actual !== sha256) throw new Error(`Checksum mismatch for ${tool.title}.`);
  return [`wheels/${filename}`, bytes];
}

function bundleFiles(picked) {
  const text = new TextEncoder();
  const components = picked.map(({ id, title, wheel_package: wheel }) => ({
    id,
    title,
    filename: wheel.filename,
    sha256: wheel.sha256,
    release: releaseUrl(wheel),
    runtime: wheel.runtime,
    guide: docs(wheel.guide),
  }));
  const requirementLines = components.map(({ filename, sha256 }) => `./wheels/${filename} --hash=sha256:${sha256}`);
  const checksumLines = components.map(({ filename, sha256 }) => `${sha256}  wheels/${filename}`);
  const guide = [
    "# OUTLANDS custom Python bundle",
    "",
    "Extract into a fresh folder. Supply Python 3.12 or 3.13 and pip.",
    "Create and activate a virtual environment, then run from the extracted folder:",
    "",
    "    python -m pip install --no-index --no-deps --require-hashes -r requirements.txt",
    "",
    "The manifest links to the source releases and install guides for each wheel.",
    "The requirements file pins the SHA-256 of each wheel. No Python runtime is included.",
    "",
  ].join("\n");
  return [
    ["START-HERE.md", text.encode(guide)],
    ["MANIFEST.json", text.encode(JSON.stringify({ schema: 1, components }, null, 2) + "\n")],
    ["requirements.txt", text.encode(requirementLines.join("\n") + "\n")],
    ["SHA256SUMS.txt", text.encode(checksumLines.join("\n") + "\n")],
  ];
}

async function downloadBundle() {
  const picked = selectedTools();
  if (!picked.length || busy) return;
  busy = true;
  renderBundle();
  bundleStatus.textContent = `Verifying ${picked.length} ${picked.length === 1 ? "wheel" : "wheels"}…`;
  try {
    if (!globalThis.crypto?.subtle) throw new Error("Open the catalog over HTTPS to verify downloads.");
    const files = bundleFiles(picked);
    files.push(["LICENSE.txt", await fetchFile("LICENSE.txt")]);
    for (let offset = 0; offset < picked.length; offset += 8) {
      files.push(...await Promise.all(picked.slice(offset, offset + 8).map(fetchWheel)));
    }
    const blobUrl = URL.createObjectURL(new Blob([createZip(files)], { type: "application/zip" }));
    const download = element("a");
    download.href = blobUrl;
    download.download = "outlands-custom-tools.zip";
    document.body.append(download);
    download.click();
    download.remove();
    window.setTimeout(() => URL.revokeObjectURL(blobUrl), 1000);
    bundleStatus.textContent = "ZIP ready. Check your browser’s downloads.";
  } catch (error) {
    bundleStatus.textContent = `${error.message} Retry or download the individual wheels.`;
  } finally {
    busy = false;
    renderBundle();
  }
}

function renderReleaseOverview() {
  const summary = catalog.overview;
  const recent = byId("recent-releases");
  byId("catalog-overview").textContent = [
    [summary.tools, "tools"],
    [summary.systems, "systems"],
    [summary.entries_with_downloads, "entries with downloads"],
    [summary.individual_wheels, "individual Python wheels"],
  ].map(([count, label]) => count + " " + label).join(" · ");
  const byToolId = new Map(tools.map((tool) => [tool.id, tool]));
  recent.replaceChildren(...summary.recent_releases.map((id) => {
    const tool = byToolId.get(id);
    const item = element("li");
    const details = new URL(window.location.pathname, window.location.href);
    details.searchParams.set("tool", id);
    details.hash = "catalog";
    const { download, version, url } = tool.standalone_release;
    const label = download ? (download.kind === "wheel" ? "Python wheel" : "Source ZIP") : "Release";
    item.append(link(tool.title, details, "text-link"),
      link(label + " v" + version, download?.url || url, "recent-download"));
    return item;
  }));
  recent.closest("section").hidden = false;
}

async function init() {
  try {
    const response = await fetch("tool-catalog.json");
    if (!response.ok) throw new Error("Catalog temporarily unavailable.");
    catalog = await response.json();
    families = new Map([...catalog.groups, { id: "systems", title: "Application workbenches" }].map(({ id, title }) => [id, title]));
    tools = [...catalog.tools].sort((left, right) => left.title.localeCompare(right.title) || left.id.localeCompare(right.id));
    indexedTools = new Map(tools.map((tool) => [tool.id, [
      tool.id.replaceAll("-", " "), tool.title, tool.purpose, tool.requirements,
      families.get(tool.group), tool.wheel_package?.title, tool.wheel_package?.filename,
    ].filter(Boolean).join(" ").toLowerCase()]));
    for (const [id, title] of families) family.add(new Option(title, id));
    search.value = params.get("q") || "";
    family.value = families.has(params.get("category")) ? params.get("category") : "all";
    const format = params.get("availability");
    availability.value = ["wheel", "download", "source"].includes(format) ? format : "all";
    readSelection();
    renderReleaseOverview();
    renderCatalog();
    renderBundle();
    renderCollections();
    if (directTool && !window.location.hash) byId(`tool-${directTool}`)?.scrollIntoView();
  } catch (error) {
    byId("tool-result").textContent = "The catalog couldn’t load. Try refreshing or open the GitHub catalog.";
    console.error(error);
    return;
  }
  search.form.addEventListener("submit", (event) => event.preventDefault());
  search.addEventListener("input", updateFilters);
  family.addEventListener("change", updateFilters);
  availability.addEventListener("change", updateFilters);
  byId("tool-reset").addEventListener("click", () => {
    search.value = "";
    family.value = "all";
    availability.value = "all";
    updateFilters();
    search.focus();
  });
  previous.addEventListener("click", () => {
    page -= 1;
    renderCatalog({ focusPagination: true });
    byId("tool-result").scrollIntoView({ block: "center" });
  });
  next.addEventListener("click", () => {
    page += 1;
    renderCatalog({ focusPagination: true });
    byId("tool-result").scrollIntoView({ block: "center" });
  });
  bundleClear.addEventListener("click", () => {
    selection.clear();
    storeSelection();
    bundleStatus.textContent = "";
    renderBundle();
    byId("bundle-count").focus();
  });
  bundleDownload.addEventListener("click", downloadBundle);
}

init();
