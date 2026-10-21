/**
 * DENTAL COST PAGE GENERATOR  (for dentalpriceguide.com)
 * -------------------------------------------------------------
 * Reads dental-input-launch.json / dental-input-rest.json — one brief per page,
 * with LOCKED, SOURCED price facts (Delta Dental claims data, CareCredit/Synchrony
 * 2023–24 cost study, GoodRx, Healthline, Pearl/ADA fee survey) and the only URLs
 * the model may cite. The model writes ONLY the prose spec as JSON; the site's
 * build.py renders it. Rules adapted from the SM7 "LLM-Optimized Mega Prompt":
 * answer-first, query-style headings, self-contained chunks, no invented data.
 *
 * Output: output-dental/<slug>.json
 * RUN:
 *   node generate-dental.js dental-input-launch.json 2   (test: first 2)
 *   node generate-dental.js dental-input-launch.json     (46 launch pages)
 *   node generate-dental.js dental-input-rest.json       (78 remaining pages)
 * ENV: DENTAL_MODEL (default claude-sonnet-5-5), DENTAL_SKIP_EXISTING=1, DENTAL_DELAY_MS
 * -------------------------------------------------------------
 */
const fs = require("fs");
const path = require("path");
const ROOT = __dirname;
const OUT = path.join(ROOT, "output-dental");

let cfg;
try { cfg = JSON.parse(fs.readFileSync(path.join(ROOT, "config.json"), "utf8")); }
catch (e) { console.error("\n config.json not found.\n"); process.exit(1); }
const API_KEY = (cfg.apiKey || "").trim();
const MODEL = ((process.env.DENTAL_MODEL || "claude-sonnet-5-5") + "").trim();
if (!API_KEY || API_KEY.startsWith("PASTE_")) { console.error("\n Set your API key in config.json\n"); process.exit(1); }

const INPUT = process.argv[2] && process.argv[2].endsWith(".json") ? process.argv[2] : "dental-input-launch.json";
let items;
try { items = JSON.parse(fs.readFileSync(path.join(ROOT, INPUT), "utf8")); }
catch (e) { console.error(`\n ${INPUT} not found or invalid.\n`); process.exit(1); }
const capArg = process.argv[2] && !process.argv[2].endsWith(".json") ? process.argv[2] : process.argv[3];
const argLimit = parseInt(capArg, 10);
if (!isNaN(argLimit)) items = items.slice(0, argLimit);
if (!fs.existsSync(OUT)) fs.mkdirSync(OUT, { recursive: true });
if (process.env.DENTAL_SKIP_EXISTING === "1") {
  const before = items.length;
  items = items.filter((t) => !fs.existsSync(path.join(OUT, t.slug + ".json")));
  if (before - items.length) console.log("  resume: skipping " + (before - items.length) + " already-generated page(s)");
}

const BANNED = ["genuinely", "honestly", "straightforward", "delve", "navigate", "landscape", "in today's", "game-changer", "unlock", "embark"];

function kindRules(t) {
  switch (t.kind) {
    case "pillar":
      return `This is a PILLAR page: the main cost hub for ${t.pillar}. Cover total cost, what changes the price, cost by type/option, with vs without insurance, how to pay less (insurance, in-network dentists, dental schools, payment plans, HSA/FSA), and what the procedure involves. Link to EVERY internal page in the INTERNAL LINKS list at least once, in context.`;
    case "cost":
      return `This is a COST page. Lead with the price range from the locked facts, then explain what drives the price, insurance vs self-pay, and how to lower it. Include a cost_table.`;
    case "comparison":
      return `This is a COMPARISON page. Lead with a one-sentence verdict on who each option suits. Include a comparison table (cost_table) comparing the options on cost (locked figures only), lifespan/durability, procedure, and best-for. Do not invent numbers: where no locked figure exists, use words ("usually longer", "varies").`;
    case "bestof":
      return `This is a buyer-guidance page. Do NOT rank or name specific commercial brands/products and do NOT claim any product is the best. Instead explain the types of at-home options (strips, trays, pens, LED kits, toothpastes), active ingredients (hydrogen peroxide, carbamide peroxide), what to look for (ADA Seal of Acceptance, sensitivity formulas), safety, and when professional whitening is the better value (use the locked in-office price). cost_table may compare option TYPES with words, plus the locked professional prices.`;
    default:
      return `This is an INFORMATIONAL page answering "${t.primary}". Answer the question directly first. Use widely accepted clinical guidance (ADA, AAOMS, AAE, AAO, Cleveland Clinic level) stated as typical ranges, and always tell the reader their own dentist's or surgeon's instructions take priority. Add one short section that connects the topic to cost using the locked figures (e.g. "What does it cost if ...?"). cost_table only if a table genuinely helps (e.g. a day-by-day timeline or comparison); otherwise set it to null.`;
  }
}

function buildPrompt(t) {
  const factList = t.facts.map((f) => `  - ${f.label}: ${f.value}  [source: ${f.source} | ${f.url}]`).join("\n");
  const srcList = t.sources.map((s, i) => `  [${i + 1}] ${s.url}  — ${s.name}`).join("\n");
  const linkList = t.related.map((r) => `  - ${r.url}  (anchor idea: "${r.anchor}")`).join("\n");
  return `You are the editor of Dental Price Guide (dentalpriceguide.com), an independent US guide to what dental procedures cost and what to expect. Pages are medically reviewed by Dr. Faisal Irshad, MBBS (a physician, not a dentist). Write ONE page as a single JSON object.

AUDIENCE: US adults deciding on dental treatment and how to pay for it. Plain English, short paragraphs (2–4 sentences), warm but factual, no hype, no sales tone. Never use these words: ${BANNED.join(", ")}. Write in a practitioner's voice with practical, specific detail; vary sentence length; no filler, no conclusion section.

PAGE TOPIC: ${t.topic}
PRIMARY KEYWORD (front-load it in title, h1, description, quick answer): "${t.primary}"
CLOSE VARIANTS PEOPLE ALSO SEARCH (cover their intent naturally, do not stuff): ${t.variations.slice(0, 30).join("; ") || "none"}
REAL QUESTIONS PEOPLE ASK (use the best ones as H2s or FAQs): ${t.question_variations.join("; ") || "none"}
CATEGORY: ${t.category} | PILLAR GROUP: ${t.pillar} | PAGE TYPE: ${t.kind}

${kindRules(t)}

LOCKED PRICE FACTS — the ONLY dollar figures, percentages and price ranges you may state. Use them verbatim. Attribute each figure to its publisher when you use it, and say these are national averages and local prices vary:
${factList}

CRITICAL RULES:
1. No dollar figure, percentage or statistic that is not in the LOCKED facts. If you need a number you don't have, describe it in words instead ("usually more", "varies by region").
2. When two locked sources give different numbers, show both and explain they measure different things (out-of-network claims vs a cost survey).
3. External links: you may link ONLY to these URLs, exactly as written, as <a href="URL" rel="noopener">Publisher name</a>:
${srcList}
4. Internal links: include 3–6 contextual internal links (pillar pages: link every page below) using ONLY these paths, as <a href="/path/">descriptive anchor</a>:
${linkList}
5. Answer first: the first sentence under every H2 directly answers that heading and makes sense if quoted alone (name the subject, no "this/it" openers).
6. Every paragraph must make sense on its own (repeat the procedure name instead of "it" at paragraph starts).
7. Medical safety: give general information only; include when to see a dentist urgently where relevant (swelling, fever, uncontrolled bleeding, severe pain). Never diagnose.

Return these JSON fields:
- title: <= 60 characters, primary keyword first, may end with "(2026)".
- h1: natural, fuller version of the title.
- description: 140–155 characters, includes the primary keyword and (if a cost page) the lead price range.
- quick_answer: HTML <p>…</p>, 40–60 words, directly answers "${t.primary}", the key figure in <strong>, one source link.
- key_takeaways: array of 3–5 short plain-text bullets (no HTML).
- cost_table: {caption, headers:[..], rows:[[..],..]} built ONLY from locked facts (include a "Source" column naming the publisher), or null if not useful.
- sections: array of ${t.kind === "pillar" ? "8–10" : "5–7"} objects {id, h2, html}. id = short kebab-case. h2 = a question or phrase a real person searches (query-style, one intent each). html = <p>, <ul>, <ol>, <div class="callout"><p>…</p></div> only (no h1/h2/h3/table/img). Total body ${t.word_target} words.
- faq: array of 5–7 {q, a}; q = real search questions; a = 40–70 words plain text (no HTML), answer-first.
- meta_keywords: comma-separated primary + close variants.

Return ONLY the JSON object. No markdown fences, no commentary.`;
}

function assemble(t, o) {
  return {
    slug: t.slug, path: t.path, primary: t.primary, topic: t.topic, pillar: t.pillar, level: t.level,
    kind: t.kind, category: t.category, category_slug: t.category_slug, launch: t.launch,
    title: o.title, h1: o.h1, description: o.description, meta_keywords: o.meta_keywords,
    quick_answer: o.quick_answer, key_takeaways: o.key_takeaways, cost_table: o.cost_table,
    sections: o.sections, faq: o.faq, facts: t.facts, sources: t.sources, related: t.related,
    variations: t.variations, generated: new Date().toISOString().slice(0, 10), model: MODEL,
  };
}

async function sleep(ms) { return new Promise((r) => setTimeout(r, ms)); }

async function generateOne(t, attempt) {
  attempt = attempt || 1;
  try { return await generateOnce(t); }
  catch (e) {
    const msg = String((e && e.message) || e);
    const retryable = /fetch failed|ECONNRESET|ETIMEDOUT|socket hang up|API 429|API 5\d\d|overloaded|No valid JSON|non-locked|banned word/i.test(msg);
    if (retryable && attempt < 4) {
      const wait = 5000 * Math.pow(2, attempt - 1);
      process.stdout.write("retry" + attempt + "(" + msg.slice(0, 40) + ") ");
      await sleep(wait);
      return generateOne(t, attempt + 1);
    }
    throw e;
  }
}

async function generateOnce(t) {
  const res = await fetch("https://api.anthropic.com/v1/messages", {
    method: "POST",
    headers: { "x-api-key": API_KEY, "anthropic-version": "2023-06-01", "content-type": "application/json" },
    body: JSON.stringify({ model: MODEL, max_tokens: 16000, messages: [{ role: "user", content: buildPrompt(t) }] }),
  });
  if (!res.ok) throw new Error(`API ${res.status}: ${(await res.text()).slice(0, 300)}`);
  const data = await res.json();
  const usage = data.usage || {};
  const raw = (data.content || []).filter((x) => x && x.type === "text").map((x) => x.text).join("\n").trim();
  let cleaned = raw.replace(/```(json)?/gi, "").trim();
  const f = cleaned.indexOf("{"), l = cleaned.lastIndexOf("}");
  if (f !== -1 && l > f) cleaned = cleaned.slice(f, l + 1);
  let obj;
  try { obj = JSON.parse(cleaned); }
  catch (e) { throw new Error("No valid JSON (stop=" + data.stop_reason + ")"); }
  for (const k of ["title", "h1", "description", "quick_answer", "sections", "faq"]) if (!obj[k]) throw new Error("No valid JSON: missing " + k);
  // Guard 1: only locked external URLs and known internal paths
  const allowed = new Set(t.sources.map((s) => s.url).concat(t.related.map((r) => r.url)));
  const hrefs = [...JSON.stringify(obj).matchAll(/href=\\?"([^"\\]+)/g)].map((m) => m[1]);
  for (const h of hrefs) if (!allowed.has(h)) throw new Error("Model cited a non-locked URL: " + h);
  // Guard 2: banned words
  const txt = JSON.stringify(obj).toLowerCase();
  for (const w of BANNED) if (txt.includes(w)) throw new Error("banned word: " + w);
  // Guard 3: every $ figure must appear in the locked facts
  const lockedTxt = t.facts.map((x) => x.value + " " + x.label).join(" ");
  const nums = [...JSON.stringify(obj).matchAll(/\$\s?([\d,]+)/g)].map((m) => m[1].replace(/,$/, ""));
  for (const n of nums) if (!lockedTxt.includes("$" + n)) throw new Error("non-locked dollar figure: $" + n);
  return { obj, usage };
}

(async () => {
  console.log(`\n Dental page generator  |  model ${MODEL}  |  input ${INPUT}  |  ${items.length} pages\n`);
  let inTok = 0, outTok = 0, ok = 0, fail = 0; const failed = [];
  for (let i = 0; i < items.length; i++) {
    const t = items[i];
    process.stdout.write(`(${i + 1}/${items.length}) ${t.slug} ... `);
    try {
      const { obj, usage } = await generateOne(t);
      fs.writeFileSync(path.join(OUT, t.slug + ".json"), JSON.stringify(assemble(t, obj), null, 2), "utf8");
      inTok += usage.input_tokens || 0; outTok += usage.output_tokens || 0; ok++;
      console.log("OK");
    } catch (e) { fail++; failed.push(t.slug); console.log("FAIL  " + e.message); }
    await sleep(parseInt(process.env.DENTAL_DELAY_MS, 10) || 1500);
  }
  console.log(`\n----------------------------------------`);
  console.log(`Done.  OK ${ok}   FAIL ${fail}${failed.length ? "  (" + failed.join(", ") + ")" : ""}`);
  console.log(`Tokens:  input ${inTok.toLocaleString()}  output ${outTok.toLocaleString()}`);
  console.log(`Specs in  output-dental/`);
  console.log(`----------------------------------------\n`);
})();
