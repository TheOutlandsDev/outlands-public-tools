(function () {
  const DEFAULT_DISCLOSURE =
    "This page may contain affiliate links. Review and replace this disclosure for your own links.";

  const state = {
    pages: [],
    pageTemplates: [],
    navigation: { items: [] },
    assets: [],
    page: null,
    data: { version: 1, theme: "natural", blocks: [] },
    selectedBlockId: null,
    dirty: false,
    navDirty: false,
    saving: false,
    lastSavedAt: "",
    assetFilter: "",
    unreadMessages: 0
  };

  const blockTypes = [
    { type: "hero", label: "Hero" },
    { type: "text", label: "Text" },
    { type: "image_text", label: "Image + Text" },
    { type: "three_cards", label: "Three Cards" },
    { type: "checklist", label: "Checklist" },
    { type: "faq", label: "FAQ" },
    { type: "affiliate_product", label: "Affiliate Product" },
    { type: "cta", label: "Call to Action" },
    { type: "divider", label: "Divider / Spacer" },
    { type: "contact", label: "Contact / Email" }
  ];

  const stylePresets = [
    { label: "Default", swatch: "#fffdf8", style: {} },
    {
      label: "Sage",
      swatch: "#edf4ea",
      style: {
        backgroundColor: "#edf4ea",
        textColor: "#4f6256",
        headingColor: "#22362b",
        accentColor: "#5c8667",
        buttonTextColor: "#ffffff"
      }
    },
    {
      label: "Cream",
      swatch: "#fff6e6",
      style: {
        backgroundColor: "#fff6e6",
        textColor: "#6a5d49",
        headingColor: "#2b2821",
        accentColor: "#9a7040",
        buttonTextColor: "#ffffff"
      }
    },
    {
      label: "Blush",
      swatch: "#f9e8e3",
      style: {
        backgroundColor: "#f9e8e3",
        textColor: "#715b58",
        headingColor: "#352827",
        accentColor: "#a85f59",
        buttonTextColor: "#ffffff"
      }
    },
    {
      label: "Sky",
      swatch: "#e8f0f4",
      style: {
        backgroundColor: "#e8f0f4",
        textColor: "#4d636d",
        headingColor: "#213038",
        accentColor: "#517d8a",
        buttonTextColor: "#ffffff"
      }
    },
    {
      label: "Moss",
      swatch: "#315b41",
      style: {
        backgroundColor: "#315b41",
        textColor: "#edf4ea",
        headingColor: "#ffffff",
        accentColor: "#d2b48c",
        buttonTextColor: "#26342d",
        itemBackgroundColor: "#416d50",
        itemTextColor: "#ffffff"
      }
    }
  ];

  const colorStyleFields = [
    ["backgroundColor", "--block-bg"],
    ["textColor", "--block-text"],
    ["headingColor", "--block-heading"],
    ["accentColor", "--block-accent"],
    ["buttonTextColor", "--block-button-text"],
    ["itemBackgroundColor", "--block-item-bg"],
    ["itemTextColor", "--block-item-text"]
  ];

  const headingSizeStyles = {
    small: {
      "--block-h1-size": "clamp(2rem, 5vw, 4rem)",
      "--block-h2-size": "clamp(1.35rem, 2.4vw, 2rem)",
      "--block-h3-size": "1.08rem"
    },
    large: {
      "--block-h1-size": "clamp(3rem, 7.5vw, 6.2rem)",
      "--block-h2-size": "clamp(2rem, 3.7vw, 3.1rem)",
      "--block-h3-size": "1.42rem"
    },
    display: {
      "--block-h1-size": "clamp(3.4rem, 8.8vw, 7rem)",
      "--block-h2-size": "clamp(2.25rem, 4.4vw, 3.65rem)",
      "--block-h3-size": "1.6rem"
    }
  };

  const bodySizeStyles = {
    small: { "--block-body-size": "0.95rem" },
    large: { "--block-body-size": "1.15rem" },
    xlarge: { "--block-body-size": "1.28rem" }
  };

  const spacingStyles = {
    tight: { "--block-space": "14px" },
    roomy: { "--block-space": "36px" },
    wide: { "--block-space": "52px" }
  };

  const paddingStyles = {
    compact: { "--block-padding": "clamp(18px, 2.5vw, 30px)" },
    roomy: { "--block-padding": "clamp(34px, 5vw, 70px)" },
    huge: { "--block-padding": "clamp(44px, 7vw, 96px)" }
  };

  const radiusStyles = {
    square: { "--block-radius": "8px" },
    soft: { "--block-radius": "18px" },
    round: { "--block-radius": "30px" }
  };

  const itemSizeStyles = {
    compact: {
      "--block-item-min-height": "40px",
      "--block-item-padding": "9px 12px",
      "--block-item-font-size": "0.95rem"
    },
    roomy: {
      "--block-item-min-height": "58px",
      "--block-item-padding": "16px 18px",
      "--block-item-font-size": "1.08rem"
    },
    large: {
      "--block-item-min-height": "66px",
      "--block-item-padding": "18px 20px",
      "--block-item-font-size": "1.18rem"
    }
  };

  const els = {};

  document.addEventListener("DOMContentLoaded", init);

  async function init() {
    state.csrf=(await api("/api/csrf")).csrf;
    cacheElements();
    bindEvents();
    renderBlockButtons();

    try {
      await Promise.all([loadPages(), loadAssets(), loadMessageCount(), loadPageTemplates(), loadNavigation()]);
      const slugFromUrl = getSlugFromUrl();
      const firstSlug =
        slugFromUrl ||
        (state.pages.find((page) => page.slug === "home") || state.pages[0] || {}).slug;
      if (firstSlug) {
        await openPage(firstSlug, false);
      }
      setStatus("Builder ready.");
      window.setInterval(function () {
        if (state.dirty && !state.saving) {
          saveDraft({ quiet: true });
        }
      }, 60000);
    } catch (error) {
      setStatus(error.message || "Builder could not load.");
      showToast(error.message || "Builder could not load.");
    }
  }

  function cacheElements() {
    els.pageList = document.getElementById("pageList");
    els.templateButtons = document.getElementById("templateButtons");
    els.blockButtons = document.getElementById("blockButtons");
    els.assetGrid = document.getElementById("assetGrid");
    els.assetUpload = document.getElementById("assetUpload");
    els.assetSearch = document.getElementById("assetSearch");
    els.preview = document.getElementById("preview");
    els.settingsPanel = document.getElementById("settingsPanel");
    els.saveDraftBtn = document.getElementById("saveDraftBtn");
    els.publishBtn = document.getElementById("publishBtn");
    els.previewBtn = document.getElementById("previewBtn");
    els.viewSiteLink = document.getElementById("viewSiteLink");
    els.inboxLink = document.getElementById("inboxLink");
    els.logoutBtn = document.getElementById("logoutBtn");
    els.addPageBtn = document.getElementById("addPageBtn");
    els.navPanel = document.getElementById("navPanel");
    els.saveNavBtn = document.getElementById("saveNavBtn");
    els.statusbar = document.getElementById("statusbar");
    els.toast = document.getElementById("toast");
    els.currentSlug = document.getElementById("currentSlug");
    els.currentStatus = document.getElementById("currentStatus");
    els.dirtyState = document.getElementById("dirtyState");
    els.pageTitleInput = document.getElementById("pageTitleInput");
    els.pageDescriptionInput = document.getElementById("pageDescriptionInput");
  }

  function bindEvents() {
    els.saveDraftBtn.addEventListener("click", saveDraft);
    els.publishBtn.addEventListener("click", publishPage);
    els.previewBtn.addEventListener("click", previewPage);
    els.logoutBtn.addEventListener("click", logout);
    els.addPageBtn.addEventListener("click", function () {
      addPage("guide");
    });
    els.saveNavBtn.addEventListener("click", saveNavigation);
    els.assetSearch.addEventListener("input", function () {
      state.assetFilter = els.assetSearch.value.trim().toLowerCase();
      renderAssets();
    });
    els.assetUpload.addEventListener("change", uploadAsset);
    els.pageTitleInput.addEventListener("input", function () {
      if (!state.page) return;
      state.page.title = els.pageTitleInput.value;
      markDirty();
      renderPageList();
    });
    els.pageDescriptionInput.addEventListener("input", function () {
      if (!state.page) return;
      state.page.description = els.pageDescriptionInput.value;
      markDirty();
    });
    window.addEventListener("beforeunload", function (event) {
      if (!state.dirty && !state.navDirty) return;
      event.preventDefault();
      event.returnValue = "";
    });
    document.addEventListener("keydown", function (event) {
      const key = event.key.toLowerCase();
      if ((event.ctrlKey || event.metaKey) && key === "s") {
        event.preventDefault();
        saveDraft();
      }
    });
  }

  async function api(path, options) {
    const opts = options || {};
    const headers = opts.headers || {};
    if(opts.method&&!["GET","HEAD"].includes(opts.method.toUpperCase()))headers["X-CSRF-Token"]=state.csrf;
    const isFormData = opts.body instanceof FormData;
    if (opts.body && !isFormData && !headers["Content-Type"]) {
      headers["Content-Type"] = "application/json";
    }
    const response = await fetch(path, {
      credentials: "same-origin",
      ...opts,
      headers
    });

    if (response.status === 401) {
      window.location.href = "/admin/login";
      throw new Error("Login required.");
    }

    const text = await response.text();
    let data = {};
    if (text) {
      try {
        data = JSON.parse(text);
      } catch {
        data = { raw: text };
      }
    }
    if (!response.ok) {
      throw new Error(data.error || "Request failed.");
    }
    return data;
  }

  async function loadPages() {
    const result = await api("/api/pages");
    state.pages = result.pages || [];
    renderPageList();
  }

  async function loadPageTemplates() {
    const result = await api("/api/page-templates");
    state.pageTemplates = result.templates || [];
    renderTemplateButtons();
  }

  async function loadNavigation() {
    const result = await api("/api/navigation");
    state.navigation = { items: result.items || [] };
    state.navDirty = false;
    renderNavigation();
  }

  async function loadAssets() {
    const result = await api("/api/assets");
    state.assets = result.assets || [];
    renderAssets();
  }

  async function loadMessageCount() {
    const result = await api("/api/messages");
    const messages = result.messages || [];
    state.unreadMessages = messages.filter((message) => message.status === "new").length;
    renderInboxBadge();
  }

  async function openPage(slug, pushHistory) {
    const result = await api(`/api/pages/${encodeURIComponent(slug)}`);
    state.page = result.page;
    state.data = normalizeData(result.page.draft_json);
    state.selectedBlockId = state.data.blocks[0] ? state.data.blocks[0].id : null;
    state.dirty = false;
    state.lastSavedAt = state.page.updated_at || "";

    els.pageTitleInput.value = state.page.title || "";
    els.pageDescriptionInput.value = state.page.description || "";
    els.currentSlug.textContent = `/${state.page.slug === "home" ? "" : state.page.slug}`;
    els.currentStatus.textContent = pageStatusLabel(state.page);
    updatePublishedLink();
    if (pushHistory !== false) {
      window.history.replaceState({}, "", `/admin/builder/${state.page.slug}`);
    }

    renderPageList();
    renderPreview();
    renderSettings();
    updateDirtyLabel();
  }

  function updatePublishedLink() {
    if (!state.page) return;
    const url = state.page.slug === "home" ? "/" : `/${state.page.slug}`;
    els.viewSiteLink.href = url;
  }

  function pageStatusLabel(page) {
    if (!page) return "";
    if (page.published_at) {
      return `Published ${formatDate(page.published_at)}`;
    }
    return page.status === "published" ? "Published" : "Draft";
  }

  function formatDate(value) {
    if (!value) return "";
    const date = new Date(value);
    if (Number.isNaN(date.getTime())) return value;
    return date.toLocaleString([], {
      month: "short",
      day: "numeric",
      hour: "numeric",
      minute: "2-digit"
    });
  }

  function renderInboxBadge() {
    if (!els.inboxLink) return;
    els.inboxLink.textContent = state.unreadMessages
      ? `Inbox (${state.unreadMessages})`
      : "Inbox";
  }

  function normalizeData(data) {
    if (!data || typeof data !== "object") {
      return { version: 1, theme: "natural", blocks: [] };
    }
    return {
      version: data.version || 1,
      theme: data.theme || "natural",
      blocks: Array.isArray(data.blocks) ? data.blocks : []
    };
  }

  function getSlugFromUrl() {
    const match = window.location.pathname.match(/^\/admin\/builder\/([^/]+)$/);
    return match ? decodeURIComponent(match[1]) : "";
  }

  function renderPageList() {
    els.pageList.innerHTML = "";
    state.pages.forEach((page) => {
      const row = document.createElement("div");
      row.className = "page-row";

      const openBtn = document.createElement("button");
      openBtn.type = "button";
      const title = document.createElement("span");
      title.className = "page-title";
      title.textContent = page.title;
      const status = document.createElement("span");
      status.className = `page-status ${page.status === "published" ? "published" : "draft"}`;
      status.textContent = page.status === "published" ? "Published" : "Draft";
      openBtn.append(title, status);
      openBtn.className = state.page && page.slug === state.page.slug ? "active" : "";
      openBtn.addEventListener("click", function () {
        if (state.dirty && !window.confirm("Discard unsaved changes and open another page?")) {
          return;
        }
        openPage(page.slug);
      });

      const deleteBtn = document.createElement("button");
      deleteBtn.type = "button";
      deleteBtn.textContent = "Del";
      deleteBtn.className = "small";
      deleteBtn.disabled = page.slug === "home";
      deleteBtn.addEventListener("click", function () {
        deletePage(page.slug);
      });

      row.append(openBtn, deleteBtn);
      els.pageList.append(row);
    });
  }

  function renderTemplateButtons() {
    if (!els.templateButtons) return;
    els.templateButtons.innerHTML = "";
    if (!state.pageTemplates.length) {
      const empty = document.createElement("p");
      empty.className = "hint";
      empty.textContent = "Templates are loading.";
      els.templateButtons.append(empty);
      return;
    }

    state.pageTemplates.forEach((template) => {
      const button = document.createElement("button");
      button.type = "button";
      const label = document.createElement("span");
      label.className = "template-label";
      label.textContent = template.label || template.id;
      const description = document.createElement("span");
      description.className = "template-description";
      description.textContent = template.description || "";
      button.append(label, description);
      button.addEventListener("click", function () {
        addPage(template.id);
      });
      els.templateButtons.append(button);
    });
  }

  function renderNavigation() {
    if (!els.navPanel) return;
    els.navPanel.innerHTML = "";
    const items = state.navigation.items || [];
    if (!items.length) {
      const empty = document.createElement("p");
      empty.className = "hint";
      empty.textContent = "No pages are available yet.";
      els.navPanel.append(empty);
      return;
    }

    items.forEach((item, index) => {
      const row = document.createElement("div");
      row.className = `nav-row${item.visible ? "" : " muted-row"}`;

      const include = document.createElement("input");
      include.type = "checkbox";
      include.checked = item.visible !== false;
      include.title = "Show in top menu";
      include.addEventListener("change", function () {
        item.visible = include.checked;
        markNavDirty();
        renderNavigation();
      });

      const body = document.createElement("div");
      body.className = "nav-row-body";
      const label = document.createElement("input");
      label.value = item.label || item.title || item.slug;
      label.placeholder = item.title || item.slug;
      label.addEventListener("input", function () {
        item.label = label.value;
        markNavDirty();
      });
      const meta = document.createElement("span");
      meta.textContent = `${item.title || item.slug} - ${item.status === "published" ? "published" : "draft"}`;
      body.append(label, meta);

      const controls = document.createElement("div");
      controls.className = "nav-row-tools";
      const up = toolButton("Up", function () {
        moveNavItem(index, -1);
      });
      const down = toolButton("Down", function () {
        moveNavItem(index, 1);
      });
      up.disabled = index === 0;
      down.disabled = index === items.length - 1;
      controls.append(up, down);

      row.append(include, body, controls);
      els.navPanel.append(row);
    });

    updateNavigationSaveButton();
  }

  function renderBlockButtons() {
    els.blockButtons.innerHTML = "";
    blockTypes.forEach((blockType) => {
      const button = document.createElement("button");
      button.type = "button";
      button.textContent = blockType.label;
      button.addEventListener("click", function () {
        addBlock(blockType.type);
      });
      els.blockButtons.append(button);
    });
  }

  function renderPreview() {
    els.preview.innerHTML = "";
    const page = document.createElement("div");
    page.className = "pm-edit-page";

    if (!state.data.blocks.length) {
      const empty = document.createElement("section");
      empty.className = "edit-block";
      empty.innerHTML = '<div class="pm-section"><h2>No blocks yet</h2><p class="pm-copy">Add a block from the left sidebar.</p></div>';
      page.append(empty);
    }

    state.data.blocks.forEach((block, index) => {
      page.append(renderEditBlock(block, index));
    });

    els.preview.append(page);
  }

  function renderEditBlock(block, index) {
    const wrapper = document.createElement("section");
    wrapper.className = `edit-block${block.id === state.selectedBlockId ? " selected" : ""}`;
    wrapper.dataset.blockId = block.id;
    applyBlockStyleVars(wrapper, block);
    wrapper.addEventListener("click", function (event) {
      if (event.target.closest(".block-tools")) return;
      if (event.target.closest(".editable")) return;
      selectBlock(block.id);
    });

    const tools = document.createElement("div");
    tools.className = "block-tools";
    tools.append(
      toolButton("Up", function () {
        moveBlock(index, -1);
      }),
      toolButton("Down", function () {
        moveBlock(index, 1);
      }),
      toolButton("Copy", function () {
        duplicateBlock(index);
      }),
      toolButton("Delete", function () {
        deleteBlock(index);
      }, true)
    );

    wrapper.append(tools, renderBlockContent(block));
    return wrapper;
  }

  function toolButton(label, onClick, danger) {
    const button = document.createElement("button");
    button.type = "button";
    button.className = `small${danger ? " danger" : ""}`;
    button.textContent = label;
    button.addEventListener("click", function (event) {
      event.stopPropagation();
      onClick();
    });
    return button;
  }

  function renderBlockContent(block) {
    const settings = ensureSettings(block);
    switch (block.type) {
      case "hero":
        return section("pm-section pm-hero", [
          editable("p", block, "settings.kicker", "pm-kicker"),
          editable("h1", block, "settings.headline"),
          editable("div", block, "settings.body", "pm-copy editable-body"),
          editable("span", block, "settings.buttonText", "pm-button-preview")
        ]);
      case "text":
        return section("pm-section", [
          editable("p", block, "settings.kicker", "pm-kicker"),
          editable("h2", block, "settings.heading"),
          editable("div", block, "settings.body", "pm-copy editable-body")
        ]);
      case "image_text":
        return section("pm-section pm-image-text", [
          imagePreview(settings.imageUrl, settings.heading),
          div([
            editable("p", block, "settings.kicker", "pm-kicker"),
            editable("h2", block, "settings.heading"),
            editable("div", block, "settings.body", "pm-copy editable-body"),
            editable("span", block, "settings.buttonText", "pm-button-preview")
          ])
        ]);
      case "three_cards":
        ensureCards(block);
        return section("pm-section", [
          editable("h2", block, "settings.heading"),
          editable("div", block, "settings.body", "pm-copy editable-body"),
          cardGrid(block)
        ]);
      case "checklist":
        ensureChecklist(block);
        return section("pm-section pm-checklist", [
          editable("h2", block, "settings.heading"),
          editable("div", block, "settings.body", "pm-copy editable-body"),
          checklist(block)
        ]);
      case "faq":
        ensureFaqs(block);
        return section("pm-section pm-faq", [
          editable("h2", block, "settings.heading"),
          faqList(block)
        ]);
      case "affiliate_product":
        return section("pm-section pm-affiliate", [
          imagePreview(settings.imageUrl, settings.productName),
          div([
            text("p", "Recommended resource", "pm-kicker"),
            editable("h2", block, "settings.productName"),
            editable("div", block, "settings.shortDescription", "pm-copy editable-body"),
            editable("span", block, "settings.buttonText", "pm-button-preview"),
            editable("p", block, "settings.disclosureText", "muted")
          ])
        ]);
      case "cta":
        return section("pm-section", [
          editable("h2", block, "settings.heading"),
          editable("div", block, "settings.body", "pm-copy editable-body"),
          editable("span", block, "settings.buttonText", "pm-button-preview")
        ]);
      case "divider":
        return section("pm-section", [
          text("p", `Spacer height: ${settings.height || 32}px`, "muted")
        ]);
      case "contact":
        return section("pm-section pm-contact", [
          div([
            text("p", "Email Outlands Local Site Builder", "pm-kicker"),
            editable("h2", block, "settings.heading"),
            editable("div", block, "settings.body", "pm-copy editable-body"),
            text("p", settings.contactEmail || "hello@example.invalid", "muted")
          ]),
          contactPreview(block)
        ]);
      default:
        return section("pm-section", [text("p", "Unknown block type", "muted")]);
    }
  }

  function section(className, children) {
    const node = document.createElement("div");
    node.className = className;
    children.filter(Boolean).forEach((child) => node.append(child));
    return node;
  }

  function div(children, className) {
    const node = document.createElement("div");
    if (className) node.className = className;
    children.filter(Boolean).forEach((child) => node.append(child));
    return node;
  }

  function text(tag, value, className) {
    const node = document.createElement(tag);
    if (className) node.className = className;
    node.textContent = value || "";
    return node;
  }

  function editable(tag, block, path, className) {
    const node = document.createElement(tag);
    node.className = `editable${className ? ` ${className}` : ""}`;
    node.contentEditable = "true";
    node.spellcheck = true;
    node.textContent = getPath(block, path) || "";
    node.addEventListener("input", function () {
      setPath(block, path, node.textContent);
      markDirty();
    });
    node.addEventListener("focus", function () {
      selectBlock(block.id, true);
    });
    return node;
  }

  function imagePreview(url, alt) {
    if (url) {
      const image = document.createElement("img");
      image.className = "pm-image-preview";
      image.src = url;
      image.alt = alt || "Selected image";
      return image;
    }
    return text("div", "Select or upload an image", "pm-image-empty");
  }

  function cardGrid(block) {
    const grid = document.createElement("div");
    grid.className = "pm-card-grid";
    block.settings.cards.slice(0, 3).forEach((_card, index) => {
      const card = document.createElement("article");
      card.className = "pm-card";
      card.append(
        editable("h3", block, `settings.cards.${index}.title`),
        editable("p", block, `settings.cards.${index}.body`, "pm-copy"),
        editable("span", block, `settings.cards.${index}.buttonText`, "pm-button-preview")
      );
      grid.append(card);
    });
    return grid;
  }

  function checklist(block) {
    const list = document.createElement("ul");
    block.settings.items.forEach((_item, index) => {
      const item = document.createElement("li");
      item.append(editable("span", block, `settings.items.${index}`));
      list.append(item);
    });
    return list;
  }

  function faqList(block) {
    const holder = document.createElement("div");
    block.settings.faqs.forEach((_faq, index) => {
      const details = document.createElement("details");
      details.open = true;
      const summary = document.createElement("summary");
      summary.append(editable("span", block, `settings.faqs.${index}.question`));
      details.append(summary, editable("div", block, `settings.faqs.${index}.answer`, "pm-copy editable-body"));
      holder.append(details);
    });
    return holder;
  }

  function contactPreview(block) {
    const form = document.createElement("div");
    form.className = "pm-contact-form";
    ["Name", "Email", "Subject", "Message"].forEach((label) => {
      const field = document.createElement("label");
      field.textContent = label;
      const input = label === "Message" ? document.createElement("textarea") : document.createElement("input");
      input.disabled = true;
      input.placeholder = label;
      field.append(input);
      form.append(field);
    });
    form.append(editable("span", block, "settings.buttonText", "pm-button-preview"));
    return form;
  }

  function renderSettings() {
    els.settingsPanel.innerHTML = "";
    const block = selectedBlock();

    if (!block) {
      const hint = document.createElement("p");
      hint.className = "hint";
      hint.textContent = "Select a block in the preview to edit its settings.";
      els.settingsPanel.append(hint);
      return;
    }

    ensureStyle(block);

    const title = document.createElement("h3");
    title.textContent = labelForBlock(block.type);
    els.settingsPanel.append(title, settingsActions(block));

    switch (block.type) {
      case "hero":
        appendFields(block, [
          ["Kicker", "settings.kicker"],
          ["Headline", "settings.headline"],
          ["Body", "settings.body", "textarea"],
          ["Button text", "settings.buttonText"],
          ["Button URL", "settings.buttonUrl"]
        ]);
        break;
      case "text":
        appendFields(block, [
          ["Kicker", "settings.kicker"],
          ["Heading", "settings.heading"],
          ["Body", "settings.body", "textarea"]
        ]);
        break;
      case "image_text":
        appendFields(block, [
          ["Kicker", "settings.kicker"],
          ["Heading", "settings.heading"],
          ["Body", "settings.body", "textarea"],
          ["Button text", "settings.buttonText"],
          ["Button URL", "settings.buttonUrl"],
          ["Image URL", "settings.imageUrl", "asset"]
        ]);
        break;
      case "three_cards":
        ensureCards(block);
        appendFields(block, [
          ["Heading", "settings.heading"],
          ["Body", "settings.body", "textarea"]
        ]);
        for (let index = 0; index < 3; index += 1) {
          appendDivider(`Card ${index + 1}`);
          appendFields(block, [
            ["Title", `settings.cards.${index}.title`],
            ["Body", `settings.cards.${index}.body`, "textarea"],
            ["Button text", `settings.cards.${index}.buttonText`],
            ["Button URL", `settings.cards.${index}.buttonUrl`]
          ]);
        }
        break;
      case "checklist":
        ensureChecklist(block);
        appendFields(block, [
          ["Heading", "settings.heading"],
          ["Body", "settings.body", "textarea"]
        ]);
        appendListField(block, "Checklist items", "settings.items");
        break;
      case "faq":
        ensureFaqs(block);
        appendFields(block, [["Heading", "settings.heading"]]);
        appendFaqField(block);
        break;
      case "affiliate_product":
        appendFields(block, [
          ["Product name", "settings.productName"],
          ["Short description", "settings.shortDescription", "textarea"],
          ["Image URL", "settings.imageUrl", "asset"],
          ["Button text", "settings.buttonText"],
          ["Affiliate URL", "settings.affiliateUrl"],
          ["Disclosure text", "settings.disclosureText", "textarea"]
        ]);
        break;
      case "cta":
        appendFields(block, [
          ["Heading", "settings.heading"],
          ["Body", "settings.body", "textarea"],
          ["Button text", "settings.buttonText"],
          ["Button URL", "settings.buttonUrl"]
        ]);
        break;
      case "divider":
        appendFields(block, [["Height", "settings.height", "number"]]);
        break;
      case "contact":
        appendFields(block, [
          ["Heading", "settings.heading"],
          ["Body", "settings.body", "textarea"],
          ["Public email", "settings.contactEmail"],
          ["Subject", "settings.subject"],
          ["Button text", "settings.buttonText"]
        ]);
        break;
    }

    if (block.type !== "divider") {
      appendDesignControls(block);
    }
  }

  function settingsActions(block) {
    const holder = document.createElement("div");
    holder.className = "settings-actions";
    const index = state.data.blocks.findIndex((item) => item.id === block.id);
    holder.append(
      toolButton("Move up", function () {
        moveBlock(index, -1);
      }),
      toolButton("Move down", function () {
        moveBlock(index, 1);
      }),
      toolButton("Duplicate", function () {
        duplicateBlock(index);
      }),
      toolButton("Delete", function () {
        deleteBlock(index);
      }, true)
    );
    return holder;
  }

  function appendDivider(label) {
    const divider = document.createElement("p");
    divider.className = "eyebrow";
    divider.textContent = label;
    els.settingsPanel.append(divider);
  }

  function appendFields(block, fields) {
    fields.forEach(([label, path, type]) => {
      if (type === "asset") {
        els.settingsPanel.append(assetField(block, label, path));
      } else {
        els.settingsPanel.append(settingField(block, label, path, type || "text"));
      }
    });
  }

  function appendDesignControls(block) {
    appendDivider("Design");

    const presets = document.createElement("div");
    presets.className = "style-presets";
    stylePresets.forEach((preset) => {
      const button = document.createElement("button");
      button.type = "button";
      button.className = "style-preset";
      const swatch = document.createElement("span");
      swatch.style.background = preset.swatch;
      const label = document.createElement("span");
      label.textContent = preset.label;
      button.append(swatch, label);
      button.addEventListener("click", function () {
        block.style = deepClone(preset.style || {});
        markDirty();
        renderPreview();
        renderSettings();
      });
      presets.append(button);
    });
    els.settingsPanel.append(presets);

    els.settingsPanel.append(
      styleSelectField(block, "Heading size", "style.headingSize", [
        ["", "Default"],
        ["small", "Small"],
        ["large", "Large"],
        ["display", "Display"]
      ]),
      styleSelectField(block, "Text size", "style.bodySize", [
        ["", "Default"],
        ["small", "Small"],
        ["large", "Large"],
        ["xlarge", "Extra large"]
      ]),
      styleSelectField(block, "Spacing after block", "style.spacing", [
        ["", "Default"],
        ["tight", "Tight"],
        ["roomy", "Roomy"],
        ["wide", "Wide"]
      ]),
      styleSelectField(block, "Inside spacing", "style.padding", [
        ["", "Default"],
        ["compact", "Compact"],
        ["roomy", "Roomy"],
        ["huge", "Huge"]
      ]),
      styleSelectField(block, "Corner shape", "style.radius", [
        ["", "Default"],
        ["square", "Square"],
        ["soft", "Soft"],
        ["round", "Round"]
      ]),
      styleColorField(block, "Section color", "style.backgroundColor", "#fffdf8"),
      styleColorField(block, "Text color", "style.textColor", "#627066"),
      styleColorField(block, "Heading color", "style.headingColor", "#202b25"),
      styleColorField(block, "Accent / button color", "style.accentColor", "#2f5b40"),
      styleColorField(block, "Button text color", "style.buttonTextColor", "#ffffff")
    );

    if (["checklist", "three_cards"].includes(block.type)) {
      els.settingsPanel.append(
        styleColorField(block, block.type === "checklist" ? "Checklist box color" : "Card color", "style.itemBackgroundColor", "#edf4ea"),
        styleColorField(block, block.type === "checklist" ? "Checklist text color" : "Card text color", "style.itemTextColor", "#26342d"),
        styleSelectField(block, block.type === "checklist" ? "Checklist item size" : "Card size", "style.itemSize", [
          ["", "Default"],
          ["compact", "Compact"],
          ["roomy", "Roomy"],
          ["large", "Large"]
        ])
      );
    }
  }

  function styleColorField(block, label, path, defaultColor) {
    const holder = document.createElement("div");
    holder.className = "field color-field";
    const labelNode = document.createElement("span");
    labelNode.textContent = label;

    const row = document.createElement("div");
    row.className = "color-row";
    const input = document.createElement("input");
    input.type = "color";
    input.value = cleanColor(getPath(block, path)) || defaultColor;
    const valueLabel = document.createElement("span");
    valueLabel.className = "color-value";
    valueLabel.textContent = cleanColor(getPath(block, path)) || "Default";
    const clear = toolButton("Default", function () {
      deletePath(block, path);
      markDirty();
      renderPreview();
      renderSettings();
    });

    input.addEventListener("input", function () {
      setPath(block, path, input.value);
      valueLabel.textContent = input.value;
      markDirty();
      renderPreview();
    });

    row.append(input, valueLabel, clear);
    holder.append(labelNode, row);
    return holder;
  }

  function styleSelectField(block, label, path, options) {
    const holder = document.createElement("label");
    holder.className = "field";
    holder.textContent = label;
    const select = document.createElement("select");
    options.forEach(([value, textValue]) => {
      const option = document.createElement("option");
      option.value = value;
      option.textContent = textValue;
      select.append(option);
    });
    select.value = getPath(block, path) || "";
    select.addEventListener("change", function () {
      if (select.value) {
        setPath(block, path, select.value);
      } else {
        deletePath(block, path);
      }
      markDirty();
      renderPreview();
    });
    holder.append(select);
    return holder;
  }

  function settingField(block, label, path, type) {
    const holder = document.createElement("label");
    holder.className = "field";
    holder.textContent = label;
    const input = type === "textarea" ? document.createElement("textarea") : document.createElement("input");
    input.value = getPath(block, path) || "";
    if (type === "number") input.type = "number";
    input.addEventListener("input", function () {
      const value = type === "number" ? Number(input.value || 0) : input.value;
      setPath(block, path, value);
      markDirty();
      renderPreview();
    });
    holder.append(input);
    return holder;
  }

  function assetField(block, label, path) {
    const holder = document.createElement("div");
    holder.className = "field";
    const labelNode = document.createElement("label");
    labelNode.textContent = label;
    const input = document.createElement("input");
    input.value = getPath(block, path) || "";
    input.placeholder = "/uploads/images/example.jpg";
    input.addEventListener("input", function () {
      setPath(block, path, input.value);
      markDirty();
      renderPreview();
    });
    labelNode.append(input);
    holder.append(labelNode);

    const select = document.createElement("select");
    const empty = document.createElement("option");
    empty.value = "";
    empty.textContent = "Choose uploaded asset";
    select.append(empty);
    state.assets.forEach((asset) => {
      const option = document.createElement("option");
      option.value = asset.url;
      option.textContent = asset.original_name || asset.filename;
      select.append(option);
    });
    select.addEventListener("change", function () {
      if (!select.value) return;
      input.value = select.value;
      setPath(block, path, select.value);
      markDirty();
      renderPreview();
    });
    holder.append(select);
    return holder;
  }

  function appendListField(block, label, path) {
    const holder = document.createElement("label");
    holder.className = "field";
    holder.textContent = label;
    const textarea = document.createElement("textarea");
    textarea.value = (getPath(block, path) || []).join("\n");
    textarea.addEventListener("input", function () {
      setPath(
        block,
        path,
        textarea.value
          .split("\n")
          .map((item) => item.trim())
          .filter(Boolean)
      );
      markDirty();
      renderPreview();
    });
    holder.append(textarea);
    els.settingsPanel.append(holder);
  }

  function appendFaqField(block) {
    const holder = document.createElement("label");
    holder.className = "field";
    holder.textContent = "FAQ pairs, one per line: Question | Answer";
    const textarea = document.createElement("textarea");
    textarea.value = block.settings.faqs
      .map((faq) => `${faq.question || ""} | ${faq.answer || ""}`)
      .join("\n");
    textarea.addEventListener("input", function () {
      block.settings.faqs = textarea.value
        .split("\n")
        .map((line) => {
          const parts = line.split("|");
          return {
            question: (parts[0] || "").trim(),
            answer: parts.slice(1).join("|").trim()
          };
        })
        .filter((faq) => faq.question || faq.answer);
      markDirty();
      renderPreview();
    });
    holder.append(textarea);
    els.settingsPanel.append(holder);
  }

  function renderAssets() {
    els.assetGrid.innerHTML = "";
    const assets = state.assets.filter((asset) => {
      const haystack = `${asset.original_name || ""} ${asset.filename || ""}`.toLowerCase();
      return !state.assetFilter || haystack.includes(state.assetFilter);
    });

    if (!assets.length) {
      const empty = document.createElement("p");
      empty.className = "hint";
      empty.textContent = "No matching assets.";
      els.assetGrid.append(empty);
      return;
    }

    assets.forEach((asset) => {
      const item = document.createElement("div");
      item.className = "asset-item";
      const img = document.createElement("img");
      img.src = asset.url;
      img.alt = asset.original_name || asset.filename;

      const body = document.createElement("div");
      const name = document.createElement("div");
      name.className = "asset-name";
      name.title = asset.original_name || asset.filename;
      name.textContent = asset.original_name || asset.filename;

      const actions = document.createElement("div");
      actions.className = "asset-actions";
      actions.append(
        toolButton("Insert", function () {
          insertAsset(asset.url);
        }),
        toolButton("Copy", function () {
          copyText(asset.url);
        }),
        toolButton("Del", function () {
          deleteAsset(asset.id);
        }, true)
      );

      body.append(name, actions);
      item.append(img, body);
      els.assetGrid.append(item);
    });
  }

  async function uploadAsset() {
    const file = els.assetUpload.files[0];
    if (!file) return;
    const form = new FormData();
    form.append("image", file);
    try {
      setStatus("Uploading asset...");
      await api("/api/assets/upload", { method: "POST", body: form });
      els.assetUpload.value = "";
      await loadAssets();
      showToast("Asset uploaded.");
      setStatus("Asset uploaded.");
    } catch (error) {
      showToast(error.message);
      setStatus(error.message);
    }
  }

  async function deleteAsset(id) {
    if (!window.confirm("Delete this asset?")) return;
    try {
      await api(`/api/assets/${id}`, { method: "DELETE" });
      await loadAssets();
      showToast("Asset deleted.");
    } catch (error) {
      showToast(error.message);
    }
  }

  function insertAsset(url) {
    const block = selectedBlock();
    if (!block) {
      copyText(url);
      return;
    }
    if (["image_text", "affiliate_product"].includes(block.type)) {
      block.settings.imageUrl = url;
      markDirty();
      renderPreview();
      renderSettings();
      showToast("Asset inserted.");
      return;
    }
    copyText(url);
    showToast("Asset URL copied. Select an image block to insert it.");
  }

  async function copyText(value) {
    try {
      await navigator.clipboard.writeText(value);
      showToast("Copied.");
    } catch {
      window.prompt("Copy this URL:", value);
    }
  }

  function moveNavItem(index, direction) {
    const items = state.navigation.items || [];
    const nextIndex = index + direction;
    if (nextIndex < 0 || nextIndex >= items.length) return;
    const [item] = items.splice(index, 1);
    items.splice(nextIndex, 0, item);
    markNavDirty();
    renderNavigation();
  }

  function markNavDirty() {
    state.navDirty = true;
    updateNavigationSaveButton();
  }

  function updateNavigationSaveButton() {
    if (!els.saveNavBtn) return;
    els.saveNavBtn.textContent = state.navDirty ? "Save*" : "Save";
    els.saveNavBtn.classList.toggle("primary", state.navDirty);
  }

  async function saveNavigation() {
    if (!state.navigation || !Array.isArray(state.navigation.items)) return;
    try {
      setStatus("Saving site menu...");
      const result = await api("/api/navigation", {
        method: "POST",
        body: JSON.stringify({ items: state.navigation.items })
      });
      state.navigation = { items: result.items || [] };
      state.navDirty = false;
      renderNavigation();
      showToast(`Menu saved. Refreshed ${result.refreshed || 0} published pages.`);
      setStatus("Site menu saved.");
    } catch (error) {
      showToast(error.message);
      setStatus(error.message);
    }
  }

  async function saveDraft(options) {
    if (!state.page) return;
    if (state.saving) return;
    const quiet = Boolean(options && options.quiet);
    try {
      state.saving = true;
      if (!quiet) setStatus("Saving draft...");
      await api(`/api/pages/${state.page.slug}/save-draft`, {
        method: "POST",
        body: JSON.stringify({
          title: state.page.title,
          description: state.page.description,
          draft_json: state.data
        })
      });
      state.dirty = false;
      state.lastSavedAt = new Date().toISOString();
      updateDirtyLabel();
      await loadPages();
      if (!state.navDirty) await loadNavigation();
      if (!quiet) showToast("Draft saved.");
      setStatus(quiet ? `Draft autosaved ${formatDate(state.lastSavedAt)}.` : "Draft saved.");
    } catch (error) {
      if (!quiet) showToast(error.message);
      setStatus(error.message);
    } finally {
      state.saving = false;
    }
  }

  async function publishPage() {
    if (!state.page) return;
    try {
      setStatus("Publishing page...");
      const result = await api(`/api/pages/${state.page.slug}/publish`, {
        method: "POST",
        body: JSON.stringify({
          title: state.page.title,
          description: state.page.description,
          page_json: state.data
        })
      });
      state.dirty = false;
      state.lastSavedAt = new Date().toISOString();
      updateDirtyLabel();
      await loadPages();
      if (!state.navDirty) await loadNavigation();
      state.page.status = "published";
      state.page.published_at = result.published_at;
      els.currentStatus.textContent = pageStatusLabel(state.page);
      showToast(`Published ${result.public_url}.`);
      setStatus("Page published.");
    } catch (error) {
      showToast(error.message);
      setStatus(error.message);
    }
  }

  function previewPage() {
    if (!state.page) return;
    if (state.dirty) {
      setStatus("The opened site shows the last published version. Save or publish to include new edits.");
    }
    window.open(state.page.slug === "home" ? "/" : `/${state.page.slug}`, "_blank", "noopener");
  }

  async function logout() {
    if ((state.dirty || state.navDirty) && !window.confirm("Log out with unsaved changes?")) return;
    await fetch("/admin/logout", { method: "POST", credentials: "same-origin",headers:{"X-CSRF-Token":state.csrf} });
    window.location.href = "/admin/login";
  }

  async function addPage(templateId) {
    if (state.navDirty && !window.confirm("Create a page now? Unsaved menu changes will be reloaded.")) return;
    const template = state.pageTemplates.find((item) => item.id === templateId) || state.pageTemplates[0];
    const title = window.prompt("Page title", template && template.id !== "blank" ? template.label.replace(" Page", "") : "");
    if (!title) return;
    const suggestedSlug = slugify(title);
    const slug = window.prompt("Page slug", suggestedSlug);
    if (!slug) return;

    try {
      const result = await api("/api/pages", {
        method: "POST",
        body: JSON.stringify({ title, slug, template: templateId || "guide" })
      });
      await loadPages();
      await loadNavigation();
      await openPage(result.page.slug);
      showToast("Page created.");
    } catch (error) {
      showToast(error.message);
    }
  }

  async function deletePage(slug) {
    if (slug === "home") return;
    if (state.navDirty && !window.confirm("Delete this page now? Unsaved menu changes will be reloaded.")) return;
    if (!window.confirm(`Delete page "${slug}"?`)) return;
    try {
      await api(`/api/pages/${encodeURIComponent(slug)}`, { method: "DELETE" });
      await loadPages();
      await loadNavigation();
      const next = (state.pages.find((page) => page.slug === "home") || state.pages[0] || {}).slug;
      if (next) await openPage(next);
      showToast("Page deleted.");
    } catch (error) {
      showToast(error.message);
    }
  }

  function addBlock(type) {
    const block = createDefaultBlock(type);
    state.data.blocks.push(block);
    state.selectedBlockId = block.id;
    markDirty();
    renderPreview();
    renderSettings();
  }

  function moveBlock(index, direction) {
    const nextIndex = index + direction;
    if (nextIndex < 0 || nextIndex >= state.data.blocks.length) return;
    const [block] = state.data.blocks.splice(index, 1);
    state.data.blocks.splice(nextIndex, 0, block);
    state.selectedBlockId = block.id;
    markDirty();
    renderPreview();
    renderSettings();
  }

  function duplicateBlock(index) {
    const clone = deepClone(state.data.blocks[index]);
    clone.id = uid();
    state.data.blocks.splice(index + 1, 0, clone);
    state.selectedBlockId = clone.id;
    markDirty();
    renderPreview();
    renderSettings();
  }

  function deleteBlock(index) {
    if (!window.confirm("Delete this block?")) return;
    const [removed] = state.data.blocks.splice(index, 1);
    if (removed && removed.id === state.selectedBlockId) {
      const next = state.data.blocks[index] || state.data.blocks[index - 1];
      state.selectedBlockId = next ? next.id : null;
    }
    markDirty();
    renderPreview();
    renderSettings();
  }

  function selectBlock(id, keepFocus) {
    if (state.selectedBlockId === id && keepFocus) return;
    state.selectedBlockId = id;
    if (keepFocus) {
      updateSelectedBlockChrome();
      renderSettings();
      return;
    }
    renderPreview();
    renderSettings();
  }

  function updateSelectedBlockChrome() {
    document.querySelectorAll(".edit-block").forEach((node) => {
      node.classList.toggle("selected", node.dataset.blockId === state.selectedBlockId);
    });
  }

  function selectedBlock() {
    return state.data.blocks.find((block) => block.id === state.selectedBlockId) || null;
  }

  function createDefaultBlock(type) {
    const base = { id: uid(), type, settings: {}, style: {} };
    switch (type) {
      case "hero":
        base.settings = {
          kicker: "A practical starting point",
          headline: "New hero headline",
          body: "Click this text and edit it directly.",
          buttonText: "Start here",
          buttonUrl: "/"
        };
        break;
      case "text":
        base.settings = {
          kicker: "Helpful notes",
          heading: "New text section",
          body: "Add clear, practical copy here."
        };
        break;
      case "image_text":
        base.settings = {
          kicker: "Featured guide",
          heading: "Image and text",
          body: "Upload or select an image, then write the supporting copy.",
          imageUrl: "",
          buttonText: "Learn more",
          buttonUrl: "/"
        };
        break;
      case "three_cards":
        base.settings = {
          heading: "Three helpful resources",
          body: "Use cards for related pages, product categories, or quick paths.",
          cards: [
            { title: "First card", body: "Short detail.", buttonText: "Open", buttonUrl: "/" },
            { title: "Second card", body: "Short detail.", buttonText: "Open", buttonUrl: "/" },
            { title: "Third card", body: "Short detail.", buttonText: "Open", buttonUrl: "/" }
          ]
        };
        break;
      case "checklist":
        base.settings = {
          heading: "Checklist",
          body: "A practical list to scan quickly.",
          items: ["First item", "Second item", "Third item"]
        };
        break;
      case "faq":
        base.settings = {
          heading: "Frequently asked questions",
          faqs: [
            { question: "What should I know first?", answer: "Add a direct answer here." },
            { question: "Where can I learn more?", answer: "Point readers to the next step." }
          ]
        };
        break;
      case "affiliate_product":
        base.settings = {
          productName: "Affiliate product",
          shortDescription: "Describe why this product is useful.",
          imageUrl: "",
          buttonText: "View product",
          affiliateUrl: "https://example.com",
          disclosureText: DEFAULT_DISCLOSURE
        };
        break;
      case "cta":
        base.settings = {
          heading: "Ready for the next step?",
          body: "Guide readers to the most useful action.",
          buttonText: "Continue",
          buttonUrl: "/"
        };
        break;
      case "divider":
        base.settings = { height: 32 };
        break;
      case "contact":
        base.settings = {
          heading: "Send a message",
          body: "Messages are saved in the local inbox and sent by SMTP when configured.",
          contactEmail: "hello@example.invalid",
          subject: "Outlands Local Site Builder website message",
          buttonText: "Send message"
        };
        break;
    }
    return base;
  }

  function ensureSettings(block) {
    if (!block.settings || typeof block.settings !== "object") {
      block.settings = createDefaultBlock(block.type).settings;
    }
    return block.settings;
  }

  function ensureStyle(block) {
    if (!block.style || typeof block.style !== "object" || Array.isArray(block.style)) {
      block.style = {};
    }
    return block.style;
  }

  function ensureCards(block) {
    ensureSettings(block);
    if (!Array.isArray(block.settings.cards)) block.settings.cards = [];
    while (block.settings.cards.length < 3) {
      block.settings.cards.push({
        title: "Card title",
        body: "Card detail.",
        buttonText: "Open",
        buttonUrl: "/"
      });
    }
  }

  function ensureChecklist(block) {
    ensureSettings(block);
    if (!Array.isArray(block.settings.items)) {
      block.settings.items = ["First item", "Second item", "Third item"];
    }
  }

  function ensureFaqs(block) {
    ensureSettings(block);
    if (!Array.isArray(block.settings.faqs)) {
      block.settings.faqs = [{ question: "Question", answer: "Answer" }];
    }
  }

  function applyBlockStyleVars(node, block) {
    buildBlockStyleEntries(ensureStyle(block)).forEach(([name, value]) => {
      node.style.setProperty(name, value);
    });
  }

  function buildBlockStyleEntries(style) {
    const entries = [];
    colorStyleFields.forEach(([field, cssVar]) => {
      const color = cleanColor(style[field]);
      if (color) entries.push([cssVar, color]);
    });
    appendMappedStyles(entries, headingSizeStyles, style.headingSize);
    appendMappedStyles(entries, bodySizeStyles, style.bodySize);
    appendMappedStyles(entries, spacingStyles, style.spacing);
    appendMappedStyles(entries, paddingStyles, style.padding);
    appendMappedStyles(entries, radiusStyles, style.radius);
    appendMappedStyles(entries, itemSizeStyles, style.itemSize);
    return entries;
  }

  function appendMappedStyles(entries, styles, key) {
    const selected = styles[key];
    if (!selected) return;
    Object.entries(selected).forEach(([name, value]) => {
      entries.push([name, value]);
    });
  }

  function cleanColor(value) {
    const color = String(value || "").trim();
    return /^#[0-9a-f]{6}$/i.test(color) ? color : "";
  }

  function labelForBlock(type) {
    return (blockTypes.find((blockType) => blockType.type === type) || { label: type }).label;
  }

  function getPath(obj, path) {
    return path.split(".").reduce((current, part) => {
      if (current == null) return undefined;
      return current[part];
    }, obj);
  }

  function setPath(obj, path, value) {
    const parts = path.split(".");
    let current = obj;
    parts.forEach((part, index) => {
      if (index === parts.length - 1) {
        current[part] = value;
        return;
      }
      if (current[part] == null) {
        current[part] = /^\d+$/.test(parts[index + 1]) ? [] : {};
      }
      current = current[part];
    });
  }

  function deletePath(obj, path) {
    const parts = path.split(".");
    let current = obj;
    for (let index = 0; index < parts.length - 1; index += 1) {
      current = current && current[parts[index]];
      if (!current) return;
    }
    delete current[parts[parts.length - 1]];
  }

  function uid() {
    return `block_${Date.now().toString(36)}_${Math.random().toString(36).slice(2, 8)}`;
  }

  function deepClone(value) {
    return JSON.parse(JSON.stringify(value));
  }

  function slugify(value) {
    return String(value || "")
      .trim()
      .toLowerCase()
      .replace(/[^a-z0-9]+/g, "-")
      .replace(/^-+|-+$/g, "")
      .slice(0, 80);
  }

  function markDirty() {
    state.dirty = true;
    updateDirtyLabel();
  }

  function updateDirtyLabel() {
    if (state.dirty) {
      els.dirtyState.textContent = "Unsaved changes";
      els.dirtyState.className = "dirty";
      return;
    }
    els.dirtyState.textContent = state.lastSavedAt
      ? `Saved ${formatDate(state.lastSavedAt)}`
      : "Saved";
    els.dirtyState.className = "saved";
  }

  function setStatus(message) {
    els.statusbar.textContent = message;
  }

  function showToast(message) {
    els.toast.textContent = message;
    els.toast.hidden = false;
    window.clearTimeout(showToast.timer);
    showToast.timer = window.setTimeout(() => {
      els.toast.hidden = true;
    }, 3200);
  }
})();
