"""End-to-end chat orchestration service connecting FastAPI /v1/chat to NETIQ agents.

Architecture Role:
------------------
Coordinates:
1. Circle & User Authorization (`AuthorizationService` + `CircleAccessPolicy`)
2. Follow-Up Session Resolution (`default_result_store`)
3. Intent Classification & Report Matching (`ReportSelector`, `KnowledgeAgent`)
4. Deterministic Data Retrieval (`ReportRetrievalService`)
5. Dynamic Column Metadata, Summary KPI Metrics, and Source Attribution
6. Result Persistence (`default_result_store`) for pagination and Excel export
"""

from __future__ import annotations

import difflib
import json
import math
import os
import re
import time
import uuid
from pathlib import Path
from typing import Any

from app.llms.knowledge_agent import KnowledgeDocument, default_knowledge_agent
from app.llms.report_selector import default_report_selector
from app.orchestrator.verify import ResponseVerifier
from src.schemas.chat import (
    ChatRequest,
    ChatResponse,
    ColumnMeta,
    ExportInfo,
    MetricCard,
    SourceReference,
    TablePayload,
)
from src.schemas.errors import ErrorCode, StandardError
from src.schemas.reports import ReportPagination, ReportQuery, ReportStatus
from src.schemas.user import UserContext
from src.security.authorization import AuthorizationError, AuthorizationService
from src.security.circle_access import UnauthorizedCircleError
from src.session.result_store import (
    ResultAccessDeniedError,
    ResultNotFoundError,
    default_result_store,
)
from src.settings.env import PROJECT_ROOT, settings
from src.settings.loader import load_catalog_config
from src.tools.data_extraction.retrieval import ReportRetrievalService

_CIRCLE_ALIASES = {
    "bihar": "BR",
    "br": "BR",
    "delhi": "DL",
    "dl": "DL",
    "haryana": "HR",
    "hr": "HR",
    "mumbai": "MH",
    "maharashtra": "MH",
    "mh": "MH",
    "punjab": "PB",
    "pb": "PB",
    "karnataka": "KA",
    "ka": "KA",
    "tamilnadu": "TN",
    "tn": "TN",
}

_BUILTIN_KNOWLEDGE_DOCS = [
    KnowledgeDocument(
        doc_id="SOP-RAN-402",
        title="RAN Cell Availability and Incident Escalation",
        domain="RAN",
        content="SOP-RAN-402: eNodeB cell availability below 98.5% triggers Severity-2 and notification to the NOC RAN team.",
    ),
    KnowledgeDocument(
        doc_id="GLOSSARY-NETIQ-001",
        title="LTE / 5G Control Plane (CPLANE) vs User Plane (UPLANE)",
        domain="RAN",
        content=(
            "CPLANE (Control Plane) carries signaling traffic such as RRC, S1-AP, and NG-AP used for "
            "call setup, handover, and mobility management. UPLANE (User Plane) carries subscriber IP "
            "data payload over GTP-U tunnels between the eNodeB/gNodeB and the core gateway (SGW/UPF)."
        ),
    ),
]


def _infer_column_type(values: list[Any]) -> str:
    """Infer column type strictly from observed non-null row values."""
    non_null = [v for v in values if v is not None]
    if not non_null:
        return "string"
    sample = non_null[0]
    if isinstance(sample, bool):
        return "boolean"
    if isinstance(sample, int):
        return "integer"
    if isinstance(sample, float):
        return "float"
    return "string"


def _humanize_label(field: str) -> str:
    """Convert camelCase or snake_case field name into a readable column header."""
    spaced = re.sub(r"([a-z0-9])([A-Z])", r"\1 \2", field).replace("_", " ")
    return spaced.strip().title()


def _build_columns(rows: list[dict[str, Any]]) -> list[ColumnMeta]:
    """Build dynamic ColumnMeta list from actual API response rows."""
    if not rows:
        return []
    ordered_keys: list[str] = []
    seen: set[str] = set()
    for row in rows:
        for k in row.keys():
            if k not in seen:
                seen.add(k)
                ordered_keys.append(k)
    return [
        ColumnMeta(
            field=k,
            label=_humanize_label(k),
            type=_infer_column_type([r.get(k) for r in rows[:20]]),
        )
        for k in ordered_keys
    ]


def _extract_circles_from_text(text: str) -> list[str]:
    """Extract normalized telecom circle codes mentioned in text."""
    tokens = re.findall(r"[A-Za-z]+", text.lower())
    found: list[str] = []
    for tok in tokens:
        code = _CIRCLE_ALIASES.get(tok)
        if code and code not in found:
            found.append(code)
    return found


def _load_knowledge_docs() -> list[KnowledgeDocument]:
    """Load local markdown documents from knowledge_base/ plus built-in verified SOPs."""
    docs = list(_BUILTIN_KNOWLEDGE_DOCS)
    kb_dir = PROJECT_ROOT / "knowledge_base"
    if kb_dir.is_dir():
        for md_file in sorted(kb_dir.rglob("*.md")):
            try:
                content = md_file.read_text(encoding="utf-8").strip()
                if content:
                    docs.append(
                        KnowledgeDocument(
                            doc_id=md_file.stem.upper(),
                            title=md_file.stem.replace("_", " ").title(),
                            domain=md_file.parent.name.upper(),
                            content=content[:2000],
                        )
                    )
            except OSError:
                continue
    return docs


# ---------------------------------------------------------------------------
# Fixed Q&A engine (deterministic, no LLM) + conversational guardrails
# ---------------------------------------------------------------------------
# Source of truth: data/knowledge/netiq_chatbot_knowledge_base.json
#   (fallbacks: netiq_fixed_qa_expanded.json, netiq_fixed_qa.json).
# Override the location with env var NETIQ_FIXED_QA_PATH.
# A matched fixed question returns the approved answer VERBATIM with citations;
# anything that does not match confidently falls through to the existing
# report / knowledge-agent routing unchanged.

_FQA_FILES = (
    "netiq_chatbot_knowledge_base.json",
    "netiq_fixed_qa_expanded.json",
    "netiq_fixed_qa.json",
)

_FQA_STOP = frozenset(
    "a an the is are was were be of in on at to do does did i me my we our you your it its this that "
    "for and or can could would should please with by from there any tell about as so if will shall "
    "am im ive pls plz".split()
)

_FQA_ABBREV = {
    "srvc": "service", "svc": "service", "rpt": "report", "rpts": "reports", "hlp": "help",
    "vendr": "vendor", "vndr": "vendor", "tech": "technology", "util": "utilisation",
    "utilization": "utilisation", "utilisations": "utilisation", "dashbrd": "dashboard",
    "dash": "dashboard", "wat": "what", "wats": "whats", "whats": "what", "schdule": "schedule",
    "schdul": "schedule", "sched": "schedule", "chng": "change", "mon": "monday", "mw": "mw",
    "2": "to", "u": "you", "cant": "cannot", "cannot": "cannot", "unable": "cannot",
    "wher": "where", "hw": "how", "mail": "email", "emailed": "email", "emailing": "email",
    "sign": "login", "signin": "login", "log": "login", "logon": "login", "meaning": "mean",
    "define": "what", "definition": "what", "explain": "what", "describe": "what",
    "weekly": "weekly", "exports": "export", "downloaded": "download",
}

# Light Hinglish / chat-style phrase normalisation (applied before tokenising).
_FQA_PHRASES = (
    ("matlab kya hai", "mean"), ("ka matlab", "mean"), ("kya hai", "what"), ("kya hota hai", "what"),
    ("kaise kare", "how"), ("kaise karein", "how"), ("kaise karna", "how"), ("kaise", "how"),
    ("kahan milega", "where"), ("kahan milta hai", "where"), ("kahan hai", "where"), ("kahan", "where"),
    ("nahi ho raha", "not working"), ("nahi hota", "not working"), ("nahi chal raha", "not working"),
    ("aa sakti hai kya", "can"), ("aa sakta hai kya", "can"), ("ho sakta hai kya", "can"),
    ("har monday", "every monday"), ("har somvar", "every monday"), ("mail pe", "email"),
    ("ka dashboard", "dashboard"), ("ke liye", ""), ("mujhe", ""), ("bata", "tell"), ("batao", "tell"),
    (" me ", " in "), (" ka ", " "), (" ki ", " "), (" ke ", " "), (" hai ", " "), (" kya ", " "),
)

# Leading verbs of data/report requests: these need a (near-)exact match to be
# answered from the fixed Q&A, so report routing is never hijacked.
_FQA_STRICT_START = (
    "show", "list", "give", "get", "find", "display", "fetch", "count", "compare", "export",
    "download", "view", "open", "pull", "check", "how many",
)
_FQA_STRICT_THRESHOLD = 0.90
_FQA_THRESHOLD = 0.72
_FQA_MARGIN = 0.03


def _fqa_stem(tok: str) -> str:
    if len(tok) > 5 and tok.endswith("ing"):
        return tok[:-3]
    if len(tok) > 5 and tok.endswith("ed"):
        return tok[:-2]
    if tok.endswith("ies") and len(tok) > 4:
        return tok[:-3] + "y"
    if tok.endswith("s") and not tok.endswith("ss") and len(tok) > 3:
        return tok[:-1]
    return tok


def _fqa_norm(text: str) -> str:
    t = f" {text.lower().strip()} "
    t = t.replace("'s ", " is ").replace("\u2019s ", " is ")
    t = re.sub(r"[^a-z0-9\-/+ ]", " ", t)
    t = re.sub(r"\s+", " ", t)
    for src, dst in _FQA_PHRASES:
        t = t.replace(src if src.startswith(" ") else f" {src} ", f" {dst} " if dst else " ")
    return re.sub(r"\s+", " ", t).strip()


def _fqa_tokens(norm: str) -> list[str]:
    out: list[str] = []
    for tok in norm.split():
        tok = _FQA_ABBREV.get(tok, tok)
        if tok in _FQA_STOP:
            continue
        out.append(_fqa_stem(tok))
    return out


# Entries added on top of the document-derived knowledge base. They close gaps found
# when the fixed Q&A set was tested against real user phrasing (chat style, Hinglish).
_FQA_SUPPLEMENTAL: list[dict[str, Any]] = [
    {
        "id": "NETIQ-SUP-001",
        "category": "Navigation, Filters & Search",
        "type": "how-to",
        "question": "How do I filter the inventory by vendor and technology?",
        "alternate_questions": [
            "filter by vendor", "filter by vendor and technology", "how do i filter by vendor and tech?",
            "inventory filter vendor how to do", "Inventory me vendor aur technology se filter kaise kare",
            "how 2 filter vendr", "How do I filter reports by vendor?",
        ],
        "answer": (
            "Open the blue funnel Dashboard Filter Panel, choose the Vendor (and Circle), and click Apply Filters. "
            "In any inventory or audit report use the Filters control to filter the Vendor and Technology columns, "
            "or the Advanced query builder when you need several conditions together. Circle and Vendor filters stay "
            "active for the session until you click Reset All."
        ),
        "keywords": ["filter", "vendor", "technology", "inventory", "filter panel", "advanced query"],
        "source_references": [{"document": "NETIQ User Manual v3.5", "section": "§3.3, §3.4, §9 Q3 Q5"}],
    },
    {
        "id": "NETIQ-SUP-002",
        "category": "Dashboards & KPIs",
        "type": "how-to",
        "question": "Where can I find the dashboard for microwave link utilisation?",
        "alternate_questions": [
            "where's the MW utilisation dashboard?", "mw utilisation dashboard where is", "MW utilization dashboard",
            "MW utilisation ka dashboard kahan milega", "mw util dashboard where?", "Where is the MW capacity dashboard?",
        ],
        "answer": (
            "Switch the Project Hub toggle to Txn, set Type to MW, and open the Network Intelligence View dashboard. "
            "Capacity-wise Hop Categorisation shows MW hops by configured capacity band (0-250 up to 2001-4000), "
            "Hop Type Distribution and Transmission-links status show the link mix, and the AI Inference panel includes "
            "MW capacity utilisation based on historical trend (BETA). NETIQ audits configuration from CM dumps; it does "
            "not ingest live performance counters, so real-time link utilisation is not shown."
        ),
        "keywords": ["MW", "utilisation", "dashboard", "capacity", "hop", "txn"],
        "source_references": [
            {"document": "NETIQ User Manual v3.5", "section": "§4.1.3"},
            {"document": "NETIQ Solution Document v3.3", "section": "§18.2, §18.5"},
        ],
    },
    {
        "id": "NETIQ-SUP-003",
        "category": "Navigation, Filters & Search",
        "type": "scope-limit",
        "question": "Can I schedule the weekly audit report to be emailed to my team every Monday?",
        "alternate_questions": [
            "can you send me the audit report every monday?", "weekly audit report mail every monday possible?",
            "schedule audit report weekly", "Audit report har Monday mail pe aa sakti hai kya", "schdule audit rpt mon",
            "Can reports be scheduled?", "Can NETIQ email reports automatically?",
        ],
        "answer": (
            "A user-configurable schedule that e-mails a specific audit report every Monday is not described in the NETIQ "
            "documentation, so I cannot confirm or set one. What is available today: audit reports refresh with every "
            "collection cycle, any report can be exported on demand to Excel/CSV and shared, and role-aware notifications "
            "(including scheduled-report-ready events and e-mail digest where enabled) are listed as a platform capability. "
            "Please confirm with your NETIQ administrator whether scheduled delivery is enabled in your deployment."
        ),
        "keywords": ["schedule", "report", "email", "weekly", "monday", "notification", "export"],
        "source_references": [{"document": "NETIQ Solution Document v3.3", "section": "§3.1.7, §3.2, §11.2"}],
    },
    {
        "id": "NETIQ-SUP-004",
        "category": "Access, Roles & Security",
        "type": "troubleshooting",
        "question": "I am unable to log in to NETIQ. Could you please help?",
        "alternate_questions": [
            "can't log in, help?", "login not happening netiq", "login issue", "NETIQ me login nahi ho raha",
            "cant login netiq pls hlp", "I cannot sign in", "NETIQ login not working",
        ],
        "answer": (
            "Try these in order: (1) open the NETIQ URL provided by your administrator on the corporate LAN/VPN with a "
            "supported browser (Chrome, Edge or Firefox); (2) re-enter your registered e-mail and password and avoid repeated "
            "failed attempts because they can lock the account; (3) use the Forgot Password link, or reset your corporate "
            "password if your organisation uses SSO/LDAP; (4) if you are still blocked or see 'Access denied', contact your "
            "NETIQ administrator, who can unlock the account, check your role and escalate to Avendum support. For security I "
            "cannot look up or share any other user's account details."
        ),
        "keywords": ["login", "log in", "cannot login", "password", "account locked", "support", "administrator"],
        "source_references": [{"document": "NETIQ User Manual v3.5", "section": "§2.3, §8.2, §9 Q2"}],
    },
    {
        "id": "NETIQ-SUP-005",
        "category": "Navigation, Filters & Search",
        "type": "concept",
        "question": "What is the difference between RAN and Txn?",
        "alternate_questions": ["RAN vs Txn", "What does the RAN / Txn toggle mean?", "difference between RAN and transmission view"],
        "answer": (
            "RAN is the radio-access context (sites, nodes, cells and their hardware and IP data). Txn is the transmission "
            "context: microwave (MW), UBR and fibre backhaul nodes, links and hops. The RAN / Txn switch on the top command "
            "bar re-scopes the dashboard, KPI strip, inventory tree and audit menus; in Txn mode the Type dropdown narrows "
            "the view to ALL, MW or UBR."
        ),
        "keywords": ["RAN", "Txn", "transmission", "microwave", "toggle", "project hub"],
        "source_references": [{"document": "NETIQ User Manual v3.5", "section": "§3.2, §4.1.2"}],
    },
    {
        "id": "NETIQ-SUP-006",
        "category": "MW, UBR & Transport Audits",
        "type": "concept",
        "question": "What is Planned vs Config?",
        "alternate_questions": [
            "What is Planned-vs-Config?", "What is Planned vs Configured?", "What does planned vs configured mean?",
            "Explain planned vs configured",
        ],
        "answer": (
            "Planned vs Configured compares the designed (planned) parameters, such as the MIDS link plan, with the live "
            "configuration discovered in the network. For MW/UBR links it checks frequency, channel spacing, modulation and "
            "hop type and classifies each link as Deployed & Matched, Deployed & Unmatched, Planned Not Deployed or Deployed "
            "Not Planned. Deployment Compliance = Deployed & Matched links divided by Total Planned links."
        ),
        "keywords": ["planned vs configured", "planned", "live configuration", "MIDS", "deployment compliance"],
        "source_references": [{"document": "NETIQ User Manual v3.5", "section": "§4.1.4"},
                              {"document": "NETIQ Solution Document v3.3", "section": "§17.8, §18.5.2"}],
    },
    {
        "id": "NETIQ-SUP-007",
        "category": "Dashboards & KPIs",
        "type": "how-to",
        "question": "Where do I see the most critical issues first?",
        "alternate_questions": [
            "Where can I see critical issues?", "How do I find the most critical anomalies?", "show most critical issues first",
            "Where are the top anomalies?",
        ],
        "answer": (
            "On the RAN dashboard open Audit Insights, which lists the Top 5 anomalies with live counts (View All Issues opens "
            "the full audit). In Catchy Search use the Smart Shortcut 'Critical anomalies impacting 10+ sites', which ranks "
            "critical anomalies by the number of sites they affect. In Txn mode the same card shows the transmission anomalies."
        ),
        "keywords": ["critical anomalies", "audit insights", "top 5", "smart shortcut", "most critical"],
        "source_references": [{"document": "NETIQ User Manual v3.5", "section": "§3.5.3, §4.1.1.4"}],
    },
]



_FQA_QUESTION_START = re.compile(
    r"^\s*(what|whats|wat|wats|how|hw|where|wher|why|when|who|which|can|could|does|do|is|are|will|should|"
    r"explain|define|describe|tell me|difference|meaning)\b|\?\s*$|\b(kya|kaise|kahan|kyun|kab|kaun)\b",
    re.I,
)
# "Which sites / cells / duplicates ..." is a data request even though it is phrased as a question.
_FQA_DATA_REQUEST = re.compile(
    r"^\s*which\b.{0,25}\b(sites?|cells?|nodes?|links?|records?|elements?|services?|circuits?|duplicates?|hardware|boards?)\b"
    r"|^\s*what\s+(sites|cells|nodes|links|records)\b",
    re.I,
)
# Context-dependent wording ("this node", "these mismatches") refers to a previous result.
_FQA_DEICTIC = re.compile(
    r"\b(this|these|that|those)\s+(node|nodes|cell|cells|site|sites|link|links|audit|result|results|mismatch\w*|"
    r"record|records|value|values|number|figure|computed|calculated)\b|\bhow was this\b",
    re.I,
)
# Circle / vendor scoping that the matched fixed answer does not itself talk about -> treat as a data query.
_FQA_SCOPE_TOKENS = frozenset(
    "ericsson nokia huawei zte samsung ceragon cambium bihar delhi haryana mumbai maharashtra punjab karnataka "
    "tamilnadu chennai kolkata ap br dl hr mh pb ka tn up wb rj gj kl hp jk mp ue uw or as ne".split()
)
_FQA_ID_TOKEN = re.compile(r"\b[a-z]{2,4}[-_]?\d{3,}\b", re.I)

# Extra phrasings (chat style / Hinglish / short forms) for document-derived entries, keyed by canonical question.
_FQA_EXTRA_ALTERNATES: dict[str, list[str]] = {
    "What is service stitching in NETIQ?": [
        "What does 'service stitching' mean in NETIQ?", "what's service stitching exactly?",
        "service stitching meaning what", "service stitching meaning", "Service stitching ka matlab kya hai",
        "wat is srvc stitching", "What does service stitching mean?", "What is stitching?",
    ],
    "How do I filter by circle and vendor?": [
        "Do my filters carry between reports?", "Do filters persist between reports?", "Are my filters remembered?",
    ],
    "What happens to elements that disappear from a dump?": [
        "What happens to deleted / aged-out elements?", "What happens to deleted elements?",
    ],
    "What are the support contact details?": [
        "Who do I contact for a problem this manual does not cover?", "Who do I contact for a problem the manual does not cover?",
        "How do I get my access changed?",
    ],
}

_FQA_WH = frozenset("what how where why when who which whats".split())


class _FixedQAEngine:
    """Weighted token + fuzzy matcher over the approved fixed Q&A entries."""

    def __init__(self) -> None:
        self.entries: list[dict[str, Any]] = []
        self._phrasings: list[list[tuple[str, set[str]]]] = []
        self._exact: dict[str, int] = {}
        self._idf: dict[str, float] = {}
        self._loaded = False

    # ---- loading
    def _candidate_paths(self) -> list[Path]:
        env = os.environ.get("NETIQ_FIXED_QA_PATH")
        base = PROJECT_ROOT / "data" / "knowledge"
        paths = [Path(env)] if env else []
        paths += [base / n for n in _FQA_FILES]
        return paths

    def load(self, force: bool = False) -> None:
        if self._loaded and not force:
            return
        entries: list[dict[str, Any]] = []
        for p in self._candidate_paths():
            if not p.is_file():
                continue
            try:
                raw = json.loads(p.read_text(encoding="utf-8"))
            except (OSError, ValueError):
                continue
            rows = raw.get("entries", raw) if isinstance(raw, dict) else raw
            if isinstance(rows, list) and rows:
                entries = self._coerce(rows)
                break
        for e in entries:
            extra = _FQA_EXTRA_ALTERNATES.get(e["question"])
            if extra:
                e["alternate_questions"] = list(e.get("alternate_questions", [])) + [x for x in extra if x not in e.get("alternate_questions", [])]
        existing = {e["question"].lower() for e in entries}
        entries += [e for e in _FQA_SUPPLEMENTAL if e["question"].lower() not in existing]
        self.entries = entries
        self._index()
        self._loaded = True

    @staticmethod
    def _coerce(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Accept rich KB entries, flat {id,question,answer} rows, or expanded one-row-per-phrasing files."""
        merged: dict[str, dict[str, Any]] = {}
        order: list[str] = []
        for r in rows:
            if not isinstance(r, dict) or not r.get("question") or not r.get("answer"):
                continue
            key = str(r.get("id") or r["question"])
            if key not in merged:
                merged[key] = {
                    "id": key, "category": r.get("category", "NETIQ"), "type": r.get("type", "concept"),
                    "question": r["question"], "answer": r["answer"],
                    "alternate_questions": list(r.get("alternate_questions", [])),
                    "keywords": list(r.get("keywords", [])),
                    "source_references": list(r.get("source_references", [])),
                }
                order.append(key)
            elif r["question"] != merged[key]["question"]:
                merged[key]["alternate_questions"].append(r["question"])
        return [merged[k] for k in order]

    def _index(self) -> None:
        df: dict[str, int] = {}
        self._phrasings = []
        self._exact = {}
        for i, e in enumerate(self.entries):
            ph: list[tuple[str, set[str]]] = []
            seen_tokens: set[str] = set()
            for text in [e["question"], *e.get("alternate_questions", [])]:
                norm = _fqa_norm(text)
                toks = set(_fqa_tokens(norm))
                if not toks:
                    continue
                ph.append((norm, toks))
                self._exact.setdefault(norm, i)
                seen_tokens |= toks
            self._phrasings.append(ph)
            for t in seen_tokens:
                df[t] = df.get(t, 0) + 1
        n = max(len(self.entries), 1)
        self._idf = {t: math.log(1.0 + n / c) for t, c in df.items()}

    # ---- matching
    def _w(self, tok: str) -> float:
        return self._idf.get(tok, math.log(1.0 + len(self.entries)))  # unseen tokens are rare = high weight

    def _score(self, idx: int, qn: str, qt: set[str], q_weight: float) -> float:
        best = 0.0
        for pn, pt in self._phrasings[idx]:
            inter = qt & pt
            if not inter:
                continue
            iw = sum(self._w(t) for t in inter)
            pw = sum(self._w(t) for t in pt)
            dice = 2 * iw / (q_weight + pw)
            cover = iw / q_weight
            ratio = difflib.SequenceMatcher(None, qn, pn).ratio()
            best = max(best, 0.50 * dice + 0.25 * cover + 0.25 * ratio)
        kw_hits = sum(1 for k in self.entries[idx].get("keywords", []) if len(k) > 3 and _fqa_norm(k) in qn)
        return min(1.0, best + min(0.12, 0.04 * kw_hits)) if best else 0.0

    def match(self, query: str, strict: bool = False, exact_only: bool = False) -> tuple[dict[str, Any], float, str] | None:
        self.load()
        if not self.entries:
            return None
        qn = _fqa_norm(query)
        qt = set(_fqa_tokens(qn))
        if not qt:
            return None
        if qn in self._exact:
            return self.entries[self._exact[qn]], 1.0, "exact"
        if exact_only:
            return None
        q_weight = sum(self._w(t) for t in qt)
        scored = sorted(((self._score(i, qn, qt, q_weight), i) for i in range(len(self.entries))), reverse=True)
        top_s, top_i = scored[0]
        second_s = scored[1][0] if len(scored) > 1 else 0.0
        top_entry = self.entries[top_i]
        threshold = _FQA_STRICT_THRESHOLD if strict else _FQA_THRESHOLD
        # Circle / vendor / ID in the query that the matched answer does not cover => a data query, be strict.
        scope = {t for t in qn.split() if t in _FQA_SCOPE_TOKENS} | set(m.lower() for m in _FQA_ID_TOKEN.findall(query))
        if scope:
            covered = {t for _, pt in self._phrasings[top_i] for t in pt} | {
                w for k in top_entry.get("keywords", []) for w in _fqa_norm(k).split()
            }
            if scope - covered:
                threshold = _FQA_STRICT_THRESHOLD
        if top_s >= threshold and (top_s - second_s >= _FQA_MARGIN or top_s >= 0.85):
            return top_entry, round(top_s, 3), "fuzzy"
        return None


_fixed_qa = _FixedQAEngine()


# ---- Guardrails (deterministic) -------------------------------------------------
_REPORT_VERBS = re.compile(r"^\s*(show|list|give|get|find|display|fetch|count|view|pull|export)\b", re.I)

_RE_INJECTION = re.compile(
    r"(ignore|disregard|forget)\b.{0,30}\b(previous|prior|above|all)\b.{0,30}\b(instruction|prompt|rule)s?"
    r"|(print|show|reveal|repeat|tell me)\b.{0,25}\b(system|hidden|initial)\s+(prompt|instruction)s?"
    r"|\bjailbreak\b|\bdeveloper mode\b",
    re.I,
)
_RE_PRIVACY = re.compile(
    r"\b(login|log in|password|credential|credentials|access|circles?)\b.{0,40}\b(of|for|assigned to|belong\w* to)\b.{0,6}\buser\b"
    r"|\b(login details|passwords?|credentials)\b.{0,40}\buser\s+[a-z0-9._-]+"
    r"|\bcircles?\s+assigned\s+to\s+user\b",
    re.I,
)
_RE_WRITE_VERB = r"(change|chng|modify|update|set|edit|configure|push|apply|delete|remove|reboot|restart|lock|unlock|reset|fix)"
_RE_WRITE_TARGET = r"(pci|tac|earfcn|bandwidth|cell|node|parameter|param|config|configuration|vlan|ip|frequency|power|site)"
_RE_CHANGE_REQUEST = re.compile(
    rf"^\s*(?:(?:can|could|would|will)\s+you\s+|please\s+|pls\s+|just\s+|kindly\s+)*{_RE_WRITE_VERB}\b.{{0,60}}\b{_RE_WRITE_TARGET}\b"
    rf"|^\s*{_RE_WRITE_TARGET}\s+{_RE_WRITE_VERB}\b.{{0,40}}\b(to|=)\s*\d+"
    rf"|\b{_RE_WRITE_TARGET}\b.{{0,40}}\b(kar\s*do|kardo)\b",
    re.I,
)
_RE_OFF_TOPIC = re.compile(
    r"\b(cricket|ipl|football|weather|forecast|movie|film|song|joke|recipe|horoscope|stock price|bitcoin|politics|election)\b"
    r"|\bwho\s+won\b|\b(wh?ats?|what'?s)\s+the\s+scor\w*\b|\bmatch\s+(kaun|jeeta|result)\b|\baaj\s+ka\s+match\b",
    re.I,
)
# Bare follow-ups ("Only 5G", "Export", "Why?") that make no sense without a previous result.
_RE_NEEDS_CONTEXT = re.compile(
    r"^\s*(only\s+(show\s+)?[\w .-]{1,25}|give me count only|show (details|trend|changed records)|compare|explain|why\??|"
    r"export( differences| the result| result)?|(make|give me)( a)? management summary|export differences)\s*[.?!]*\s*$"
    r"|^\s*(what|why|how|explain|who|where)\b.{0,30}\b(this|these|that|those)\s+"
    r"(node|nodes|cell|cells|link|links|audit|result|results|mismatch\w*|record|records|value|values|number|computed|calculated)\b"
    r"|^\s*how was this (computed|calculated)\b",
    re.I,
)
_MSG_NEEDS_CONTEXT = (
    "I don't have a previous result in this conversation to work from. Tell me which report, circle or site you mean "
    "(for example 'Show eNodeB nodes for Delhi') and I can then filter, explain, compare or export it."
)
_VAGUE_TOKENS = frozenset(
    "show me the data give report details detail info information status dikhao please pls what is it all "
    "some any more tell do de dena kar".split()
)
_RE_ALARM_KPI = re.compile(
    r"^\s*(why|what'?s wrong|what is wrong|reason)\b.{0,40}\b(down|failing|failed|outage|not working|degrad\w*|dropp\w*|congest\w*)\b"
    r"|\b(alarms?|kpis?|counters?|throughput|drop\s*call|call\s*drop|prb\s+utili[sz]ation|rsrp|sinr)\b.{0,40}\b(cell|site|node)\b",
    re.I,
)
_RE_3G = re.compile(r"\b(3g|umts|wcdma|hspa|nodeb|rnc)\b(?!\s*b\b)", re.I)
_RE_PCI_CONFLICT = re.compile(r"\bpci\b.{0,30}\b(conflict|collision|clash|confusion|plan\w*)\b|\b(conflict|collision)\b.{0,30}\bpci\b", re.I)
_RE_VENDOR_EQUIV = re.compile(
    r"\b(equivalent|mapping|map|corresponding)\b.{0,50}\b(ericsson|nokia|huawei|zte|samsung)\b|"
    r"\b(ericsson|nokia|huawei|zte|samsung)\b.{0,50}\b(equivalent|corresponding)\b",
    re.I,
)

_MSG_READ_ONLY = (
    "NETIQ is a read-only platform: it audits and reports on your network inventory, but it cannot change, push or write "
    "configuration (for example PCI, TAC or any cell/node parameter) to the network. Please raise this with your OSS / "
    "network operations team through the normal change process. Once the value is corrected at source it will appear in "
    "NETIQ after the next collection cycle, and I can then show you the updated inventory or audit result."
)
_MSG_OFF_TOPIC = (
    "I can only help with NETIQ network inventory, audit, service-stitching and platform questions, so I can't help with "
    "that. You could try, for example, 'Show eNodeB nodes for Delhi' or 'What is service stitching?'."
)
_MSG_INJECTION = (
    "I can't share or change my instructions. I answer NETIQ network inventory, audit and platform questions only - "
    "what would you like to look up?"
)
_MSG_PRIVACY = (
    "I cannot share another user's login details, credentials or circle assignments. Access questions are handled by your "
    "NETIQ administrator (Admin / Super Admin), who manages roles and circle access centrally."
)
_MSG_AMBIGUOUS = (
    "Could you tell me a little more? Which circle, site or domain (RAN, MW/UBR, FTTH, Wireline) and which report or "
    "audit would you like to see?"
)
_MSG_ALARM_KPI = (
    "SCOPE_LIMIT: NETIQ does not hold alarm or KPI/performance data, so it cannot tell why a cell is down or degraded. "
    "It audits configuration and inventory from CM dumps. For fault or performance analysis please use your alarm / PM "
    "system; in NETIQ I can show the cell's inventory, audit findings and service path."
)
_MSG_3G = (
    "SCOPE_LIMIT: NETIQ covers 2G, 4G and 5G radio, microwave/UBR, FTTH and Wireline. 3G (UMTS/RNC) data is not held in NETIQ."
)
_MSG_PCI_CONFLICT = (
    "SCOPE_LIMIT: NETIQ audits PCI values as cell attributes (for example missing or duplicate configuration), but it does not "
    "run PCI conflict / collision-risk or RF planning analysis. Use your RF planning tool for that."
)
_MSG_VENDOR_EQUIV = (
    "INSUFFICIENT_EVIDENCE: a vendor-to-vendor parameter equivalence (for example Ericsson to Nokia) is not loaded as an approved "
    "mapping in the NETIQ knowledge base, so I will not guess one. Name the exact parameter and refer to the Ericsson / Nokia "
    "Attributes and Mapping documents, or ask your NETIQ administrator to add the approved mapping."
)


def _guard_reply(query: str) -> tuple[str, str, str, str] | None:
    """Return (status, answer, agent, response_type) for policy / scope guards, else None."""
    q = query.strip()
    ql = q.lower()
    if _RE_INJECTION.search(q):
        return "NO_MATCH", _MSG_INJECTION, "POLICY_GUARD", "RT-06"
    if _RE_PRIVACY.search(q):
        return "NO_MATCH", _MSG_PRIVACY, "POLICY_GUARD", "RT-12"
    if _RE_CHANGE_REQUEST.search(q) and not re.match(r"^\s*(show|list|what|which|how|where|why|who|find|get|give|display)\b", ql):
        return "NO_MATCH", _MSG_READ_ONLY, "POLICY_GUARD", "RT-12"
    if _RE_OFF_TOPIC.search(q) and not re.search(r"\b(netiq|cell|node|site|circle|audit|stitch)\w*", ql):
        return "NO_MATCH", _MSG_OFF_TOPIC, "POLICY_GUARD", "RT-06"
    return None


def _scope_reply(query: str) -> tuple[str, str, str, str] | None:
    """Scope-limit answers for question-form queries about data NETIQ does not hold."""
    q = query.strip()
    if _REPORT_VERBS.match(q) and not re.search(r"\bpci\b.*\b(conflict|collision)", q, re.I):
        return None
    if _FQA_ID_TOKEN.search(q):  # a concrete site / cell / node id means a data question, not a scope question
        return None
    if _RE_PCI_CONFLICT.search(q):
        return "NO_MATCH", _MSG_PCI_CONFLICT, "SCOPE_GUARD", "RT-05"
    if _RE_VENDOR_EQUIV.search(q):
        return "NO_MATCH", _MSG_VENDOR_EQUIV, "SCOPE_GUARD", "RT-04"
    if _RE_ALARM_KPI.search(q):
        return "NO_MATCH", _MSG_ALARM_KPI, "SCOPE_GUARD", "RT-05"
    if re.search(r"\b3g\b|\bumts\b|\bwcdma\b|\brnc\b", q, re.I) and re.match(r"^\s*(which|what|where|how|why|is|are|does|do)\b", q, re.I):
        # 3G data questions only; definition questions (e.g. "Explain RNC relationship") go to the knowledge agent.
        if re.search(r"\b(cells?|sites?|nodes?|carrier|inventory|data|audit)\b", q, re.I):
            return "NO_MATCH", _MSG_3G, "SCOPE_GUARD", "RT-05"
    return None


def _is_vague(query: str) -> bool:
    toks = re.findall(r"[a-z]+", query.lower())
    return bool(toks) and len(toks) <= 5 and all(t in _VAGUE_TOKENS for t in toks)



class ChatService:
    """Orchestrates chat queries into standardized, verified ChatResponse payloads."""

    def __init__(self, retrieval_service: ReportRetrievalService | None = None) -> None:
        self.retrieval = retrieval_service or ReportRetrievalService()
        self.auth_service = AuthorizationService()

    def _get_report_meta(self, report_id: str) -> dict[str, Any]:
        try:
            catalog = load_catalog_config()
            for r in catalog.get("reports", []):
                if r.get("id") == report_id:
                    return r
        except Exception:
            pass
        return {}

    # ------------------------------------------------------------------
    # Step 0: fixed Q&A + guardrails (deterministic, runs before routing)
    # ------------------------------------------------------------------
    def _handle_fixed_qa(
        self,
        request: ChatRequest,
        user: UserContext,
        session_id: str,
        session_state: Any,
        t0: float,
    ) -> ChatResponse | None:
        query = request.query.strip()
        q_lower = query.lower()

        def _respond(
            status: str,
            answer: str,
            agent: str,
            sources: list[SourceReference] | None = None,
            warnings: list[str] | None = None,
            limitations: list[str] | None = None,
        ) -> ChatResponse:
            default_result_store.update_session(
                session_id=session_id,
                owner_username=user.username,
                user_question=request.query,
                assistant_answer=answer,
            )
            return ChatResponse(
                request_id=request.request_id,
                session_id=session_id,
                status=status,
                intent="KNOWLEDGE",
                agent=agent,
                answer=answer,
                sources=sources or [],
                warnings=warnings or [],
                limitations=limitations or [],
                mode=settings.netiq_api_mode.value,
                execution_time_ms=int((time.perf_counter() - t0) * 1000),
            )

        # A. Policy guards: prompt-injection, other users' data, change requests, off-topic
        guard = _guard_reply(query)
        if guard:
            status, answer, agent, _rt = guard
            return _respond(status, answer, agent)

        # A2. Bare follow-ups with no previous result to refer to -> ask for context
        if not session_state.last_result_id and _RE_NEEDS_CONTEXT.search(query):
            return _respond("AMBIGUOUS", _MSG_NEEDS_CONTEXT, "CLARIFY_AGENT")

        # B. Follow-up filters on a live result are handled by the data path, not the FAQ
        is_followup_filter = bool(session_state.last_result_id) and q_lower.startswith(
            ("show only ", "filter ", "only ")
        )
        if not is_followup_filter:
            strict = (
                q_lower.startswith(_FQA_STRICT_START)
                or not _FQA_QUESTION_START.search(query)
                or bool(_FQA_DATA_REQUEST.search(query))
                or bool(_FQA_DEICTIC.search(query))
            )
            hit = _fixed_qa.match(query, strict=strict, exact_only=not _FQA_QUESTION_START.search(query))
            if hit:
                entry, score, how = hit
                answer = entry["answer"].strip()
                warnings: list[str] = []
                if entry.get("type") == "deployment-specific":
                    answer += (
                        " (This value is confirmed per deployment - please verify it with your NETIQ administrator.)"
                    )
                    warnings.append("Deployment-specific: confirm the final value with your NETIQ administrator.")
                sources = [
                    SourceReference(
                        reportId=None,
                        reportName=(
                            f"{r.get('document', 'NETIQ')} {r.get('section', '')}".strip()
                        ),
                        domain=entry.get("category"),
                        mode=settings.netiq_api_mode.value,
                        docId=entry["id"],
                    )
                    for r in (entry.get("source_references") or [])[:3]
                ] or [
                    SourceReference(
                        reportName="NETIQ fixed Q&A",
                        domain=entry.get("category"),
                        mode=settings.netiq_api_mode.value,
                        docId=entry["id"],
                    )
                ]
                limitations = (
                    ["Scope limit: " + entry["question"]] if entry.get("type") == "scope-limit" else []
                )
                resp = _respond("SUCCESS", answer, "FIXED_QA_AGENT", sources, warnings, limitations)
                return resp

        # C. Scope-limit answers (data NETIQ does not hold) for question-form queries
        scope = _scope_reply(query)
        if scope:
            status, answer, agent, _rt = scope
            return _respond(status, answer, agent)

        # D. Too vague to route: ask one short clarifying question
        if _is_vague(query) and not session_state.last_result_id:
            return _respond("AMBIGUOUS", _MSG_AMBIGUOUS, "CLARIFY_AGENT")

        return None

    async def process_chat(self, request: ChatRequest, user: UserContext) -> ChatResponse:
        """Process a user chat request and return a standardized ChatResponse."""
        t0 = time.perf_counter()
        session_id = request.session_id or f"session-{uuid.uuid4().hex[:10]}"
        query = request.query.strip()
        q_lower = query.lower()

        # Merge user context with request-level circle permissions if provided
        permitted_circles = user.permitted_circles or request.user_permitted_circles or ["*"]
        roles = user.roles or request.user_roles

        # Load/verify session ownership
        session_state = default_result_store.get_or_create_session(session_id, user.username)

        # Resolve requested circle (explicit param > filters > text extraction > session state)
        requested_circle = request.circle or (request.filters.get("circle") if request.filters else None)
        extracted_circles = _extract_circles_from_text(query)
        if not requested_circle and len(extracted_circles) == 1:
            requested_circle = extracted_circles[0]

        # 0. Fixed Q&A answers and conversational guardrails (deterministic, no LLM)
        fixed = self._handle_fixed_qa(request, user, session_id, session_state, t0)
        if fixed is not None:
            return fixed

        # 1. Handle Export Follow-Up ("Export the result", "Export to Excel")
        if any(w in q_lower for w in ("export", "download excel", "xlsx")) and session_state.last_result_id:
            elapsed_ms = int((time.perf_counter() - t0) * 1000)
            return ChatResponse(
                request_id=request.request_id,
                session_id=session_id,
                result_id=session_state.last_result_id,
                status="SUCCESS",
                intent="EXPORT",
                agent="EXPORT_TOOL",
                answer=(
                    f"Verified result '{session_state.last_result_id}' is ready for Excel export. "
                    "Use the Export button or POST /v1/export to download the XLSX workbook."
                ),
                export=ExportInfo(available=True, resultId=session_state.last_result_id, formats=["XLSX"]),
                mode=settings.netiq_api_mode.value,
                execution_time_ms=elapsed_ms,
            )

        # 2. Handle Comparison Queries (e.g. "Compare RAN inventory between Delhi and Haryana")
        if "compare" in q_lower and (len(extracted_circles) >= 2 or (len(extracted_circles) == 1 and session_state.last_circle)):
            target_circles = (
                extracted_circles[:2]
                if len(extracted_circles) >= 2
                else [session_state.last_circle, extracted_circles[0]]
            )
            return await self._handle_comparison(
                request=request,
                user=user,
                session_id=session_id,
                circles=[c for c in target_circles if c],
                permitted_circles=permitted_circles,
                roles=roles,
                last_report_id=session_state.last_report_id,
                t0=t0,
            )

        # 3. Handle Follow-Up Filter on Previous Result (e.g. "Show only Ericsson")
        if session_state.last_result_id and any(
            q_lower.startswith(prefix) for prefix in ("show only ", "filter ", "only ")
        ):
            return await self._handle_followup_filter(
                request=request,
                user=user,
                session_id=session_id,
                last_result_id=session_state.last_result_id,
                permitted_circles=permitted_circles,
                t0=t0,
            )

        # 4. Handle Knowledge Questions
        if any(kw in q_lower for kw in ("explain", "difference between", "what is", "what happens", "sop-", "cplane", "uplane", "rsrp")) or (
            "severity" in q_lower and not q_lower.startswith(_FQA_STRICT_START)
        ):
            return await self._handle_knowledge(request, user, session_id, t0)

        # 5. Authorize Circle before Report Execution
        try:
            authorized_circle = self.auth_service.authorize_report_query(
                user_permitted_circles=permitted_circles,
                requested_circle=requested_circle,
                user_roles=roles,
            )
        except UnauthorizedCircleError as err:
            raise PermissionError(str(err)) from err
        except AuthorizationError as err:
            raise PermissionError(str(err)) from err

        # 6. Resolve Report ID (explicit filter > ReportSelector)
        explicit_report_id = (request.filters or {}).get("report_id")
        if explicit_report_id:
            report_id = explicit_report_id
            rep_meta = self._get_report_meta(report_id)
            if not rep_meta:
                elapsed_ms = int((time.perf_counter() - t0) * 1000)
                return ChatResponse(
                    request_id=request.request_id,
                    session_id=session_id,
                    status="NO_MATCH",
                    intent="REPORT",
                    agent="REPORT_SELECTOR",
                    answer=f"Report ID '{report_id}' does not exist in the verified catalog.",
                    mode=settings.netiq_api_mode.value,
                    execution_time_ms=elapsed_ms,
                )
        else:
            sel = default_report_selector.select_report(query)
            if sel.status == "NO_MATCH":
                elapsed_ms = int((time.perf_counter() - t0) * 1000)
                return ChatResponse(
                    request_id=request.request_id,
                    session_id=session_id,
                    status="NO_MATCH",
                    intent="REPORT",
                    agent="REPORT_SELECTOR",
                    answer=sel.explanation or "No registered NETIQ report matched your question.",
                    mode=settings.netiq_api_mode.value,
                    execution_time_ms=elapsed_ms,
                )
            if sel.status == "AMBIGUOUS":
                elapsed_ms = int((time.perf_counter() - t0) * 1000)
                return ChatResponse(
                    request_id=request.request_id,
                    session_id=session_id,
                    status="AMBIGUOUS",
                    intent="REPORT",
                    agent="REPORT_SELECTOR",
                    answer=(
                        f"Your question matches multiple candidate reports: {', '.join(sel.candidate_ids)}. "
                        "Please select a specific report in the sidebar or clarify your request."
                    ),
                    mode=settings.netiq_api_mode.value,
                    warnings=[sel.explanation] if sel.explanation else [],
                    execution_time_ms=elapsed_ms,
                )
            report_id = sel.report_id
            rep_meta = self._get_report_meta(report_id)

        # 7. Retrieve Report Data via ReportRetrievalService
        page_num = int((request.pagination or {}).get("page", 0))
        page_size = int((request.pagination or {}).get("size", 50))
        applied_filters = dict(request.filters or {})
        if authorized_circle:
            applied_filters["circle"] = authorized_circle

        report_query = ReportQuery(
            report_id=report_id,
            circle=authorized_circle,
            filters=applied_filters,
            page=page_num,
            size=page_size,
        )

        page_result = await self.retrieval.get_single_page(
            query=report_query,
            user_permitted_circles=permitted_circles,
            correlation_id=request.request_id,
        )

        # Optional grouping if asked "grouped by vendor"
        rows = list(page_result.data)
        group_summary_metrics: list[MetricCard] = []
        if "grouped by vendor" in q_lower and rows and any("vendor" in r for r in rows):
            counts: dict[str, int] = {}
            for r in rows:
                v = str(r.get("vendor") or "Unknown")
                counts[v] = counts.get(v, 0) + 1
            rows = [{"vendor": v, "recordCount": c} for v, c in sorted(counts.items(), key=lambda x: -x[1])]
            group_summary_metrics.append(MetricCard(label="Distinct Vendors", value=len(rows)))

        columns = _build_columns(rows)
        total_records = page_result.pagination.totalRecords if page_result.pagination.totalRecords is not None else len(rows)

        metrics = [
            MetricCard(label="Returned Records", value=len(rows)),
            MetricCard(label="Total Records", value=total_records),
            *group_summary_metrics,
        ]

        report_name = rep_meta.get("name") or report_id
        domain = rep_meta.get("domain") or page_result.domain
        source_ref = SourceReference(
            reportId=report_id,
            reportName=report_name,
            circle=page_result.circle or authorized_circle,
            domain=domain,
            dataVersion=page_result.source.dataVersion,
            dataAsOf=page_result.source.dataAsOf,
            mode=page_result.source.mode.value,
        )

        saved = default_result_store.save_result(
            owner_username=user.username,
            report_id=report_id,
            report_name=report_name,
            circle=source_ref.circle,
            domain=domain,
            columns=columns,
            rows=rows,
            sources=[source_ref],
            applied_filters=applied_filters,
            data_version=source_ref.dataVersion,
            data_as_of=source_ref.dataAsOf,
            mode=source_ref.mode,
        )

        circle_str = f" for circle '{source_ref.circle}'" if source_ref.circle else ""
        if not rows:
            answer = f"No records found for '{report_name}'{circle_str}."
        else:
            answer = f"Retrieved {len(rows)} records for '{report_name}'{circle_str} (Total matching: {total_records})."

        warnings: list[str] = []
        if source_ref.mode == "MOCK":
            warnings.append("MOCK mode active: data is served from offline synthetic test fixtures.")
        if not source_ref.dataAsOf:
            warnings.append("Data date unavailable from source.")

        ResponseVerifier.verify_provenance_honesty(answer, source_ref.mode)
        evidence_item = ResponseVerifier.create_evidence_from_page(page_result)

        default_result_store.update_session(
            session_id=session_id,
            owner_username=user.username,
            user_question=query,
            assistant_answer=answer,
            report_id=report_id,
            report_name=report_name,
            circle=source_ref.circle,
            domain=domain,
            result_id=saved.result_id,
            filters=applied_filters,
        )

        elapsed_ms = int((time.perf_counter() - t0) * 1000)
        return ChatResponse(
            request_id=request.request_id,
            session_id=session_id,
            result_id=saved.result_id,
            status=page_result.status.value,
            intent="REPORT",
            agent="REPORT_AGENT",
            answer=answer,
            metrics=metrics,
            table=TablePayload(
                columns=columns,
                rows=rows,
                pagination=ReportPagination(
                    page=page_num,
                    size=page_size,
                    returnedRecords=len(rows),
                    totalRecords=total_records,
                    hasNext=page_result.pagination.hasNext,
                ),
            ),
            sources=[source_ref],
            export=ExportInfo(available=True, resultId=saved.result_id, formats=["XLSX"]),
            execution_time_ms=elapsed_ms,
            warnings=warnings,
            structured_data=rows,
            report_id=report_id,
            applied_filters=applied_filters,
            source_api=page_result.source.endpoint,
            evidence=[evidence_item],
            data_version=source_ref.dataVersion,
            data_freshness=source_ref.dataAsOf,
            mode=source_ref.mode,
            pagination=page_result.pagination,
            limitations=warnings,
        )

    async def _handle_knowledge(
        self,
        request: ChatRequest,
        user: UserContext,
        session_id: str,
        t0: float,
    ) -> ChatResponse:
        docs = _load_knowledge_docs()
        q_tokens = set(re.findall(r"[a-z0-9-]+", request.query.lower()))
        scored: list[tuple[int, KnowledgeDocument]] = []
        for doc in docs:
            doc_tokens = set(re.findall(r"[a-z0-9-]+", f"{doc.doc_id} {doc.title} {doc.content}".lower()))
            overlap = len(q_tokens.intersection(doc_tokens))
            if overlap > 0:
                scored.append((overlap, doc))
        scored.sort(key=lambda x: x[0], reverse=True)
        top_docs = [d for _, d in scored[:2]]

        if not top_docs:
            elapsed_ms = int((time.perf_counter() - t0) * 1000)
            return ChatResponse(
                request_id=request.request_id,
                session_id=session_id,
                status="NO_MATCH",
                intent="KNOWLEDGE",
                agent="KNOWLEDGE_AGENT",
                answer="INSUFFICIENT_EVIDENCE: No approved local knowledge documents matched your question.",
                mode=settings.netiq_api_mode.value,
                execution_time_ms=elapsed_ms,
            )

        # Deterministic threshold check first, then LLM if available, with safe grounded fallback
        det_sev, det_rule = default_knowledge_agent.evaluate_threshold_rule(
            request.query,
            "\n".join(d.content for d in top_docs),
        )
        try:
            k_ans = await default_knowledge_agent.answer_question(request.query, documents=top_docs)
            answer_text = k_ans.answer
            cited = k_ans.cited_sources
        except Exception:
            # Offline fallback when Ollama daemon is not running: return strictly grounded excerpt
            if det_sev:
                answer_text = f"[{top_docs[0].doc_id}] {det_rule}. {top_docs[0].content}"
            else:
                answer_text = f"[{top_docs[0].doc_id}] {top_docs[0].content}"
            cited = [top_docs[0].doc_id]

        sources = [
            SourceReference(
                reportId=None,
                reportName=d.title,
                domain=d.domain,
                mode=settings.netiq_api_mode.value,
                docId=d.doc_id,
            )
            for d in top_docs if d.doc_id in cited
        ]

        default_result_store.update_session(
            session_id=session_id,
            owner_username=user.username,
            user_question=request.query,
            assistant_answer=answer_text,
        )

        elapsed_ms = int((time.perf_counter() - t0) * 1000)
        return ChatResponse(
            request_id=request.request_id,
            session_id=session_id,
            status="SUCCESS",
            intent="KNOWLEDGE",
            agent="KNOWLEDGE_AGENT",
            answer=answer_text,
            sources=sources,
            mode=settings.netiq_api_mode.value,
            execution_time_ms=elapsed_ms,
        )

    async def _handle_followup_filter(
        self,
        request: ChatRequest,
        user: UserContext,
        session_id: str,
        last_result_id: str,
        permitted_circles: list[str],
        t0: float,
    ) -> ChatResponse:
        try:
            prev = default_result_store.get_result(
                result_id=last_result_id,
                username=user.username,
                is_admin=user.is_admin,
                permitted_circles=permitted_circles,
            )
        except (ResultNotFoundError, ResultAccessDeniedError) as err:
            raise PermissionError(str(err)) from err

        # Extract filter keyword (e.g., "show only ericsson" -> "ericsson")
        filter_term = re.sub(r"^(show\s+only|filter\s+by|filter|only)\s+", "", request.query.strip(), flags=re.IGNORECASE).strip().lower()
        filtered_rows = [
            r for r in prev.rows
            if any(filter_term in str(v).lower() for v in r.values() if v is not None)
        ]

        new_filters = dict(prev.applied_filters)
        new_filters["followup_filter"] = filter_term

        saved = default_result_store.save_result(
            owner_username=user.username,
            report_id=prev.report_id,
            report_name=prev.report_name,
            circle=prev.circle,
            domain=prev.domain,
            columns=prev.columns,
            rows=filtered_rows,
            sources=prev.sources,
            applied_filters=new_filters,
            data_version=prev.data_version,
            data_as_of=prev.data_as_of,
            mode=prev.mode,
        )

        answer = f"Filtered '{prev.report_name}' for '{filter_term}': {len(filtered_rows)} matching records."
        default_result_store.update_session(
            session_id=session_id,
            owner_username=user.username,
            user_question=request.query,
            assistant_answer=answer,
            result_id=saved.result_id,
            filters=new_filters,
        )

        elapsed_ms = int((time.perf_counter() - t0) * 1000)
        return ChatResponse(
            request_id=request.request_id,
            session_id=session_id,
            result_id=saved.result_id,
            status="SUCCESS" if filtered_rows else "EMPTY",
            intent="REPORT",
            agent="REPORT_AGENT",
            answer=answer,
            metrics=[
                MetricCard(label="Filtered Records", value=len(filtered_rows)),
                MetricCard(label="Previous Records", value=len(prev.rows)),
            ],
            table=TablePayload(
                columns=prev.columns,
                rows=filtered_rows,
                pagination=ReportPagination(
                    page=0,
                    size=50,
                    returnedRecords=len(filtered_rows),
                    totalRecords=len(filtered_rows),
                    hasNext=False,
                ),
            ),
            sources=prev.sources,
            export=ExportInfo(available=True, resultId=saved.result_id, formats=["XLSX"]),
            mode=prev.mode,
            structured_data=filtered_rows,
            report_id=prev.report_id,
            applied_filters=new_filters,
            execution_time_ms=elapsed_ms,
        )

    async def _handle_comparison(
        self,
        request: ChatRequest,
        user: UserContext,
        session_id: str,
        circles: list[str],
        permitted_circles: list[str],
        roles: list[str],
        last_report_id: str | None,
        t0: float,
    ) -> ChatResponse:
        # Authorize every requested circle independently
        authorized_circles: list[str] = []
        for c in circles:
            auth_c = self.auth_service.authorize_report_query(
                user_permitted_circles=permitted_circles,
                requested_circle=c,
                user_roles=roles,
            )
            if auth_c:
                authorized_circles.append(auth_c)

        sel = default_report_selector.select_report(request.query)
        report_id = (
            (request.filters or {}).get("report_id")
            or (sel.report_id if sel.status == "MATCH" else None)
            or last_report_id
            or "RAN_CELL_4G"
        )
        rep_meta = self._get_report_meta(report_id)
        report_name = rep_meta.get("name") or report_id
        domain = rep_meta.get("domain")

        comparison_rows: list[dict[str, Any]] = []
        sources: list[SourceReference] = []
        metrics: list[MetricCard] = []

        for c in authorized_circles:
            q = ReportQuery(report_id=report_id, circle=c, filters={"circle": c}, page=0, size=50)
            page_res = await self.retrieval.get_single_page(q, user_permitted_circles=permitted_circles)
            total = page_res.pagination.totalRecords if page_res.pagination.totalRecords is not None else len(page_res.data)
            comparison_rows.append({
                "circle": c,
                "reportId": report_id,
                "returnedRecords": len(page_res.data),
                "totalRecords": total,
                "dataVersion": page_res.source.dataVersion,
            })
            metrics.append(MetricCard(label=f"{c} Total", value=total))
            sources.append(
                SourceReference(
                    reportId=report_id,
                    reportName=report_name,
                    circle=c,
                    domain=domain,
                    dataVersion=page_res.source.dataVersion,
                    dataAsOf=page_res.source.dataAsOf,
                    mode=page_res.source.mode.value,
                )
            )

        columns = _build_columns(comparison_rows)
        mode_val = sources[0].mode if sources else settings.netiq_api_mode.value
        saved = default_result_store.save_result(
            owner_username=user.username,
            report_id=report_id,
            report_name=f"{report_name} (Comparison)",
            circle=",".join(authorized_circles),
            domain=domain,
            columns=columns,
            rows=comparison_rows,
            sources=sources,
            applied_filters={"circles": authorized_circles},
            data_version=sources[0].dataVersion if sources else None,
            data_as_of=sources[0].dataAsOf if sources else None,
            mode=mode_val,
        )

        answer = f"Comparison of '{report_name}' across circles: {', '.join(authorized_circles)}."
        default_result_store.update_session(
            session_id=session_id,
            owner_username=user.username,
            user_question=request.query,
            assistant_answer=answer,
            report_id=report_id,
            report_name=report_name,
            circle=authorized_circles[0] if authorized_circles else None,
            domain=domain,
            result_id=saved.result_id,
        )

        elapsed_ms = int((time.perf_counter() - t0) * 1000)
        return ChatResponse(
            request_id=request.request_id,
            session_id=session_id,
            result_id=saved.result_id,
            status="SUCCESS",
            intent="COMPARISON",
            agent="COMPARISON_AGENT",
            answer=answer,
            metrics=metrics,
            table=TablePayload(
                columns=columns,
                rows=comparison_rows,
                pagination=ReportPagination(
                    page=0,
                    size=50,
                    returnedRecords=len(comparison_rows),
                    totalRecords=len(comparison_rows),
                    hasNext=False,
                ),
            ),
            sources=sources,
            export=ExportInfo(available=True, resultId=saved.result_id, formats=["XLSX"]),
            mode=mode_val,
            structured_data=comparison_rows,
            report_id=report_id,
            execution_time_ms=elapsed_ms,
        )


default_chat_service = ChatService()
