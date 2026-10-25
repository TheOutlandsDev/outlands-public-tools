require("dotenv").config({path:require("path").join(__dirname,".env"),quiet:true});

const path = require("path");
const fs = require("fs");
const crypto = require("crypto");
const {plainAncestors,dataRoot,lock,validatePage,imageType}=require("./lib/safety");
const express = require("express");
const session = require("express-session");
const bcrypt = require("bcryptjs");
const multer = require("multer");
const Database = require("better-sqlite3");
const nodemailer = require("nodemailer");
const { renderPageDocument, escapeHtml } = require("./views/render");
const starterContent = require("./content/starter-pages");
const brand = require("./content/brand");

const app = express();
const ENGINE_DIR = __dirname;
const ROOT_DIR = dataRoot();
const DB_DIR = path.join(ROOT_DIR, "db");
const LOG_DIR = path.join(ROOT_DIR, "logs");
const ADMIN_DIR = path.join(ENGINE_DIR, "admin");
const UPLOAD_DIR = path.join(ROOT_DIR, "uploads");
const IMAGE_DIR = path.join(UPLOAD_DIR, "images");
const SITE_DIR = path.join(ROOT_DIR, "site");
const SITE_ASSETS_DIR = path.join(SITE_DIR, "assets");
const SITE_PAGES_DIR = path.join(SITE_DIR, "pages");
const BACKUP_DIR = path.join(ROOT_DIR, "backups");

const PORT = Number(process.env.PORT || 3000);
const HOST = "127.0.0.1";
if(process.env.HOST&&process.env.HOST!==HOST)throw new Error("This editor supports loopback only.");
if(!Number.isInteger(PORT)||PORT<0||PORT>65535)throw new Error("Invalid port.");
const ADMIN_USERNAME = process.env.ADMIN_USERNAME || "admin";
const ADMIN_PASSWORD_HASH = process.env.ADMIN_PASSWORD_HASH || "";
const SESSION_SECRET = process.env.SESSION_SECRET || crypto.randomBytes(32).toString("hex");
const COMMUNITY_EMAIL = process.env.COMMUNITY_EMAIL || brand.communityEmail;
const OWNER_EMAIL = process.env.OWNER_EMAIL || brand.ownerEmail;
const CONTACT_TO_EMAIL = process.env.CONTACT_TO_EMAIL || process.env.SMTP_TO || COMMUNITY_EMAIL;
const CONTACT_CC_EMAIL = process.env.CONTACT_CC_EMAIL || OWNER_EMAIL;

const DEFAULT_PAGES = starterContent.DEFAULT_PAGES;
const PAGE_TEMPLATES = starterContent.PAGE_TEMPLATES;
const NAV_SETTING_KEY = "navigation";

if(!/^\$2[aby]\$/.test(ADMIN_PASSWORD_HASH))throw new Error("Run npm run setup before starting.");
const releaseLock=lock(ROOT_DIR);
process.once("exit",()=>{try{releaseLock();}catch{}});
[
  DB_DIR,
  LOG_DIR,
  IMAGE_DIR,
  SITE_DIR,
  SITE_ASSETS_DIR,
  SITE_PAGES_DIR,
  BACKUP_DIR
].forEach((dir) => {plainAncestors(dir);fs.mkdirSync(dir, { recursive: true });});
fs.copyFileSync(path.join(ENGINE_DIR,"assets/logo.svg"),path.join(SITE_ASSETS_DIR,"logo.svg"));

let db;

function nowIso() {
  return new Date().toISOString();
}

function getLocalUrls(port) {return [`http://127.0.0.1:${port}`];}

function appendLogFile(level, message, meta) {
  const line = `${nowIso()} [${level.toUpperCase()}] ${message}${meta ? ` ${JSON.stringify(meta)}` : ""}\n`;
  const target = level === "error" ? "error.log" : "app.log";
  fs.appendFileSync(path.join(LOG_DIR, "run.log"), line, "utf8");
  fs.appendFileSync(path.join(LOG_DIR, target), line, "utf8");
}

function appendStartupLog(message, meta) {
  const line = `${nowIso()} ${message}${meta ? ` ${JSON.stringify(meta)}` : ""}\n`;
  fs.appendFileSync(path.join(LOG_DIR, "startup.log"), line, "utf8");
}

function logEvent(level, message, meta = {}) {
  appendLogFile(level, message, meta);
  if (!db) return;
  try {
    db.prepare(
      "INSERT INTO logs (level, message, meta_json, created_at) VALUES (?, ?, ?, ?)"
    ).run(level, message, JSON.stringify(meta || {}), nowIso());
  } catch (error) {
    appendLogFile("error", "Could not write SQLite log", { error: error.message });
  }
}

function logRequest(req, res, elapsedMs) {
  const line = `${nowIso()} [REQUEST] ${req.method} ${req.originalUrl} ${res.statusCode} ${elapsedMs}ms ${req.ip || ""}\n`;
  fs.appendFileSync(path.join(LOG_DIR, "run.log"), line, "utf8");
}

function normalizeSlug(value) {
  return String(value || "")
    .trim()
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, "-")
    .replace(/^-+|-+$/g, "")
    .slice(0, 80);
}

function cleanText(value, fallback = "") {
  const text = String(value ?? "").trim();
  return text || fallback;
}

function parseJsonField(value, fallback) {
  if (!value) return fallback;
  try {
    return JSON.parse(value);
  } catch {
    return fallback;
  }
}

function pagePathForSlug(slug) {
  return slug === "home"
    ? path.join(SITE_DIR, "index.html")
    : path.join(SITE_PAGES_DIR, `${slug}.html`);
}

function writeStaticPage(slug, html) {
  const target = pagePathForSlug(slug);
  fs.mkdirSync(path.dirname(target), { recursive: true });
  fs.writeFileSync(target, html, "utf8");
}

function createBlock(type, settings) {
  return {
    id: `block_${crypto.randomBytes(6).toString("hex")}`,
    type,
    settings
  };
}

function defaultPageData(title, slug) {
  return starterContent.defaultPageData(title, slug);
}

function templatePageData(templateId, title, slug) {
  if (typeof starterContent.templatePageData === "function") {
    return starterContent.templatePageData(templateId, title, slug);
  }
  return defaultPageData(title, slug);
}

function initDatabase() {
  db = new Database(path.join(DB_DIR, "site.sqlite"));
  db.pragma("journal_mode = WAL");
  db.exec(`
    CREATE TABLE IF NOT EXISTS pages (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      slug TEXT UNIQUE NOT NULL,
      title TEXT NOT NULL,
      description TEXT DEFAULT '',
      status TEXT DEFAULT 'draft',
      draft_json TEXT DEFAULT '',
      published_json TEXT DEFAULT '',
      published_html TEXT DEFAULT '',
      published_title TEXT DEFAULT '',
      published_description TEXT DEFAULT '',
      created_at TEXT NOT NULL,
      updated_at TEXT NOT NULL,
      published_at TEXT
    );

    CREATE TABLE IF NOT EXISTS assets (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      filename TEXT NOT NULL,
      original_name TEXT NOT NULL,
      url TEXT NOT NULL,
      mime_type TEXT NOT NULL,
      size_bytes INTEGER NOT NULL,
      created_at TEXT NOT NULL
    );

    CREATE TABLE IF NOT EXISTS logs (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      level TEXT NOT NULL,
      message TEXT NOT NULL,
      meta_json TEXT DEFAULT '',
      created_at TEXT NOT NULL
    );

    CREATE TABLE IF NOT EXISTS email_messages (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      name TEXT NOT NULL,
      email TEXT NOT NULL,
      subject TEXT DEFAULT '',
      message TEXT NOT NULL,
      status TEXT DEFAULT 'new',
      meta_json TEXT DEFAULT '',
      created_at TEXT NOT NULL,
      sent_at TEXT
    );

    CREATE TABLE IF NOT EXISTS site_settings (
      key TEXT PRIMARY KEY,
      value_json TEXT NOT NULL,
      updated_at TEXT NOT NULL
    );
  `);
}

function getSetting(key, fallback) {
  const row = db.prepare("SELECT value_json FROM site_settings WHERE key = ?").get(key);
  return parseJsonField(row && row.value_json, fallback);
}

function setSetting(key, value) {
  const now = nowIso();
  db.prepare(
    `INSERT INTO site_settings (key, value_json, updated_at)
     VALUES (?, ?, ?)
     ON CONFLICT(key) DO UPDATE SET value_json = excluded.value_json, updated_at = excluded.updated_at`
  ).run(key, JSON.stringify(value), now);
}

function allPagesForNavigation(overrides = {}) {
  return db
    .prepare("SELECT id, slug, COALESCE(NULLIF(published_title,''),title) AS title, status FROM pages ORDER BY id ASC")
    .all()
    .map((page) => {
      if (overrides.slug === page.slug) {
        return {
          ...page,
          title: overrides.title || page.title,
          status: overrides.status || page.status
        };
      }
      return page;
    });
}

function defaultVisibleNavSlugs(pages) {
  const pageSlugs = new Set(pages.map((page) => page.slug));
  const configured = Array.isArray(brand.primaryNavSlugs) ? brand.primaryNavSlugs : [];
  const visible = configured.filter((slug) => pageSlugs.has(slug));
  if (visible.length) return visible;
  return pages.slice(0, 7).map((page) => page.slug);
}

function getNavigationState(overrides = {}) {
  const pages = allPagesForNavigation(overrides);
  const pagesBySlug = new Map(pages.map((page) => [page.slug, page]));
  const saved = getSetting(NAV_SETTING_KEY, null);
  const savedItems = saved && Array.isArray(saved.items) ? saved.items : null;
  const defaultVisible = new Set(defaultVisibleNavSlugs(pages));
  const ordered = [];
  const seen = new Set();

  if (savedItems) {
    savedItems.forEach((item) => {
      const slug = normalizeSlug(item && item.slug);
      if (!slug || seen.has(slug) || !pagesBySlug.has(slug)) return;
      const page = pagesBySlug.get(slug);
      const label = cleanText(item.label, page.title).slice(0, 80);
      ordered.push({
        slug,
        title: page.title,
        status: page.status,
        label,
        visible: item.visible !== false
      });
      seen.add(slug);
    });
  }

  pages.forEach((page) => {
    if (seen.has(page.slug)) return;
    ordered.push({
      slug: page.slug,
      title: page.title,
      status: page.status,
      label: page.title,
      visible: savedItems ? false : defaultVisible.has(page.slug)
    });
  });

  return { items: ordered };
}

function getNavPages(overrides = {}) {
  return getNavigationState(overrides).items
    .filter((item) => item.visible && item.status === "published")
    .map((item) => ({
      slug: item.slug,
      title: item.title,
      label: item.label || item.title
    }));
}

function refreshPublishedPages() {
  const pages = db.prepare("SELECT * FROM pages ORDER BY id ASC").all();
  const navPages = getNavPages();
  const update = db.prepare("UPDATE pages SET published_html = ? WHERE slug = ?");
  let refreshed = 0;

  for (const page of pages) {
    const data = parseJsonField(page.published_json, null);
    if (!data) continue;
    const html = renderPageDocument({...page,title:page.published_title||page.title,description:page.published_description}, data, navPages);
    update.run(html, page.slug);
    writeStaticPage(page.slug, html);
    refreshed += 1;
  }

  return refreshed;
}

function seedPagesIfEmpty() {
  const count = db.prepare("SELECT COUNT(*) AS count FROM pages").get().count;
  if (count > 0) return;

  const insert = db.prepare(`
    INSERT INTO pages
      (slug, title, description, status, draft_json, published_json, published_html, published_title, published_description, created_at, updated_at, published_at)
    VALUES
      (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
  `);
  const navPages = DEFAULT_PAGES.map(([title, slug]) => ({ title, slug }));
  const now = nowIso();

  const seed = db.transaction(() => {
    for (const [title, slug] of DEFAULT_PAGES) {
      const data = defaultPageData(title, slug);
      const json = JSON.stringify(data);
      const description = `${title} resources from Outlands Local Site Builder.`;
      const html = renderPageDocument({ title, slug, description }, data, navPages);
      insert.run(slug, title, description, "published", json, json, html, title, description, now, now, now);
      writeStaticPage(slug, html);
    }
  });

  seed();
  logEvent("info", "Default pages seeded", { count: DEFAULT_PAGES.length });
}

function isAuthed(req) {
  return Boolean(req.session && req.session.user);
}

function requireAuth(req, res, next) {
  if (isAuthed(req)) return next();
  if (req.path.startsWith("/api/")) {
    return res.status(401).json({ error: "Login required." });
  }
  return res.redirect("/admin/login");
}

function renderLogin(errorMessage = "") {
  return `<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Admin Login | Outlands Local Site Builder</title>
  <link rel="stylesheet" href="/admin-assets/admin.css">
</head>
<body class="login-page">
  <main class="login-panel">
    <p class="eyebrow">Outlands Local Site Builder</p>
    <h1>Admin Login</h1>
    ${errorMessage ? `<p class="alert">${escapeHtml(errorMessage)}</p>` : ""}
    <form method="post" action="/admin/login" class="login-form">
      <label>Username <input name="username" autocomplete="username" required></label>
      <label>Password <input name="password" type="password" autocomplete="current-password" required></label>
      <button type="submit">Login</button>
    </form>
    <p class="muted">The password hash lives in your .env file.</p>
  </main>
</body>
</html>`;
}

function renderAdminTablePage(title, bodyHtml) {
  return `<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>${escapeHtml(title)} | Outlands Local Site Builder Admin</title>
  <link rel="stylesheet" href="/admin-assets/admin.css">
</head>
<body class="admin-table-page">
  <header class="table-topbar">
    <a href="/admin">Builder</a>
    <a href="/admin/launch">Launch</a>
    <a href="/admin/email">Email</a>
    <a href="/admin/logs">Logs</a>
    <a href="/admin/inbox">Inbox</a>
    <form method="post" action="/admin/logout"><button type="submit">Logout</button></form>
  </header>
  <main class="table-wrap">
    <h1>${escapeHtml(title)}</h1>
    ${bodyHtml}
  </main>
</body>
</html>`;
}

function asyncHandler(fn) {
  return (req, res, next) => Promise.resolve(fn(req, res, next)).catch(next);
}

function parseBoolean(value) {
  return String(value || "").toLowerCase() === "true";
}

function emailEnabled() {
  return String(process.env.EMAIL_SERVICE_ENABLED || "false").toLowerCase() === "true";
}

function smtpConfigured() {
  return emailEnabled() && Boolean(process.env.SMTP_HOST && CONTACT_TO_EMAIL && getSmtpFrom());
}

function getSmtpFrom() {
  return process.env.SMTP_FROM || `Outlands Local Site Builder <${COMMUNITY_EMAIL}>`;
}

function createTransporter() {
  if (!emailEnabled() || !smtpConfigured()) return null;
  const auth =
    process.env.SMTP_USER && process.env.SMTP_PASS
      ? { user: process.env.SMTP_USER, pass: process.env.SMTP_PASS }
      : undefined;
  return nodemailer.createTransport({
    host: process.env.SMTP_HOST,
    port: Number(process.env.SMTP_PORT || 587),
    secure: parseBoolean(process.env.SMTP_SECURE),
    auth, connectionTimeout:5000, greetingTimeout:5000, socketTimeout:10000
  });
}

async function deliverContactEmail(messageRow) {
  const transporter = createTransporter();
  if (!transporter) return false;

  await transporter.sendMail({
    from: getSmtpFrom(),
    to: CONTACT_TO_EMAIL,
    cc: CONTACT_CC_EMAIL || undefined,
    replyTo: messageRow.email,
    subject: messageRow.subject || "Outlands Local Site Builder website message",
    text: [
      `Name: ${messageRow.name}`,
      `Email: ${messageRow.email}`,
      "",
      messageRow.message
    ].join("\n")
  });

  return true;
}

initDatabase();
seedPagesIfEmpty();

if (!process.env.SESSION_SECRET) {
  logEvent("info", "SESSION_SECRET not set; using a temporary in-memory secret for this run");
}

app.disable("x-powered-by");
app.use((req,res,next)=>{
  const port=server.address()?.port;
  const allowed=[`127.0.0.1:${port}`,`localhost:${port}`];
  if(!allowed.includes(req.headers.host))return res.status(403).json({error:"Unrecognized local host."});
  res.set({"X-Content-Type-Options":"nosniff","X-Frame-Options":"DENY","Referrer-Policy":"no-referrer","Content-Security-Policy":"default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline'; img-src 'self' https: http:; connect-src 'self'; object-src 'none'; base-uri 'none'; frame-ancestors 'none'; form-action 'self'"});
  if(req.path.startsWith('/api/')||req.path.startsWith('/admin'))res.set('Cache-Control','no-store');
  // Opaque-origin local webviews may send "null". They still must supply the
  // session-bound CSRF token below; a foreign non-opaque origin is rejected.
  if(!['GET','HEAD','OPTIONS'].includes(req.method)&&req.get('origin')&&req.get('origin')!=='null'&&req.get('origin')!==`http://${req.headers.host}`)return res.status(403).json({error:"A matching Origin is required for changes."});
  next();
});
app.use(express.urlencoded({ extended: false, limit:"256kb",parameterLimit:30 }));
app.use(express.json({ limit: "2mb" }));
app.use(
  session({
    name: "outlands.sid",
    secret: SESSION_SECRET,
    resave: false,
    saveUninitialized: false,
    cookie: {
      httpOnly: true,
      sameSite: "strict",
      secure: false,
      maxAge: 1000 * 60 * 60 * 12
    }
  })
);

app.use((req,res,next)=>{
  if(!req.session.csrf)req.session.csrf=crypto.randomBytes(32).toString('hex');
  const token=req.get('x-csrf-token')||req.body?._csrf;
  if(!['GET','HEAD','OPTIONS'].includes(req.method)&&token!==req.session.csrf)return res.status(403).json({error:'A valid CSRF token is required.'});
  const originalSend=res.send;
  res.send=function(body){
    if(typeof body==='string'&&body.includes('<form'))body=body.replace(/(<form[^>]*>)/g,`$1<input type="hidden" name="_csrf" value="${req.session.csrf}">`);
    return originalSend.call(this,body);
  };
  next();
});
app.get('/api/csrf',(req,res)=>res.json({csrf:req.session.csrf}));
app.use("/admin-assets", express.static(ADMIN_DIR));
app.use("/uploads/images", express.static(IMAGE_DIR));
app.use("/assets", express.static(SITE_ASSETS_DIR));

app.use((req, res, next) => {
  const started = Date.now();
  res.on("finish", () => {
    logRequest(req, res, Date.now() - started);
  });
  next();
});

const upload=multer({storage:multer.memoryStorage(),limits:{fileSize:5*1024*1024,files:1,fields:0,parts:1}});
let loginWindow=0,loginAttempts=0;
app.use('/admin/login',(req,res,next)=>{
  if(req.method!=='POST')return next();
  if(Date.now()-loginWindow>15*60*1000){loginWindow=Date.now();loginAttempts=0;}
  if(++loginAttempts>10)return res.status(429).send(renderLogin('Too many attempts. Try again in 15 minutes.'));
  next();
});
let contactWindow=0,contactAttempts=0;
app.use('/api/contact',(req,res,next)=>{
  if(Date.now()-contactWindow>60000){contactWindow=Date.now();contactAttempts=0;}
  if(++contactAttempts>10)return res.status(429).json({error:'Too many messages. Try again in a minute.'});
  next();
});

app.get("/admin/login", (req, res) => {
  if (isAuthed(req)) return res.redirect("/admin");
  return res.send(renderLogin());
});

app.post(
  "/admin/login",
  asyncHandler(async (req, res) => {
    const username = cleanText(req.body.username);
    const password = String(req.body.password || "");

    if (!ADMIN_PASSWORD_HASH) {
      logEvent("error", "Login attempted before ADMIN_PASSWORD_HASH was configured", { username });
      return res.status(500).send(renderLogin("Admin password hash is not configured yet."));
    }

    const usernameMatches = username === ADMIN_USERNAME;
    const passwordMatches = usernameMatches
      ? await bcrypt.compare(password, ADMIN_PASSWORD_HASH)
      : false;

    if (!usernameMatches || !passwordMatches) {
      logEvent("warn", "Login failure", { username });
      return res.status(401).send(renderLogin("Username or password is incorrect."));
    }

    req.session.regenerate((error) => {
      if (error) {
        logEvent("error", "Could not create admin session", { username, error: error.message });
        return res.status(500).send(renderLogin("Could not start an admin session."));
      }
      loginAttempts=0;
      req.session.csrf=crypto.randomBytes(32).toString("hex");
      req.session.user = { username };
      logEvent("info", "Login success", { username });
      res.redirect("/admin");
    });
  })
);

app.post("/admin/logout", requireAuth, (req, res) => {
  req.session.destroy(() => {
    res.redirect("/admin/login");
  });
});

app.get("/admin/logs", requireAuth, (req, res) => {
  const logs = db
    .prepare("SELECT level, message, meta_json, created_at FROM logs ORDER BY id DESC LIMIT 200")
    .all();
  const rows = logs
    .map(
      (log) => `<tr>
        <td>${escapeHtml(log.created_at)}</td>
        <td>${escapeHtml(log.level)}</td>
        <td>${escapeHtml(log.message)}</td>
        <td><code>${escapeHtml(log.meta_json || "")}</code></td>
      </tr>`
    )
    .join("");
  res.send(
    renderAdminTablePage(
      "Admin Logs",
      `<table class="data-table"><thead><tr><th>Time</th><th>Level</th><th>Message</th><th>Meta</th></tr></thead><tbody>${rows}</tbody></table>`
    )
  );
});

app.get("/admin/email", requireAuth, (req, res) => {
  const rows = [
    ["Community / public contact", COMMUNITY_EMAIL],
    ["Owner / business account", OWNER_EMAIL],
    ["Contact form sends to", CONTACT_TO_EMAIL],
    ["Contact form CC", CONTACT_CC_EMAIL || "None"],
    ["SMTP from address", getSmtpFrom()],
    ["SMTP host", process.env.SMTP_HOST || "Not configured"],
    ["SMTP delivery", smtpConfigured() ? "Ready" : "Not configured. Messages are saved locally in the admin inbox."]
  ]
    .map(
      ([label, value]) => `<tr>
        <th>${escapeHtml(label)}</th>
        <td>${escapeHtml(value)}</td>
      </tr>`
    )
    .join("");

  res.send(
    renderAdminTablePage(
      "Company Email",
      `<p class="muted">These are the email identities wired into the site. The public contact shown on the website is <strong>${escapeHtml(COMMUNITY_EMAIL)}</strong>. The owner/business account is <strong>${escapeHtml(OWNER_EMAIL)}</strong>.</p>
       <table class="data-table settings-table"><tbody>${rows}</tbody></table>
       <p class="muted">To send form messages as real email, add SMTP credentials to <code>.env</code>. Until then, messages still save in <a href="/admin/inbox">the admin inbox</a>.</p>`
    )
  );
});

app.get("/admin/launch", requireAuth, (req, res) => {
  const nav = getNavigationState().items;
  const pageCounts = db
    .prepare("SELECT status, COUNT(*) AS count FROM pages GROUP BY status")
    .all()
    .reduce((acc, row) => {
      acc[row.status] = row.count;
      return acc;
    }, {});
  const visibleNavCount = nav.filter((item) => item.visible).length;
  const checks = [
    ["Local website engine", "Ready", `Running on port ${PORT}.`],
    ["Admin account", ADMIN_PASSWORD_HASH ? "Ready" : "Needs setup", ADMIN_PASSWORD_HASH ? `Username is ${ADMIN_USERNAME}.` : "ADMIN_PASSWORD_HASH is missing in .env."],
    ["Published pages", pageCounts.published ? "Ready" : "Needs content", `${pageCounts.published || 0} published, ${pageCounts.draft || 0} draft.`],
    ["Top menu", visibleNavCount ? "Ready" : "Needs setup", `${visibleNavCount} pages visible in the menu.`],
    ["Contact inbox", "Ready", "Contact form messages save locally in admin inbox."],
    ["SMTP email sending", smtpConfigured() ? "Ready" : "Later", smtpConfigured() ? "SMTP is configured." : "Messages save locally until SMTP is configured."],
    ["Domain", "Later", "example.invalid is registered, but DNS is not pointed at this local server yet."],
    ["Public internet hosting", "Later", "No port forwarding, HTTPS, or public DNS is configured in this local build."]
  ];
  const rows = checks
    .map(
      ([item, status, note]) => `<tr>
        <td>${escapeHtml(item)}</td>
        <td><span class="status-pill">${escapeHtml(status)}</span></td>
        <td>${escapeHtml(note)}</td>
      </tr>`
    )
    .join("");

  res.send(
    renderAdminTablePage(
      "Launch Checklist",
      `<p class="muted">This is the quick readiness view for Outlands Local Site Builder. It is local/admin-only.</p>
       <table class="data-table"><thead><tr><th>Area</th><th>Status</th><th>Note</th></tr></thead><tbody>${rows}</tbody></table>`
    )
  );
});

app.get("/admin/inbox", requireAuth, (req, res) => {
  const messages = db
    .prepare(
      "SELECT id, name, email, subject, message, status, created_at, sent_at FROM email_messages ORDER BY id DESC LIMIT 200"
    )
    .all();
  const rows = messages
    .map(
      (message) => `<tr>
        <td>${escapeHtml(message.created_at)}</td>
        <td>${escapeHtml(message.status)}</td>
        <td>${escapeHtml(message.name)}<br><a href="mailto:${escapeHtml(message.email)}">${escapeHtml(message.email)}</a></td>
        <td>${escapeHtml(message.subject || "")}</td>
        <td>${escapeHtml(message.message)}</td>
        <td>${escapeHtml(message.sent_at || "Saved locally")}</td>
      </tr>`
    )
    .join("");
  res.send(
    renderAdminTablePage(
      "Email Inbox",
      `<p class="muted">Contact forms are always saved here. Public/community messages are for <strong>${escapeHtml(COMMUNITY_EMAIL)}</strong>. SMTP delivery is ${smtpConfigured() ? "configured" : "not configured"}.</p>
       <table class="data-table"><thead><tr><th>Time</th><th>Status</th><th>Sender</th><th>Subject</th><th>Message</th><th>Email delivery</th></tr></thead><tbody>${rows}</tbody></table>`
    )
  );
});

app.get(["/admin", "/admin/builder/:slug"], requireAuth, (_req, res) => {
  res.sendFile(path.join(ADMIN_DIR, "admin.html"));
});

app.get("/api/session", requireAuth, (req, res) => {
  res.json({
    user: req.session.user,
    emailConfigured: smtpConfigured(),
    communityEmail: COMMUNITY_EMAIL,
    ownerEmail: OWNER_EMAIL
  });
});

app.get("/api/page-templates", requireAuth, (_req, res) => {
  res.json({ templates: PAGE_TEMPLATES || [] });
});

app.get("/api/navigation", requireAuth, (_req, res) => {
  res.json(getNavigationState());
});

app.post("/api/navigation", requireAuth, (req, res) => {
  const submitted = Array.isArray(req.body.items) ? req.body.items : [];
  const pages = allPagesForNavigation();
  const pageSlugs = new Set(pages.map((page) => page.slug));
  const seen = new Set();
  const items = [];

  submitted.forEach((item) => {
    const slug = normalizeSlug(item && item.slug);
    if (!slug || seen.has(slug) || !pageSlugs.has(slug)) return;
    const page = pages.find((candidate) => candidate.slug === slug);
    items.push({
      slug,
      label: cleanText(item.label, page ? page.title : slug).slice(0, 80),
      visible: item.visible !== false
    });
    seen.add(slug);
  });

  pages.forEach((page) => {
    if (seen.has(page.slug)) return;
    items.push({ slug: page.slug, label: page.title, visible: false });
  });

  setSetting(NAV_SETTING_KEY, { items });
  const refreshed = refreshPublishedPages();
  logEvent("info", "Navigation saved", { visible: items.filter((item) => item.visible).length, refreshed });
  res.json({ ok: true, refreshed, ...getNavigationState() });
});

app.get("/api/pages", requireAuth, (_req, res) => {
  const pages = db
    .prepare("SELECT id, slug, title, description, status, updated_at, published_at FROM pages ORDER BY id ASC")
    .all();
  res.json({ pages });
});

app.post("/api/pages", requireAuth, (req, res) => {
  const title = cleanText(req.body.title, "Untitled Page").slice(0,200);
  if(db.prepare("SELECT COUNT(*) AS n FROM pages").get().n>=200)return res.status(400).json({error:"The 200-page limit was reached."});
  const slug = normalizeSlug(req.body.slug || title);
  if (!slug||["admin","api","assets","uploads","admin-assets","pages"].includes(slug)) return res.status(400).json({ error: "Choose a non-reserved page slug." });

  const existing = db.prepare("SELECT id FROM pages WHERE slug = ?").get(slug);
  if (existing) return res.status(409).json({ error: "That slug already exists." });

  const template = cleanText(req.body.template, "guide");
  const data = templatePageData(template, title, slug);
  const now = nowIso();
  db.prepare(
    "INSERT INTO pages (slug, title, description, status, draft_json, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?)"
  ).run(slug, title, `${title} resources from Outlands Local Site Builder.`, "draft", JSON.stringify(data), now, now);

  logEvent("info", "Page created", { slug, title, template });
  res.status(201).json({ page: { slug, title } });
});

app.get("/api/pages/:slug", requireAuth, (req, res) => {
  const slug = normalizeSlug(req.params.slug);
  const page = db.prepare("SELECT * FROM pages WHERE slug = ?").get(slug);
  if (!page) return res.status(404).json({ error: "Page not found." });
  res.json({
    page: {
      id: page.id,
      slug: page.slug,
      title: page.title,
      description: page.description,
      status: page.status,
      draft_json: parseJsonField(page.draft_json, { version: 1, theme: "natural", blocks: [] }),
      published_json: parseJsonField(page.published_json, null),
      updated_at: page.updated_at,
      published_at: page.published_at
    }
  });
});

app.post("/api/pages/:slug/save-draft", requireAuth, (req, res) => {
  const slug = normalizeSlug(req.params.slug);
  const page = db.prepare("SELECT * FROM pages WHERE slug = ?").get(slug);
  if (!page) return res.status(404).json({ error: "Page not found." });

  let draft;try{draft=validatePage(req.body.draft_json);}catch{return res.status(400).json({error:"Invalid or oversized page blocks."});}
  if (!draft || typeof draft !== "object" || !Array.isArray(draft.blocks)) {
    return res.status(400).json({ error: "Draft JSON must include a blocks array." });
  }

  const title = cleanText(req.body.title, page.title).slice(0,200);
  const description = cleanText(req.body.description, page.description).slice(0,1000);
  const now = nowIso();
  db.prepare(
    "UPDATE pages SET title = ?, description = ?, draft_json = ?, updated_at = ? WHERE slug = ?"
  ).run(title, description, JSON.stringify(draft), now, slug);

  logEvent("info", "Draft saved", { slug });
  res.json({ ok: true, updated_at: now });
});

app.post("/api/pages/:slug/publish", requireAuth, (req, res) => {
  const slug = normalizeSlug(req.params.slug);
  const page = db.prepare("SELECT * FROM pages WHERE slug = ?").get(slug);
  if (!page) return res.status(404).json({ error: "Page not found." });

  const publishData =
    req.body.page_json && typeof req.body.page_json === "object"
      ? req.body.page_json
      : parseJsonField(page.draft_json, { version: 1, theme: "natural", blocks: [] });

  try{validatePage(publishData);}catch{return res.status(400).json({error:"Invalid or oversized page blocks."});}
  if (!Array.isArray(publishData.blocks)) {
    return res.status(400).json({ error: "Page JSON must include a blocks array." });
  }

  const title = cleanText(req.body.title, page.title).slice(0,200);
  const description = cleanText(req.body.description, page.description).slice(0,1000);
  const navPages = getNavPages({ slug, title, status: "published" });
  const html = renderPageDocument({ title, slug, description }, publishData, navPages);
  const json = JSON.stringify(publishData);
  const now = nowIso();

  db.prepare(
    `UPDATE pages
     SET title = ?, description = ?, status = 'published', draft_json = ?, published_json = ?,
         published_html = ?, published_title = ?, published_description = ?, updated_at = ?, published_at = ?
     WHERE slug = ?`
  ).run(title, description, json, json, html, title, description, now, now, slug);

  writeStaticPage(slug, html);
  const refreshed = refreshPublishedPages();
  logEvent("info", "Page published", { slug, file: pagePathForSlug(slug), refreshed });
  res.json({ ok: true, published_at: now, public_url: slug === "home" ? "/" : `/${slug}` });
});

app.delete("/api/pages/:slug", requireAuth, (req, res) => {
  const slug = normalizeSlug(req.params.slug);
  if (slug === "home") return res.status(400).json({ error: "The home page cannot be deleted." });

  const page = db.prepare("SELECT id FROM pages WHERE slug = ?").get(slug);
  if (!page) return res.status(404).json({ error: "Page not found." });

  db.prepare("DELETE FROM pages WHERE slug = ?").run(slug);
  const staticPath = pagePathForSlug(slug);
  if (fs.existsSync(staticPath)) fs.unlinkSync(staticPath);
  const refreshed = refreshPublishedPages();
  logEvent("info", "Page deleted", { slug, refreshed });
  res.json({ ok: true });
});

app.get("/api/assets", requireAuth, (_req, res) => {
  const assets = db.prepare("SELECT * FROM assets ORDER BY id DESC").all();
  res.json({ assets });
});

app.post("/api/assets/upload", requireAuth, (req, res) => {
  upload.single("image")(req, res, (error) => {
    if (error) {
      logEvent("warn", "Asset upload rejected", { error: error.message });
      return res.status(400).json({ error: error.message });
    }
    if (!req.file) return res.status(400).json({ error: "No image file was uploaded." });

    const detected=imageType(req.file.buffer);
    if(!detected||detected[0]!==req.file.mimetype)return res.status(400).json({error:"Use a matching PNG, JPEG, GIF or WebP raster image."});
    if(db.prepare("SELECT COUNT(*) AS n FROM assets").get().n>=1000)return res.status(400).json({error:"The 1000-image limit was reached."});
    req.file.filename=crypto.randomBytes(16).toString('hex')+detected[1];
    plainAncestors(IMAGE_DIR);
    fs.writeFileSync(path.join(IMAGE_DIR,req.file.filename),req.file.buffer,{flag:'wx'});
    const url = `/uploads/images/${req.file.filename}`;
    const now = nowIso();
    const result = db
      .prepare(
        "INSERT INTO assets (filename, original_name, url, mime_type, size_bytes, created_at) VALUES (?, ?, ?, ?, ?, ?)"
      )
      .run(req.file.filename, req.file.originalname, url, req.file.mimetype, req.file.size, now);
    const asset = db.prepare("SELECT * FROM assets WHERE id = ?").get(result.lastInsertRowid);
    logEvent("info", "Asset uploaded", { id: asset.id, filename: asset.filename });
    res.status(201).json({ asset });
  });
});

app.delete("/api/assets/:id", requireAuth, (req, res) => {
  const id = Number(req.params.id);
  const asset = db.prepare("SELECT * FROM assets WHERE id = ?").get(id);
  if (!asset) return res.status(404).json({ error: "Asset not found." });

  const resolved = path.resolve(IMAGE_DIR, asset.filename);
  if (path.dirname(resolved)===path.resolve(IMAGE_DIR) && fs.existsSync(resolved)) {
    fs.unlinkSync(resolved);
  }
  db.prepare("DELETE FROM assets WHERE id = ?").run(id);
  logEvent("info", "Asset deleted", { id, filename: asset.filename });
  res.json({ ok: true });
});

app.get("/api/logs", requireAuth, (_req, res) => {
  const logs = db
    .prepare("SELECT id, level, message, meta_json, created_at FROM logs ORDER BY id DESC LIMIT 200")
    .all();
  res.json({ logs });
});

app.get("/api/messages", requireAuth, (_req, res) => {
  const messages = db
    .prepare("SELECT * FROM email_messages ORDER BY id DESC LIMIT 200")
    .all();
  res.json({ messages, emailConfigured: smtpConfigured(), communityEmail: COMMUNITY_EMAIL, ownerEmail: OWNER_EMAIL });
});

app.patch("/api/messages/:id/read", requireAuth, (req, res) => {
  const id = Number(req.params.id);
  const status = req.body.status === "new" ? "new" : "read";
  const result = db.prepare("UPDATE email_messages SET status = ? WHERE id = ?").run(status, id);
  if (!result.changes) return res.status(404).json({ error: "Message not found." });
  res.json({ ok: true, status });
});

app.delete("/api/messages/:id", requireAuth, (req, res) => {
  const id = Number(req.params.id);
  const result = db.prepare("DELETE FROM email_messages WHERE id = ?").run(id);
  if (!result.changes) return res.status(404).json({ error: "Message not found." });
  res.json({ ok: true });
});

app.post(
  "/api/email/test",
  requireAuth,
  asyncHandler(async (req, res) => {
    const testRow = {
      name: "Outlands Local Site Builder Admin",
      email: CONTACT_TO_EMAIL || "admin@localhost",
      subject: "Outlands Local Site Builder test email",
      message: "This is a test email from your local Outlands Local Site Builder website engine."
    };
    const delivered = await deliverContactEmail(testRow);
    if (!delivered) {
      return res.status(400).json({ error: "SMTP is not configured. The local inbox still works." });
    }
    logEvent("info", "Test email sent");
    res.json({ ok: true });
  })
);

app.post(
  "/api/contact",
  asyncHandler(async (req, res) => {
    const name = cleanText(req.body.name).slice(0, 120);
    const email = cleanText(req.body.email).slice(0, 180);
    const subject = cleanText(req.body.subject, "Outlands Local Site Builder website message").slice(0, 180);
    const message = cleanText(req.body.message).slice(0, 5000);

    if (!name || !email || !message) {
      return res.status(400).json({ error: "Name, email, and message are required." });
    }
    if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email)) {
      return res.status(400).json({ error: "Please enter a valid email address." });
    }

    const now = nowIso();
    const result = db
      .prepare(
        `INSERT INTO email_messages
          (name, email, subject, message, status, meta_json, created_at)
         VALUES (?, ?, ?, ?, ?, ?, ?)`
      )
      .run(
        name,
        email,
        subject,
        message,
        "new",
        JSON.stringify({ ip: req.ip, userAgent: req.get("user-agent") || "" }),
        now
      );

    const row = db.prepare("SELECT * FROM email_messages WHERE id = ?").get(result.lastInsertRowid);
    let delivered = false;
    try {
      delivered = await deliverContactEmail(row);
      if (delivered) {
        const sentAt = nowIso();
        db.prepare("UPDATE email_messages SET status = ?, sent_at = ? WHERE id = ?").run(
          "sent",
          sentAt,
          row.id
        );
      }
    } catch (error) {
      logEvent("error", "Contact email delivery failed", { id: row.id, error: error.message });
    }

    logEvent("info", "Contact message received", { id: row.id, delivered });
    res.status(201).json({ ok: true, delivered });
  })
);

function renderPublicSlug(slug, res, next) {
  const page = db.prepare("SELECT * FROM pages WHERE slug = ?").get(slug);
  if (page && page.published_html) {
    return res.send(page.published_html);
  }

  const staticPath = pagePathForSlug(slug);
  if (fs.existsSync(staticPath)) {
    return res.sendFile(staticPath);
  }

  return next();
}

app.get("/", (req, res, next) => renderPublicSlug("home", res, next));

app.get("/:slug", (req, res, next) => {
  const slug = normalizeSlug(req.params.slug);
  if (!slug) return next();
  return renderPublicSlug(slug, res, next);
});

app.use((req, res) => {
  if (req.path.startsWith("/api/")) {
    return res.status(404).json({ error: "Not found." });
  }
  res.status(404).send(
    renderPageDocument(
      { title: "Page not found", slug: "not-found", description: "This page was not found." },
      {
        version: 1,
        theme: "natural",
        blocks: [
          {
            id: "not_found",
            type: "text",
            settings: {
              kicker: "404",
              heading: "Page not found",
              body: "The page you requested could not be found."
            }
          }
        ]
      },
      getNavPages()
    )
  );
});

app.use((error, req, res, _next) => {
  logEvent("error", "Unhandled server error", {
    message: error.message,
    path: req.path
  });
  if (req.path.startsWith("/api/")) {
    return res.status(error.status===413?413:500).json({ error: error.status===413?"Request too large.":"Server error." });
  }
  return res.status(500).send(renderLogin("A server error occurred. Check /admin/logs after logging in."));
});

const server = app.listen(PORT, HOST, () => {
  const siteUrls = getLocalUrls(server.address().port);
  const adminUrls = siteUrls.map((url) => `${url}/admin`);
  appendStartupLog("Server started", { host: HOST, port: PORT, siteUrls, adminUrls });
  logEvent("info", "Server start", {
    host: HOST,
    port: PORT,
    siteUrls,
    adminUrls
  });
  console.log("");
  console.log("Outlands Local Site Builder is running.");
  console.log("Site URLs:");
  siteUrls.forEach((url) => console.log(`  ${url}`));
  console.log("Admin URLs:");
  adminUrls.forEach((url) => console.log(`  ${url}`));
  console.log("");
  console.log(`Logs: ${LOG_DIR}`);
});

server.on("error", (error) => {
  appendStartupLog("Server failed to start", {
    host: HOST,
    port: PORT,
    code: error.code,
    message: error.message
  });
  logEvent("error", "Server listen failed", {
    host: HOST,
    port: PORT,
    code: error.code,
    message: error.message
  });
  console.error(`Outlands Local Site Builder could not start on ${HOST}:${PORT}.`);
  console.error(error.message);
  process.exit(1);
});

function shutdown(){server.close(()=>{db.close();releaseLock();process.exit(0);});server.closeIdleConnections();setTimeout(()=>process.exit(1),5000).unref();}
process.once('SIGTERM',shutdown);process.once('SIGINT',shutdown);
// Private parent-process channel for controlled integration fixtures; no HTTP stop endpoint.
if(process.send)process.on('message',message=>{if(message==='shutdown')shutdown();});
