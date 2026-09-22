import type { IncidentBundle, IncidentObservation } from "./types";
import { MAX_INCIDENT_BYTES, MAX_INCIDENT_OBSERVATIONS, parseIncidentJson } from "./incident-import";

export const SUPPORTED_INCIDENT_FORMATS = "JSON, JSONL/NDJSON, CSV, and UTF-8 text/log/Markdown files";
export const INCIDENT_FILE_ACCEPT = ".json,.jsonl,.ndjson,.csv,.txt,.log,.md,.markdown,text/plain,application/json,text/csv";
export type PreparedIncidentFile = {
  bundle: IncidentBundle;
  converted: boolean;
  format: "incident-bundle" | "json" | "jsonl" | "csv" | "text";
  warnings: string[];
  summary?: { source_line_count: number; observation_count: number; recognized_journal_lines: number };
};

type Metadata = { observed_at: string | null; node: string | null; severity: string };
type SourceRecord = { value: unknown; message: string; metadata?: Metadata };
const TEXT_EXTENSIONS = new Set(["", "txt", "log", "md", "markdown"]);
const SUPPORTED_EXTENSIONS = new Set([...TEXT_EXTENSIONS, "json", "jsonl", "ndjson", "csv"]);
const LOG_SEVERITIES = new Set(["debug", "info", "warning", "error", "critical"]);
const TIME_FIELDS = new Set(["observed_at", "timestamp", "time", "@timestamp", "datetime", "date"]);
const NODE_FIELDS = new Set(["node", "host", "hostname"]);

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

class JsonSyntaxError extends Error {}

function parseJson(text: string, context: string): unknown {
  let value: unknown;
  try { value = JSON.parse(text); } catch { throw new JsonSyntaxError(`${context} is not valid JSON. Correct its syntax or export it as a text/log file to preserve it as text.`); }
  // Reject duplicate keys instead of silently keeping only the last value.
  const objects: Array<Set<string>> = [];
  for (let i = 0; i < text.length; i += 1) {
    if (text[i] === "{") objects.push(new Set());
    else if (text[i] === "}") objects.pop();
    else if (text[i] === '"') {
      const start = i++;
      while (i < text.length) {
        if (text[i] === "\\") { i += 2; continue; }
        if (text[i] === '"') break;
        i += 1;
      }
      let next = i + 1;
      while (/\s/.test(text[next] ?? "") && next < text.length) next += 1;
      if (text[next] === ":") {
        const key: string = JSON.parse(text.slice(start, i + 1));
        const keys = objects[objects.length - 1];
        if (keys?.has(key)) throw new Error(`${context} contains duplicate object keys. Give each field a unique name so conversion cannot discard a value.`);
        keys?.add(key);
      }
    }
  }
  return value;
}

function assertRecordCount(count: number): void {
  if (count > MAX_INCIDENT_OBSERVATIONS) throw new Error("The file contains more than 32 records. Split it into smaller files; no records were discarded or imported.");
}

function serializeRecord(value: unknown): string {
  try { return JSON.stringify(value); } catch { throw new Error("The JSON structure is too deeply nested to convert. Export a flatter record structure."); }
}

function skipSpace(text: string, start: number): number {
  let index = start;
  while (index < text.length && /\s/.test(text[index])) index += 1;
  return index;
}

/** Input has already passed JSON.parse; scan boundaries without rewriting literals. */
function stringEnd(text: string, start: number): number {
  let index = start + 1;
  while (index < text.length) {
    if (text[index] === "\\") index += 2;
    else if (text[index++] === '"') return index;
  }
  return index;
}

function valueEnd(text: string, start: number): number {
  if (text[start] === '"') return stringEnd(text, start);
  if (text[start] !== "{" && text[start] !== "[") {
    let index = start;
    while (index < text.length && !/[\s,}\]]/.test(text[index])) index += 1;
    return index;
  }
  let depth = 0;
  for (let index = start; index < text.length; index += 1) {
    const char = text[index];
    if (char === '"') index = stringEnd(text, index) - 1;
    else if (char === "{" || char === "[") depth += 1;
    else if ((char === "}" || char === "]") && --depth === 0) return index + 1;
  }
  return text.length;
}

function collectionStart(text: string, key: string): number {
  let cursor = skipSpace(text, skipSpace(text, 0) + 1);
  while (cursor < text.length && text[cursor] !== "}") {
    const keyEnd = stringEnd(text, cursor);
    const property: string = JSON.parse(text.slice(cursor, keyEnd));
    const start = skipSpace(text, skipSpace(text, keyEnd) + 1);
    if (property === key) return start;
    cursor = skipSpace(text, valueEnd(text, start));
    if (text[cursor] === ",") cursor = skipSpace(text, cursor + 1);
  }
  throw new Error("The JSON collection could not be located. Export individual records as JSONL.");
}

function recordsFromJson(value: unknown, text: string): SourceRecord[] {
  let rows: unknown[] | null = null;
  let start = skipSpace(text, 0);
  if (Array.isArray(value)) rows = value;
  else if (isRecord(value)) {
    const collection = ["logs", "events", "alerts"].find((key) => Array.isArray(value[key]));
    if (collection) { rows = value[collection] as unknown[]; start = collectionStart(text, collection); }
  }
  if (!rows || rows.length === 0) return [{ value, message: text }];
  assertRecordCount(rows.length);
  let cursor = skipSpace(text, start + 1);
  let previousBoundary = 0;
  return rows.map((item, index) => {
    const end = valueEnd(text, cursor);
    const boundary = index === rows.length - 1 ? text.length : end;
    // Prefix/suffix, delimiters, unknown envelope fields, number precision, and
    // escape spellings are retained exactly once. Join ordered fragments to
    // reconstruct the input; parsed values supply metadata only.
    const message = text.slice(previousBoundary, boundary);
    previousBoundary = boundary;
    cursor = skipSpace(text, end);
    if (text[cursor] === ",") cursor = skipSpace(text, cursor + 1);
    return { value: item, message };
  });
}

/** RFC-style quoted fields, escaped quotes, and embedded CR/LF are preserved. */
function recordsFromCsv(text: string): SourceRecord[] {
  const rows: string[][] = [];
  let row: string[] = [];
  let field = "";
  let quoted = false;
  let afterQuote = false;
  let started = false;
  function finishRow() {
    if (started || row.length || field.length) { rows.push([...row, field]); assertRecordCount(Math.max(0, rows.length - 1)); }
    row = []; field = ""; started = false; afterQuote = false;
  }
  for (let i = 0; i < text.length; i += 1) {
    const char = text[i];
    if (quoted) {
      if (char === '"' && text[i + 1] === '"') { field += '"'; i += 1; }
      else if (char === '"') { quoted = false; afterQuote = true; }
      else field += char;
      continue;
    }
    if (char === ",") { row.push(field); field = ""; started = true; afterQuote = false; }
    else if (char === "\r" || char === "\n") { finishRow(); if (char === "\r" && text[i + 1] === "\n") i += 1; }
    else if (char === '"' && !field && !afterQuote) { quoted = true; started = true; }
    else if (char === '"' || afterQuote) throw new Error("CSV contains malformed quoting. Quote fields containing commas/newlines and escape a quote as two quotes.");
    else { field += char; started = true; }
  }
  if (quoted) throw new Error("CSV has an unclosed quoted field. Close the quote before importing.");
  finishRow();
  if (rows.length < 2) throw new Error("CSV needs a header row and at least one data row.");
  const headers = rows[0];
  if (headers.some((header) => !header.trim()) || new Set(headers).size !== headers.length) {
    throw new Error("CSV headers must be non-empty and unique so every column can be preserved.");
  }
  return rows.slice(1).map((values, index) => {
    if (values.length !== headers.length) throw new Error(`CSV data row ${index + 1} has a different number of fields from the header. No rows were imported.`);
    const value = Object.fromEntries(headers.map((header, column) => [header, values[column]]));
    return { value, message: serializeRecord(value) };
  });
}

function validTimestamp(value: string): boolean {
  const match = /^(\d{4})-(\d{2})-(\d{2})[Tt ](\d{2}):(\d{2})(?::(\d{2})(?:\.\d{1,9})?)?([Zz]|[+-]\d{2}:\d{2})$/.exec(value);
  if (!match) return false;
  const [, yearText, monthText, dayText, hourText, minuteText, secondText = "0", zone] = match;
  const year = Number(yearText), month = Number(monthText), day = Number(dayText);
  const leap = year % 4 === 0 && (year % 100 !== 0 || year % 400 === 0);
  const days = [31, leap ? 29 : 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31];
  if (year < 1 || month < 1 || month > 12 || day < 1 || day > days[month - 1] || Number(hourText) > 23 || Number(minuteText) > 59 || Number(secondText) > 59) return false;
  if (zone !== "Z" && zone !== "z" && (Number(zone.slice(1, 3)) > 23 || Number(zone.slice(4)) > 59)) return false;
  return Number.isFinite(Date.parse(value));
}

function metadataFor(value: unknown, warnings: Set<string>): Metadata {
  const entries = isRecord(value) ? Object.entries(value) : [];
  const times: string[] = [];
  const nodes: string[] = [];
  let severity = "info";
  let recognizedSeverity = false;
  for (const [rawKey, item] of entries) {
    const key = rawKey.trim().toLowerCase();
    if (TIME_FIELDS.has(key)) {
      if (typeof item === "string" && validTimestamp(item.trim())) times.push(item.trim());
      else warnings.add("Some timestamp fields are invalid or lack a timezone. Their original values remain in the log text; no timestamp was invented.");
    }
    if (NODE_FIELDS.has(key)) {
      if (typeof item === "string" && item.trim() && Array.from(item.trim()).length <= 100) nodes.push(item.trim());
      else warnings.add("Some node/host fields are invalid or too long. Their original values remain in the log text; no target was invented.");
    }
    if ((key === "severity" || key === "level") && typeof item === "string" && LOG_SEVERITIES.has(item.toLowerCase())) {
      severity = item.toLowerCase(); recognizedSeverity = true;
    }
  }
  const distinctTimes = [...new Set(times)];
  const distinctNodes = [...new Set(nodes)];
  if (distinctTimes.length > 1) warnings.add("Conflicting timestamp fields were preserved in the log text. The observation time is left unknown.");
  if (distinctNodes.length > 1) warnings.add("Conflicting node/host fields were preserved in the log text. The observation target is left unknown.");
  const observed_at = distinctTimes.length === 1 ? distinctTimes[0] : null;
  const node = distinctNodes.length === 1 ? distinctNodes[0] : null;
  if (!observed_at) warnings.add("Some observations have no recognized timezone-bearing event time. Missing times remain null; the upload time is not used as event time.");
  if (!node) warnings.add("Some observations have no explicit node/host. Missing targets remain null; target-specific operations may be unavailable.");
  if (!recognizedSeverity) warnings.add("Unrecognized or missing log severity defaults to info. Original fields are retained as text.");
  return { observed_at, node, severity };
}

function asciiSnapshotBytes(value: unknown): number {
  // Python ensure_ascii JSON expands each UTF-16 unit to six ASCII characters.
  // Reserve more than the eleven separators added by Python's default encoder.
  return JSON.stringify(value).replace(/[\u007f-\uffff]/g, (char) => `\\u${char.charCodeAt(0).toString(16).padStart(4, "0")}`).length + 32;
}

function appendRecord(observations: IncidentObservation[], record: SourceRecord, source: string, warnings: Set<string>) {
  const metadata = record.metadata ?? metadataFor(record.value, warnings);
  const chars = Array.from(record.message);
  let offset = 0;
  const originalCount = observations.length;
  while (offset < chars.length) {
    if (observations.length === MAX_INCIDENT_OBSERVATIONS) throw new Error("Conversion needs more than 32 observations. Split the source into smaller files; no content was truncated or imported.");
    let lower = 1, upper = Math.min(2000, chars.length - offset), accepted = 0;
    const make = (length: number): IncidentObservation => ({ kind: "log", source, observed_at: metadata.observed_at, node: metadata.node, severity: metadata.severity, message: chars.slice(offset, offset + length).join("") });
    while (lower <= upper) {
      const middle = Math.floor((lower + upper) / 2);
      if (asciiSnapshotBytes(make(middle)) <= 12000) { accepted = middle; lower = middle + 1; }
      else upper = middle - 1;
    }
    if (!accepted) throw new Error("A record cannot fit the observation size limit. Export a smaller record.");
    const observation = make(accepted);
    if (!(observation.message as string).trim()) {
      throw new Error("The file contains a whitespace-only segment too large for a log observation. Export smaller records; no content was discarded.");
    }
    observations.push(observation);
    offset += accepted;
  }
  if (observations.length - originalCount > 1) warnings.add(record.metadata
    ? "An overlong log line was split into consecutive fragments to fit size limits. Join its fragments in order to reconstruct the original text."
    : "Long records were split into consecutive log fragments within the message and snapshot limits. Their text is preserved in order; JSON fragments must be joined to reconstruct a long original record.");
}

const JOURNAL_HOST = "([A-Za-z0-9][A-Za-z0-9._-]{0,99})";
const JOURNAL_TAG = "[A-Za-z0-9_./@-]+(?:\\[\\d+\\])?:";
const SHORT_JOURNAL = new RegExp(`^(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec) +([0-9]{1,2}) +(\\d{2}):(\\d{2}):(\\d{2})(?:\\.\\d+)? +${JOURNAL_HOST} +${JOURNAL_TAG}`);
const ISO_JOURNAL = new RegExp(`^(\\d{4}-\\d{2}-\\d{2}[Tt ]\\d{2}:\\d{2}:\\d{2}(?:\\.\\d{1,9})?(?:[Zz]|[+-]\\d{2}:?\\d{2})?) +${JOURNAL_HOST} +${JOURNAL_TAG}`);

function journalMetadata(line: string): { metadata: Metadata; incompleteTime: boolean } | null {
  const short = SHORT_JOURNAL.exec(line);
  if (short) {
    const month = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"].indexOf(short[1]);
    const maxDay = [31, 29, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31][month];
    if (Number(short[2]) < 1 || Number(short[2]) > maxDay || Number(short[3]) > 23 || Number(short[4]) > 59 || Number(short[5]) > 59) return null;
    return { metadata: { node: short[6], observed_at: null, severity: "info" }, incompleteTime: true };
  }
  const iso = ISO_JOURNAL.exec(line);
  if (!iso) return null;
  // Normalize the spelling of an explicit offset, never infer its value.
  const time = iso[1].replace(/[Tt ]/, "T").replace(/z$/, "Z").replace(/([+-]\d{2})(\d{2})$/, "$1:$2");
  const observed_at = validTimestamp(time) ? time : null;
  return { metadata: { node: iso[2], observed_at, severity: "info" }, incompleteTime: observed_at === null };
}

/** Keep line boundaries and original separators while packing bounded chunks. */
function recordsFromText(text: string, source: string, warnings: Set<string>) {
  const lines = text.match(/[^\r\n]*(?:\r\n|\r|\n)|[^\r\n]+$/g) ?? [];
  const records: SourceRecord[] = [];
  let group: SourceRecord | null = null;
  let pendingBlank = "";
  let recognized = 0;
  let unknownLines = false;
  let incompleteJournalTimes = false;
  const explicitTimes = new Set<string>();
  const fits = (message: string, metadata: Metadata) => Array.from(message).length <= 2000 && asciiSnapshotBytes({ kind: "log", source, ...metadata, message }) <= 12000;
  const flush = () => { if (group) { records.push(group); assertRecordCount(records.length); } group = null; };
  for (const line of lines) {
    if (!line.trim()) {
      if (group && fits(group.message + line, group.metadata!)) group.message += line;
      else { flush(); pendingBlank += line; }
      continue;
    }
    const journal = journalMetadata(line);
    const metadata = journal?.metadata ?? { node: null, observed_at: null, severity: "info" };
    if (journal) {
      recognized += 1;
      incompleteJournalTimes ||= journal.incompleteTime;
      if (metadata.observed_at) explicitTimes.add(metadata.observed_at);
    } else unknownLines = true;
    const combinedMetadata: Metadata = {
      ...metadata,
      observed_at: group?.metadata?.observed_at === metadata.observed_at ? metadata.observed_at : null,
    };
    if (group && group.metadata!.node === metadata.node && fits(group.message + line, combinedMetadata)) {
      group.message += line;
      group.metadata = combinedMetadata;
    } else {
      flush();
      group = { value: null, message: pendingBlank + line, metadata };
      pendingBlank = "";
      // Only a single overlong source line is split later by appendRecord.
      if (!fits(group.message, metadata)) flush();
    }
  }
  if (pendingBlank) {
    if (group) group.message += pendingBlank;
    else if (records.length) records[records.length - 1].message += pendingBlank;
  }
  flush();
  if (recognized) {
    warnings.add("Log severity defaults to info; journal message wording is not used to infer severity.");
    if (incompleteJournalTimes) warnings.add("Some journal dates omit a year/timezone or are invalid. Those event times remain unknown; export full ISO timestamps with a timezone to retain them. Original date text is preserved.");
    if (explicitTimes.size > 1) warnings.add("Multiple explicit event times are preserved in the text. Chunks containing different times, and the overall incident, have no single timestamp.");
    if (unknownLines) warnings.add("Some lines have no recognized journal prefix. Their host and event time remain unknown; no metadata is inherited from nearby lines.");
  } else {
    // Retain the established generic conversion notes for unstructured text.
    metadataFor(null, warnings);
  }
  return { records, source_line_count: lines.length, recognized_journal_lines: recognized };
}

/** Local conversion only. This function performs no network or model calls. */
export async function prepareIncidentFile(file: Pick<File, "name" | "size" | "text">): Promise<PreparedIncidentFile> {
  const name = file.name.split(/[\\/]/).pop() || "incident.txt";
  const extension = name.includes(".") ? name.split(".").pop()!.toLowerCase() : "";
  if (!SUPPORTED_EXTENSIONS.has(extension)) throw new Error(`This file type is not supported. Export ${SUPPORTED_INCIDENT_FORMATS}. PDF, office documents, archives, and binary files cannot be imported directly.`);
  if (file.size > MAX_INCIDENT_BYTES) throw new Error("The file exceeds 1 MiB. Export a smaller incident file before converting.");
  let text: string;
  try { text = await file.text(); } catch { throw new Error("The file could not be read. Select a UTF-8 export and try again."); }
  if (new TextEncoder().encode(text).byteLength > MAX_INCIDENT_BYTES) throw new Error("The file exceeds 1 MiB. Export a smaller incident file before converting.");
  if (/[\u0000-\u0008\u000b\u000c\u000e-\u001a\u001c-\u001f]/.test(text) || text.startsWith("%PDF-") || text.startsWith("PK\u0003\u0004")) throw new Error(`The file appears to contain binary or non-UTF-8 text. Export ${SUPPORTED_INCIDENT_FORMATS}.`);
  if (text.includes("\uFFFD")) throw new Error("The file contains Unicode replacement characters, which may indicate invalid UTF-8. Re-export it as UTF-8 so source content is not silently changed.");
  text = text.replace(/^\uFEFF/, "");
  if (!text.trim()) throw new Error("The file is empty. Select an export containing at least one observation.");
  let records: SourceRecord[];
  let format: PreparedIncidentFile["format"];
  let invalidJsonPreserved = false;
  if (extension === "json") {
    let value: unknown;
    try { value = parseJson(text, "The JSON file"); }
    catch (error) {
      if (!(error instanceof JsonSyntaxError)) throw error;
      invalidJsonPreserved = true;
    }
    if (!invalidJsonPreserved && isRecord(value) && (value.schema_version === "incident-bundle-v1" || "incident" in value && "observations" in value)) {
      return { bundle: parseIncidentJson(text), converted: false, format: "incident-bundle", warnings: [] };
    }
    records = invalidJsonPreserved ? [{ value: null, message: text }] : recordsFromJson(value, text);
    format = invalidJsonPreserved ? "text" : "json";
  } else if (extension === "jsonl" || extension === "ndjson") {
    records = [];
    for (const [index, line] of text.split(/\r?\n/).entries()) {
      if (!line.trim()) continue;
      const value = parseJson(line, `JSONL line ${index + 1}`);
      if (!isRecord(value)) throw new Error(`JSONL line ${index + 1} must contain a JSON object.`);
      records.push({ value, message: line });
      assertRecordCount(records.length);
    }
    format = "jsonl";
  } else if (extension === "csv") {
    records = recordsFromCsv(text); format = "csv";
  } else {
    // Recognize JSON exports with a text suffix, but preserve malformed JSON
    // verbatim as ordinary log text instead of silently repairing it.
    let parsed: unknown;
    let recognized = false;
    if (/^\s*[\[{]/.test(text)) {
      try { parsed = parseJson(text, "The text file"); recognized = true; } catch { /* Preserve it as text. */ }
    }
    if (recognized) {
      if (isRecord(parsed) && (parsed.schema_version === "incident-bundle-v1" || "incident" in parsed && "observations" in parsed)) {
        return { bundle: parseIncidentJson(text), converted: false, format: "incident-bundle", warnings: [] };
      }
      records = recordsFromJson(parsed, text); format = "json";
    } else {
      records = [{ value: null, message: text }]; format = "text";
    }
  }
  if (!records.length) throw new Error("The file contains no records. Select an export with at least one observation.");
  const warnings = new Set<string>(["Converted locally without a model. Imported data remains untrusted; review the generated bundle before importing.", "Incident severity defaults to warning. Review the incident classification before relying on it."]);
  if (invalidJsonPreserved) warnings.add("JSON syntax is invalid. The file was preserved verbatim as untrusted log text, not repaired or interpreted as JSON.");
  if (format === "json" && records.length > 1) warnings.add("JSON source records are stored as ordered text fragments. Join their messages to reconstruct the original file, including collection delimiters and surrounding fields.");
  const safeName = name.replace(/[\u0000-\u001f\u007f]/g, "_");
  const source = `upload:${Array.from(safeName).slice(0, 72).join("")}`;
  const title = `Imported ${Array.from(safeName).slice(0, 200).join("")}`;
  if (Array.from(safeName).length > 72) warnings.add("The filename-derived source label was shortened to fit the schema. Observation content was not truncated.");
  let textSummary: Omit<NonNullable<PreparedIncidentFile["summary"]>, "observation_count"> | undefined;
  if (format === "text") {
    const converted = recordsFromText(text, source, warnings);
    records = converted.records;
    textSummary = { source_line_count: converted.source_line_count, recognized_journal_lines: converted.recognized_journal_lines };
  }
  const observations: IncidentObservation[] = [];
  records.forEach((record) => appendRecord(observations, record, source, warnings));
  const eventTimes = [...new Set(observations.map((item) => item.observed_at))];
  const targets = [...new Set(observations.map((item) => item.node))];
  const bundle: IncidentBundle = {
    schema_version: "incident-bundle-v1",
    incident: {
      title,
      description: `Locally converted ${format.toUpperCase()} evidence export. Source content is preserved in ${observations.length} untrusted log observations. Review source data, missing metadata, and severity before investigation.`,
      severity: "warning", source,
      observed_at: eventTimes.length === 1 ? eventTimes[0] : null,
      node: targets.length === 1 ? targets[0] : null,
      infrastructure_type: "unknown",
    },
    observations,
  };
  if (!bundle.incident.observed_at && !textSummary?.recognized_journal_lines) warnings.add("No single explicit incident timestamp is available. Incident time remains null; individual observation times are preserved where provided.");
  if (!bundle.incident.node) warnings.add("No single explicit incident target is available. Incident node remains null; individual observation targets are preserved where provided.");
  return { bundle, converted: true, format, warnings: [...warnings], ...(textSummary ? { summary: { ...textSummary, observation_count: observations.length } } : {}) };
}
