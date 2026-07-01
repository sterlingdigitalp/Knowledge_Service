const PROFILE_STORAGE_KEY = "knowledge-service:intelligence-profiles";

let state = {
  documents: [],
  document: null,
  markdown: "",
  brief: null,
  itemsById: new Map(),
};

const briefScreen = document.querySelector("#brief-screen");
const profilesScreen = document.querySelector("#profiles-screen");
const content = document.querySelector("#brief-content");
const meta = document.querySelector("#brief-meta");
const status = document.querySelector("#copy-status");
const dateSelect = document.querySelector("#brief-date");
const profilesContent = document.querySelector("#profiles-content");

const defaultProfiles = [
  {
    name: "AI",
    interests: "Inference\nCUDA\nAgents\nDatacenters",
    watchList: "Sam Altman\nKarpathy\nJensen\nDario",
    sourcePreferences: "Podcasts\nX\nCompany Blogs\nResearch Papers\nConference Talks",
  },
  {
    name: "Investing",
    interests: "Market structure\nSecondaries\nEnterprise software\nPower demand",
    watchList: "Bill Ackman\nDan Loeb\nThomas Laffont\nMarc Andreessen",
    sourcePreferences: "Podcasts\nInvestor letters\nCompany Blogs\nConference Talks",
  },
  {
    name: "Founders",
    interests: "Founder-led companies\nHiring\nDistribution\nProduct velocity",
    watchList: "Brian Chesky\nPatrick Collison\nElon Musk\nTobi Lutke",
    sourcePreferences: "Podcasts\nFounder essays\nX\nConference Talks",
  },
  {
    name: "Longevity",
    interests: "Biomarkers\nClinical trials\nDiagnostics\nProtocol design",
    watchList: "Bryan Johnson\nPeter Attia\nDavid Sinclair\nLaura Deming",
    sourcePreferences: "Research Papers\nCompany Blogs\nPodcasts\nConference Talks",
  },
];

init();

async function init() {
  try {
    const payload = loadPayload();
    state.documents = payload.documents?.length ? payload.documents : [payload];
    setDocument(state.documents[0]);
    renderDateOptions();
    renderProfiles();
    bindEvents();
  } catch (error) {
    content.innerHTML = `<p>The Morning Intelligence payload could not be loaded.</p>`;
    meta.textContent = "No brief available";
    console.error(error);
  }
}

function loadPayload() {
  const embedded = document.querySelector("#morning-intelligence-data");
  if (embedded?.textContent?.trim()) {
    return JSON.parse(embedded.textContent);
  }

  throw new Error("Morning Intelligence data was not embedded in this document.");
}

function bindEvents() {
  document.querySelector("[data-copy-brief]").addEventListener("click", () => {
    copyText(state.markdown, "Brief copied");
  });

  dateSelect.addEventListener("change", () => {
    const selected = state.documents.find((document) => document.id === dateSelect.value);
    if (selected) setDocument(selected);
  });

  document.querySelectorAll("[data-route]").forEach((link) => {
    link.addEventListener("click", () => selectRoute(link.dataset.route));
  });

  window.addEventListener("hashchange", () => selectRoute(currentRoute()));
  selectRoute(currentRoute());
}

function setDocument(document) {
  state.document = document;
  state.markdown = document.markdown || "";
  state.brief = document.brief || null;
  state.itemsById = new Map((document.items || []).map((item) => [item.item_id, item]));
  if (dateSelect.value !== document.id) dateSelect.value = document.id;
  renderMeta();
  renderBrief();
}

function renderDateOptions() {
  dateSelect.replaceChildren(
    ...state.documents.map((briefDocument) => {
      const option = window.document.createElement("option");
      option.value = briefDocument.id;
      option.textContent = briefDocument.label || briefDocument.date || "Previous date";
      return option;
    }),
  );
  if (state.document) dateSelect.value = state.document.id;
}

function currentRoute() {
  return window.location.hash.replace("#", "") === "profiles" ? "profiles" : "brief";
}

function selectRoute(route) {
  const showProfiles = route === "profiles";
  briefScreen.classList.toggle("is-active", !showProfiles);
  profilesScreen.classList.toggle("is-active", showProfiles);
}

function renderMeta() {
  const generatedAt = state.brief?.generated_at ? new Date(state.brief.generated_at) : null;
  const weekday = generatedAt ? generatedAt.toLocaleDateString(undefined, { weekday: "long" }) : "Today";
  const dateText = generatedAt
    ? generatedAt.toLocaleDateString(undefined, { month: "long", day: "numeric" })
    : "";
  const readingTime = state.brief?.reading_time_seconds
    ? `${state.brief.reading_time_seconds} seconds`
    : extractMarkdownValue("Reading time") || "60 seconds";
  meta.textContent = `${weekday}\n${dateText}\n\nReading Time\n${readingTime}`;
}

function renderBrief() {
  const sections = parseBriefMarkdown(state.markdown);
  content.replaceChildren(...sections.map(renderSection));
}

function renderSection(section) {
  const briefEntry = findBriefEntry(section.title);
  const sourceItem = briefEntry ? state.itemsById.get(briefEntry.intelligence_item_id) : null;
  const article = window.document.createElement("section");
  article.className = "brief-item";

  const stars = window.document.createElement("div");
  stars.className = "stars";
  stars.textContent = section.stars || starText(briefEntry?.star_rating);
  article.append(stars);

  const heading = window.document.createElement("h2");
  heading.textContent = section.title;
  article.append(heading);

  section.lines.forEach((line) => {
    const paragraph = markdownLineToParagraph(line);
    if (paragraph) article.append(paragraph);
  });

  const actions = window.document.createElement("div");
  actions.className = "item-actions";
  actions.append(
    copyButton("Copy Summary", () => itemSummary(section, briefEntry)),
    copyButton("Copy AI Prompt", () => aiPrompt(section, briefEntry, sourceItem)),
    copyButton("Copy Sources", () => sourcesText(sourceItem, briefEntry)),
  );
  article.append(actions);
  return article;
}

function renderProfiles() {
  const profiles = loadProfiles();
  profilesContent.replaceChildren(...profiles.map(renderProfile));
}

function renderProfile(profile, index) {
  const section = window.document.createElement("section");
  section.className = "profile";

  const heading = window.document.createElement("h3");
  heading.textContent = profile.name;
  section.append(heading);

  const fields = window.document.createElement("div");
  fields.className = "profile-fields";
  fields.append(
    profileField(index, "interests", "Interests", profile.interests),
    profileField(index, "watchList", "Watch List", profile.watchList),
    profileField(index, "sourcePreferences", "Source Preferences", profile.sourcePreferences),
  );
  section.append(fields);
  return section;
}

function profileField(index, key, label, value) {
  const wrap = window.document.createElement("div");
  wrap.className = "profile-field";
  const labelNode = window.document.createElement("label");
  const textarea = window.document.createElement("textarea");
  const id = `profile-${index}-${key}`;
  labelNode.setAttribute("for", id);
  labelNode.textContent = label;
  textarea.id = id;
  textarea.value = value;
  textarea.addEventListener("input", () => updateProfile(index, key, textarea.value));
  wrap.append(labelNode, textarea);
  return wrap;
}

function loadProfiles() {
  try {
    const saved = JSON.parse(localStorage.getItem(PROFILE_STORAGE_KEY) || "null");
    if (Array.isArray(saved) && saved.length === defaultProfiles.length) return saved;
  } catch {
    try {
      localStorage.removeItem(PROFILE_STORAGE_KEY);
    } catch {
      // Some browsers restrict localStorage for file:// pages.
    }
  }
  return JSON.parse(JSON.stringify(defaultProfiles));
}

function updateProfile(index, key, value) {
  const profiles = loadProfiles();
  profiles[index] = { ...profiles[index], [key]: value };
  try {
    localStorage.setItem(PROFILE_STORAGE_KEY, JSON.stringify(profiles));
  } catch {
    // Edits remain visible in the current document even if persistence is blocked.
  }
}

function parseBriefMarkdown(markdown) {
  const lines = markdown.split(/\r?\n/);
  const sections = [];
  let active = null;

  for (const raw of lines) {
    const line = raw.trim();
    if (line.startsWith("## ")) {
      if (active) sections.push(active);
      active = { title: line.replace(/^##\s+/, ""), stars: "", lines: [] };
      continue;
    }
    if (!active) continue;
    if (/^[★☆]{3,5}$/.test(line)) {
      active.stars = line;
      continue;
    }
    if (line) active.lines.push(line);
  }
  if (active) sections.push(active);
  return sections;
}

function markdownLineToParagraph(line) {
  const match = line.match(/^\*\*(.+?)\*\*\s*(.*)$/);
  const paragraph = window.document.createElement("p");
  if (match) {
    const label = window.document.createElement("strong");
    label.textContent = match[1];
    paragraph.append(label, window.document.createTextNode(match[2]));
  } else {
    paragraph.textContent = line.replace(/\*\*/g, "");
  }
  return paragraph;
}

function findBriefEntry(title) {
  return state.brief?.items?.find((item) => normalize(item.title) === normalize(title));
}

function copyButton(label, getText) {
  const button = window.document.createElement("button");
  button.type = "button";
  button.textContent = label;
  button.addEventListener("click", () => copyText(getText(), `${label.replace("Copy ", "")} copied`));
  return button;
}

async function copyText(text, message) {
  try {
    if (!navigator.clipboard?.writeText) throw new Error("Clipboard API unavailable");
    await navigator.clipboard.writeText(text || "");
    status.textContent = message;
  } catch {
    if (fallbackCopy(text || "")) {
      status.textContent = message;
    } else {
      status.textContent = "Copy failed";
    }
  }
  window.clearTimeout(copyText.timer);
  copyText.timer = window.setTimeout(() => (status.textContent = ""), 1800);
}

function fallbackCopy(text) {
  const field = window.document.createElement("textarea");
  field.value = text;
  field.setAttribute("readonly", "");
  field.style.position = "fixed";
  field.style.inset = "0 auto auto 0";
  field.style.opacity = "0";
  window.document.body.append(field);
  field.select();
  let copied = false;
  try {
    copied = window.document.execCommand("copy");
  } finally {
    field.remove();
  }
  return copied;
}

function itemSummary(section, entry) {
  if (!entry) return [`## ${section.title}`, section.stars, ...section.lines].join("\n\n");
  return [
    `## ${entry.title}`,
    starText(entry.star_rating),
    `Executive summary: ${entry.what_changed}`,
    `Why it matters: ${entry.why_you_care}`,
    `Evidence: ${entry.evidence_summary}`,
  ].join("\n\n");
}

function aiPrompt(section, entry, item) {
  const title = entry?.title || section.title;
  const evidence = item?.supporting_evidence || [];
  const citations = item?.timestamped_citations || [];
  return [
    `Prepare a 10-20 minute verbal analyst explanation of this intelligence item for me.`,
    "",
    `Title: ${title}`,
    `Executive summary: ${entry?.what_changed || section.lines.join(" ")}`,
    `Why it matters: ${entry?.why_you_care || "Not provided."}`,
    `Historical context: ${historicalContext(item, entry)}`,
    "Evidence:",
    evidence.length ? evidence.map(formatEvidence).join("\n") : `- ${entry?.evidence_summary || "No evidence summary provided."}`,
    "Timestamp links:",
    citations.length ? citations.map(formatCitation).join("\n") : "- No timestamped links provided.",
    "Suggested exploration questions:",
    "- What is the strongest interpretation of this signal?",
    "- What would make this signal wrong or less important?",
    "- What second-order effects should I watch over the next 30 days?",
    "- Which source would best confirm or falsify this?",
    "- What should I ask Grok, ChatGPT, or Claude next?",
  ].join("\n");
}

function sourcesText(item, entry) {
  const citations = item?.timestamped_citations || [];
  if (citations.length) return citations.map(formatCitation).join("\n");
  return entry?.evidence_summary || "No sources available.";
}

function formatEvidence(evidence) {
  const speaker = evidence.speaker && evidence.speaker !== "unknown" ? `${evidence.speaker}, ` : "";
  const time = evidence.timestamp_label ? ` @ ${evidence.timestamp_label}` : "";
  return `- ${speaker}${evidence.source || "Unknown source"}${time}: ${evidence.excerpt || ""}`;
}

function formatCitation(citation) {
  const speaker = citation.speaker && citation.speaker !== "unknown" ? `${citation.speaker}, ` : "";
  const time = citation.timestamp_label ? ` @ ${citation.timestamp_label}` : "";
  return `- ${speaker}${citation.source || "Unknown source"}${time}: ${citation.url || ""}`;
}

function historicalContext(item, entry) {
  const history = item?.historical_developments || entry?.explainability?.historical_context || [];
  return history.length ? history.map((value) => String(value)).join("; ") : "No prior development history was attached to this item.";
}

function extractMarkdownValue(label) {
  const match = state.markdown.match(new RegExp(`${label}:\\s*~?([^\\n]+)`, "i"));
  return match?.[1]?.trim();
}

function starText(count = 0) {
  return `${"★".repeat(count)}${"☆".repeat(Math.max(0, 5 - count))}`;
}

function normalize(value = "") {
  return value.toLowerCase().replace(/\s+/g, " ").trim();
}
