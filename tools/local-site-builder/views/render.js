const DEFAULT_DISCLOSURE =
  "This page may contain affiliate links. Review and replace this disclosure for your own links.";
const BRAND = require("../content/brand");

function escapeHtml(value) {
  return String(value ?? "")
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#039;");
}

function escapeAttr(value) {
  return escapeHtml(value).replace(/`/g, "&#096;");
}

function safeUrl(value,fallback='#'){
  const url=String(value??'').trim();
  if(/[\\\x00-\x20\x7f]/.test(url))return fallback;
  if(url.startsWith('/')&&!url.startsWith('//'))return url;
  if(url.startsWith('#'))return url;
  try{const parsed=new URL(url);if(['https:','http:','mailto:'].includes(parsed.protocol))return url;}catch{}
  return fallback;
}

const COLOR_STYLE_FIELDS = [
  ["backgroundColor", "--block-bg"],
  ["textColor", "--block-text"],
  ["headingColor", "--block-heading"],
  ["accentColor", "--block-accent"],
  ["buttonTextColor", "--block-button-text"],
  ["itemBackgroundColor", "--block-item-bg"],
  ["itemTextColor", "--block-item-text"]
];

const HEADING_SIZE_STYLES = {
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

const BODY_SIZE_STYLES = {
  small: { "--block-body-size": "0.95rem" },
  large: { "--block-body-size": "1.15rem" },
  xlarge: { "--block-body-size": "1.28rem" }
};

const SPACING_STYLES = {
  tight: { "--block-space": "14px" },
  roomy: { "--block-space": "36px" },
  wide: { "--block-space": "52px" }
};

const PADDING_STYLES = {
  compact: { "--block-padding": "clamp(18px, 2.5vw, 30px)" },
  roomy: { "--block-padding": "clamp(34px, 5vw, 70px)" },
  huge: { "--block-padding": "clamp(44px, 7vw, 96px)" }
};

const RADIUS_STYLES = {
  square: { "--block-radius": "8px" },
  soft: { "--block-radius": "18px" },
  round: { "--block-radius": "30px" }
};

const ITEM_SIZE_STYLES = {
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

function cleanColor(value) {
  const color = String(value || "").trim();
  return /^#[0-9a-f]{6}$/i.test(color) ? color : "";
}

function appendMappedStyles(entries, styles, key) {
  const selected = styles[key];
  if (!selected) return;
  Object.entries(selected).forEach(([name, value]) => {
    entries.push([name, value]);
  });
}

function blockStyleDeclarations(block) {
  const style = block && block.style && typeof block.style === "object" ? block.style : {};
  const entries = [];
  COLOR_STYLE_FIELDS.forEach(([field, cssVar]) => {
    const color = cleanColor(style[field]);
    if (color) entries.push([cssVar, color]);
  });
  appendMappedStyles(entries, HEADING_SIZE_STYLES, style.headingSize);
  appendMappedStyles(entries, BODY_SIZE_STYLES, style.bodySize);
  appendMappedStyles(entries, SPACING_STYLES, style.spacing);
  appendMappedStyles(entries, PADDING_STYLES, style.padding);
  appendMappedStyles(entries, RADIUS_STYLES, style.radius);
  appendMappedStyles(entries, ITEM_SIZE_STYLES, style.itemSize);
  return entries;
}

function blockStyleAttribute(block) {
  const style = blockStyleDeclarations(block)
    .map(([name, value]) => `${name}:${value}`)
    .join(";");
  return style ? ` style="${escapeAttr(style)}"` : "";
}

function paragraphs(value) {
  return escapeHtml(value)
    .split(/\n{2,}/)
    .map((part) => `<p>${part.replace(/\n/g, "<br>")}</p>`)
    .join("");
}

function normalizePageData(data) {
  if (!data || typeof data !== "object") {
    return { version: 1, theme: "natural", blocks: [] };
  }
  return {
    version: data.version || 1,
    theme: data.theme || "natural",
    blocks: Array.isArray(data.blocks) ? data.blocks : []
  };
}

function renderButton(text, url) {
  if (!text) return "";
  return `<a class="pm-button" href="${escapeAttr(safeUrl(url))}">${escapeHtml(text)}</a>`;
}

function renderImage(url, alt, className = "") {
  const src = safeUrl(url, "");
  if (!src) {
    return `<div class="pm-image-placeholder ${className}">Image</div>`;
  }
  return `<img class="${className}" src="${escapeAttr(src)}" alt="${escapeAttr(alt || "Outlands Local Site Builder image")}" loading="lazy">`;
}

function renderHero(settings, block) {
  return `
    <section class="pm-section pm-hero"${blockStyleAttribute(block)}>
      <div>
        ${settings.kicker ? `<p class="pm-kicker">${escapeHtml(settings.kicker)}</p>` : ""}
        <h1>${escapeHtml(settings.headline || "Outlands Local Site Builder")}</h1>
        <div class="pm-copy">${paragraphs(settings.body || "")}</div>
        ${renderButton(settings.buttonText, settings.buttonUrl)}
      </div>
    </section>`;
}

function renderText(settings, block) {
  return `
    <section class="pm-section pm-text"${blockStyleAttribute(block)}>
      ${settings.kicker ? `<p class="pm-kicker">${escapeHtml(settings.kicker)}</p>` : ""}
      <h2>${escapeHtml(settings.heading || "Helpful guidance")}</h2>
      <div class="pm-copy">${paragraphs(settings.body || "")}</div>
    </section>`;
}

function renderImageText(settings, block) {
  return `
    <section class="pm-section pm-image-text"${blockStyleAttribute(block)}>
      <div class="pm-media">
        ${renderImage(settings.imageUrl, settings.heading, "pm-feature-image")}
      </div>
      <div>
        ${settings.kicker ? `<p class="pm-kicker">${escapeHtml(settings.kicker)}</p>` : ""}
        <h2>${escapeHtml(settings.heading || "Support for this season")}</h2>
        <div class="pm-copy">${paragraphs(settings.body || "")}</div>
        ${renderButton(settings.buttonText, settings.buttonUrl)}
      </div>
    </section>`;
}

function renderCards(settings, block) {
  const cards = Array.isArray(settings.cards) ? settings.cards : [];
  return `
    <section class="pm-section"${blockStyleAttribute(block)}>
      ${settings.heading ? `<h2>${escapeHtml(settings.heading)}</h2>` : ""}
      ${settings.body ? `<div class="pm-copy">${paragraphs(settings.body)}</div>` : ""}
      <div class="pm-card-grid">
        ${cards
          .slice(0, 3)
          .map(
            (card) => `
              <article class="pm-card">
                <h3>${escapeHtml(card.title || "Resource")}</h3>
                <p>${escapeHtml(card.body || "")}</p>
                ${card.buttonText ? `<a href="${escapeAttr(safeUrl(card.buttonUrl))}">${escapeHtml(card.buttonText)}</a>` : ""}
              </article>`
          )
          .join("")}
      </div>
    </section>`;
}

function renderChecklist(settings, block) {
  const items = Array.isArray(settings.items) ? settings.items : [];
  return `
    <section class="pm-section pm-checklist"${blockStyleAttribute(block)}>
      <h2>${escapeHtml(settings.heading || "Checklist")}</h2>
      ${settings.body ? `<div class="pm-copy">${paragraphs(settings.body)}</div>` : ""}
      <ul>
        ${items.map((item) => `<li><span>${escapeHtml(item)}</span></li>`).join("")}
      </ul>
    </section>`;
}

function renderFaq(settings, block) {
  const faqs = Array.isArray(settings.faqs) ? settings.faqs : [];
  return `
    <section class="pm-section pm-faq"${blockStyleAttribute(block)}>
      <h2>${escapeHtml(settings.heading || "Questions")}</h2>
      ${faqs
        .map(
          (faq) => `
            <details>
              <summary>${escapeHtml(faq.question || "Question")}</summary>
              <div class="pm-copy">${paragraphs(faq.answer || "")}</div>
            </details>`
        )
        .join("")}
    </section>`;
}

function renderAffiliate(settings, block) {
  return `
    <section class="pm-section pm-affiliate"${blockStyleAttribute(block)}>
      <div class="pm-media">
        ${renderImage(settings.imageUrl, settings.productName, "pm-product-image")}
      </div>
      <div>
        <p class="pm-kicker">Recommended resource</p>
        <h2>${escapeHtml(settings.productName || "Affiliate product")}</h2>
        <div class="pm-copy">${paragraphs(settings.shortDescription || "")}</div>
        ${renderButton(settings.buttonText || "View product", settings.affiliateUrl)}
        <p class="pm-disclosure">${escapeHtml(settings.disclosureText || DEFAULT_DISCLOSURE)}</p>
      </div>
    </section>`;
}

function renderCta(settings, block) {
  return `
    <section class="pm-section pm-cta"${blockStyleAttribute(block)}>
      <h2>${escapeHtml(settings.heading || "Take the next step")}</h2>
      <div class="pm-copy">${paragraphs(settings.body || "")}</div>
      ${renderButton(settings.buttonText || "Start here", settings.buttonUrl)}
    </section>`;
}

function renderDivider(settings) {
  const height = Math.max(12, Math.min(Number(settings.height || 32), 120));
  return `<div class="pm-spacer" style="height:${height}px"></div>`;
}

function renderContact(settings, block) {
  const contactEmail = settings.contactEmail || BRAND.communityEmail;
  return `
    <section class="pm-section pm-contact" id="contact"${blockStyleAttribute(block)}>
      <div>
        <p class="pm-kicker">Email ${escapeHtml(BRAND.siteName)}</p>
        <h2>${escapeHtml(settings.heading || "Send a message")}</h2>
        <div class="pm-copy">${paragraphs(settings.body || "Questions, ideas, and collaboration notes can be sent here.")}</div>
        <p class="pm-contact-email"><a href="mailto:${escapeAttr(contactEmail)}">${escapeHtml(contactEmail)}</a></p>
      </div>
      <form class="pm-contact-form" data-contact-form>
        <label>
          Name
          <input name="name" autocomplete="name" required>
        </label>
        <label>
          Email
          <input name="email" type="email" autocomplete="email" required>
        </label>
        <label>
          Subject
          <input name="subject" value="${escapeAttr(settings.subject || "Website message")}">
        </label>
        <label>
          Message
          <textarea name="message" rows="5" required></textarea>
        </label>
        <button class="pm-button" type="submit">${escapeHtml(settings.buttonText || "Send message")}</button>
        <p class="pm-form-status" aria-live="polite"></p>
      </form>
    </section>`;
}

function renderBlock(block) {
  if(!block||typeof block!=="object")return "";
  const settings = block.settings && typeof block.settings === "object" ? block.settings : {};
  switch (block.type) {
    case "hero":
      return renderHero(settings, block);
    case "text":
      return renderText(settings, block);
    case "image_text":
      return renderImageText(settings, block);
    case "three_cards":
      return renderCards(settings, block);
    case "checklist":
      return renderChecklist(settings, block);
    case "faq":
      return renderFaq(settings, block);
    case "affiliate_product":
      return renderAffiliate(settings, block);
    case "cta":
      return renderCta(settings, block);
    case "divider":
      return renderDivider(settings);
    case "contact":
      return renderContact(settings, block);
    default:
      return "";
  }
}

function navHref(slug) {
  return slug === "home" ? "/" : `/${encodeURIComponent(slug)}`;
}

function renderSiteHeader(navPages) {
  const links = (navPages || [])
    .filter((page) => page && page.slug && page.title)
    .map((page) => `<a href="${navHref(page.slug)}">${escapeHtml(page.label || page.title)}</a>`)
    .join("");

  return `
    <header class="pm-site-header">
      <div class="pm-page pm-nav">
        <a class="pm-brand" href="/">
          <img src="${escapeAttr(BRAND.logoUrl)}" alt="" aria-hidden="true">
          <span>
            <strong>${escapeHtml(BRAND.siteName)}</strong>
            <small>${escapeHtml(BRAND.shortTagline)}</small>
          </span>
        </a>
        <nav>${links}</nav>
      </div>
    </header>`;
}

function renderSiteFooter() {
  const links = (BRAND.footerLinks || [])
    .map((link) => `<a href="${escapeAttr(safeUrl(link.url))}">${escapeHtml(link.label)}</a>`)
    .join("");

  return `
    <footer class="pm-site-footer">
      <div class="pm-page pm-footer-grid">
        <div>
          <a class="pm-footer-brand" href="/">
            <img src="${escapeAttr(BRAND.logoUrl)}" alt="" aria-hidden="true">
            <span>${escapeHtml(BRAND.siteName)}</span>
          </a>
          <p>${escapeHtml(BRAND.footerText)}</p>
        </div>
        <nav>${links}</nav>
      </div>
      <p class="pm-copyright">&copy; ${new Date().getFullYear()} ${escapeHtml(BRAND.siteName)}.</p>
    </footer>`;
}

function siteStyles() {
  return `
    :root {
      --pm-ink: #26342d;
      --pm-muted: #66766a;
      --pm-bg: #f8f6ef;
      --pm-panel: #fffdf7;
      --pm-sage: #dfeade;
      --pm-sage-strong: #5f8a6b;
      --pm-moss: #315b41;
      --pm-tan: #d8b98f;
      --pm-border: #ded8c8;
      --pm-shadow: 0 18px 48px rgba(48, 69, 54, 0.11);
    }

    * { box-sizing: border-box; }

    body {
      margin: 0;
      background: var(--pm-bg);
      color: var(--pm-ink);
      font-family: Georgia, "Times New Roman", serif;
      line-height: 1.6;
    }

    a { color: var(--pm-moss); }

    img { max-width: 100%; display: block; }

    .pm-page {
      width: min(1180px, calc(100% - 48px));
      margin: 0 auto;
    }

    .pm-site-header {
      padding: 12px 0;
      background: rgba(248, 246, 239, 0.92);
      position: sticky;
      top: 0;
      z-index: 5;
      backdrop-filter: blur(12px);
      border-bottom: 1px solid rgba(222, 216, 200, 0.75);
    }

    .pm-nav {
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 24px;
    }

    .pm-brand {
      display: inline-flex;
      align-items: center;
      gap: 10px;
      color: var(--pm-moss);
      text-decoration: none;
      min-width: 230px;
    }

    .pm-brand img,
    .pm-footer-brand img {
      width: 44px;
      height: 44px;
      flex: 0 0 auto;
    }

    .pm-brand strong,
    .pm-footer-brand span {
      display: block;
      font-family: Georgia, "Times New Roman", serif;
      font-size: 1.22rem;
      line-height: 1.05;
      color: var(--pm-moss);
      white-space: nowrap;
    }

    .pm-brand small {
      display: block;
      margin-top: 2px;
      color: var(--pm-muted);
      font-family: Arial, Helvetica, sans-serif;
      font-size: 0.75rem;
      line-height: 1.2;
    }

    .pm-nav nav {
      display: flex;
      gap: 14px;
      flex-wrap: wrap;
      justify-content: flex-end;
      font-family: Arial, Helvetica, sans-serif;
      font-size: 0.92rem;
    }

    .pm-nav nav a {
      text-decoration: none;
      color: var(--pm-muted);
      border-bottom: 2px solid transparent;
      padding: 4px 0;
    }

    .pm-nav nav a:hover {
      color: var(--pm-moss);
      border-color: var(--pm-tan);
    }

    main.pm-page {
      padding: 34px 0 56px;
    }

    .pm-section {
      background: var(--block-bg, var(--pm-panel));
      border: 1px solid var(--pm-border);
      border-radius: var(--block-radius, 22px);
      box-shadow: var(--pm-shadow);
      margin: 0 0 var(--block-space, 24px);
      padding: var(--block-padding, clamp(24px, 3.6vw, 48px));
      overflow: hidden;
      color: var(--block-text, var(--pm-ink));
    }

    .pm-hero {
      min-height: 420px;
      display: grid;
      align-items: center;
      background: var(--block-bg,
        linear-gradient(135deg, rgba(223, 234, 222, 0.96), rgba(255, 253, 247, 0.95)),
        radial-gradient(circle at 90% 12%, rgba(216, 185, 143, 0.34), transparent 32%));
    }

    .pm-kicker {
      margin: 0 0 10px;
      color: var(--block-accent, var(--pm-sage-strong));
      font-family: Arial, Helvetica, sans-serif;
      font-size: 0.78rem;
      font-weight: 700;
      letter-spacing: 0;
      text-transform: uppercase;
    }

    h1, h2, h3 {
      margin: 0;
      line-height: 1.08;
      color: var(--block-heading, var(--pm-ink));
    }

    h1 {
      max-width: 780px;
      font-size: var(--block-h1-size, clamp(2.6rem, 7vw, 5.8rem));
    }

    h2 {
      font-size: var(--block-h2-size, clamp(1.7rem, 3.2vw, 2.65rem));
    }

    h3 { font-size: var(--block-h3-size, 1.25rem); }

    .pm-copy {
      max-width: 760px;
      color: var(--block-text, var(--pm-muted));
      font-family: Arial, Helvetica, sans-serif;
      font-size: var(--block-body-size, 1.03rem);
    }

    .pm-copy p:first-child { margin-top: 14px; }
    .pm-copy p:last-child { margin-bottom: 0; }

    .pm-button {
      display: inline-flex;
      align-items: center;
      justify-content: center;
      min-height: 44px;
      margin-top: 22px;
      padding: 12px 18px;
      border-radius: 999px;
      background: var(--block-accent, var(--pm-moss));
      color: var(--block-button-text, #fff);
      border: 1px solid var(--block-accent, var(--pm-moss));
      text-decoration: none;
      font-family: Arial, Helvetica, sans-serif;
      font-weight: 700;
    }

    .pm-image-text,
    .pm-affiliate,
    .pm-contact {
      display: grid;
      grid-template-columns: minmax(0, 0.9fr) minmax(0, 1.1fr);
      gap: clamp(22px, 4vw, 46px);
      align-items: center;
    }

    .pm-feature-image,
    .pm-product-image,
    .pm-image-placeholder {
      width: 100%;
      aspect-ratio: 4 / 3;
      border-radius: 18px;
      object-fit: cover;
      border: 1px solid var(--pm-border);
      background: linear-gradient(135deg, var(--pm-sage), #fff7e8);
      box-shadow: 0 16px 36px rgba(48, 69, 54, 0.12);
    }

    .pm-image-placeholder {
      display: grid;
      place-items: center;
      color: var(--pm-muted);
      font-family: Arial, Helvetica, sans-serif;
      min-height: 220px;
    }

    .pm-card-grid {
      display: grid;
      grid-template-columns: repeat(3, minmax(0, 1fr));
      gap: 18px;
      margin-top: 24px;
    }

    .pm-card {
      border: 1px solid var(--pm-border);
      border-radius: 18px;
      padding: var(--block-item-padding, 22px);
      background: var(--block-item-bg, #fbfaf4);
      color: var(--block-item-text, var(--pm-ink));
      font-family: Arial, Helvetica, sans-serif;
      font-size: var(--block-item-font-size, 1rem);
    }

    .pm-card p { color: var(--block-item-text, var(--pm-muted)); }

    .pm-checklist ul {
      display: grid;
      gap: 10px;
      margin: 22px 0 0;
      padding: 0;
      list-style: none;
      font-family: Arial, Helvetica, sans-serif;
    }

    .pm-checklist li {
      display: grid;
      grid-template-columns: 28px minmax(0, 1fr);
      gap: 12px;
      align-items: start;
      min-height: var(--block-item-min-height, 48px);
      padding: var(--block-item-padding, 12px 15px);
      border-radius: 14px;
      background: var(--block-item-bg, #edf4ea);
      border: 1px solid rgba(95, 138, 107, 0.2);
      color: var(--block-item-text, #26342d);
      font-size: var(--block-item-font-size, 1rem);
      box-shadow: 0 8px 18px rgba(48, 69, 54, 0.06);
    }

    .pm-checklist li::before {
      content: "";
      width: 22px;
      height: 22px;
      margin-top: 1px;
      border-radius: 999px;
      background:
        linear-gradient(135deg, rgba(255,255,255,0.5), transparent),
        var(--block-accent, var(--pm-sage-strong));
      box-shadow: inset 0 0 0 1px rgba(49, 91, 65, 0.18);
    }

    .pm-checklist li span {
      padding-top: 1px;
    }

    .pm-faq details {
      border-bottom: 1px solid var(--pm-border);
      padding: 16px 0;
      font-family: Arial, Helvetica, sans-serif;
    }

    .pm-faq summary {
      cursor: pointer;
      font-weight: 700;
    }

    .pm-disclosure,
    .pm-contact-email,
    .pm-form-status {
      color: var(--pm-muted);
      font-family: Arial, Helvetica, sans-serif;
      font-size: 0.88rem;
    }

    .pm-contact-email {
      margin-top: 18px;
      font-weight: 700;
    }

    .pm-cta {
      text-align: center;
      background: var(--block-bg, linear-gradient(135deg, #fffdf7, var(--pm-sage)));
    }

    .pm-cta .pm-copy { margin: 0 auto; }

    .pm-contact-form {
      display: grid;
      gap: 12px;
      font-family: Arial, Helvetica, sans-serif;
    }

    .pm-contact-form label {
      display: grid;
      gap: 6px;
      color: var(--pm-muted);
      font-size: 0.92rem;
      font-weight: 700;
    }

    .pm-contact-form input,
    .pm-contact-form textarea {
      width: 100%;
      border: 1px solid var(--pm-border);
      border-radius: 12px;
      padding: 12px 13px;
      color: var(--pm-ink);
      background: #fff;
      font: inherit;
    }

    .pm-site-footer {
      padding: 34px 0 44px;
      background: #eeeadf;
      border-top: 1px solid var(--pm-border);
      color: var(--pm-muted);
      font-family: Arial, Helvetica, sans-serif;
      font-size: 0.9rem;
    }

    .pm-footer-grid {
      display: grid;
      grid-template-columns: minmax(0, 1fr) auto;
      gap: 28px;
      align-items: start;
    }

    .pm-footer-brand {
      display: inline-flex;
      align-items: center;
      gap: 10px;
      text-decoration: none;
    }

    .pm-footer-grid p {
      max-width: 620px;
      margin: 12px 0 0;
    }

    .pm-site-footer nav {
      display: flex;
      gap: 14px;
      flex-wrap: wrap;
      justify-content: flex-end;
    }

    .pm-site-footer nav a {
      color: var(--pm-moss);
      text-decoration: none;
      font-weight: 700;
    }

    .pm-copyright {
      width: min(1180px, calc(100% - 48px));
      margin: 18px auto 0;
      color: var(--pm-muted);
      text-align: left;
    }

    @media (max-width: 820px) {
      .pm-page { width: min(100% - 28px, 1180px); }
      .pm-nav { align-items: flex-start; flex-direction: column; }
      .pm-nav nav { justify-content: flex-start; }
      .pm-brand { min-width: 0; }
      .pm-brand small { display: none; }
      .pm-section { border-radius: 18px; }
      .pm-image-text,
      .pm-affiliate,
      .pm-contact,
      .pm-card-grid {
        grid-template-columns: 1fr;
      }
      .pm-footer-grid { grid-template-columns: 1fr; }
      .pm-site-footer nav { justify-content: flex-start; }
      .pm-copyright { width: min(100% - 28px, 1180px); }
      h1 { font-size: clamp(2.25rem, 13vw, 4rem); }
    }
  `;
}

function publicScript() {
  return `
    <script>
      document.addEventListener("submit", async function (event) {
        var form = event.target.closest("[data-contact-form]");
        if (!form) return;
        event.preventDefault();
        var status = form.querySelector(".pm-form-status");
        var button = form.querySelector("button[type='submit']");
        var data = Object.fromEntries(new FormData(form).entries());
        if (status) status.textContent = "Sending...";
        if (button) button.disabled = true;
        try {
          var csrfResponse=await fetch("/api/csrf");
          var csrfData=await csrfResponse.json();
          var response = await fetch("/api/contact", {
            method: "POST",
            headers: { "Content-Type": "application/json", "X-CSRF-Token": csrfData.csrf },
            body: JSON.stringify(data)
          });
          var result = await response.json();
          if (!response.ok) throw new Error(result.error || "Message could not be sent.");
          form.reset();
          if (status) status.textContent = result.delivered ? "Message sent." : "Message saved. Email delivery is not configured yet.";
        } catch (error) {
          if (status) status.textContent = error.message || "Message could not be sent.";
        } finally {
          if (button) button.disabled = false;
        }
      });
    </script>`;
}

function renderPageDocument(page, rawData, navPages) {
  const data = normalizePageData(rawData);
  const title = page && page.title ? page.title : BRAND.siteName;
  const description = page && page.description ? page.description : "A fictional community workshop website.";
  const blocks = data.blocks.map(renderBlock).join("\n");

  return `<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>${escapeHtml(title)} | ${escapeHtml(BRAND.siteName)}</title>
  <meta name="description" content="${escapeAttr(description)}">
  <link rel="icon" href="${escapeAttr(BRAND.logoUrl)}" type="image/svg+xml">
  <style>${siteStyles()}</style>
</head>
<body>
  ${renderSiteHeader(navPages)}
  <main class="pm-page">
    ${blocks || renderText({ heading: title, body: "This page is ready for your content." })}
  </main>
  ${renderSiteFooter()}
  ${publicScript()}
</body>
</html>`;
}

module.exports = {
  DEFAULT_DISCLOSURE,
  escapeHtml,
  renderBlock,
  renderPageDocument,
  safeUrl
};
