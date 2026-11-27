# NETIQ AI Chatbot - Fixed Question & Answer Knowledge Base

**Product:** NETIQ - Network Intelligence & Quality (Avendum Technologies Private Limited)  
**Version:** 1.0  |  **Generated:** 2026-11-27  |  **Total Q&A entries:** 199  
**Audience:** Technical staff of the operator (Airtel): NOC, operations, audit, planning, administrators and management

**Source documents**

- NETIQ Solution Document v3.3 (2026-10-04) - `NETIQ_Solution_Document_v3_3_04-10-2026.pdf`
- NETIQ User Manual & Operations Guide (Avendum) v3.5 (2026-10-04) - `NETIQ_User_Manual_Avendum_v3_5_04-10-2026.pdf`

## How the chatbot should use this knowledge base

- Answer only from the 'answer' field of the best-matching entry; match on 'question', 'alternate_questions' and 'keywords'.
- Entries with type 'deployment-specific' describe items the documents leave to be confirmed per deployment (server specs, SLAs, RPO/RTO, support contacts, SSO/MFA, retention). Give the stated answer and tell the user to confirm the final value with their NETIQ administrator or Avendum.
- Entries with type 'scope-limit' describe what NETIQ does not do today. State the limitation plainly and do not imply the capability exists.
- AI Intelligence dashboards are BETA: remind users to validate counts and model outputs before treating them as a source of truth.
- Sample counts and figures in the source documents are illustrative; never present them as the user's live data.
- If no entry matches, say the information is not in the NETIQ documentation and suggest contacting the NETIQ administrator or Avendum support. Do not invent values, thresholds or contact details.
- Cite the source_references (document and section) when the user asks where an answer comes from.

**Entry types:** `concept` = Explains what something is or why it exists; `how-to` = Step-oriented guidance for using the console; `reference` = Lists, fields, tables or definitions to look up; `design-rule` = Exact logic, thresholds or algorithm rules; `troubleshooting` = Symptom-to-action guidance; `scope-limit` = What NETIQ does not do today / roadmap; `deployment-specific` = Value set or confirmed per deployment

## Contents

- **Platform Overview** (GEN) - 12 entries: What NETIQ is, the problems it solves, who uses it and how the data model is organised.
- **Scope, Limitations & Roadmap** (SCP) - 8 entries: What NETIQ does not do today and what is planned for later phases.
- **Architecture, Deployment & Technology** (ARC) - 12 entries: Logical architecture, components, deployment model, sizing and performance.
- **Data Collection, Ingestion & Delta Import** (ING) - 12 entries: How CM dumps are collected, validated, loaded and counted.
- **Access, Roles & Security** (SEC) - 9 entries: Login, roles, RBAC, SSO/MFA and governance.
- **Navigation, Filters & Search** (UI) - 12 entries: Using the console frame, filters, grids, Catchy Search / Smart Filter and the Platform Tour.
- **Dashboards & KPIs** (DSH) - 13 entries: Reading the RAN, Transport, MW and UBR dashboards.
- **RAN Audits & Validation Rules** (AUD) - 16 entries: Validation, Duplicate and Mapping audits in the Network Health Scorecard.
- **MW, UBR & Transport Audits** (TXN) - 8 entries: Microwave/UBR link validation, planned-vs-configured and transport audit details.
- **E2E Service Stitching Logic** (STI) - 28 entries: How every RAN service is traced from RAN to Core: inputs, parent TX discovery, hop chain, L2/AGW, Core, link naming and labels.
- **AI Audit Engine for Stitching** (AIA) - 12 entries: Gap detection and auto-suggestion for Partial and Unresolved services.
- **Stitch Status, Confidence Score & Flags** (SCR) - 8 entries: How stitching quality is scored and what each state and flag means.
- **AI Inference & AI Intelligence (BETA)** (AIN) - 13 entries: AI Insights Engine, inference accuracy and the eight AI/ML audit dashboards.
- **Inventory Repository, Reports & Decommission Ledger** (INV) - 8 entries: Network Truth Repository, report schemas and retired-asset history.
- **Operations, Monitoring, Support & DR** (OPS) - 9 entries: Daily routines, support tiers, backup/DR and items that are deployment-specific.
- **KPIs, Acceptance & Testing** (KPI) - 3 entries: Acceptance criteria, test cases and how delivery is signed off.
- **Troubleshooting & Common Issues** (TRB) - 8 entries: Typical user problems and what to do.
- **Glossary & Definitions** (GLO) - 8 entries: Short definitions of NETIQ and telecom terms used in the documents.

---

## Platform Overview (GEN)

_What NETIQ is, the problems it solves, who uses it and how the data model is organised._

### Q: What is NETIQ?

**ID:** NETIQ-GEN-001 | **Audience:** All | **Type:** concept

**Answer:** NETIQ (Network Intelligence & Quality) is an AI-powered audit and intelligence platform from Avendum Technologies. It collects configuration-management (CM) dumps from every domain's NMS/EMS, normalises them into one common data model, audits them against configurable rules, and stitches the result into a single end-to-end picture from radio cell to core. It does not replace existing systems; it sits above them and reconciles them.

**Also asked as:** "What does NETIQ do?" / "Give me an overview of NETIQ" / "What is Network Intelligence & Quality?"

**Keywords:** NETIQ, overview, audit, stitching, CM dump, single source of truth

**Source:** NETIQ Solution Document v3.3 Executive Summary, §1; NETIQ User Manual v3.5 §1.2

---

### Q: What problems does NETIQ solve for the operator?

**ID:** NETIQ-GEN-002 | **Audience:** All | **Type:** concept

**Answer:** It addresses five problems: (1) the 'illusion of accuracy' where NMS/OSS data is used without verification; (2) legacy/ghost elements that stay active after decommissioning; (3) incorrect site/node linkages that break fault isolation; (4) conflicting data across Excel sheets and vendor files; and (5) the lack of a deep audit engine, because NMS tools are built for operations, not cross-validation of topology.

**Also asked as:** "Why do we need NETIQ?" / "What are the problems with current NMS data?" / "What gaps does NETIQ close?"

**Keywords:** problem statement, ghost elements, illusion of accuracy, conflicting data, linkages

**Source:** NETIQ Solution Document v3.3 §2.1-2.5

---

### Q: Does NETIQ replace our existing NMS, EMS or OSS?

**ID:** NETIQ-GEN-003 | **Audience:** All | **Type:** scope-limit

**Answer:** No. NETIQ operates independently of live OSS and sits above the existing systems. It consumes their exports (CM dumps), reconciles them and gives a single trustworthy view. It is read-and-reconcile only and never writes configuration back to the network.

**Also asked as:** "Is NETIQ an NMS replacement?" / "Will NETIQ change our OSS?" / "Does NETIQ push configuration to the network?"

**Keywords:** replace NMS, OSS, read-only, reconcile, no write-back

**Source:** NETIQ Solution Document v3.3 §3.2, §6; NETIQ User Manual v3.5 §1.2.1

---

### Q: Which network domains does NETIQ cover today?

**ID:** NETIQ-GEN-004 | **Audience:** All | **Type:** reference

**Answer:** Live domains are RAN (2G/4G/5G nodes, cells, hardware, cabinet, IP, Core IP), Microwave (MW), UBR, Transport, FTTH and Wireline, plus end-to-end Service Stitching from RAN through MW/UBR/FTTH, Wireline and aggregation to the Core. The Core itself is only the stitching endpoint and is not deeply audited.

**Also asked as:** "What domains are in scope?" / "Is MW covered?" / "Is FTTH covered?" / "Is Wireline covered?"

**Keywords:** domains, RAN, MW, UBR, Transport, FTTH, Wireline, core, scope

**Source:** NETIQ Solution Document v3.3 §3.1.1; NETIQ User Manual v3.5 §1.1.1

**Related:** NETIQ-GLO-005, NETIQ-STI-004, NETIQ-AIN-004

---

### Q: Which vendors and technologies does NETIQ support?

**ID:** NETIQ-GEN-005 | **Audience:** All | **Type:** reference

**Answer:** Technologies: 2G/4G/5G radio, microwave and UBR transport, FTTH and Wireline. Vendors are multi-vendor, for example Ericsson, Nokia, Huawei, ZTE and Samsung for radio, and Ceragon (and Cambium per the manual) for microwave/UBR. Detailed attribute-mapping documents are maintained for Ericsson and Nokia. The exact vendor set per domain is confirmed per deployment.

**Also asked as:** "Does NETIQ support Huawei?" / "Which OEMs are supported?" / "Is Samsung supported?" / "Which MW vendors are supported?"

**Keywords:** vendors, Ericsson, Nokia, Huawei, ZTE, Samsung, Ceragon, Cambium, OEM

**Source:** NETIQ Solution Document v3.3 §3.1.2, §13.1; NETIQ User Manual v3.5 §1.3

---

### Q: What are the main modules of the NETIQ console?

**ID:** NETIQ-GEN-006 | **Audience:** All | **Type:** reference

**Answer:** The sidebar has six modules: Network Intelligence View (dashboards), Service Path Explorer Canvas (topology and stitching), Network Health Scorecard (audits), Network Truth Repository (normalised inventory), AI Insights Engine (inference reports) and Decommission Ledger (deleted/retired assets). The Network Intelligence View also contains AI Intelligence (BETA). Two global tools support them: Catchy Search / Smart Filter and the Platform Tour.

**Also asked as:** "What are the sections in the left menu?" / "List the NETIQ modules" / "What is in the sidebar?"

**Keywords:** modules, sidebar, Network Intelligence View, Service Path Explorer, Health Scorecard, Truth Repository, AI Insights Engine, Decommission Ledger

**Source:** NETIQ Solution Document v3.3 §3.1.7; NETIQ User Manual v3.5 §3.1

---

### Q: Who are the intended users of NETIQ?

**ID:** NETIQ-GEN-007 | **Audience:** All | **Type:** reference

**Answer:** Circle Operations, NOC/OSS teams, Audit and Inventory/Data Governance teams, Network Planning and Analytics, Administrators and management. OEMs are stakeholders because they are responsible for CM dump delivery. Each user sees only the circles and domains their role permits.

**Also asked as:** "Who uses NETIQ?" / "What roles use the tool?" / "Who are the stakeholders?"

**Keywords:** users, stakeholders, NOC, planning, audit, operations, administrators

**Source:** NETIQ Solution Document v3.3 §5; NETIQ User Manual v3.5 §1.1.2

---

### Q: What business benefits does NETIQ target?

**ID:** NETIQ-GEN-008 | **Audience:** Mgmt | **Type:** concept

**Answer:** Improve RAN inventory accuracy to 99.9% or better, reduce MTTR through better network visibility, detect and eliminate ghost/legacy elements, enforce naming and planned-configuration compliance, and reduce dependency on manual Excel-based audits. Management can also track the stitch percentage with evidence.

**Also asked as:** "What is the ROI of NETIQ?" / "What is the target inventory accuracy?" / "How does NETIQ reduce MTTR?"

**Keywords:** benefits, accuracy 99.9, MTTR, ghost, compliance, Excel

**Source:** NETIQ Solution Document v3.3 §6; NETIQ User Manual v3.5 §1.2.3

---

### Q: What is the hierarchy NETIQ uses to organise RAN inventory?

**ID:** NETIQ-GEN-009 | **Audience:** All | **Type:** concept

**Answer:** Nation, Circle, Site, Node, Cell, Attributes. Site is the anchor: every element rolls up to a Site. A Site holds one or more Nodes (eNodeB/gNodeB/SRAN), each Node holds Cells (for example 4G LNCEL, 5G NRCELL) and each Cell has attributes such as TAC, PCI, EARFCN, bandwidth and GPS. Hardware (cabinets, boards, RUs) links to both Site and Node.

**Also asked as:** "How is the inventory hierarchy structured?" / "What is a Site in NETIQ?" / "How are sites, nodes and cells related?"

**Keywords:** hierarchy, site, node, cell, attributes, anchor

**Source:** NETIQ Solution Document v3.3 §9.3.1

---

### Q: How does NETIQ assign a circle to a node or cell?

**ID:** NETIQ-GEN-010 | **Audience:** Ops | **Type:** design-rule

**Answer:** Circle is derived from the MCC/MNC defined on the node or cell class, using the 'MCC MNC Mapping' tab of the 'Reporting and Attribute Details' reference workbook. If an OSS dump contains MCC/MNC values belonging to a different circle, those sites, nodes and cells are routed to that circle.

**Also asked as:** "How are circles mapped?" / "What if a dump contains another circle's cells?" / "MCC MNC to circle mapping"

**Keywords:** circle, MCC, MNC, routing, mapping sheet

**Source:** NETIQ Solution Document v3.3 §9.3.1, §13.2, §20

---

### Q: How does NETIQ derive the Site ID?

**ID:** NETIQ-GEN-011 | **Audience:** Audit | **Type:** design-rule

**Answer:** Site ID can be derived from Node or Cell data, with Cell taking priority. If both derivations match, Site ID Source is 'Same in Cell and Node'; if they differ it is 'Cell Name'; if it comes from a static sheet or customer-approved entry it is 'Manual/Customer Approved'. Vendor-specific logic and nomenclature overrides are defined in the Ericsson and Nokia mapping documents. GPS, Cell IDs and TACs cross-validate the mapping.

**Also asked as:** "What is Site ID Source?" / "Which takes priority, cell name or node name, for Site ID?" / "How is Site ID created?"

**Keywords:** site ID, site source, cell priority, nomenclature, manual approved

**Source:** NETIQ Solution Document v3.3 §9.3.2; NETIQ User Manual v3.5 §12.3

---

### Q: What documents describe NETIQ and which is the controlling reference?

**ID:** NETIQ-GEN-012 | **Audience:** All | **Type:** reference

**Answer:** The Solution Document (v3.3) is the controlling design reference covering objective, scope, architecture, FRD, reporting schema, KPIs, test cases and NFRs. The User Manual (v3.5) is the screen-by-screen operating companion. The Technical Solution Document (v1.2) is the build-level design for development teams. The AI-driven service stitching design (updated 29-Sep-2026) is consolidated into Solution Document section 9.10.

**Also asked as:** "Where can I find the design document?" / "Which document should I read for screens?" / "What is the Technical Solution Document?"

**Keywords:** documents, solution document, user manual, technical solution, versions

**Source:** NETIQ Solution Document v3.3 References; NETIQ User Manual v3.5 §1.1.3

---

## Scope, Limitations & Roadmap (SCP)

_What NETIQ does not do today and what is planned for later phases._

### Q: What is out of scope for the current NETIQ release?

**ID:** NETIQ-SCP-001 | **Audience:** All | **Type:** scope-limit

**Answer:** Deep configuration audit of the Core (EPC/5GC); a dedicated IP/Router domain and optical/DWDM deep audit; live real-time API integration with source OSS/NMS (ingestion is file-based); integration with ticketing and external planning tools (for example ServiceNow, Remedy); automated corrective actions or closed-loop orchestration; writing configuration back to the network; and real-time fault/performance management (alarms and counters).

**Also asked as:** "What does NETIQ not do?" / "What are the limitations of NETIQ?" / "Which features are not available?"

**Keywords:** out of scope, limitations, core audit, API, ticketing, auto-remediation, FM, PM

**Source:** NETIQ Solution Document v3.3 §3.2, §33

**Related:** NETIQ-SCP-002

---

### Q: Does NETIQ do real-time alarm or performance monitoring?

**ID:** NETIQ-SCP-002 | **Audience:** NOC | **Type:** scope-limit

**Answer:** No. NETIQ audits configuration and inventory from CM dumps. It does not consume live alarms, counters or performance KPIs. Data freshness is bounded by the collection cadence, typically a daily cycle.

**Also asked as:** "Can NETIQ show live alarms?" / "Does NETIQ do PM or FM?" / "Is NETIQ real-time?"

**Keywords:** real-time, FM, PM, alarms, counters, freshness

**Source:** NETIQ Solution Document v3.3 §3.2, §4.3, §9.10.4

**Related:** NETIQ-SCP-001

---

### Q: Does NETIQ integrate with ServiceNow, Remedy or other ticketing systems?

**ID:** NETIQ-SCP-003 | **Audience:** Ops | **Type:** scope-limit

**Answer:** Not in the current scope. Integration with ticketing systems, external planning tools and other OSS/BSS systems is listed as a future-phase capability. Today, findings are exported to Excel/CSV and handed to the owning team.

**Also asked as:** "Can NETIQ raise tickets automatically?" / "Is there ITSM integration?"

**Keywords:** ticketing, ServiceNow, Remedy, integration, future phase

**Source:** NETIQ Solution Document v3.3 §3.2, §33

---

### Q: Does NETIQ provide a REST API for downstream systems?

**ID:** NETIQ-SCP-004 | **Audience:** Planning | **Type:** scope-limit

**Answer:** Not in the delivered scope today. Exposing stitching results through REST endpoints for OSS/BSS consumption is a proposed optional enhancement awaiting scope confirmation. Current outbound integration is on-demand Excel/CSV export from any report.

**Also asked as:** "Is there an API for stitching results?" / "Can other systems pull data from NETIQ?"

**Keywords:** REST API, outbound, export, enhancement, OSS BSS

**Source:** NETIQ Solution Document v3.3 §9.10.18, §11.2

---

### Q: Does NETIQ automatically fix the inventory or network configuration?

**ID:** NETIQ-SCP-005 | **Audience:** Audit | **Type:** scope-limit

**Answer:** No. NETIQ is read-and-reconcile. Fixes are made at source; the finding clears automatically once the corrected data is ingested in the next cycle. AI suggestions are surfaced for review and are not written back without acceptance. Auto-healing (promoting AI-suggested links to draft link records) is a recommended enhancement awaiting confirmation.

**Also asked as:** "Does NETIQ auto-remediate?" / "Does NETIQ correct data automatically?" / "Will AI suggestions change my inventory?"

**Keywords:** auto-remediation, auto-healing, fix at source, write back, suggestions

**Source:** NETIQ Solution Document v3.3 §3.2, §9.10.18, §18.5.9

---

### Q: Does NETIQ audit the Core network (EPC / 5GC)?

**ID:** NETIQ-SCP-006 | **Audience:** Audit | **Type:** scope-limit

**Answer:** No. The Core is referenced only as the end point of service stitching (matched through the Core IP Report). Deep configuration and inventory audit of the packet/mobile core is a future-phase item.

**Also asked as:** "Is Core audit included?" / "Can NETIQ audit MME, SGW, AMF or UPF?"

**Keywords:** core, EPC, 5GC, audit, stitching endpoint

**Source:** NETIQ Solution Document v3.3 §3.2, §33

---

### Q: What enhancements are proposed for service stitching?

**ID:** NETIQ-SCP-007 | **Audience:** Mgmt | **Type:** reference

**Answer:** Six enhancements await scope confirmation: (1) auto-healing of AI-suggested links, (2) multi-circle rollout dashboard with stitching coverage per circle, (3) REST API for stitching results, (4) historical delta tracking between stitching snapshots, (5) planning-link comparison module to detect missing deployments, and (6) a mobile map/service-status view for field engineers. Items 1, 2 and 5 are marked recommended.

**Also asked as:** "What is on the roadmap?" / "What future enhancements are planned?" / "Is there a mobile app?"

**Keywords:** enhancements, roadmap, auto-healing, mobile, API, historical delta

**Source:** NETIQ Solution Document v3.3 §9.10.18

---

### Q: What future phases are planned beyond the current platform?

**ID:** NETIQ-SCP-008 | **Audience:** Mgmt | **Type:** reference

**Answer:** Core network audit (EPC/5GC), IP/Router and optical/DWDM domains, live OSS/NMS API integration, external system integration (ticketing, planning), closed-loop automation and auto-remediation, predictive analytics (capacity forecasting and predictive anomaly detection), and extended long-term retention.

**Also asked as:** "What is in the next phase?" / "Future scope of NETIQ"

**Keywords:** future phases, roadmap, predictive analytics, retention, automation

**Source:** NETIQ Solution Document v3.3 §33

---

## Architecture, Deployment & Technology (ARC)

_Logical architecture, components, deployment model, sizing and performance._

### Q: What is the high-level architecture of NETIQ?

**ID:** NETIQ-ARC-001 | **Audience:** All | **Type:** concept

**Answer:** Five cooperating layers: Collection (scheduled collectors pull CM dumps), Ingestion & Parsing (vendor-specific parsers normalise to the common model), Intelligence & Audit (validation, duplicate, mapping and compliance rules plus AI inference), Storage (inventory, audit results, stitched paths and history) and Presentation (role-aware web console). Process flow: CM Dumps, Data Collection Layer, NETIQ, Audit & Validation, Dashboards/Reports.

**Also asked as:** "Explain the NETIQ architecture" / "What layers does NETIQ have?" / "Show me the logical architecture"

**Keywords:** architecture, layers, collection, parsing, storage, presentation

**Source:** NETIQ Solution Document v3.3 §7.1-7.2, §6

---

### Q: What are the architecture principles of NETIQ?

**ID:** NETIQ-ARC-002 | **Audience:** All | **Type:** concept

**Answer:** Single source of truth across domains; source-agnostic ingestion (vendor dialects normalised to a common model); idempotent processing (re-ingestion updates in place, never duplicates); separation of concerns across collection, intelligence, storage and presentation; and security by design with role-based access on every circle, domain and action.

**Also asked as:** "What design principles does NETIQ follow?" / "Is ingestion idempotent?"

**Keywords:** principles, idempotent, single source of truth, separation, security

**Source:** NETIQ Solution Document v3.3 §7.1

---

### Q: What components make up the NETIQ platform?

**ID:** NETIQ-ARC-003 | **Audience:** Admin | **Type:** reference

**Answer:** Collector (one profile per domain/source), Parser registry (pluggable parsers keyed by file signature), Normaliser (field mapping, types, units, controlled vocabularies), Audit engine (rule-driven, severity-tagged findings), Stitching engine (site matching then cross-domain link resolution and scoring), Inference engine (Site/Node/Cell relationships with confidence), Data store, Web application (RBAC, server-side filtering/pagination) and Scheduler (cadence, no overlapping runs).

**Also asked as:** "What are the NETIQ components?" / "What is the parser registry?" / "What does the scheduler do?"

**Keywords:** components, collector, parser, normaliser, audit engine, stitching engine, inference engine, scheduler

**Source:** NETIQ Solution Document v3.3 §7.6

---

### Q: What is the processing pipeline for each cycle?

**ID:** NETIQ-ARC-004 | **Audience:** Admin | **Type:** concept

**Answer:** The scheduler runs an ordered pipeline: collect, parse, normalise, validate, load, audit, stitch, infer and publish. Domains can run on independent cadences, but within a domain the stages run in sequence so audits and stitching always work on a fully loaded inventory. The scheduler prevents overlapping runs for a domain and records start/end times and record counts per stage.

**Also asked as:** "How does a daily cycle run?" / "In what order does NETIQ process data?" / "Can two runs overlap?"

**Keywords:** pipeline, schedule, cycle, order, collect, parse, audit, stitch

**Source:** NETIQ Solution Document v3.3 §7.7, §10.2

---

### Q: How is NETIQ deployed and accessed?

**ID:** NETIQ-ARC-005 | **Audience:** Admin | **Type:** deployment-specific

**Answer:** NETIQ is a server-hosted, browser-accessed application with an application/web tier, a processing tier (collectors, parsers, audit and stitching engines, scheduler) and a data store, which may be co-located or separated by scale. Users open the URL provided by their administrator (example format http://<server-ip>:8095/login). No client software is installed. Exact server topology, CPU/RAM/disk and OS versions are deployment-specific and confirmed with the infrastructure team.

**Also asked as:** "How do I access NETIQ?" / "Do I need to install anything?" / "What is the NETIQ URL?" / "What are the server requirements?"

**Keywords:** deployment, web console, URL, port 8095, no client, server

**Source:** NETIQ Solution Document v3.3 §7.3, §24; NETIQ User Manual v3.5 §2.1-2.3

---

### Q: What are the client browser and screen requirements?

**ID:** NETIQ-ARC-006 | **Audience:** All | **Type:** reference

**Answer:** Use the latest Chrome, Edge or Firefox; Internet Explorer is not supported. Minimum screen 1366x768, with 1920x1080 or higher recommended for dashboards and the Service Path Explorer canvas. HTTPS access to the NETIQ URL over corporate LAN or VPN, a valid account with an assigned role, and about 8 GB RAM or more is comfortable for large inventory grids.

**Also asked as:** "Which browsers work with NETIQ?" / "Is Internet Explorer supported?" / "What screen resolution is recommended?"

**Keywords:** browser, Chrome, Edge, Firefox, resolution, requirements

**Source:** NETIQ User Manual v3.5 §2.1; NETIQ Solution Document v3.3 §24.2

---

### Q: What environments are used for NETIQ delivery?

**ID:** NETIQ-ARC-007 | **Audience:** Mgmt | **Type:** reference

**Answer:** Development (build and unit verification), UAT/Staging (customer acceptance on production-like data) and Production (live operation across in-scope circles and domains). Rollout is phased: Proof of Concept, Domain Expansion (FTTH, Wireline, Transport detail), Stitching & Analytics, then PAN-India rollout.

**Also asked as:** "What is the rollout plan?" / "Is there a UAT environment?" / "What are the delivery phases?"

**Keywords:** environments, UAT, production, phases, rollout

**Source:** NETIQ Solution Document v3.3 §24.1, §28

---

### Q: What is the technology stack of NETIQ?

**ID:** NETIQ-ARC-008 | **Audience:** Admin | **Type:** deployment-specific

**Answer:** The solution document describes the stack by layer: a browser-based web application with no client install; server-side application/API services; processing components (collector, parser, audit, stitching, scheduler); a persistent data store for inventory, audit results and stitched paths; and RBAC/authentication/session/audit-logging controls. Specific products, versions and frameworks are implementation choices recorded for the delivered build and are not fixed in the document.

**Also asked as:** "What database does NETIQ use?" / "What technology is NETIQ built on?" / "Which framework is used?"

**Keywords:** technology stack, database, framework, implementation

**Source:** NETIQ Solution Document v3.3 §7.5

---

### Q: What data volumes is NETIQ designed for?

**ID:** NETIQ-ARC-009 | **Audience:** Admin | **Type:** reference

**Answer:** Indicative discovery volumes across the estate: about 18 source NMS, 46,000+ sites, 64,000+ nodes, 629,000+ cells, 309,000+ hardware items and about 7.9 million Wireline logical records (the largest dataset). These figures are indicative and should be refreshed from the live platform for the delivered baseline.

**Also asked as:** "How many sites can NETIQ handle?" / "What is the scale of the platform?" / "How big is the Wireline dataset?"

**Keywords:** sizing, volumes, sites, nodes, cells, wireline, 7.9 million

**Source:** NETIQ Solution Document v3.3 §22.1

---

### Q: What performance and availability targets apply?

**ID:** NETIQ-ARC-010 | **Audience:** Admin | **Type:** reference

**Answer:** Parse and audit about 100,000+ cells in under 10 minutes; reports stay responsive on multi-million-row datasets through server-side filtering and pagination; console availability target of at least 99.5%; the processing tier tolerates a missed cycle without data loss because ingestion is idempotent. Targets marked indicative are confirmed and contracted per deployment.

**Also asked as:** "How fast does NETIQ process data?" / "What is the uptime target?" / "Is the system scalable?"

**Keywords:** performance, availability, 99.5, 100000 cells, 10 minutes, scalability, NFR

**Source:** NETIQ Solution Document v3.3 §21, §22.2, §23.1

---

### Q: How do rules and parsers change without code changes?

**ID:** NETIQ-ARC-011 | **Audience:** Admin | **Type:** concept

**Answer:** Vendor-neutral logic is held in external reference documents and configuration: the Ericsson and Nokia Attributes and Mapping documents and the 'Reporting and Attribute Details' workbook (report formats, mandatory attributes, Site ID rules, severity rules, MCC/MNC mapping, NMS IP/name mapping). Audit rules are kept in versioned YAML files, parsers are modular and pluggable, and ML models are versioned and validated before promotion. Changes take effect on the next cycle.

**Also asked as:** "How are audit rules configured?" / "Can we add a new vendor?" / "What is the Reporting and Attribute Details sheet?"

**Keywords:** YAML, configuration, parser, reference sheet, change management, rules

**Source:** NETIQ Solution Document v3.3 §13.1, §25, §30, §21

---

### Q: How are logging, errors and reprocessing handled?

**ID:** NETIQ-ARC-012 | **Audience:** Admin | **Type:** concept

**Answer:** Every stage logs start/end, volumes processed and rejects. Malformed records are quarantined as rejects with a reason code rather than failing the whole cycle. Because loading is an idempotent upsert on natural keys, a failed or partial cycle can be safely re-run without duplication.

**Also asked as:** "What happens if a cycle fails?" / "Are rejected records lost?" / "Can I re-run a failed cycle?"

**Keywords:** logging, error handling, rejects, reprocess, idempotent

**Source:** NETIQ Solution Document v3.3 §7.8, §11.5

---

## Data Collection, Ingestion & Delta Import (ING)

_How CM dumps are collected, validated, loaded and counted._

### Q: What data does NETIQ ingest and how often?

**ID:** NETIQ-ING-001 | **Audience:** Ops | **Type:** concept

**Answer:** The primary input is daily Configuration Management (CM) dumps from each domain's NMS/EMS, collected on a schedule per domain (for example daily). Planning/reference files are used for validation where available, and the static 'Reporting and Attribute Details' workbook supplies reference rules. Dumps are parsed, normalised into the common model, validated and loaded via idempotent upsert.

**Also asked as:** "What are the input data sources?" / "How frequently is data collected?" / "Which files does NETIQ need?"

**Keywords:** CM dump, ingestion, frequency, daily, planning data, inputs

**Source:** NETIQ Solution Document v3.3 §3.1.3, §11.1; NETIQ User Manual v3.5 §1.2.1

---

### Q: What are the steps of the daily ingestion and sync process?

**ID:** NETIQ-ING-002 | **Audience:** Ops | **Type:** concept

**Answer:** 1) Collect circle-wise CM dumps and copy them from OSS folders to the NETIQ environment; 2) vendor-specific parsers extract node, cell, hardware and attributes into a unified schema; 3) load into the central inventory database against the last baseline; 4) validate: dump-size consistency, attribute completeness (Site ID, Node ID, GPS, IP, cabinet) and duplicates. The output is a validated, normalised, site-mapped dataset that feeds all audits, reports and dashboards.

**Also asked as:** "How does NETIQ sync data?" / "Explain the ingestion flow" / "What validations run on ingestion?"

**Keywords:** ingestion steps, parsing, normalization, validation, sync

**Source:** NETIQ Solution Document v3.3 §8.2, §9.6

---

### Q: What is delta import and how are New, Updated, Removed and Total counts defined?

**ID:** NETIQ-ING-003 | **Audience:** All | **Type:** concept

**Answer:** NETIQ compares each day's dump with the previous state on the natural key and processes only the change set. Total = New + Updated + Available (unchanged) inventory; New = first seen in today's dump; Updated = changed versus last discovered values; Remove = present previously but absent today. Unchanged 'Available' records count in Total but are not reprocessed, which is the source of the performance gain.

**Also asked as:** "What do New, Updated and Deleted counts mean?" / "How is the Total count calculated?" / "Why is import fast?"

**Keywords:** delta import, total count, new count, updated count, remove count, available

**Source:** NETIQ Solution Document v3.3 §10.9; NETIQ User Manual v3.5 §4.1.5

---

### Q: What happens if the same dump is ingested twice?

**ID:** NETIQ-ING-004 | **Audience:** Admin | **Type:** concept

**Answer:** Nothing is duplicated. Loading is an idempotent upsert on natural keys (node, cell, serial or link identifiers), so re-ingesting updates records in place and counts are not inflated.

**Also asked as:** "Will re-ingesting create duplicates?" / "Is ingestion idempotent?"

**Keywords:** idempotent, re-ingest, duplicate, upsert, natural key

**Source:** NETIQ Solution Document v3.3 §7.1, §10.6, §10.9.3; NETIQ User Manual v3.5 §4.1.5

---

### Q: How does NETIQ decide whether an NMS is Updated or Non-Updated?

**ID:** NETIQ-ING-005 | **Audience:** NOC | **Type:** design-rule

**Answer:** An NMS (unique NMS IP from the reference sheet) is Updated when its dump size exceeds 10 MB and the dump date is the current date or current date minus one. It is Non-Updated when the dump exceeds 10 MB but is older than that window. NMS folders under 10 MB or 0 bytes are treated as orphan and excluded from counts. New NMS are folders not processed before. NMS with reduced dump sizes are highlighted.

**Also asked as:** "What makes an NMS non-updated?" / "What is an orphan NMS?" / "How is NMS Discovery % computed?"

**Keywords:** NMS discovery, updated, non-updated, 10 MB, orphan NMS, dump size

**Source:** NETIQ Solution Document v3.3 §13.3, §14.1

---

### Q: When does NETIQ flag a reduced dump size as an anomaly?

**ID:** NETIQ-ING-006 | **Audience:** NOC | **Type:** design-rule

**Answer:** The dump-size consistency check compares file size and record count with the previous day. For RAN, if the size reduces by more than 100 MB the record is flagged as an anomaly. NMS instances with reduced dump sizes are highlighted on dashboards and reports.

**Also asked as:** "What is the dump size check?" / "Why is my NMS highlighted?" / "Dump size reduction threshold"

**Keywords:** dump size, anomaly, 100 MB, reduced dump, consistency check

**Source:** NETIQ Solution Document v3.3 §8.2, §13.3

---

### Q: What happens to malformed or invalid records during ingestion?

**ID:** NETIQ-ING-007 | **Audience:** Ops | **Type:** concept

**Answer:** Rows failing validation (mandatory fields, types, ranges, controlled values) go to a reject store with a reason code and source reference; they are never silently dropped. A per-cycle ingestion summary records files processed, records loaded and records rejected per domain, so data owners can correct the source and have it re-ingested next cycle.

**Also asked as:** "Where do rejected rows go?" / "How do I see rejected records?"

**Keywords:** rejects, reason code, ingestion summary, malformed, quarantine

**Source:** NETIQ Solution Document v3.3 §9.6, §11.5

---

### Q: How current is the data shown in NETIQ?

**ID:** NETIQ-ING-008 | **Audience:** All | **Type:** concept

**Answer:** It reflects the last scheduled collection cycle. Check the last-updated indicator in the report footer or the status tile at the foot of the sidebar. Data freshness is bounded by the source collection cadence.

**Also asked as:** "How fresh is the data?" / "When was data last refreshed?" / "Why is the data a day old?"

**Keywords:** freshness, last updated, refresh, cycle

**Source:** NETIQ User Manual v3.5 §9 Q1, §3.3, §3.1; NETIQ Solution Document v3.3 §4.3

---

### Q: What happens if a source dump is missed or delayed?

**ID:** NETIQ-ING-009 | **Audience:** Ops | **Type:** troubleshooting

**Answer:** NETIQ tolerates a missed cycle without data loss because ingestion is idempotent. The affected NMS shows as Non-Updated on the dashboard, and the scheduler-completion record helps operations spot missing cycles. Timely, complete source exports are a stated dependency, so source SLAs should be agreed and missing cycles alerted.

**Also asked as:** "What if the OEM does not deliver the dump?" / "How do I know a cycle was missed?"

**Keywords:** missed cycle, delayed dump, scheduler, dependency, non-updated

**Source:** NETIQ Solution Document v3.3 §4.2, §21, §31

---

### Q: What happens to elements that disappear from a dump?

**ID:** NETIQ-ING-010 | **Audience:** Audit | **Type:** concept

**Answer:** Records present in the previous dump but absent today are counted as Removed (Deleted). They age out of the live inventory and are preserved in the Decommission Ledger, so history stays auditable. Retention is governed by a configurable policy.

**Also asked as:** "Where do deleted nodes go?" / "How are decommissioned elements tracked?"

**Keywords:** removed, deleted, decommission, ledger, aged out

**Source:** NETIQ Solution Document v3.3 §10.4, §10.9; NETIQ User Manual v3.5 §4.6

---

### Q: What lineage information does each record carry?

**ID:** NETIQ-ING-011 | **Audience:** Audit | **Type:** concept

**Answer:** Each record stores its originating source (NMS/EMS), site source (Cell, Node, Both or Manual) and insert/update timestamps. This lets users judge how current and trustworthy a record is, supports delta tracking between cycles and underpins the Deleted Reports view.

**Also asked as:** "How can I tell where a record came from?" / "What is provenance in NETIQ?"

**Keywords:** lineage, provenance, source, site source, timestamps

**Source:** NETIQ Solution Document v3.3 §10.8

---

### Q: How long is data retained?

**ID:** NETIQ-ING-012 | **Audience:** Admin | **Type:** deployment-specific

**Answer:** Each cycle is retained for trend and historical analysis under a configurable retention policy; the window is set per deployment (the user manual cites 180 days as an example) and administrators manage it. The purge/archival policy uses partitioned database storage and gzip archive jobs and is exposed in the UI for visibility.

**Also asked as:** "What is the retention period?" / "Can we archive old data?"

**Keywords:** retention, archive, purge, 180 days, history

**Source:** NETIQ Solution Document v3.3 §10.4, §25; NETIQ User Manual v3.5 §9 Q15

---

## Access, Roles & Security (SEC)

_Login, roles, RBAC, SSO/MFA and governance._

### Q: How do I log in to NETIQ?

**ID:** NETIQ-SEC-001 | **Audience:** All | **Type:** how-to

**Answer:** Open the NETIQ URL provided by your administrator, enter your registered user e-mail and password, and click Sign In. On success you land on the default dashboard (RAN), scoped to the circles and domains your role allows. On failure an inline error appears; re-enter credentials or use the password-reset option.

**Also asked as:** "How to sign in?" / "What is the login URL?" / "What happens after login?"

**Keywords:** login, sign in, credentials, landing page, RBAC session

**Source:** NETIQ User Manual v3.5 §2.3

---

### Q: I forgot my password. What should I do?

**ID:** NETIQ-SEC-002 | **Audience:** All | **Type:** how-to

**Answer:** Avoid repeated attempts because repeated failures may lock the account. With NETIQ's built-in login, use the Forgot Password link and follow the e-mailed reset instructions. If your organisation uses single sign-on (SSO/LDAP), reset your network password through the normal corporate process. If still locked out, contact your NETIQ administrator or the support desk.

**Also asked as:** "Reset password" / "My account is locked" / "Forgot password flow"

**Keywords:** forgot password, account lock, reset, SSO, lockout

**Source:** NETIQ User Manual v3.5 §2.3.3; NETIQ Solution Document v3.3 §25

---

### Q: What is the password and session policy?

**ID:** NETIQ-SEC-003 | **Audience:** Admin | **Type:** reference

**Answer:** Built-in login enforces a password policy (minimum length and complexity, periodic expiry, password history) and lockout after repeated failed attempts. Sessions expire after inactivity and return the user to the login screen. Logins and significant actions are logged in an audit trail retained per policy.

**Also asked as:** "How long is the session timeout?" / "Is there account lockout?" / "Are logins audited?"

**Keywords:** password policy, session timeout, lockout, audit log

**Source:** NETIQ Solution Document v3.3 §25, §21

---

### Q: Does NETIQ support SSO, LDAP and multi-factor authentication?

**ID:** NETIQ-SEC-004 | **Audience:** Admin | **Type:** deployment-specific

**Answer:** Where configured, NETIQ integrates with corporate SSO/LDAP so the network account governs access, and supports optional MFA with an authenticator app, e-mail or SMS. The user manual marks MFA as not applicable for the documented build, so confirm whether SSO/LDAP and MFA are enabled in your deployment with your administrator.

**Also asked as:** "Can we use Active Directory?" / "Is MFA available?" / "Does NETIQ integrate with LDAP?"

**Keywords:** SSO, LDAP, MFA, authentication, corporate login

**Source:** NETIQ Solution Document v3.3 §25; NETIQ User Manual v3.5 §2.3.4

---

### Q: What access roles exist in NETIQ?

**ID:** NETIQ-SEC-005 | **Audience:** Admin | **Type:** reference

**Answer:** The governance model has three tiers: Admin (PAN India; read, write, update, delete, approve; limited to product owner and super-admin), Hub Lead (multiple circles; read, update, approve; approves exceptions for Cell Name, Site ID and Node Name; no write/delete) and Circle User (read-only, scoped to one circle). The live console exposes finer roles: Super Admin, Admin, Operator, Auditor, NOC User and Read Only, which map onto those tiers.

**Also asked as:** "What are the user roles?" / "What can a Hub Lead do?" / "What is the difference between Admin and Circle User?"

**Keywords:** roles, RBAC, Admin, Hub Lead, Circle User, Super Admin, Operator, Auditor, NOC User, Read Only

**Source:** NETIQ Solution Document v3.3 §26, §3.1.7

---

### Q: Why can I see only some circles or menus?

**ID:** NETIQ-SEC-006 | **Audience:** All | **Type:** troubleshooting

**Answer:** Your role scopes you to specific circles and domains through RBAC. A message such as 'Access denied / not authorised' means the dashboard, repository or action is outside your role. If you believe you need access, ask your administrator; access is managed centrally by an Admin/Super Admin.

**Also asked as:** "Why is a menu missing?" / "How do I get more circle access?" / "Access denied error"

**Keywords:** RBAC, circle scope, access denied, permissions

**Source:** NETIQ User Manual v3.5 §9 Q2 Q17, §8.2; NETIQ Solution Document v3.3 §26

---

### Q: Can two people share one NETIQ login?

**ID:** NETIQ-SEC-007 | **Audience:** All | **Type:** concept

**Answer:** No. Each user should have their own account so that actions are attributed correctly and audit logging remains meaningful.

**Also asked as:** "Can we use a shared account?" / "One login for the team"

**Keywords:** shared login, account, attribution

**Source:** NETIQ User Manual v3.5 §9 Q16

---

### Q: Can NETIQ users modify the underlying network data?

**ID:** NETIQ-SEC-008 | **Audience:** Audit | **Type:** concept

**Answer:** Exports are read-only and do not modify source data, and NETIQ never writes configuration to the network. Corrections are made at the source system and flow in through the next CM dump. Hub Leads approve exceptions (Cell Name, Site ID, Node Name) and perform day-to-day metadata fixes; Circle Users are read-only.

**Also asked as:** "Is export read-only?" / "Who approves naming exceptions?"

**Keywords:** read-only, exceptions, approval, fix at source

**Source:** NETIQ Solution Document v3.3 §11.2, §26

---

### Q: What security and governance controls does NETIQ provide?

**ID:** NETIQ-SEC-009 | **Audience:** Admin | **Type:** reference

**Answer:** RBAC on every circle, domain and action; authentication with password policy and optional SSO/MFA; session management; audit logs of parser runs, rule changes and model promotions (version-controlled); versioned YAML rules and ML models; configurable data retention; and least-privilege role assignment with periodic access reviews as a mitigation for RBAC misconfiguration.

**Also asked as:** "Is NETIQ secure?" / "What compliance controls exist?" / "Is there an audit trail?"

**Keywords:** security, governance, audit log, RBAC, compliance

**Source:** NETIQ Solution Document v3.3 §25, §21, §31

---

## Navigation, Filters & Search (UI)

_Using the console frame, filters, grids, Catchy Search / Smart Filter and the Platform Tour._

### Q: How do I switch between RAN and Transport views?

**ID:** NETIQ-UI-001 | **Audience:** All | **Type:** how-to

**Answer:** Use the Project Hub switcher (RAN / Txn) on the top command bar. Txn opens the microwave, UBR and fibre backhaul context; the Type dropdown then narrows it to ALL, MW or UBR (it only appears with Txn). The dashboard, KPI strip, inventory tree and audit menus all re-scope, and the selection persists as you move between modules until you switch back.

**Also asked as:** "How to see MW only?" / "What is the Txn toggle?" / "What does the Type dropdown do?"

**Keywords:** RAN Txn toggle, Project Hub, Type dropdown, MW, UBR, ALL

**Source:** NETIQ User Manual v3.5 §3.2, §4.1.2

**Related:** NETIQ-AIN-004, NETIQ-DSH-009, NETIQ-GEN-004

---

### Q: How do I filter by circle and vendor?

**ID:** NETIQ-UI-002 | **Audience:** All | **Type:** how-to

**Answer:** Set Circle in the top command bar, or open the blue funnel Dashboard Filter Panel (Circle, Vendor, Apply Filters, Reset). Circle and Vendor filters are sticky for the session and carry between reports until you click Reset All. Column filters apply only to the single report you are viewing.

**Also asked as:** "How do I scope a report to my circle?" / "Do filters persist between reports?" / "How to reset filters?"

**Keywords:** circle filter, vendor filter, sticky, filter panel, reset all

**Source:** NETIQ User Manual v3.5 §3.2, §3.4, §9 Q3 Q5

---

### Q: What controls are common to every report grid?

**ID:** NETIQ-UI-003 | **Audience:** All | **Type:** reference

**Answer:** View toggle (table, card, list), Columns (show/hide), Filters (per column), Export (CSV/Excel), Advanced multi-condition query builder, column sort (multi-level), row expand for the full record, record count, pagination with rows per page, and a last-updated indicator in the footer.

**Also asked as:** "What can I do in a report?" / "How do I hide columns?" / "How do I sort?"

**Keywords:** grid controls, columns, filters, export, advanced query, pagination, row expand

**Source:** NETIQ User Manual v3.5 §3.3

**Related:** NETIQ-UI-004

---

### Q: How do I export a report?

**ID:** NETIQ-UI-004 | **Audience:** All | **Type:** how-to

**Answer:** Open the report, apply the circle/vendor/column filters and column choices you want, click Export and choose CSV or Excel. The file contains exactly the rows and columns in view and is read-only. Scope the report first to avoid exporting the whole estate. If nothing downloads, allow pop-ups and downloads for the NETIQ site.

**Also asked as:** "How to download data?" / "Export to Excel" / "Does export respect filters?"

**Keywords:** export, CSV, Excel, filters, download

**Source:** NETIQ User Manual v3.5 §5.1, §9 Q6; NETIQ Solution Document v3.3 §11.6

**Related:** NETIQ-UI-003

---

### Q: How do I find one specific node, cell or serial number?

**ID:** NETIQ-UI-005 | **Audience:** All | **Type:** how-to

**Answer:** Use the per-column filter or search on the relevant report, or open the Advanced query builder for multi-condition searches. You can also type the identifier into Catchy Search, and on the Service Path Explorer the 'Filter Site ID' search centres the canvas on any site, node or link.

**Also asked as:** "Search for a node ID" / "Find a serial number" / "Advanced search"

**Keywords:** search, find node, serial number, advanced query, filter site ID

**Source:** NETIQ User Manual v3.5 §9 Q4, §3.3, §4.2.2

---

### Q: What is Catchy Search (Smart Filter)?

**ID:** NETIQ-UI-006 | **Audience:** All | **Type:** concept

**Answer:** A command palette in the top bar that turns plain-language questions into precise checks. It offers Quick Ideas (friendly aliases for technical audits) and Smart Shortcuts (one-click deep links), then opens the matching audit or inventory report already filtered to the relevant records. In the current build it is labelled 'Smart Filter (BETA) - Powered by AI'.

**Also asked as:** "What is the search bar at the top?" / "What is Smart Filter?" / "How does AI search work?"

**Keywords:** Catchy Search, Smart Filter, command palette, quick ideas, smart shortcuts

**Source:** NETIQ Solution Document v3.3 §3.1.7, §18.7; NETIQ User Manual v3.5 §3.5

**Related:** NETIQ-UI-007

---

### Q: What are the Quick Ideas and which reports do they open?

**ID:** NETIQ-UI-007 | **Audience:** All | **Type:** reference

**Answer:** 'This link is feeling weak' opens the Degraded Link Audit; 'Lost? multiple sites forgot where they are' opens GPS Accuracy Audit/GPS Suggestion; 'Two nodes, same name' opens Duplicate Node Audit/Duplicate Resolution; 'Your plan and reality disagree' opens Planned vs Configured/Frequency Deviation; 'These cells forgot their frequency' opens Missing EARFCN; 'A node that won't leave' opens Ghost Nodes; 'Unplugged? Cells without a radio unit' opens Cell-to-RU Link Audit; 'This name doesn't follow the rules' opens Nomenclature/Site ID validation.

**Also asked as:** "List the quick ideas" / "What does 'this link is feeling weak' do?" / "Plain language prompts in NETIQ"

**Keywords:** quick ideas, prompts, smart filter, plain language, mapping

**Source:** NETIQ Solution Document v3.3 §18.7; NETIQ User Manual v3.5 §3.5.2

**Related:** NETIQ-UI-006

---

### Q: What are the Smart Shortcuts?

**ID:** NETIQ-UI-008 | **Audience:** NOC | **Type:** reference

**Answer:** Five one-click tiles: 'Critical anomalies impacting 10+ sites' (highest-impact findings ranked by site count), 'Show sites missing GPS coordinates' (GPS Accuracy Audit filtered to failures), 'Find duplicate Node IDs in network' (Duplicate Node Audit), 'List cells missing EARFCN' and 'Show ghost or legacy nodes' (Ghost Nodes report).

**Also asked as:** "What shortcuts are available?" / "How do I see critical anomalies quickly?"

**Keywords:** smart shortcuts, critical anomalies, missing GPS, duplicate node, ghost nodes

**Source:** NETIQ User Manual v3.5 §3.5.3

---

### Q: What Smart Filter prompts are available on the Service Path Explorer?

**ID:** NETIQ-UI-009 | **Audience:** NOC | **Type:** reference

**Answer:** Stitching-aware prompts include: 'Where is the edge VLAN mismatch?' (VLAN_MISMATCH / MISSING_TX_HOP), 'Edge routing discrepancy on L2/L3 hops' (MISSING_AGW, Default_AP/Default_AGW), 'Stitching paths with confidence < 80%' (Partial, Suggested, Unresolved), 'AI Inference: recommended topology fixes' (Condition 1-4 suggestions), 'Unresolved edges (missing transport nodes)' (NO_TX_NODE), and 'Fully stitched active paths (E2E verified)' (score 80 or more). Others open the animated path, the media-mix distribution or the stitching report.

**Also asked as:** "Stitching prompts in Smart Filter" / "How do I find unresolved edges?" / "Query for confidence below 80"

**Keywords:** smart filter, stitching prompts, VLAN mismatch, NO_TX_NODE, confidence, edge routing

**Source:** NETIQ Solution Document v3.3 §18.7; NETIQ User Manual v3.5 §3.5.5

---

### Q: What is the Platform Tour?

**ID:** NETIQ-UI-010 | **Audience:** All | **Type:** concept

**Answer:** A built-in interactive guided walkthrough that highlights each control in turn and explains what it does inside the live application. It covers orientation and navigation, the RAN and Transmission dashboards, inventory grids, the Network Health Scorecard and the Service Path Explorer, and is the quickest way for a new user to get oriented.

**Also asked as:** "Is there a tutorial?" / "How do new users learn the tool?" / "Guided walkthrough"

**Keywords:** platform tour, onboarding, guided walkthrough, training

**Source:** NETIQ Solution Document v3.3 §3.1.7; NETIQ User Manual v3.5 §3.6

**Related:** NETIQ-OPS-008

---

### Q: What notifications and alerts does NETIQ send?

**ID:** NETIQ-UI-011 | **Audience:** All | **Type:** reference

**Answer:** Role-aware notifications for audit findings, health/threshold breaches, AI-inference insights, scheduled-report-ready events and data-refresh completion, delivered in-app and, where enabled, by e-mail digest. Detailed notification preference screens are marked not applicable in the current user manual.

**Also asked as:** "Does NETIQ send emails?" / "How do I get alerts?" / "Notification settings"

**Keywords:** notifications, alerts, e-mail digest, thresholds

**Source:** NETIQ Solution Document v3.3 §3.1.7; NETIQ User Manual v3.5 §7

---

### Q: Are there keyboard shortcuts?

**ID:** NETIQ-UI-012 | **Audience:** All | **Type:** reference

**Answer:** NETIQ is mainly mouse-driven. Catchy Search opens the command palette (the in-app hint shows the key for your build); Esc closes dialogs, panels and the palette; F5 or Ctrl+R reloads the screen; Ctrl+F searches the current page; Ctrl +/- adjusts zoom (reset to 100% if dashboards are clipped). Availability varies by browser and deployment.

**Also asked as:** "Keyboard shortcuts" / "How to open search with keyboard?"

**Keywords:** keyboard shortcuts, Esc, F5, zoom

**Source:** NETIQ User Manual v3.5 §12.5

---

## Dashboards & KPIs (DSH)

_Reading the RAN, Transport, MW and UBR dashboards._

### Q: What does the RAN dashboard show?

**ID:** NETIQ-DSH-001 | **Audience:** NOC | **Type:** concept

**Answer:** Read top to bottom: the Discovered Inventories KPI strip (NMS, Site, Node, Cell, Hardware), a discovery-metrics drill-down, Health Overview donut, Audit Insights (Top 5 anomalies), AI Inference (Site/Node/Cell), Network Audit Overview (total vs consistent issues), Network IP Audit (User/Control/Management/NR-ENDC planes by 2G/4G/5G), Node and Cell Distribution charts, and Node & Cell Change Tracking cards. Every number drills into the report behind it.

**Also asked as:** "Explain the RAN dashboard" / "What is on the landing page?" / "What are the dashboard panels?"

**Keywords:** RAN dashboard, KPI strip, health overview, audit insights, AI inference, distribution

**Source:** NETIQ User Manual v3.5 §4.1.1; NETIQ Solution Document v3.3 §18.1

---

### Q: What does the Health Overview card mean?

**ID:** NETIQ-DSH-002 | **Audience:** NOC | **Type:** concept

**Answer:** It shows a data-health score as a donut with a colour-coded status word (Good, Fair or Poor), the Total, Deleted and Not-Updated counts and a Health Progress bar. Green means clean, amber means records need attention and red means critical data-quality issues, so you know where to focus first.

**Also asked as:** "What is the health score?" / "What do green, amber and red mean?"

**Keywords:** health overview, good fair poor, health score, colour bands

**Source:** NETIQ User Manual v3.5 §4.1.1.3

---

### Q: How is NMS Discovery (%) calculated?

**ID:** NETIQ-DSH-003 | **Audience:** NOC | **Type:** design-rule

**Answer:** NMS Discovery % = NMS processed on the current date divided by the number of NMS listed in the static reference sheet (Total OSS/NMS count). Clicking it shows Total NMS, Today Updated, Not Updated and Newly Discovered NMS, each with tabular detail (circle, EMS IP, name, vendor, last updated date, current and last dump size).

**Also asked as:** "What does NMS discovery percentage mean?" / "How are updated NMS counted?"

**Keywords:** NMS discovery percentage, formula, updated NMS, total OSS NMS

**Source:** NETIQ Solution Document v3.3 §18.1.1, §13.3

---

### Q: What is shown under Audit Insights?

**ID:** NETIQ-DSH-004 | **Audience:** NOC | **Type:** concept

**Answer:** The Top 5 data-validation anomalies with live counts and a category tag (Configuration or Data Quality), for example Missing Class attribute, Missing Hardware, Duplicate Cell 2G, Missing IP & Components and Duplicate IP. 'View All Issues' opens the full audit. In Txn mode it lists transmission anomalies such as Missing Txn Links, Non-Matched Freq. HOP, Non-Matched Channel BW. HOP, Duplicate Node and Orphan Nodes.

**Also asked as:** "What are audit insights?" / "Top anomalies on the dashboard" / "Txn audit insights"

**Keywords:** audit insights, top 5 anomalies, view all issues, missing txn links, configuration, data quality

**Source:** NETIQ User Manual v3.5 §4.1.1.4, §4.1.3.2; NETIQ Solution Document v3.3 §18.2.3

---

### Q: What is the Network Audit Overview and what is a 'Consistent' count?

**ID:** NETIQ-DSH-005 | **Audience:** Audit | **Type:** concept

**Answer:** A bar chart of Total Issues against Consistent Count for each audit category (Missing Class attribute, Missing Hardware, Duplicate Cell, Missing IP & Components, Duplicate IP, 2G Compliance, Duplicate Node, Duplicate Hardware, GPS issue, Missing Cell to RU, Nomenclature Issue), with Total Issues, Consistent Cases and a Consistency Rate tile. 'Consistent' means issues persisting over the last 3 weeks (configurable). Click a bar to drill into the offending records.

**Also asked as:** "What does consistent count mean?" / "What is the consistency rate?" / "What is the 3 week rule?"

**Keywords:** network audit overview, consistent count, consistency rate, persisting issues, 3 weeks

**Source:** NETIQ User Manual v3.5 §4.1.1.6; NETIQ Solution Document v3.3 §18.1.1

---

### Q: What does the Network IP Audit panel show?

**ID:** NETIQ-DSH-006 | **Audience:** Ops | **Type:** concept

**Answer:** Plane-wise addressing health across the User, Control, M-Plane and NR-ENDC planes, switchable by 2G/4G/5G tabs, with issue cards such as Nodes With Missing IPs, Duplicate IPs, Missing Gateway, Missing VLAN and Missing Core Details, plus a short written insight. The Solution Document adds checks of destination core mapping (SGW for user plane, MME/AMF for control plane), VLAN consistency, gateway alignment and subnet definitions.

**Also asked as:** "How are IPs validated?" / "What are the IP audit gauges?"

**Keywords:** network IP audit, user plane, control plane, M-plane, NR-ENDC, gateway, VLAN

**Source:** NETIQ User Manual v3.5 §4.1.1.7; NETIQ Solution Document v3.3 §18.1.1

**Related:** NETIQ-AUD-008

---

### Q: What does Node & Cell Change Tracking show?

**ID:** NETIQ-DSH-007 | **Audience:** Ops | **Type:** concept

**Answer:** For each element type (BTS, gNodeB, eNodeB, Ghost, SRANBS and 2G cells) NETIQ compares the latest cycle with the previous one and classifies records as Technology change, ID change, Name change or Stable. A record can fall into more than one class. Cards show Total, Changed vs prev and a progress bar; click a category to open the matching records. Ghost nodes have no technology change; their ID/Name changes appear in the change report.

**Also asked as:** "How do I see renamed nodes?" / "What is technology change?" / "Track node ID changes"

**Keywords:** change tracking, technology change, ID change, name change, stable, SRANBS

**Source:** NETIQ User Manual v3.5 §4.1.1.9; NETIQ Solution Document v3.3 §18.6

---

### Q: What do the Site Discovery, Node Discovery, Cell Discovery and HW Inventory tiles drill into?

**ID:** NETIQ-DSH-008 | **Audience:** Ops | **Type:** reference

**Answer:** Site Discovery: total unique Site IDs, updated per accepted nomenclature, non-uniform nomenclature, sites with no GPS and removed sites. Node Discovery: total, new, updated, name correction, non-uniform nomenclature, no-cell-mapped and orphan nodes. Cell Discovery: unique cells (4G and 5G), new, updated names, inconsistent nomenclature, missing EARFCN, missing TAC and missing Cell-to-RU mapping. HW Inventory: total, updated, removed and new inventory with circle-wise and vendor-wise breakdown.

**Also asked as:** "What is in the site discovery drill-down?" / "What are orphan nodes?" / "Cell discovery breakdown"

**Keywords:** site discovery, node discovery, cell discovery, HW inventory, drill-down, orphan

**Source:** NETIQ Solution Document v3.3 §18.1.1, §13.4

---

### Q: What dashboard panels are available for Transport, MW and UBR?

**ID:** NETIQ-DSH-009 | **Audience:** Planning | **Type:** reference

**Answer:** Txn discovery KPIs (NMS, Site, Node, Transmission-Link, Hardware), Txn Audit Insights, Vendor-wise Node Distribution, Node IP Version (IPv4 vs IPv6), Capacity-wise Hop Categorisation (0-250, 251-500, 501-1000, 1001-2000, 2001-4000 bands), Hop Type Distribution (1+0, 2+0 XPIC, 1+0 EBAND, 4+0 XPIC, MIMO), Transmission-links status (active/inactive, 1+0, 1+1, XPIC) and Planned vs Configured analysis.

**Also asked as:** "What is on the MW dashboard?" / "Capacity bands for MW hops" / "Hop type distribution"

**Keywords:** transport dashboard, MW, UBR, capacity bands, hop type, XPIC, IPv6

**Source:** NETIQ User Manual v3.5 §4.1.3; NETIQ Solution Document v3.3 §18.2

**Related:** NETIQ-AIN-004, NETIQ-GEN-004, NETIQ-GLO-005

---

### Q: What is Deployment Compliance in the Planned vs Configured analysis?

**ID:** NETIQ-DSH-010 | **Audience:** Planning | **Type:** design-rule

**Answer:** Deployment Compliance = Deployed & Matched links divided by Total Planned links. The KPI tiles classify every planned link as Deployed & Matched, Deployed & Unmatched, Planned Not Deployed or Deployed Not Planned. 'Planned Not Deployed' feeds the Missing Txn Links insight. Configuration Validation compares Frequency, Channel Spacing, Modulation and Hop Type with Match % against Mismatch %.

**Also asked as:** "How is deployment compliance computed?" / "What is planned not deployed?" / "Planned vs deployed KPIs"

**Keywords:** deployment compliance, planned vs configured, matched, unmatched, planned not deployed

**Source:** NETIQ User Manual v3.5 §4.1.4; NETIQ Solution Document v3.3 Definitions

---

### Q: Can I drill down from PAN India to a single cell?

**ID:** NETIQ-DSH-011 | **Audience:** All | **Type:** concept

**Answer:** Yes. Dashboards support multi-level drill-down PAN India, Circle, NMS, Site, Node, Cell with dynamic filters for Vendor, Technology, Date Range and Audit Type, and views can be sliced PAN India-wise, circle-wise, vendor-wise and domain-wise for different teams.

**Also asked as:** "Drill-down levels" / "Can I see circle-wise data?"

**Keywords:** drill-down, PAN India, circle, vendor, domain

**Source:** NETIQ Solution Document v3.3 §18.1

---

### Q: How are dashboards computed and refreshed?

**ID:** NETIQ-DSH-012 | **Audience:** NOC | **Type:** concept

**Answer:** Dashboards are computed from the freshly loaded inventory and the latest audit results for the active circle, vendor and domain context. Discovery counts, the NMS health gauge, distribution charts, IP-audit gauges and top anomalies are aggregated per circle and per domain at view time and recomputed on refresh.

**Also asked as:** "When do dashboard numbers update?" / "How are KPIs calculated?"

**Keywords:** dashboard computation, refresh, aggregation, view time

**Source:** NETIQ Solution Document v3.3 §18.3

---

### Q: What does the summary audit dashboard report?

**ID:** NETIQ-DSH-013 | **Audience:** Audit | **Type:** reference

**Answer:** A pass/fail summary per validation area: total checks, passed, failed and pass % for Node/Class/Attribute count, Duplicate Data, Missing Classes/Attributes, Nomenclature Validation, Hardware & Cabinet Information, Site ID Mapping, GPS Validation and Cell-to-RU Mapping. The figures in the solution document are illustrative examples.

**Also asked as:** "Audit pass percentage" / "Summary dashboard validation areas"

**Keywords:** summary dashboard, pass percentage, validation areas

**Source:** NETIQ Solution Document v3.3 §18.2.3

---

## RAN Audits & Validation Rules (AUD)

_Validation, Duplicate and Mapping audits in the Network Health Scorecard._

### Q: What are the three audit families in NETIQ?

**ID:** NETIQ-AUD-001 | **Audience:** Audit | **Type:** concept

**Answer:** Validation (completeness and correctness: missing attributes, GPS, hardware, Site ID, IP), Duplicate (uniqueness: same identity discovered more than once) and Mapping (relationship and rule compliance: cell-to-radio-unit, mapping rules). The same discipline applies to Transport through the Transport Audit Suite. Each rule belongs to a family, targets an element type, encodes a check and assigns High/Medium/Low severity.

**Also asked as:** "What are validation, duplicate and mapping audits?" / "How are audit rules classified?"

**Keywords:** audit families, validation, duplicate, mapping, severity

**Source:** NETIQ Solution Document v3.3 §9.7, §10.3; NETIQ User Manual v3.5 §4.3.1, §9 Q7

---

### Q: Which RAN audit validators are available in the Network Health Scorecard?

**ID:** NETIQ-AUD-002 | **Audience:** Audit | **Type:** reference

**Answer:** Configuration Validator (Validation): Missing Field Detector, GPS Accuracy Audit, Hardware Health Check, Site ID Integrity Check, IP Address Validator. Duplicate Detector: Duplicate Node Audit, 4G/5G/2G Duplicate Cell Audits, Duplicate IP Finder, Duplicate Equipment Audit. Mapping Compliance Audit: Cell-to-RU Link Audit and Mapping Rule Checker. A Transport Audit Suite covers MW Node Validation, MW Hardware Validation, MW Link Audit and UBR Link Audit.

**Also asked as:** "List all RAN audits" / "What audits exist in the scorecard?"

**Keywords:** audit list, scorecard, validators, duplicate detector, mapping compliance

**Source:** NETIQ User Manual v3.5 §4.3.2-4.3.5

---

### Q: How do I work an audit finding?

**ID:** NETIQ-AUD-003 | **Audience:** Audit | **Type:** how-to

**Answer:** Choose the family tab and validator; use column filters to narrow to your circle, technology or node; expand a row to read the exact attribute or rule that failed; export the filtered list to the team owning the source data; fix at source. The finding clears automatically once the corrected dump is ingested in the next cycle.

**Also asked as:** "How to resolve audit findings?" / "Why does a finding remain after I fixed it?" / "Audit workflow"

**Keywords:** audit workflow, finding, fix at source, clears next cycle

**Source:** NETIQ User Manual v3.5 §4.3.6, §9 Q8

---

### Q: What does the Missing Field Detector check?

**ID:** NETIQ-AUD-004 | **Audience:** Audit | **Type:** concept

**Answer:** It finds nodes and cells missing mandatory classes or attributes (for example EARFCN, MCC/MNC, TAC, latitude/longitude, cabinet product name). Columns include Circle, Entity ID, Entity Name, Report Name, Site ID, Missing Attribute, Missing Class and Remark. Mandatory attributes and severity come from the static reference workbook.

**Also asked as:** "What are missing attributes?" / "Missing class audit"

**Keywords:** missing field detector, missing class, missing attribute, mandatory

**Source:** NETIQ User Manual v3.5 §4.3.2.1; NETIQ Solution Document v3.3 §16.1, §16.3

---

### Q: How does the GPS validation work?

**ID:** NETIQ-AUD-005 | **Audience:** Audit | **Type:** design-rule

**Answer:** GPS values of node and cell are checked for completeness and correct mapping to the Site ID. Coordinates outside the valid range (latitude -90 to +90, longitude -180 to +180) or equal to 0,0 are flagged invalid. A Status column shows Pass or Failed. Accurate GPS is a prerequisite for topology, geo-based stitching and proximity searches.

**Also asked as:** "What is invalid GPS?" / "Why is a site flagged for GPS?"

**Keywords:** GPS validation, latitude, longitude, 0, 0, range, invalid

**Source:** NETIQ Solution Document v3.3 §20.9, §16.7; NETIQ User Manual v3.5 §4.3.2.2

**Related:** NETIQ-STI-022, NETIQ-TXN-008

---

### Q: What do the Hardware Health Check and Hardware & Cabinet validations cover?

**ID:** NETIQ-AUD-006 | **Audience:** Audit | **Type:** reference

**Answer:** They verify that each node has complete cabinet and hardware information: cabinet availability, board mapping, and missing board attributes such as product code, version, serial number and vendor. Examples of anomalies: Missing Cabinet Record, Cabinet with No Inventory, Unknown Cabinet Model, Missing Serial Number (High), Duplicate Serial Numbers (High), New Board/Product Code identified (High) and Orphan Boards (Medium). Cabinet sources are CABINET_R for Nokia and vsDataCabinet for Ericsson.

**Also asked as:** "Missing serial number audit" / "Duplicate board serials" / "Cabinet validation"

**Keywords:** hardware, cabinet, board, serial number, product code, orphan boards

**Source:** NETIQ Solution Document v3.3 §13.5, §16.5, §20.8; NETIQ User Manual v3.5 §4.3.2.3

---

### Q: What is checked by the Site ID Integrity Check and Nomenclature validation?

**ID:** NETIQ-AUD-007 | **Audience:** Audit | **Type:** concept

**Answer:** That the Site ID generated from node-level and cell-level data is identical and follows the standard format; deviations, including those produced by AI inference, are highlighted. Node and cell naming conventions are enforced, with exceptions handled through the static 'Reporting & Attribute Details' sheet. Non-conforming Site IDs are reported with supported technology and status.

**Also asked as:** "Why is my site name flagged?" / "Naming convention audit" / "Site ID mismatch"

**Keywords:** site ID integrity, nomenclature, naming convention, exceptions

**Source:** NETIQ Solution Document v3.3 §16.4, §16.6, §13.2; NETIQ User Manual v3.5 §4.3.2.4

---

### Q: What does the IP Address Validator and IP Data Report catch?

**ID:** NETIQ-AUD-008 | **Audience:** Ops | **Type:** concept

**Answer:** Out-of-range, unassigned, overlapping or conflicting addresses across planes; extra IPs mapped to a node; IPs missing VLAN, gateway, subnet mask or name; and VLAN entries missing IP details. Node logical parameters (IP, subnet mask, VLAN) are validated separately across C-Plane, U-Plane and M-Plane to ensure transport separation and management reachability.

**Also asked as:** "Missing gateway audit" / "IP validation rules" / "Duplicate VLAN"

**Keywords:** IP validator, IP data report, gateway, VLAN, subnet mask, planes

**Source:** NETIQ Solution Document v3.3 §16.10, §13.6; NETIQ User Manual v3.5 §4.3.2.5

**Related:** NETIQ-DSH-006

---

### Q: What duplicate checks does NETIQ run?

**ID:** NETIQ-AUD-009 | **Audience:** Audit | **Type:** reference

**Answer:** Duplicate Node IDs and Names, 4G/5G/2G Cell IDs and Cell Names (for example repeated ECGI, NCGI or CGI), duplicate IPs and VLANs, and duplicate hardware serials. Duplicate Node IDs and Names, and Duplicate Serial Numbers, are High severity. Uniqueness is checked per circle scope, and a Count column shows how many times each identity appears.

**Also asked as:** "How are duplicate cells detected?" / "What is duplicate equipment audit?"

**Keywords:** duplicate, node ID, cell ID, ECGI, NCGI, serial, IP, VLAN

**Source:** NETIQ Solution Document v3.3 §13.5, §20.6; NETIQ User Manual v3.5 §4.3.3

---

### Q: What is a Ghost node?

**ID:** NETIQ-AUD-010 | **Audience:** Audit | **Type:** concept

**Answer:** A node discovered without a complete expected profile, flagged for investigation. Decommissioned nodes that remain active in the NMS inflate counts and distort audits; NETIQ identifies them, among other ways, by their absence from CM dumps. Ghost nodes are listed in Network Truth Repository, RAN Repository, Node, Ghost Nodes, and a Smart Shortcut opens them directly.

**Also asked as:** "Define ghost node" / "What are legacy elements?" / "How do I find ghost nodes?"

**Keywords:** ghost node, legacy element, decommissioned, orphan

**Source:** NETIQ Solution Document v3.3 §2.2; NETIQ User Manual v3.5 §4.4.1.6, §9 Q12

---

### Q: What is an orphan element?

**ID:** NETIQ-AUD-011 | **Audience:** Audit | **Type:** concept

**Answer:** An element without a valid parent in the hierarchy, for example a Cell without a parent Node, a Node without a Site, or a Board without a Node. Orphan nodes, orphan boards (Medium) and orphan MW/UBR links (an endpoint node or interface missing) are flagged. Orphan RAN Sites are RAN sites where no media node (MW/UBR/FTTH/POP) is identified.

**Also asked as:** "Orphan node definition" / "What are orphan RAN sites?"

**Keywords:** orphan node, orphan cell, orphan board, orphan link, orphan RAN site

**Source:** NETIQ Solution Document v3.3 §13.2, §13.4, §14.2, §18.2.3

---

### Q: How does NETIQ distinguish an SRAN node from a standalone 2G BTS?

**ID:** NETIQ-AUD-012 | **Audience:** Audit | **Type:** design-rule

**Answer:** Using GNBCF and BCF classes: if the BSC ID, BCF ID and SBTS (MRBTS) ID in class GNBCF also exist in class BCF (checked in either direction), the node is SRAN; otherwise it is a standalone BTS. The mapping must be validated across all EMS IPs within the same circle, not restricted to a single EMS IP.

**Also asked as:** "SRAN compliance rule" / "GNBCF BCF logic" / "How is standalone BTS identified?"

**Keywords:** SRAN, BTS, GNBCF, BCF, MRBTS, compliance

**Source:** NETIQ Solution Document v3.3 §16.9

**Related:** NETIQ-GLO-003

---

### Q: What does the Cell-to-RU Link Audit check?

**ID:** NETIQ-AUD-013 | **Audience:** Audit | **Type:** concept

**Answer:** That every configured cell maps to its serving radio unit, aligning cell identifiers, RU serial details and hardware placement. Missing, incorrect or unmapped relationships are highlighted, and NETIQ surfaces a suggested RRU mapping for the gaps (see Cell-to-RU Mapping Suggestion in AI Intelligence).

**Also asked as:** "Cells without radio unit" / "Unmapped cell to RU"

**Keywords:** cell to RU, radio unit, RRU, mapping audit, unmapped

**Source:** NETIQ Solution Document v3.3 §16.8; NETIQ User Manual v3.5 §4.3.4.1

---

### Q: Which node model and parameter anomalies are tracked and at what severity?

**ID:** NETIQ-AUD-014 | **Audience:** Audit | **Type:** reference

**Answer:** Node model: Unexpected Model Type (High), Model Mismatch vs Planning (Medium), Model Count Deviation (Medium), Duplicate Node IDs/Names (High). Parameter rules: TAC, EARFCN UL/DL and Bandwidth UL/DL must be integers; Cell Admin Status must be Locked or Unlocked; Duplex Mode must be FDD or TDD; MCC/MNC must match the MCC-MNC sheet. Anything else is counted as Non-Uniform. Each parameter is tracked as Available, Non-Available, New, Updated, Removed and Non-Uniform.

**Also asked as:** "What are accepted values for admin status?" / "What makes a parameter non-uniform?" / "Severity of model anomalies"

**Keywords:** parameter validation, non-uniform, TAC, EARFCN, admin status, duplex, severity, model type

**Source:** NETIQ Solution Document v3.3 §13.5-13.6

**Related:** NETIQ-AIN-006, NETIQ-GLO-004, NETIQ-INV-004

---

### Q: What consistency checks apply across aggregation levels?

**ID:** NETIQ-AUD-015 | **Audience:** Audit | **Type:** design-rule

**Answer:** PAN India totals must equal the sum of Circle totals, which equal the sum of NMS totals and node/cell totals; Vendor split (Ericsson/Nokia) and Technology split (eNodeB/gNodeB/SRANBs, 4G/5G) are cross-checked. The PAN-01 test expects a 100% match. Reduced or deviated counts are flagged in dashboards and reports.

**Also asked as:** "How is aggregation validated?" / "PAN India vs circle totals"

**Keywords:** aggregation, consistency, PAN India, circle totals, vendor split

**Source:** NETIQ Solution Document v3.3 §13.2, §20.1

---

### Q: How are audit scores calculated?

**ID:** NETIQ-AUD-016 | **Audience:** Audit | **Type:** concept

**Answer:** The audit scoring dashboard calculates compliance scores per Circle and PAN India and computes Match %, Severity Index and Confidence Index, offering unified views for normal reporting and audit reporting. Findings carry severity (High/Medium/Low) and the offending-element context.

**Also asked as:** "What is the severity index?" / "Compliance score per circle"

**Keywords:** audit scoring, match percent, severity index, confidence index, compliance

**Source:** NETIQ Solution Document v3.3 §12, §9.7

---

## MW, UBR & Transport Audits (TXN)

_Microwave/UBR link validation, planned-vs-configured and transport audit details._

### Q: What does the Transport Audit Suite cover?

**ID:** NETIQ-TXN-001 | **Audience:** Audit | **Type:** reference

**Answer:** MW Node Validation, MW Hardware Validation, MW Link Audit and UBR Link Audit, applying the same validation, duplicate and mapping discipline as RAN. The MW audit reports include the Site Report, Node Validation, Duplicate Data, Nomenclature, Hardware Validation, MW/UBR Links Validation, Planned vs Configured and IP data reports.

**Also asked as:** "What MW audits are available?" / "MW audit report list"

**Keywords:** transport audit suite, MW audit, UBR audit, node validation, hardware validation

**Source:** NETIQ Solution Document v3.3 §17; NETIQ User Manual v3.5 §4.3.5

---

### Q: Which MW link parameters does NETIQ validate?

**ID:** NETIQ-TXN-002 | **Audience:** Planning | **Type:** reference

**Answer:** Tx/Rx frequency (aligned to the MIDS frequency table of the circle), channel bandwidth (for example 7/14/28/56 MHz), modulation scheme, capacity/throughput, ATPC status (mismatch between link ends is non-uniform) and link availability. For each parameter NETIQ tracks availability, new discovery, updates, removal and non-uniform values.

**Also asked as:** "MW link audit parameters" / "What is checked in MW links?" / "ATPC mismatch"

**Keywords:** MW link, frequency, channel bandwidth, modulation, capacity, ATPC, MIDS

**Source:** NETIQ Solution Document v3.3 §14.4

---

### Q: How does NETIQ identify modulation from capacity and bandwidth?

**ID:** NETIQ-TXN-003 | **Audience:** Planning | **Type:** design-rule

**Answer:** Spectral Efficiency = (Capacity / Channel Spacing) / K, mapped to a modulation order (BPSK 1 bps/Hz, QPSK 2, 8QAM 3, 16QAM 4, 32QAM 5, 64QAM 6, 128QAM 7, 256QAM 8, 512QAM 9, 1024QAM 10, 2048QAM 11, 4096QAM 12). K = 0.85 for Ceragon and 0.80 for other vendors (except E-Band, where K is vendor-specific: Ceragon 0.88-0.95, Nokia 0.87-0.94, Huawei 0.85-0.92, Aviat 0.90). Modulation inconsistent with bandwidth and capacity is non-uniform.

**Also asked as:** "Modulation identification formula" / "What is K in the spectral efficiency formula?" / "E-band K values"

**Keywords:** modulation, spectral efficiency, formula, K factor, E-band, Ceragon, QAM

**Source:** NETIQ Solution Document v3.3 §14.4

---

### Q: How does NETIQ classify an MW link as Up, Down or Degraded?

**ID:** NETIQ-TXN-004 | **Audience:** NOC | **Type:** design-rule

**Answer:** A link is Up when Node1 or Node2 Rx level (min/max) is not in the range -90 to -100 dBm, and Down when the values fall within that range. For the Degraded RSL Links count, links whose Node1 or Node2 Max/Min 24-hour Rx power falls between -85 and -100 are counted. In AI Intelligence the Degraded Link Audit groups hops into Healthy, At Risk or Degraded.

**Also asked as:** "What is a degraded RSL link?" / "MW link up down rule" / "Rx level thresholds"

**Keywords:** degraded RSL, link up, link down, Rx power, -85, -90, -100

**Source:** NETIQ Solution Document v3.3 §14.2, §14.4, §18.5.1

---

### Q: Which UBR link checks does NETIQ run?

**ID:** NETIQ-TXN-005 | **Audience:** Planning | **Type:** design-rule

**Answer:** MCS (flagged where not feasible for the reported RSSI or capacity), Downlink vs Uplink RSSI (flagged where the DL-UL difference exceeds the threshold, for example plus/minus 3 dB), and capacity/throughput (flagged where inconsistent with bandwidth, MCS or interface speed).

**Also asked as:** "UBR audit rules" / "RSSI difference threshold" / "MCS check"

**Keywords:** UBR, MCS, RSSI, capacity, 3 dB

**Source:** NETIQ Solution Document v3.3 §14.5

---

### Q: What MW/UBR element counts and anomalies are reported?

**ID:** NETIQ-TXN-006 | **Audience:** Planning | **Type:** reference

**Answer:** Site level: total unique sites, new MW sites, RAN with MW/UBR, standalone MW, standalone RAN, deleted, non-uniform nomenclature and standalone MW sites with no lat/long. Node level: total, new, updated, non-uniform nomenclature, no link mapping, orphan and duplicate. Link level: total, new, updated, modified (same Link ID but changed frequency, band, spacing, modulation or configuration), degraded RSL, orphan links and links with no traffic (no VLAN on any interface).

**Also asked as:** "What are standalone MW sites?" / "What is a modified link?" / "Links with no traffic"

**Keywords:** MW counts, standalone MW, orphan links, modified links, no traffic, degraded RSL

**Source:** NETIQ Solution Document v3.3 §14.2

---

### Q: How does the Planned vs Configured comparison work for MW/UBR links?

**ID:** NETIQ-TXN-007 | **Audience:** Planning | **Type:** design-rule

**Answer:** NETIQ matches planned and configured links on the composite key (HOP ID plus manufacturer against Link ID Site A-Site B in either order plus manufacturer), then compares Frequency, Channel Spacing, Modulation and HOP Type. Each link is classified: Missing Link, Unplanned Link (Likely New / Partial / Match Gap), Modulation Deviation, Frequency Deviation, Channel Spacing Deviation, combinations, or Out of Scope (vendor not in the live report). The top 10 categories are shown and the rest grouped as Other.

**Also asked as:** "How are planned links matched?" / "Deviation categories" / "Frequency deviation report"

**Keywords:** planned vs configured, MIDS, deviation, missing link, unplanned link, frequency deviation

**Source:** NETIQ Solution Document v3.3 §18.5.2, §17.8; NETIQ User Manual v3.5 §4.1.4

**Related:** NETIQ-AIN-005, NETIQ-INV-007

---

### Q: Where do MW and UBR site coordinates come from?

**ID:** NETIQ-TXN-008 | **Audience:** Planning | **Type:** reference

**Answer:** The MW Site Report consolidates sites from RAN where MW/UBR is present plus standalone MW/UBR sites. For standalone sites latitude and longitude are fetched from the MIDS / UBR LB reports (and validated against RAN GPS and MIDS planning data); standalone sites with no coordinates after validation are counted separately.

**Also asked as:** "Standalone MW site GPS" / "MIDS lat long source"

**Keywords:** MW site report, standalone MW, MIDS, latitude, longitude

**Source:** NETIQ Solution Document v3.3 §17.1, §14.2

**Related:** NETIQ-AUD-005, NETIQ-STI-022

---

## E2E Service Stitching Logic (STI)

_How every RAN service is traced from RAN to Core: inputs, parent TX discovery, hop chain, L2/AGW, Core, link naming and labels._

### Q: What is service stitching in NETIQ?

**ID:** NETIQ-STI-001 | **Audience:** All | **Type:** concept

**Answer:** Stitching links elements across domains into an end-to-end path anchored to physical sites: RAN, then MW/UBR/FTTH, then the first Wireline node (L2 Access POP), then the Aggregation Gateway (AGW, L3 POP), and finally the Core node. It works in two phases: site resolution (site IDs, co-location and, where needed, geo-proximity) and path construction. All logic operates on deployed NMS inventory and live logical configuration, not on KPIs or alarms.

**Also asked as:** "What does stitching mean?" / "How does NETIQ build the RAN to core path?" / "Explain E2E stitching"

**Keywords:** stitching, E2E, RAN to core, L2, AGW, site resolution, path construction

**Source:** NETIQ Solution Document v3.3 §9.8, §9.10; NETIQ User Manual v3.5 §9 Q9

**Related:** NETIQ-GLO-002, NETIQ-STI-009, NETIQ-STI-015

---

### Q: What input reports does the stitching engine use?

**ID:** NETIQ-STI-002 | **Audience:** Ops | **Type:** reference

**Answer:** Thirteen NMS report types: RAN IP Report (primary), Transmission Node Report, MW Port Report, MW Link Report, UBR Link Report, FTTH Node Report, FTTH Link Report, Wireline Node Report, Wireline Link Report, Wireline IP_VLAN Report, Core IP Report, Site Report (with Default LATITUDE_LONGITUDE sheet) and the Planned vs Configured Link Report (used only by the AI Audit Engine as supporting evidence). No performance KPIs or alarm data are consumed.

**Also asked as:** "Which reports feed stitching?" / "What data is needed for stitching?" / "Does stitching use alarms?"

**Keywords:** input reports, RAN IP report, port report, wireline IP_VLAN, core IP report, planned vs configured

**Source:** NETIQ Solution Document v3.3 §9.10.4

---

### Q: How is a RAN service identified and its plane classified?

**ID:** NETIQ-STI-003 | **Audience:** Ops | **Type:** design-rule

**Answer:** Every RAN IP record becomes a service with the composite key RAN_Node_ID : Technology : Plane : IP, for example MRBTS-90550:4G:UP:100.120.0.90. Technology comes from node type (eNodeB/SRANBS is 4G, gNodeB is 5G). Plane: 4G S1-U/UPLANE is UP, S1-MME/CPLANE is CP, MPLANE/OAM is MP; 5G N3 is UP, N2 is CP, O1 is MP. VLAN is the primary match key and the plane-specific Gateway IP is used for AGW matching.

**Also asked as:** "What is the service key?" / "How are UP, CP and MP planes defined?" / "Service entity in stitching"

**Keywords:** service key, plane, UP, CP, MP, S1-U, S1-MME, N3, N2, O1

**Source:** NETIQ Solution Document v3.3 §9.10.5

**Related:** NETIQ-STI-019

---

### Q: In what order does NETIQ look for the RAN parent transmission node?

**ID:** NETIQ-STI-004 | **Audience:** Ops | **Type:** design-rule

**Answer:** 1) A direct Wireline connection (RAN Site ID matches a Wireline node site); 2) a collocated MW node chosen by VLAN-group probability match; 3) a UBR node at the site; 4) an FTTH ONT at the site (FTTH fallback); 5) an MW node with a free port within 100 metres (proximity search, SUGGESTED). If none qualifies, NO_TX_NODE is raised and L2 identification continues using Gateway IP matching only.

**Also asked as:** "How does NETIQ find the parent MW node?" / "What is the transmission discovery order?" / "What is FTTH fallback?"

**Keywords:** parent transmission, discovery order, MW, UBR, FTTH, proximity, 100 m

**Source:** NETIQ Solution Document v3.3 §9.10.6; NETIQ User Manual v3.5 §4.2.7

**Related:** NETIQ-GEN-004, NETIQ-GLO-005, NETIQ-AIN-004

---

### Q: How does VLAN-group probability matching work?

**ID:** NETIQ-STI-005 | **Audience:** Ops | **Type:** design-rule

**Answer:** NETIQ extracts the full VLAN group of the RAN Site ID and technology from the RAN IP Report. For every MW node at the site it scans all ETH, GETH, FETH and SFP ports in the Port Report and computes Match % = (VLANs in common with the RAN VLAN group / total VLANs in the group) x 100 against the port's VLAN TRUNK. The highest Match % wins; ties go to the lowest port index; with several MW nodes the node with the highest best-port match is chosen.

**Also asked as:** "What is VLAN match percentage?" / "How is the MW port selected?" / "Explain probability match"

**Keywords:** VLAN match, probability, port selection, VLAN trunk, match percent

**Source:** NETIQ Solution Document v3.3 §9.10.6.4; NETIQ Solution Document v3.3 Definitions

---

### Q: What are the VLAN match thresholds and what happens below them?

**ID:** NETIQ-STI-006 | **Audience:** Ops | **Type:** design-rule

**Answer:** Priority 1 is a 100% match, Priority 2 is 80% or more, Priority 3 is 70% or more. The default threshold is 70% and is operator-configurable per circle. Matches below it are recorded with the VLAN_MISMATCH audit flag and escalated to the AI Audit Engine, which re-runs with a lowered 50% threshold, records the partial match score and flags it for review.

**Also asked as:** "What is the VLAN match threshold?" / "Can the 70 percent threshold be changed?" / "What triggers VLAN_MISMATCH?"

**Keywords:** VLAN threshold, 70 percent, 80 percent, 100 percent, VLAN_MISMATCH, configurable

**Source:** NETIQ Solution Document v3.3 §9.10.6.4, §9.10.15.1

---

### Q: Why does a RAN node get only one parent transmission connection?

**ID:** NETIQ-STI-007 | **Audience:** Ops | **Type:** design-rule

**Answer:** The Mandatory Parent Transmission Uniqueness Rule: once a valid parent MW/UBR/FTTH/Wireline device is established for a RAN node, the same RAN-to-transmission connection is reused for all its services. The engine does not create separate physical connections to other devices just because another service or IP record yields an alternate candidate. Where service-specific VLAN evidence conflicts with the identified parent, that service is sent to AI Audit as an exception.

**Also asked as:** "Can a RAN node have two MW parents?" / "Why are all services on the same port?" / "Parent uniqueness rule"

**Keywords:** parent uniqueness, single parent, RAN node, exception, AI audit

**Source:** NETIQ Solution Document v3.3 §9.10.6.1

---

### Q: When does NETIQ prefer a direct Wireline connection over MW?

**ID:** NETIQ-STI-008 | **Audience:** Ops | **Type:** design-rule

**Answer:** Per the connection hierarchy: if all RAN VLANs are on the Wireline node (alone or alongside MW), RAN connects directly to Wireline. If some VLANs are missing on Wireline but all match on MW, or no VLAN is on Wireline but all match on MW, MW is selected as parent (RAN to MW to Wireline). If all VLANs are on Wireline and only partial on MW, Wireline is preferred. Partial on both goes to AI Audit; no VLAN on either does not create a confirmed link and falls to AI audit, planning or co-location fallback logic.

**Also asked as:** "Wireline vs MW decision" / "Scenario table for connection hierarchy" / "When is MW selected?"

**Keywords:** connection hierarchy, wireline preferred, MW parent, scenarios, VLAN check

**Source:** NETIQ Solution Document v3.3 §9.10.6.2

---

### Q: How does NETIQ detect a direct RAN-to-Wireline connection?

**ID:** NETIQ-STI-009 | **Audience:** Ops | **Type:** design-rule

**Answer:** It matches the RAN IP Report SITE ID with the Wireline Node Report SITE ID. If the RAN VLAN matches the Wireline IP_VLAN VLAN ID and the RAN Gateway IP matches a WAN IP, the RAN connects directly to the AGW (L3). If only the VLAN matches (Gateway IP absent or unmatched) it connects to an L2 Access POP. Otherwise MW node identification follows. WAN IP entries are comma-separated and each is compared individually.

**Also asked as:** "Direct wireline connection rule" / "How is the Gateway IP matched to the WAN IP?"

**Keywords:** direct wireline, gateway IP, WAN IP, VLAN ID, AGW, L2

**Source:** NETIQ Solution Document v3.3 §9.10.6.3

**Related:** NETIQ-STI-015, NETIQ-GLO-002, NETIQ-STI-001

---

### Q: How is a UBR parent identified and which interfaces are used?

**ID:** NETIQ-STI-010 | **Audience:** Ops | **Type:** design-rule

**Answer:** If no MW node is at the RAN site, NETIQ checks the Transmission Node Report for a UBR node (Node Category = UBR) at the same site and creates a RAN-UBR internal link with default interface mapping RAN Slot 0/Port 1 and UBR Slot 0/Port 2. The far end is found from the UBR Link Report and continues to an MW or Wireline site. No VLAN check is done at each UBR hop.

**Also asked as:** "UBR parent rule" / "Default interface for UBR link"

**Keywords:** UBR, parent node, default interface, 0/1, 0/2

**Source:** NETIQ Solution Document v3.3 §9.10.6.5, §9.10.7.2

---

### Q: How does the FTTH fallback work?

**ID:** NETIQ-STI-011 | **Audience:** Ops | **Type:** design-rule

**Answer:** If neither MW nor UBR is at the RAN site, NETIQ looks for an FTTH ONT at the same site in the FTTH Node Report and creates an internal RAN-FTTH link (RAN Slot 0/Port 1 to FTTH Slot 1/Port 1). It then traces FTTH to FTTH hops through the FTTH Link Report accuracy chain L1 to L4 until a Wireline site is reached. No VLAN validation is performed on FTTH hops.

**Also asked as:** "FTTH hop chain" / "What if there is no MW or UBR at the site?"

**Keywords:** FTTH, ONT, fallback, hop chain, accuracy level, 1/1

**Source:** NETIQ Solution Document v3.3 §9.10.6.6, §9.10.7.3

---

### Q: How does the proximity search work for RAN sites with no collocated transmission?

**ID:** NETIQ-STI-012 | **Audience:** Ops | **Type:** design-rule

**Answer:** NETIQ computes the Haversine distance from the RAN site to all MW sites, keeps those within 100 metres, and checks each for a free ETH/GETH/FETH/SFP port (not present in the MW Link Report as SITE 1 or SITE 2) whose VLAN TRUNK holds at least one RAN service VLAN. If found it creates a SUGGESTED internal link with TX_SUGGESTION_FLAG = Y, SUGGESTION_METHOD = PROXIMITY_100M and the distance recorded. Otherwise NO_TX_NODE is raised.

**Also asked as:** "100 metre proximity rule" / "What is PROXIMITY_100M?" / "NO_TX_NODE cause"

**Keywords:** proximity, 100 m, Haversine, free port, TX_SUGGESTION_FLAG, NO_TX_NODE

**Source:** NETIQ Solution Document v3.3 §9.10.6.7

**Related:** NETIQ-STI-004

---

### Q: How is the MW hop chain traced to the Wireline site?

**ID:** NETIQ-STI-013 | **Audience:** Ops | **Type:** design-rule

**Answer:** From the RAN-side IDU the engine follows the MW Link Report hop by hop, verifying at each intermediate node that the RAN VLAN is on the incoming port using the same VLAN probability match. If the VLAN disappears, MISSING_TX_HOP is flagged to the AI Audit Engine and traversal continues from the last confirmed hop. The chain ends at an MW node located at a Wireline node site, where an internal MW-to-Wireline link is created using VLAN availability in the IP_VLAN report. If the VLAN is not on that Wireline node, an alternate hop chain is checked.

**Also asked as:** "MW hop chain logic" / "What is MISSING_TX_HOP?" / "How does NETIQ trace hops?"

**Keywords:** MW hop chain, VLAN per hop, MISSING_TX_HOP, traversal, link report

**Source:** NETIQ Solution Document v3.3 §9.10.7.1

---

### Q: Which port types are preferred when connecting MW to Wireline?

**ID:** NETIQ-STI-014 | **Audience:** Ops | **Type:** design-rule

**Answer:** The interface priority is SFP, then FETH, then GETH, then ETH, with ports selected by the VLAN matching rule. The source design also lists SFP, GETH, FETH, ETH in places; the consolidation notes state SFP, FETH, GETH, ETH (stated three times) is used and should be confirmed with the rule owners.

**Also asked as:** "Port priority SFP FETH GETH ETH" / "Which port is chosen for MW to wireline?"

**Keywords:** port priority, SFP, FETH, GETH, ETH, interface selection

**Source:** NETIQ Solution Document v3.3 §9.10.7.2, §9.10.19

---

### Q: How does NETIQ classify the first Wireline node as L2 (Access POP) or AGW (L3)?

**ID:** NETIQ-STI-015 | **Audience:** Ops | **Type:** design-rule

**Answer:** It searches the Wireline IP_VLAN Report of the first Wireline node for the service's plane-specific Gateway IP under WAN IP. Case A: Gateway IP found, so the node is the AGW (L3) with no separate L2. Case B: Gateway IP not found but the RAN VLAN is present, so the node is L2 (Access POP) and the AGW is discovered next. Case C: neither found, so another Wireline site via another hop chain is tried, then AI audit. Case D: another IP of the same node/technology/plane is stitched to an AGW, so Same-Service/Alternate IP validation applies.

**Also asked as:** "L2 vs L3 classification" / "What is Case A, B, C, D?" / "How is AGW identified?"

**Keywords:** L2, AGW, L3, access POP, gateway IP, WAN IP, case A B C D

**Source:** NETIQ Solution Document v3.3 §9.10.8.1

**Related:** NETIQ-GLO-002, NETIQ-STI-009, NETIQ-OPS-003

---

### Q: How does NETIQ find the AGW (L3) after identifying an L2?

**ID:** NETIQ-STI-016 | **Audience:** Ops | **Type:** design-rule

**Answer:** It first matches the RAN VLAN to the VLAN ID column of the Wireline IP_VLAN Report; then traverses the Wireline Link Report from the L2 to the next Wireline node holding the RAN Gateway IP under WAN IP. If found via TX links it becomes the AGW and a physical L2-AGW link is created. If not, it searches all nodes for a Gateway IP (plus VLAN) match and creates a default cloud connection. If still not found, Default_AGW is assigned, MISSING_AGW is raised and the AGW is marked unresolved.

**Also asked as:** "AGW discovery steps" / "What triggers Default_AGW?" / "L2 to AGW connectivity"

**Keywords:** AGW discovery, default AGW, MISSING_AGW, cloud connection, wireline link

**Source:** NETIQ Solution Document v3.3 §9.10.8.2, §9.10.8.4

---

### Q: What is Same-Service / Alternate IP validation (Case D)?

**ID:** NETIQ-STI-017 | **Audience:** Ops | **Type:** design-rule

**Answer:** Before assigning Default_AGW, NETIQ checks whether another IP of the same RAN Node ID, Technology and Plane (for example IPv4 vs IPv6) is already stitched to an actual AGW. That AGW is reference evidence only and is not inherited automatically. If the unmatched IP has no live AGW configuration of its own, no Default_AGW is created; the status is UNRESOLVED with flags MISSING_AGW / SUSPECT_NON_LIVE_SERVICE, and the other AGW may be shown as a Reference AGW without a confirmed logical connection.

**Also asked as:** "What is SUSPECT_NON_LIVE_SERVICE?" / "Why does an IPv6 service show unresolved?" / "Reference AGW"

**Keywords:** alternate IP, IP version, SUSPECT_NON_LIVE_SERVICE, reference AGW, case D

**Source:** NETIQ Solution Document v3.3 §9.10.8.3

---

### Q: What is an IP Cloud connection and how is it drawn?

**ID:** NETIQ-STI-018 | **Audience:** NOC | **Type:** design-rule

**Answer:** A logical segment used when no physical Wireline TX link exists, either between L2 and AGW or between AGW and Core. It is drawn as a dashed/cloud line in all views, whereas physical links are solid. Using the L2-to-AGW default cloud reduces the confidence score of that segment by 30 points. Names follow <L2 NODE NAME>_Wireline_Cloud - <L3 NODE NAME>_Cloud_IP and <AGW NODE NAME>_IPCloud - <DESTINATION NODE NAME>_IPCloud.

**Also asked as:** "What is a cloud link?" / "Why is a link dashed?" / "Default cloud connection penalty"

**Keywords:** IP cloud, default cloud connection, dashed line, wireline cloud, confidence reduction

**Source:** NETIQ Solution Document v3.3 §9.10.8.4, §9.10.11.2; Definitions

---

### Q: How does NETIQ associate the Core node?

**ID:** NETIQ-STI-019 | **Audience:** Ops | **Type:** design-rule

**Answer:** It matches the NODE ID of the Core IP Report to the RAN IP Report NODE ID and retrieves the DESTINATION NODE IP; the IP NAME is chosen by plane (UPLANE maps to S1-U, CPLANE to S1-MME; MPLANE is ignored). If the AGW site has a Wireline TX link to a site in the Core IP Report, a physical AGW-to-Core connection (solid line) is created; otherwise an IP CLOUD connection is made using DESTINATION NODE IP. If the destination IP is not in the Core IP Report, MISSING_CORE is raised.

**Also asked as:** "How is Core identified?" / "What is MISSING_CORE?" / "AGW to Core connection"

**Keywords:** core association, DESTINATION NODE IP, core IP report, S1-U, S1-MME, MISSING_CORE

**Source:** NETIQ Solution Document v3.3 §9.10.9; NETIQ User Manual v3.5 §4.2.6

**Related:** NETIQ-STI-003

---

### Q: What are internal links and in which order are they created?

**ID:** NETIQ-STI-020 | **Audience:** Ops | **Type:** design-rule

**Answer:** Internal links join collocated nodes at the same site and are created before inter-site links. Priority 1 (intra-site, same domain): RAN-MW IDU (VLAN matched on ETH/GETH/FETH/SFP) and RAN-UBR (same site only, no VLAN check). Priority 2 (intra-site cross-domain and inter-site TX): MW IDU-Wireline (VLAN match), FTTH ONT-Wireline, and UBR-MW at a different site via the UBR Link Report. Priority 3: RAN-MW proximity fallback (SUGGESTED).

**Also asked as:** "What is an internal link?" / "Internal link priorities" / "RAN to MW internal link"

**Keywords:** internal link, intra-site, priority, RAN-MW, RAN-UBR, MW-Wireline

**Source:** NETIQ Solution Document v3.3 §9.10.10

---

### Q: How is the TXN Link ID built?

**ID:** NETIQ-STI-021 | **Audience:** Ops | **Type:** reference

**Answer:** Internal links use <SITE A NODE NAME> <PORT TYPE> <SLOT>/<PORT> _ <SITE B NODE NAME> <PORT TYPE> <SLOT>/<PORT> (for Wireline ends, the node interface). For external links: MW to MW takes the Link ID from the MW Link Report; UBR to UBR takes the Transmission Link ID from the UBR Link Report; FTTH to FTTH is built from Node A/B ID and interface; L2 to AGW takes the Link Name from the Wireline Link Report (or the Wireline_Cloud name if none); AGW to Core uses the IPCloud default link name. Port Type is no longer a separate column; it is embedded in INTERFACE and LINK ID.

**Also asked as:** "What is a TXN Link ID?" / "How are link names generated?" / "Why is there no port type column?"

**Keywords:** TXN Link ID, link naming, internal link, external link, interface

**Source:** NETIQ Solution Document v3.3 §9.10.11, §15.9.1

---

### Q: How are site latitude and longitude determined for each hop?

**ID:** NETIQ-STI-022 | **Audience:** Ops | **Type:** design-rule

**Answer:** From the Site Report by matching the A-End and Z-End Site IDs. If coordinates are not available, the values from the 'Default LATITUDE_LONGITUDE' sheet are used. Defaults apply to all Site IDs except Core sites; default coordinates are never applied to Core Site IDs.

**Also asked as:** "Where do stitching coordinates come from?" / "Default latitude longitude sheet"

**Keywords:** site location, latitude, longitude, default sheet, site report, core sites

**Source:** NETIQ Solution Document v3.3 §9.10.12

**Related:** NETIQ-AUD-005, NETIQ-TRB-008, NETIQ-TXN-008

---

### Q: How are the L3 and L2 circuit labels populated?

**ID:** NETIQ-STI-023 | **Audience:** Ops | **Type:** design-rule

**Answer:** CIRCUIT LABEL (L3) comes from the L3 Circuit ID of the Wireline IP_VLAN row where the service Gateway IP is under WAN IP and the VLAN is under VLAN ID in the same row (GW-IP-only match if VLAN did not match). A special case for a Direct Aggregator with TIER T5 (ECI) or Node Domain CSR takes the L2 Circuit value, and a fallback uses L2VPNID_Name. CIRCUIT LABEL (L2) comes from the L2 Circuit column where the Access POP node name and VLAN match and the GW IP is not under WAN IP; it stays empty if no match. Entries with 'dummy' or 'lag' interfaces are ignored and numeric 'Port=' entries preferred; unique values are listed once.

**Also asked as:** "Where does the circuit label come from?" / "L2 circuit label logic" / "Why is circuit label empty?"

**Keywords:** circuit label, L2 circuit, L3 circuit, IP_VLAN, T5, CSR, L2VPNID_Name

**Source:** NETIQ Solution Document v3.3 §9.10.13-9.10.14

**Related:** NETIQ-AIA-004, NETIQ-STI-026

---

### Q: What does the Service Stitching Report contain?

**ID:** NETIQ-STI-024 | **Audience:** Ops | **Type:** reference

**Answer:** One row per hop per service (SEQ NO 1 to n) in a horizontal A-End / Z-End format, with service attributes (SERVICE ID, SITE ID, 4G/5G, PLANE, IP ADDRESS, GATEWAY IP, VLAN, IP (CORE)), hop TYPE (Internal, MW radio link, L2 circuit, L3 circuit), A-End and Z-End details (site, lat/long, domain, node ID/name, interface, VLAN), LINK ID, CIRCUIT LABEL (L2/L3), POP SITE ID (L2/L3) and result attributes STATUS, SCORE, FLAG and REMARKS/AUDIT FLAG. Sort by SCORE ascending to work the weakest services first.

**Also asked as:** "Stitching report columns" / "What fields are in the E2E report?" / "How do I read the stitching report?"

**Keywords:** stitching report, columns, A-End, Z-End, hop, SEQ NO, SCORE, FLAG, remarks

**Source:** NETIQ Solution Document v3.3 §15.9; NETIQ User Manual v3.5 §5.2

---

### Q: What is the Service Path Explorer Canvas?

**ID:** NETIQ-STI-025 | **Audience:** NOC | **Type:** concept

**Answer:** An interactive canvas (branded 'NetIQ Stitching - NOC Operations Platform') to trace end-to-end connectivity from RAN through transport to the core. It has BOQ/KPI cards (Total Sites, Fully Stitched, Partial, Unresolved, Suggested, Stitch %), a Map View and Topology View (Nodes/Topo toggle), a Filters Intelligence panel, a site service panel with PATH and AUDIT actions, an animated service path view and a Report tab. It is used for impact analysis, dependency checks and spotting single points of failure.

**Also asked as:** "What is the stitching UI?" / "How do I view the topology?" / "What can I do on the canvas?"

**Keywords:** service path explorer, canvas, map view, topology, PATH, AUDIT, BOQ

**Source:** NETIQ User Manual v3.5 §4.2; NETIQ Solution Document v3.3 §18.4.3

---

### Q: How do I read the animated service path view?

**ID:** NETIQ-STI-026 | **Audience:** NOC | **Type:** how-to

**Answer:** It draws the selected service left to right in lanes: RAN, TRANSPORT, ACCESS, AGGREGATION and CORE. Connectors are labelled INTERNAL (RAN to MW/UBR/FTTH), INTERNAL (MW to Access POP), L2 CIRCUIT (Access POP to Aggregation router, dashed where no physical link) and L3 CIRCUIT (Aggregation router to Core). Badges show AI INFERRED (proposed by the audit engine), Default_AGW/Default_AP placeholders and MISSING_CORE. Open it from a site's PATH button or the Smart Filter prompt 'Inspect E2E service pipeline flow'.

**Also asked as:** "What do the labels in the animated path mean?" / "How do I see the E2E path for a site?" / "AI INFERRED badge"

**Keywords:** animated path, service path, lanes, INTERNAL, L2 circuit, L3 circuit, AI inferred

**Source:** NETIQ User Manual v3.5 §4.2.6; NETIQ Solution Document v3.3 §18.4.3

**Related:** NETIQ-STI-023

---

### Q: How do I check the blast radius before a maintenance window?

**ID:** NETIQ-STI-027 | **Audience:** NOC | **Type:** how-to

**Answer:** On the Service Path Explorer, search for the transport node (for example in the Filter Site ID box), select it and review every RAN site and service riding on it, along with the chain hops and status. This quantifies dependencies before approving the change.

**Also asked as:** "Impact analysis for a transport node" / "Which sites depend on this MW node?"

**Keywords:** impact analysis, blast radius, dependency, maintenance, transport node

**Source:** NETIQ User Manual v3.5 §4.2, §4.2.5

---

### Q: What is the Haversine formula used for in NETIQ?

**ID:** NETIQ-STI-028 | **Audience:** Planning | **Type:** design-rule

**Answer:** It computes the great-circle distance between two latitude/longitude points for the 100 m proximity search and the 6 km / 10 km geo-based AI searches: a = sin^2(dphi/2) + cos(phi1) x cos(phi2) x sin^2(dlambda/2); c = 2 x atan2(sqrt(a), sqrt(1-a)); d = R x c, with Earth mean radius R = 6,371,000 m. The documented worked example gives 1,115.755 m.

**Also asked as:** "How is distance calculated?" / "What formula does NETIQ use for proximity?"

**Keywords:** Haversine, distance, great-circle, 6371 km, geo search

**Source:** NETIQ Solution Document v3.3 §9.10.16

---

## AI Audit Engine for Stitching (AIA)

_Gap detection and auto-suggestion for Partial and Unresolved services._

### Q: What does the AI Audit Engine do in service stitching?

**ID:** NETIQ-AIA-001 | **Audience:** Ops | **Type:** concept

**Answer:** It runs after each stitching pass, inspects every service whose chain is incomplete (Partial or Unresolved), classifies the gap type, evaluates available evidence and generates a structured auto-suggestion with a confidence score. Results appear in the AI Audit report/dashboard and feed corrections back into the pipeline (L-6 to L-1 feedback loop). It uses inputs 1-11 and 13 of the stitching input set.

**Also asked as:** "What is the AI audit for stitching?" / "How does NETIQ suggest missing links?" / "AI audit feedback loop"

**Keywords:** AI audit engine, gap detection, auto-suggestion, confidence, partial, unresolved

**Source:** NETIQ Solution Document v3.3 §9.10.15, §9.10.3

**Related:** NETIQ-SCR-001, NETIQ-SCR-007

---

### Q: Which gap types does the AI Audit Engine detect?

**ID:** NETIQ-AIA-002 | **Audience:** Ops | **Type:** reference

**Answer:** MISSING RAN-TX (no MW/UBR/FTTH within 100 m; suggests the nearest MW node with a free port carrying the RAN VLAN), MISSING TX HOP (VLAN absent on an intermediate MW hop; hop flagged FREE INVENTORY and compared to planning), NO L2 (no Wireline node with the RAN VLAN after the TX chain), L2-AGW MISSING (no Wireline link; default cloud connection created), AGW L3-CORE ABSENT (IP Cloud created from the Core IP Report) and VLAN MISMATCH (best match below 70%; re-run at 50%).

**Also asked as:** "AI audit gap types" / "What are the AI audit flags?" / "What is MISSING RAN-TX?"

**Keywords:** gap types, MISSING TX HOP, NO L2, L2-AGW missing, VLAN mismatch, free inventory

**Source:** NETIQ Solution Document v3.3 §9.10.15.1; §15.9.5

---

### Q: What is Condition A (CoLoco_AP / CoLoco_AGW)?

**ID:** NETIQ-AIA-003 | **Audience:** Ops | **Type:** design-rule

**Answer:** For each RAN site, the AI first checks whether it is directly connected to an L2 or L3 by looking up the Site ID in the Wireline Node Report. If the site is present but neither VLAN nor Gateway IP/WAN IP match, the Wireline node is classified CoLoco_AP (co-located Access POP) and AGW discovery continues (RAN, L2, L3, Core). If VLAN plus Gateway IP, or only Gateway IP, matches, it is CoLoco_AGW and Core association follows directly (RAN, L3, Core).

**Also asked as:** "What is CoLoco_AP?" / "What does CoLoco_AGW mean?" / "Condition A"

**Keywords:** CoLoco_AP, CoLoco_AGW, condition A, co-located, access POP

**Source:** NETIQ Solution Document v3.3 §9.10.15.4

---

### Q: What is Condition 1 (Default L2) and when is Default_AP created?

**ID:** NETIQ-AIA-004 | **Audience:** Ops | **Type:** design-rule

**Answer:** Condition 1 applies only to unresolved cases where the first Wireline node reached through an MW/UBR/FTTH chain has no matching VLAN or Gateway IP in the IP_VLAN Report, or no Wireline node is reached at all. NETIQ assigns Default_AP as the L2 Site/Node ID so the case can be stitched and continues to AGW and Core discovery; if no AGW is found it creates Default_AGW (Default_AP, Default_AGW, Core). Default_AP is not created when the AGW's Wireline node is TIER T5, CSR or Node Domain CEN.

**Also asked as:** "When is Default_AP used?" / "Default L2 logic" / "Why is there no Default_AP for T5?"

**Keywords:** condition 1, Default_AP, Default_AGW, default L2, T5, CSR, CEN

**Source:** NETIQ Solution Document v3.3 §9.10.15.5

**Related:** NETIQ-AIA-011, NETIQ-STI-023

---

### Q: What is Condition 2 (planning and inventory matched)?

**ID:** NETIQ-AIA-005 | **Audience:** Planning | **Type:** design-rule

**Answer:** When no MW/UBR media is linked at the RAN site in inventory but planning and inventory agree. NETIQ finds MW (first priority) or UBR candidates, matches the RAN VLAN on port VLAN TRUNK at the far-end site, follows the MW Link Report (or UBR Link Report) hop by hop, and uses the Planned vs Configured Link Report (Planned HOP NMS STATUS = Unmatched, matched on the Site ID before '_') when no link exists. It checks free ports with the Key ID rule and validates TX frequency against RX frequency of the connected site; if frequencies differ the link is still created with the remark 'Link Identified but Frequency Not Matched'.

**Also asked as:** "Condition 2 explained" / "What does 'Frequency Not Matched' mean?"

**Keywords:** condition 2, planning matched, planned links, free port, frequency, remark

**Source:** NETIQ Solution Document v3.3 §9.10.15.6

---

### Q: What is Condition 3 (planning available, inventory mismatched)?

**ID:** NETIQ-AIA-006 | **Audience:** Planning | **Type:** design-rule

**Answer:** The RAN site is in the Planned vs Configured Link Report but its VLAN is not on any Port Report VLAN TRUNK. Case 1 (multiple far-end sites, VLAN not matched): use Key ID free-port detection and, if the VLAN is found, create the link on the planned sites with Node ID 'MW Inferred'; otherwise fall to Condition 4. Case 2 (several far ends carry the VLAN): pick the best candidate by distance, port availability, VLAN quality, node type closeness to L2/L3 and operational status. If no VLAN match or free port exists, the link is created from planning with the remark 'Link Created as per Planning; Inventory Mismatch (No VLAN match / No Free Port Found)'.

**Also asked as:** "Condition 3 explained" / "What is MW Inferred?" / "Inventory mismatch remark"

**Keywords:** condition 3, planning, inventory mismatch, MW Inferred, best candidate, priority

**Source:** NETIQ Solution Document v3.3 §9.10.15.7

**Related:** NETIQ-SCR-008

---

### Q: What is Condition 4 (geo-based mapping)?

**ID:** NETIQ-AIA-007 | **Audience:** Planning | **Type:** design-rule

**Answer:** Used when neither planning nor port data exists for the RAN site. NETIQ takes the RAN site latitude/longitude, searches all sites within 6 km for the nearest node carrying the RAN VLAN on an ETH/GETH/FETH/SFP port and creates the link with remark 'Link Created as per GEO Location Mapping using 6KM radius'. If none, it expands to 10 km (remark '...10KM radius'). If still none, the service is marked Unstitched with 'No Matching VLAN found within 10KM radius (Unstitched)'. Nearer sites get higher priority (0-2 km High/Very High, down to Very Low at 8-10 km).

**Also asked as:** "How does geo-based stitching work?" / "6 km and 10 km rule" / "What is Unstitched?"

**Keywords:** condition 4, geo mapping, 6 km, 10 km, unstitched, distance priority

**Source:** NETIQ Solution Document v3.3 §9.10.15.8

---

### Q: What is the Key ID logic for free-port detection?

**ID:** NETIQ-AIA-008 | **Audience:** Planning | **Type:** design-rule

**Answer:** Key IDs identify free ports on MW nodes. MW Key ID 1 and 2 are built from the MW Link Report (NE ID, Site, Equipment Model, Vendor plus cabinet/shelf/slot/index-on-slot/port of each end); the Port Report Key ID is built from Site ID, Node ID, Node Type, Manufacturer plus cabinet/shelf/slot/index/port. At the far-end site, if a Port Report Key matches an MW Key ID the port is in use; if there is no match the port is free. Links are only created on free ports; with none, Condition 4 applies.

**Also asked as:** "How does NETIQ know a port is free?" / "What is a Key ID?"

**Keywords:** key ID, free port, MW link report, port report, inventory

**Source:** NETIQ Solution Document v3.3 §9.10.15.3

**Related:** NETIQ-INV-003

---

### Q: What is a Free Inventory Audit?

**ID:** NETIQ-AIA-009 | **Audience:** Planning | **Type:** design-rule

**Answer:** Free inventory is an MW node with at least one port carrying an IF frequency (active radio hardware) but no corresponding entry in the MW Link Report for that port. NETIQ flags it as FREE_INVENTORY_FOUND and compares it against planning links between the RAN site and that node; if a planning link exists it auto-suggests creating the MW link. It publishes node ID, site, port, IF frequency, nearest RAN site, distance and planning-link reference.

**Also asked as:** "Free inventory meaning" / "FREE_INVENTORY_FOUND flag" / "Unconnected MW hardware"

**Keywords:** free inventory, IF frequency, FREE_INVENTORY_FOUND, planning link, MW hardware

**Source:** NETIQ Solution Document v3.3 §9.10.15.10

**Related:** NETIQ-AIA-010

---

### Q: What confidence does the AI assign to suggestions from free inventory?

**ID:** NETIQ-AIA-010 | **Audience:** Planning | **Type:** reference

**Answer:** Free inventory with a planning link is High (score 75-85); free inventory without a planning link is Medium (40-55); with neither, the result is Low, a cloud fallback with score 30.

**Also asked as:** "AI suggestion confidence levels" / "How reliable is a free inventory suggestion?"

**Keywords:** confidence, free inventory, planning link, 75-85, 40-55, 30

**Source:** NETIQ Solution Document v3.3 §9.10.15.10

**Related:** NETIQ-AIA-009

---

### Q: What are Infered_MW, Default_AP and Default_AGW?

**ID:** NETIQ-AIA-011 | **Audience:** NOC | **Type:** concept

**Answer:** They are AI placeholders. Infered_MW is the Node ID created (with default interface GETH) when no free SFP/FETH/GETH/ETH port exists for an internal connection. Default_AP and Default_AGW are placeholder L2 and L3 nodes created when no Access POP or AGW can be identified from configuration. All are shown with AI INFERRED badges and need field or data confirmation.

**Also asked as:** "What is Infered_MW?" / "Meaning of Default_AGW" / "Placeholder nodes in stitching"

**Keywords:** Infered_MW, Default_AP, Default_AGW, placeholder, AI inferred

**Source:** NETIQ Solution Document v3.3 §9.10.15.5, §9.10.15.9, Definitions; NETIQ User Manual v3.5 §4.2.6

**Related:** NETIQ-AIA-004

---

### Q: What does the AI Audit Report contain?

**ID:** NETIQ-AIA-012 | **Audience:** Ops | **Type:** reference

**Answer:** For every Partial/Unresolved service: Site ID and service key, gap type, condition applied (CoLoco_AP/CoLoco_AGW or Condition 1-4), evidence (Port Report Key ID, planning link, free inventory, geo distance), suggested link (A-End, Z-End, TXN Link ID), distance and priority band for geo cases, confidence score, standard remark and status (Suggested, Partial, Unresolved, Unstitched). Open it from a site's AUDIT button or the Report tab filtered to Partial/Unresolved.

**Also asked as:** "AI audit report fields" / "Where do I see AI suggestions for stitching?"

**Keywords:** AI audit report, evidence, suggested link, remark, status

**Source:** NETIQ Solution Document v3.3 §15.9.5; NETIQ User Manual v3.5 §5.3

---

## Stitch Status, Confidence Score & Flags (SCR)

_How stitching quality is scored and what each state and flag means._

### Q: What are the stitching states and score ranges?

**ID:** NETIQ-SCR-001 | **Audience:** All | **Type:** reference

**Answer:** STITCHED: score 80 or more, all major segments resolved with confirmed evidence. PARTIAL: 70-79, at least one gap filled by a cloud or suggestion. SUGGESTED: 30-69, AI-inferred path with TX_SUGGESTION_FLAG = Y requiring field confirmation. UNRESOLVED: below 30, cannot be traced beyond the last confirmed segment. UNSTITCHED: no link even with the 10 km geo-mapping rule. The canvas also shows Error when a conflict or data problem prevented stitching.

**Also asked as:** "What does Stitched, Partial, Suggested and Unresolved mean?" / "Score bands for stitching" / "What is an Error state?"

**Keywords:** stitch states, score ranges, stitched, partial, suggested, unresolved, unstitched, error

**Source:** NETIQ Solution Document v3.3 §9.10.17, §15.9.4; NETIQ User Manual v3.5 §4.2.5

**Related:** NETIQ-AIA-001, NETIQ-SCR-007

---

### Q: How is the confidence score calculated?

**ID:** NETIQ-SCR-002 | **Audience:** Planning | **Type:** design-rule

**Answer:** Each stitched service receives a composite 0-100 score that is the sum of per-segment scores. Examples: RAN-MW with 100% VLAN match 15 (probability match 10, none 0); RAN-UBR 5; UBR-MW verified 5; RAN-FTTH 15; direct RAN-Wireline 25; L2 with VLAN found 25 (VLAN not found but path exists 15, unresolved 0); AGW with Gateway IP plus VLAN 50 (Gateway IP only 45); AGW L3-only fallback 25/20/15/0; Core physical TX link 25, IP Cloud 20, not identified 0; MW hop chain 10 (VLAN-verified), 8 (continuous but non-VLAN), 5 (missing hops); UBR chain 5; FTTH chain 10.

**Also asked as:** "How is the score computed?" / "Score breakdown by segment" / "What gives 95 points?"

**Keywords:** confidence score, segment score, scoring, 0-100, AGW 50, Core 25

**Source:** NETIQ Solution Document v3.3 §9.10.17

---

### Q: What audit flags can appear on a stitched service?

**ID:** NETIQ-SCR-003 | **Audience:** Ops | **Type:** reference

**Answer:** VLAN_MISMATCH (best VLAN match below threshold, default 70%); NO_TX_NODE (no MW/UBR/FTTH at the site and no MW within 100 m); MISSING_TX_HOP (VLAN lost on an intermediate MW hop); MISSING_AGW (Gateway IP not under any WAN IP; Default_AGW assigned); SUSPECT_NON_LIVE_SERVICE (another IP/IP version of the same service is live on an AGW, this one is not); MISSING_CORE (destination node IP not in Core IP Report); FREE_INVENTORY_FOUND (MW port with IF frequency but no link); and TX_SUGGESTION_FLAG = Y (AI-suggested link).

**Also asked as:** "List the stitching flags" / "What does NO_TX_NODE mean?" / "What is TX_SUGGESTION_FLAG?"

**Keywords:** audit flags, VLAN_MISMATCH, NO_TX_NODE, MISSING_TX_HOP, MISSING_AGW, MISSING_CORE, FREE_INVENTORY_FOUND

**Source:** NETIQ Solution Document v3.3 §15.9.4; NETIQ User Manual v3.5 §4.2.7

---

### Q: What are the stitching KPIs, targets and alert thresholds?

**ID:** NETIQ-SCR-004 | **Audience:** Mgmt | **Type:** reference

**Answer:** Per circle per cycle: Stitching Coverage % (STITCHED / total RAN IPs) target 85% or more, alert below 70%; TX Discovery Rate 90% or more, alert below 75%; VLAN Match Rate (services with 70% or more match) 95% or more, alert below 85%; L2 Resolution Rate 88% or more, alert below 75%; Cloud Connection Rate 10% or less, alert above 25%; Audit Flag Resolution Rate (30-day) 80% or more, alert below 60%; Average Confidence Score 78 or more, alert below 65; Free Inventory Detected tracked weekly (alert above 5% of MW nodes).

**Also asked as:** "Stitching coverage target" / "What is a good average confidence score?" / "Data quality KPIs for stitching"

**Keywords:** stitching KPIs, coverage, TX discovery rate, VLAN match rate, L2 resolution, cloud rate, thresholds

**Source:** NETIQ Solution Document v3.3 §18.4.1

---

### Q: What is Stitch %?

**ID:** NETIQ-SCR-005 | **Audience:** Mgmt | **Type:** design-rule

**Answer:** On the Service Path Explorer, Stitch % is the share of fully stitched sites out of total sites. In the data-quality KPI set, Stitching Coverage % is STITCHED services divided by total RAN IPs (services) x 100, with a target of at least 85%. Management uses the trend to report service readiness with evidence.

**Also asked as:** "How is stitch percentage calculated?" / "Stitch % vs stitching coverage"

**Keywords:** stitch percentage, coverage, fully stitched, KPI

**Source:** NETIQ User Manual v3.5 §4.2.1, §9 Q10; NETIQ Solution Document v3.3 §18.4.1

---

### Q: What widgets does the Service Stitching dashboard provide?

**ID:** NETIQ-SCR-006 | **Audience:** NOC | **Type:** reference

**Answer:** Stitching status distribution per circle, technology and plane; confidence score profile and trend; transmission media mix (direct Wireline, MW, UBR, FTTH, proximity, AI-inferred); AI audit flags with 30-day resolution rate; AI suggestions from Conditions 1-4 for accept/reject; cloud dependency (L2-AGW and AGW-Core segments); and drill-down circle, site, service, hop linked to the report, topology and map views.

**Also asked as:** "Stitching dashboard widgets" / "Media mix chart"

**Keywords:** stitching dashboard, widgets, media mix, cloud dependency, AI suggestions

**Source:** NETIQ Solution Document v3.3 §18.4.2

---

### Q: Why is my service Partial or Unresolved and how do I improve it?

**ID:** NETIQ-SCR-007 | **Audience:** Ops | **Type:** troubleshooting

**Answer:** Partial means at least one segment used an IP cloud or suggestion; Unresolved means the path could not be traced beyond the last confirmed segment. Check the flag and remark: VLAN_MISMATCH (RAN VLAN not on the transmission port), NO_TX_NODE (no transmission node at/near site), MISSING_TX_HOP (VLAN lost on a hop), MISSING_AGW (Gateway IP not on any Wireline WAN IP) or MISSING_CORE (destination IP not in the Core IP Report). Fix the source data, then confirm the status improves after the next cycle; stitching completeness depends on source data quality.

**Also asked as:** "How to improve stitch percentage?" / "Why is a service unresolved?" / "Fix partial stitching"

**Keywords:** partial, unresolved, troubleshooting, improve stitching, flags, source data

**Source:** NETIQ User Manual v3.5 §4.2.7; NETIQ Solution Document v3.3 §4.3, §15.9.4

**Related:** NETIQ-AIA-001, NETIQ-SCR-001

---

### Q: What does 'Link Created as per Planning; Inventory Mismatch' mean?

**ID:** NETIQ-SCR-008 | **Audience:** Planning | **Type:** reference

**Answer:** A link was taken from planning data because port inventory does not confirm it (no VLAN match or no free port found). It is created to continue the path but flagged to highlight the data inconsistency between planning and inventory. Validate it in the field or correct the inventory.

**Also asked as:** "Planning inventory mismatch remark" / "Link created as per planning"

**Keywords:** remark, planning, inventory mismatch, flag

**Source:** NETIQ Solution Document v3.3 §9.10.15.7; NETIQ User Manual v3.5 §4.2.7

**Related:** NETIQ-AIA-006

---

## AI Inference & AI Intelligence (BETA) (AIN)

_AI Insights Engine, inference accuracy and the eight AI/ML audit dashboards._

### Q: What is the AI Insights Engine?

**ID:** NETIQ-AIN-001 | **Audience:** All | **Type:** concept

**Answer:** NETIQ's explainable intelligence layer that works only on your own network data. It infers Site, Node and Cell relationships and attributes where the raw dump is silent, each with a confidence score and a plain-language remark. Discovered facts are never silently mixed with inferred ones, and accepted inferences feed back into stitching, improving the stitch percentage cycle over cycle. Reports are under AI Insights Engine, RAN Inference Intelligence: Site, Node and Cell Inference.

**Also asked as:** "What is AI inference?" / "How does NETIQ use AI?" / "Is the AI explainable?"

**Keywords:** AI insights engine, inference, confidence, explainable, site inference, node inference, cell inference

**Source:** NETIQ Solution Document v3.3 §9.9; NETIQ User Manual v3.5 §4.5, §1.3

**Related:** NETIQ-AIN-013

---

### Q: What does the AI Inference card on the RAN dashboard show?

**ID:** NETIQ-AIN-002 | **Audience:** NOC | **Type:** reference

**Answer:** Site, Node and Cell tabs report the AI-inferred count and a breakdown, for example Total Sites, Correct Sites, Node-Only and Cell-Only, with percentages and a confidence bar. It shows the accuracy split between directly discovered and inferred relationships.

**Also asked as:** "AI inference accuracy split" / "What is node-only and cell-only?"

**Keywords:** AI inference card, correct sites, node-only, cell-only, accuracy

**Source:** NETIQ User Manual v3.5 §4.1.1.5; NETIQ Solution Document v3.3 §9.9

---

### Q: What is AI Intelligence (BETA)?

**ID:** NETIQ-AIN-003 | **Audience:** All | **Type:** concept

**Answer:** A sub-module of the Network Intelligence View with eight AI/ML audit dashboards: Degraded Link Audit, Frequency Deviation (Planned vs Configured), Missing Parameter Prediction, Duplicate Node & Cell Resolution, Baseline Parameter Audit, Cell-to-RU Mapping Suggestion, 5G Upgrade Readiness and GPS Suggestion. Each pairs a deterministic audit rule with an AI/ML prediction, separates discovered from inferred values and exposes drillable, exportable reports. Because it is BETA, validate counts and model outputs before using them as a source of truth.

**Also asked as:** "What AI dashboards are available?" / "Is AI Intelligence production ready?" / "List the AI/ML audits"

**Keywords:** AI Intelligence, BETA, AI/ML audits, dashboards, eight audits

**Source:** NETIQ Solution Document v3.3 §18.5; NETIQ User Manual v3.5 §4.1.6

---

### Q: How does the Degraded Link Audit work?

**ID:** NETIQ-AIN-004 | **Audience:** NOC | **Type:** design-rule

**Answer:** It reads status signals of every active MW/UBR hop from the latest link inventory, maps each hop to a signal class (Strong Signal, Nodes In Range, Holding Status, Improving Signal, Recovering States, Holding Steady or Critical Down Signal) using the previous cycle to detect improvement, and rolls them up into Healthy, At Risk or Degraded. The dashboard shows the Link Health Status Mix, signal-class counts and Operational links % (healthy hops / total hops x 100).

**Also asked as:** "Degraded link audit logic" / "What are the signal classes?" / "How is link health computed?"

**Keywords:** degraded link audit, signal class, healthy, at risk, degraded, MW, UBR

**Source:** NETIQ Solution Document v3.3 §18.5.1; NETIQ User Manual v3.5 §4.1.6.1

**Related:** NETIQ-DSH-009, NETIQ-GEN-004, NETIQ-GLO-005

---

### Q: How does the Frequency Deviation dashboard work?

**ID:** NETIQ-AIN-005 | **Audience:** Planning | **Type:** design-rule

**Answer:** It compares live MW/UBR link configuration with the planned MIDS design on frequency, channel spacing, modulation and HOP type, classifies every deviation (Missing Link, Unplanned Link, Modulation/Frequency/Channel Spacing Deviation and combinations, Out of Scope), ranks the categories and shows the top 10 plus Other. The Validation Outcome tile splits compared links into validated and deviating.

**Also asked as:** "Frequency deviation planned vs configured" / "How to find link deviations?"

**Keywords:** frequency deviation, planned vs configured, deviation category, MIDS

**Source:** NETIQ Solution Document v3.3 §18.5.2; NETIQ User Manual v3.5 §4.1.6.2

**Related:** NETIQ-TXN-007, NETIQ-INV-007

---

### Q: How does Missing Parameter Prediction work?

**ID:** NETIQ-AIN-006 | **Audience:** Audit | **Type:** design-rule

**Answer:** The Missing Field Detector finds missing mandatory attributes (EARFCN, MCC/MNC, TAC, latitude/longitude, cabinet product name and so on). For each gap NETIQ derives candidate values from sibling cells of the same node, the same site, the same band and other source reports, selects the most probable value and attaches a confidence and the evidence. Predictions are grouped by attribute set and by type (2G, 4G, 5G, HW). Fix the CM data at source; predicted values are not written back without acceptance.

**Also asked as:** "Predict missing EARFCN" / "How does NETIQ predict missing attributes?"

**Keywords:** missing parameter prediction, EARFCN, MCC, TAC, prediction, evidence, confidence

**Source:** NETIQ Solution Document v3.3 §18.5.3; NETIQ User Manual v3.5 §4.1.6.3

**Related:** NETIQ-AUD-014, NETIQ-GLO-004, NETIQ-INV-004

---

### Q: How does Duplicate Node & Cell Resolution decide which record is correct?

**ID:** NETIQ-AIN-007 | **Audience:** Audit | **Type:** design-rule

**Answer:** It forms duplicate groups on the key (Node ID or Cell Name), scores each member on evidence (presence in the latest dump, NMS ownership, site consistency, cell-to-node mapping and naming rules) and classifies each group as Correct ID/Cell Identified, Having Issue, Removed (stale member) or Manual Validation Required. Tiles show Total Nodes, Dup Node IDs, Dup Cells and Correct Records. Unresolvable groups are routed to the owning team.

**Also asked as:** "Which duplicate is correct?" / "Manual validation required meaning"

**Keywords:** duplicate resolution, correct record, stale member, manual validation, node ID, cell name

**Source:** NETIQ Solution Document v3.3 §18.5.4; NETIQ User Manual v3.5 §4.1.6.4

---

### Q: What is the Baseline Parameter Audit?

**ID:** NETIQ-AIN-008 | **Audience:** Planning | **Type:** concept

**Answer:** It selects the approved baseline for each cell by technology, band and vendor (from the Reporting and Attribute Details workbook), compares configured values such as Bandwidth DL/UL and EARFCN DL/UL with the baseline, counts deviations per parameter and lists the deviating cells for a parameter-correction work order.

**Also asked as:** "Baseline deviation audit" / "Which cells deviate from baseline?"

**Keywords:** baseline parameter audit, bandwidth, EARFCN, deviation, baseline

**Source:** NETIQ Solution Document v3.3 §18.5.5; NETIQ User Manual v3.5 §4.1.6.5

---

### Q: How does the Cell-to-RU Mapping Suggestion work?

**ID:** NETIQ-AIN-009 | **Audience:** Planning | **Type:** design-rule

**Answer:** It audits cells for a mapped radio unit (Hardware Mapped vs Missing HW). For cells without hardware, it learns RRU models used by comparable cells (same node, band, vendor) across reports ('model learning: multi-report frequency'), suggests the most frequent model with a High or Low confidence class and ranks the suggested RRU types. The dashboard shows Mapping Completeness (Hardware Mapped, AI Auto-Suggested High/Low Confidence, Unmapped Missing HW).

**Also asked as:** "Suggest RRU model for unmapped cells" / "AI auto-suggested high confidence meaning"

**Keywords:** cell to RU, RRU suggestion, model learning, confidence class, missing HW

**Source:** NETIQ Solution Document v3.3 §18.5.6; NETIQ User Manual v3.5 §4.1.6.6

---

### Q: What does 5G Upgrade Readiness show?

**ID:** NETIQ-AIN-010 | **Audience:** Planning | **Type:** concept

**Answer:** It classifies every site (5G Active, 5G Not Available, Ghost Node, Site No Longer Present, Unknown Hardware), checks installed hardware of target sites against 5G compatibility, and classifies the upgrade path: Ready to Upgrade to 5G, HW Available/Compatible (SW Upgrade), HW Not Available/Compatible (HW Swap), Partial Upgrade Possible or Unknown Hardware. Useful for 5G rollout planning.

**Also asked as:** "Which sites can be upgraded to 5G?" / "5G readiness classes" / "Technology upgrade suggestion"

**Keywords:** 5G upgrade readiness, SW upgrade, HW swap, 5G rollout, technology upgrade

**Source:** NETIQ Solution Document v3.3 §18.5.7; NETIQ User Manual v3.5 §4.1.6.7

---

### Q: How does GPS Suggestion impute missing coordinates?

**ID:** NETIQ-AIN-011 | **Audience:** Ops | **Type:** design-rule

**Answer:** For sites with missing or invalid GPS (GPS Accuracy Audit), NETIQ searches other source reports in order (RAN Site Report, 2G/4G/5G Cell Reports, Transmission Site Report, Planned vs Configured Link Report), takes valid coordinates for the same site and records the source report. Sites with no source are 'GPS Not Identified'. Summaries cover GPS Suggested %, source-wise counts, technology-wise status and circle-wise success rate.

**Also asked as:** "How does NETIQ suggest GPS?" / "What is GPS Not Identified?"

**Keywords:** GPS suggestion, imputation, source report, GPS not identified, success rate

**Source:** NETIQ Solution Document v3.3 §18.5.8; NETIQ User Manual v3.5 §4.1.6.8

---

### Q: How are AI suggestions governed?

**ID:** NETIQ-AIN-012 | **Audience:** Audit | **Type:** concept

**Answer:** Discovered and inferred values are stored and shown separately; every suggestion carries a confidence (score or High/Low class) and its evidence; suggestions are reviewed in the dashboard drill-down and only accepted values are written back with source tagging; results the model cannot resolve go to manual validation by the owning team; and counts and models are validated against field data before AI Intelligence leaves BETA.

**Also asked as:** "Are AI suggestions applied automatically?" / "How is AI output validated?"

**Keywords:** AI governance, acceptance, separation, manual validation, BETA

**Source:** NETIQ Solution Document v3.3 §18.5.9

---

### Q: What do Site, Node and Cell Inference reports contain?

**ID:** NETIQ-AIN-013 | **Audience:** Audit | **Type:** reference

**Answer:** Site Inference predicts the correct Site ID for each record with a remark (for example 'Site ID correct - no issue') and proposes a Site ID where the dump leaves it unidentified. Node and Cell Inference complete node and cell relationships and attributes with a confidence and remark. Typical columns: Circle, predicted/inferred identity, Node/Cell Name, Remark, Vendor, EMS IP.

**Also asked as:** "Site inference report columns" / "What is predicted site ID?"

**Keywords:** site inference, node inference, cell inference, predicted site ID, remark

**Source:** NETIQ User Manual v3.5 §4.5.1-4.5.3

**Related:** NETIQ-AIN-001

---

## Inventory Repository, Reports & Decommission Ledger (INV)

_Network Truth Repository, report schemas and retired-asset history._

### Q: What is the Network Truth Repository?

**ID:** NETIQ-INV-001 | **Audience:** All | **Type:** concept

**Answer:** The normalised, audited single-source-of-truth inventory for nodes, cells, hardware, ports, links and IP across every domain, organised as RAN, TXN (Transport), FTTH and Wireline repositories. Each record carries source, site source and insert/update provenance. All grids share the common toolbar (columns, filters, export, advanced query).

**Also asked as:** "What is the single source of truth?" / "Where is the inventory?" / "What reports are in the repository?"

**Keywords:** network truth repository, inventory, RAN repository, TXN repository, FTTH, wireline

**Source:** NETIQ User Manual v3.5 §4.4; NETIQ Solution Document v3.3 §3.1.7

**Related:** NETIQ-INV-003, NETIQ-GEN-004, NETIQ-GLO-005

---

### Q: Which reports are in the RAN Repository?

**ID:** NETIQ-INV-002 | **Audience:** Ops | **Type:** reference

**Answer:** Node reports (All Nodes, BTS 2G, eNodeB 4G, gNodeB 5G, SRAN, Ghost Nodes), Cell reports (2G, 4G, 5G), Hardware Report, Cabinet Report, IP Data Report and Core / Network IP Report. Node reports show Circle, Node ID, Node Name, Site ID, Site Source, Latitude, Longitude and Location Source.

**Also asked as:** "RAN inventory reports" / "Where do I find eNodeB data?"

**Keywords:** RAN repository, node report, cell report, hardware report, cabinet report, IP data, core IP

**Source:** NETIQ User Manual v3.5 §4.4.1

**Related:** NETIQ-INV-004

---

### Q: Which reports are in the TXN, FTTH and Wireline repositories?

**ID:** NETIQ-INV-003 | **Audience:** Ops | **Type:** reference

**Answer:** TXN: Site, Node, Hardware, Port, MW Link, UBR Link, IP, VLAN and Planned vs Configured Link reports. FTTH: Node Inventory, Hardware, Link and Port reports. Wireline: Node Inventory, Hardware, Port, Logical Inventory, VLAN Report and Link Inventory. The Wireline logical inventory is the largest dataset (millions of rows) and is served with server-side pagination.

**Also asked as:** "Where are MW links?" / "Wireline inventory reports" / "FTTH reports"

**Keywords:** TXN repository, MW link report, UBR link report, port report, VLAN report, FTTH, wireline

**Source:** NETIQ User Manual v3.5 §4.4.2-4.4.4; NETIQ Solution Document v3.3 §10.7

**Related:** NETIQ-INV-001, NETIQ-AIA-008, NETIQ-GEN-004

---

### Q: What key fields are in the RAN Node and 4G Cell reports?

**ID:** NETIQ-INV-004 | **Audience:** Ops | **Type:** reference

**Answer:** Node Report: Node_ID (for example MRBTS-901305), Node_Name, Vendor, Technology (highest present), Latitude, Longitude, Cabinet_Model, Product_Code, Primary_IP and more. 4G Cell Report: Node ID/Name, Site ID, Site ID Source, EnodeB ID/Name, MCC, MNC, Cell Name, Cell ID, TAC, EARFCN UL/DL, Bandwidth UL/DL, plus CGI, admin status and duplex mode. 5G and 2G schemas are defined analogously in the Solution Document section 15.

**Also asked as:** "RAN node report columns" / "What fields are in the cell report?" / "Report schema"

**Keywords:** reporting schema, node report, cell report, columns, TAC, EARFCN, CGI

**Source:** NETIQ Solution Document v3.3 §15.1-15.2

**Related:** NETIQ-GLO-004, NETIQ-AIN-006, NETIQ-AUD-014

---

### Q: What is the Decommission Ledger?

**ID:** NETIQ-INV-005 | **Audience:** Audit | **Type:** concept

**Answer:** A complete, auditable log of retired, deleted and decommissioned assets across RAN (NMS, Site, Node, Cell, Hardware inventory) and Transport (NMS, Site, Node, Hardware). Entities that disappear from a dump (the Deleted count on dashboards) land here. A date-range control (All Time or Days) answers questions such as 'what was decommissioned this week?' and supports tear-down reconciliation for change tickets.

**Also asked as:** "Where are deleted nodes?" / "How do I verify a site tear-down?" / "What is the Deleted Reports view?"

**Keywords:** decommission ledger, deleted reports, decommissioned, tear-down, date range

**Source:** NETIQ User Manual v3.5 §4.6; NETIQ Solution Document v3.3 §3.1.7

---

### Q: The Decommission Ledger shows 'No data found'. What should I do?

**ID:** NETIQ-INV-006 | **Audience:** Audit | **Type:** troubleshooting

**Answer:** Widen the date range (for example All Time) or clear the column filters. The combination of filters may be too narrow for the chosen period or circle.

**Also asked as:** "No data found in ledger" / "Empty deleted report"

**Keywords:** no data found, ledger, date range, filters

**Source:** NETIQ User Manual v3.5 §4.6.3, §8.2

---

### Q: What is the Planned vs Configured Link Report?

**ID:** NETIQ-INV-007 | **Audience:** Planning | **Type:** reference

**Answer:** A transport report comparing the planned link design (MIDS plan) with what is discovered in the network. It lists planned HOP sites, NMS status (Matched / Unmatched), frequency, channel spacing, modulation and HOP type. It underpins Deployment Compliance, the Missing Txn Links insight and the AI Frequency Deviation dashboard, and the stitching AI audit uses it as supporting evidence.

**Also asked as:** "Planned vs configured report fields" / "What is MIDS?"

**Keywords:** planned vs configured, MIDS, planned links, hop, report

**Source:** NETIQ Solution Document v3.3 §17.8, §9.10.4; NETIQ User Manual v3.5 §4.4.2.9

**Related:** NETIQ-AIN-005, NETIQ-TXN-007

---

### Q: What does the MW Link Report contain?

**ID:** NETIQ-INV-008 | **Audience:** Planning | **Type:** reference

**Answer:** Link identity and the two sites and NEs (Link ID, Site 1/Site 2, NE ID 1/2), TX/RX frequency channels, cabinet/shelf/slot/index/port details of each end and D-XPIC TX/RX frequency, along with capacity, modulation, link configuration (for example 1+0, 1+1, XPIC) and status. It is a primary input for hop-chain tracing in stitching.

**Also asked as:** "MW link report columns" / "Which MW link fields exist?"

**Keywords:** MW link report, link ID, NE ID, frequency, XPIC, slot, port

**Source:** NETIQ Solution Document v3.3 §15.6.4, §9.10.4; NETIQ User Manual v3.5 §4.4.2.5

---

## Operations, Monitoring, Support & DR (OPS)

_Daily routines, support tiers, backup/DR and items that are deployment-specific._

### Q: What is the recommended daily operational routine?

**ID:** NETIQ-OPS-001 | **Audience:** NOC | **Type:** how-to

**Answer:** Confirm each domain's latest collection cycle completed (scheduler record / last-refreshed); review discovery counts and the NMS health gauge for unexpected drops; work new high-severity audit findings and coordinate source corrections; confirm corrected findings clear next cycle and track the stitch-percentage trend; review the reject summary and re-ingest corrected files where needed.

**Also asked as:** "Daily checklist for NOC" / "What should I check every morning?" / "Operational runbook"

**Keywords:** daily routine, runbook, NOC, health gauge, scheduler, rejects

**Source:** NETIQ Solution Document v3.3 §27.1, §27.4; NETIQ User Manual v3.5 §1.2.2

---

### Q: How is platform health monitored?

**ID:** NETIQ-OPS-002 | **Audience:** NOC | **Type:** reference

**Answer:** Through the NMS health gauge and the 'All systems operational' status tile (with last-updated time), the scheduler-completion record per domain, records loaded/rejected per cycle, audit-finding volume by severity and Stitch %. These are complemented by infrastructure-level monitoring of the tiers.

**Also asked as:** "How do I know NETIQ is healthy?" / "Monitoring metrics"

**Keywords:** monitoring, health gauge, scheduler completion, metrics, all systems operational

**Source:** NETIQ Solution Document v3.3 §27.2, §27.5, §24.6

---

### Q: What is the support model and who handles which tier?

**ID:** NETIQ-OPS-003 | **Audience:** Admin | **Type:** deployment-specific

**Answer:** L1: first-line triage of anomalies and user queries (NOC/Operations). L2: data-quality investigation and source-correction coordination (Operations/Audit/Admin). L3: platform, rule and configuration issues (Avendum support / Super Admin). Response and resolution SLAs per severity and tier are to be agreed with the customer and recorded; they are not fixed in the documents.

**Also asked as:** "Who do I contact for support?" / "What are the SLAs?" / "L1 L2 L3 support"

**Keywords:** support model, L1, L2, L3, SLA, escalation, Avendum support

**Source:** NETIQ Solution Document v3.3 §27.3; NETIQ User Manual v3.5 §10

**Related:** NETIQ-GLO-002, NETIQ-STI-015

---

### Q: What are the support contact details?

**ID:** NETIQ-OPS-004 | **Audience:** All | **Type:** deployment-specific

**Answer:** The user manual leaves contact fields (help channels and escalation contacts) as placeholders to be completed per organisation. In the meantime, contact your NETIQ administrator, who can escalate to the Avendum support team. For problems not covered by the manual, the same route applies.

**Also asked as:** "Support email or phone" / "Escalation contacts" / "Who do I call?"

**Keywords:** support contact, escalation, administrator, helpdesk

**Source:** NETIQ User Manual v3.5 §9 Q20, §10

---

### Q: What is the backup, RPO, RTO and disaster recovery approach?

**ID:** NETIQ-OPS-005 | **Audience:** Admin | **Type:** deployment-specific

**Answer:** Regular backup of inventory, audit results and configuration (sources, rules, schedules, users/roles). To recover, restore the latest backup to a standby environment and re-run collection; because ingestion is idempotent, this re-establishes the live state without duplication. Concrete backup frequency, RPO/RTO targets and DR topology are to be agreed with the customer and are not fixed in the document.

**Also asked as:** "What is the RPO and RTO?" / "How do we recover from failure?" / "Backup procedure"

**Keywords:** backup, restore, RPO, RTO, disaster recovery, standby

**Source:** NETIQ Solution Document v3.3 §23, §27.6

**Related:** NETIQ-GLO-007

---

### Q: Is NETIQ highly available?

**ID:** NETIQ-OPS-006 | **Audience:** Admin | **Type:** deployment-specific

**Answer:** The design targets high availability for the web/application tier (minimum 99.5% console uptime target), while the processing tier runs on the collection schedule and tolerates a missed cycle without data loss. Exact HA topology (co-located or separated tiers) depends on the deployment.

**Also asked as:** "HA architecture" / "Is there redundancy?" / "What is the uptime SLA?"

**Keywords:** high availability, 99.5, redundancy, uptime

**Source:** NETIQ Solution Document v3.3 §23.1, §21, §24.4

---

### Q: What are the main risks and their mitigations?

**ID:** NETIQ-OPS-007 | **Audience:** Mgmt | **Type:** reference

**Answer:** Incomplete/delayed source exports (monitor scheduler, alert on missing cycles, agree source SLAs); poor source data quality (continuous audits, fix-at-source, trend tracking); inconsistent identifiers across sources (normalisation, duplicate and mapping audits, AI inference); volume growth (capacity planning, server-side pagination, scale infrastructure); and RBAC misconfiguration (periodic access reviews, least privilege).

**Also asked as:** "Project risks" / "What can go wrong?"

**Keywords:** risks, mitigation, data quality, RBAC, volume

**Source:** NETIQ Solution Document v3.3 §31

---

### Q: What training is available for NETIQ?

**ID:** NETIQ-OPS-008 | **Audience:** Mgmt | **Type:** reference

**Answer:** Role-based training anchored on the User Manual: end users/read-only (navigation, dashboards, exports), operations/NOC (monitoring, triage, validation, escalation), audit (running and interpreting audits, exception handling) and administrators (users/roles, scheduler, rules, configuration). Knowledge transfer covers architecture, data flows, rule configuration and runbooks. New users can also launch the in-app Platform Tour.

**Also asked as:** "How do we train our team?" / "Is there user documentation?"

**Keywords:** training, knowledge transfer, user manual, platform tour

**Source:** NETIQ Solution Document v3.3 §29; NETIQ User Manual v3.5 §10.4

**Related:** NETIQ-UI-010

---

### Q: How does cutover work, and is there a risk to existing systems?

**ID:** NETIQ-OPS-009 | **Audience:** Mgmt | **Type:** concept

**Answer:** Because NETIQ is read-and-reconcile and consumes source exports, cutover is low-risk: collection is enabled per domain, the first cycles establish the baseline, and audits and stitching improve as source data is corrected. No destructive migration of source systems is required.

**Also asked as:** "Is migration needed?" / "Will go-live affect our NMS?"

**Keywords:** cutover, migration, go-live, baseline, low risk

**Source:** NETIQ Solution Document v3.3 §28.1

---

## KPIs, Acceptance & Testing (KPI)

_Acceptance criteria, test cases and how delivery is signed off._

### Q: What are the acceptance criteria for NETIQ?

**ID:** NETIQ-KPI-001 | **Audience:** Mgmt | **Type:** reference

**Answer:** Parser accuracy of 99% or more per vendor/technology; audit detection rate of 100% for seeded High-severity issues and 98% or more for seeded Medium severity; and all mandatory columns populated in the Node/Cell/HW report schemas. Acceptance is validated through the defined test cases and UAT on production-like data against functional coverage, reporting accuracy and non-functional targets.

**Also asked as:** "How is NETIQ accepted?" / "What are the UAT criteria?" / "Parser accuracy target"

**Keywords:** acceptance criteria, KPIs, parser accuracy, detection rate, UAT

**Source:** NETIQ Solution Document v3.3 §19, §32

---

### Q: What test cases are defined for NETIQ?

**ID:** NETIQ-KPI-002 | **Audience:** Audit | **Type:** reference

**Answer:** PAN-01 (PAN India totals equal the sum of Circle totals, 100% match); circle-level aggregation and vendor/technology splits; SITE-01 to SITE-05 (site count, no orphan sites, cells per site, GPS completeness, Site ID consistency between node and cell); node and cell availability; VAL-06 to VAL-11 duplicate checks (node name/ID, cell name/ID, IP, VLAN); VAL-12/13 missing class and attribute; VAL-22/23 cabinet and board completeness; and VAL-26/27 GPS completeness and range.

**Also asked as:** "List the test cases" / "What is PAN-01?" / "What is VAL-26?"

**Keywords:** test cases, PAN-01, SITE-01, VAL-06, VAL-26, validation

**Source:** NETIQ Solution Document v3.3 §20

---

### Q: Who signs off and what is the UAT approach?

**ID:** NETIQ-KPI-003 | **Audience:** Mgmt | **Type:** reference

**Answer:** UAT validates against production-like data in the UAT environment: functional coverage (section 12), reporting and audit accuracy (sections 15-18) and non-functional targets (sections 21-22). Sign-off roles are Solution Architect, Operations/NOC Lead, Delivery Manager and Customer SPOC, who accepts for production use.

**Also asked as:** "UAT process" / "Who approves go-live?"

**Keywords:** UAT, sign-off, acceptance, customer SPOC, delivery manager

**Source:** NETIQ Solution Document v3.3 §32

---

## Troubleshooting & Common Issues (TRB)

_Typical user problems and what to do._

### Q: A dashboard or the Service Path Explorer does not render correctly. What should I check?

**ID:** NETIQ-TRB-001 | **Audience:** All | **Type:** troubleshooting

**Answer:** Use a supported, current browser (Chrome, Edge or Firefox; not Internet Explorer); hard-refresh or clear the cache; reset browser zoom to 100% and use at least 1366x768 (1920x1080 recommended); disable ad-blockers or script-blocking extensions, or test in a private/incognito window; and allow pop-ups and downloads for the NETIQ site.

**Also asked as:** "Dashboard is blank" / "Screen is clipped" / "Page not loading properly"

**Keywords:** browser issues, rendering, cache, zoom, extensions, troubleshooting

**Source:** NETIQ User Manual v3.5 §8.3

---

### Q: I see 'No data for the selected filters'. What does it mean?

**ID:** NETIQ-TRB-002 | **Audience:** All | **Type:** troubleshooting

**Answer:** The filter combination returns nothing, often because the date range, circle or technology is too narrow. Widen or clear the filters (use Reset All) and try again.

**Also asked as:** "No data message" / "Report shows empty"

**Keywords:** no data, filters, reset all, empty report

**Source:** NETIQ User Manual v3.5 §8.2

---

### Q: Export failed or the file did not download. What should I do?

**ID:** NETIQ-TRB-003 | **Audience:** All | **Type:** troubleshooting

**Answer:** Retry the export. If it recurs, check that the browser is not blocking pop-ups or downloads for the NETIQ site (see browser issues) and that the filtered result set is not excessively large. If it persists, note the exact message and screen and pass it to support.

**Also asked as:** "Export not working" / "Download blocked"

**Keywords:** export failed, download blocked, pop-up, troubleshooting

**Source:** NETIQ User Manual v3.5 §8.2-8.3

---

### Q: I get 'Unable to load' or 'something went wrong'. What now?

**ID:** NETIQ-TRB-004 | **Audience:** All | **Type:** troubleshooting

**Answer:** It is usually a transient loading problem. Refresh the page; if it continues, clear the browser cache or sign out and back in. If it still persists, report the exact wording and the screen to support.

**Also asked as:** "Something went wrong error" / "Page unable to load"

**Keywords:** unable to load, error message, refresh, troubleshooting

**Source:** NETIQ User Manual v3.5 §8.2

---

### Q: My session expired. What should I do?

**ID:** NETIQ-TRB-005 | **Audience:** All | **Type:** troubleshooting

**Answer:** Sessions expire after a period of inactivity for security and return you to the login screen. Sign in again. The exact timeout is set by deployment policy.

**Also asked as:** "Session timeout message" / "Logged out automatically"

**Keywords:** session expired, timeout, login

**Source:** NETIQ Solution Document v3.3 §25; NETIQ User Manual v3.5 §8.2

---

### Q: The data in NETIQ differs from my NMS. Why?

**ID:** NETIQ-TRB-006 | **Audience:** Ops | **Type:** troubleshooting

**Answer:** NETIQ reflects the last collected CM dump, so data freshness is bounded by the collection cadence. Differences can also be genuine: NETIQ reconciles multiple sources and flags ghost elements, duplicates, naming and mapping inconsistencies that the individual NMS may not show. Check the last-updated indicator, the NMS Updated/Non-Updated status for that NMS and the relevant audit report; correct at source and confirm after the next cycle.

**Also asked as:** "Counts do not match my NMS" / "Why is a node missing?" / "NETIQ vs OSS mismatch"

**Keywords:** data mismatch, NMS difference, dump, freshness, reconciliation

**Source:** NETIQ User Manual v3.5 §9 Q1; NETIQ Solution Document v3.3 §2, §10.9

---

### Q: Why does a finding still appear after the data was fixed?

**ID:** NETIQ-TRB-007 | **Audience:** Audit | **Type:** troubleshooting

**Answer:** The corrected CM dump has not been ingested yet. Findings clear automatically on the next cycle after the corrected data is ingested. Confirm the NMS dump was refreshed and check the reject summary in case the corrected rows were rejected.

**Also asked as:** "Audit finding not clearing" / "I fixed the issue but it still shows"

**Keywords:** finding not clearing, next cycle, re-ingest, rejects

**Source:** NETIQ User Manual v3.5 §9 Q8, §4.3.6; NETIQ Solution Document v3.3 §9.7

---

### Q: Why is a site missing from the Service Path Explorer map or shown with wrong location?

**ID:** NETIQ-TRB-008 | **Audience:** Ops | **Type:** troubleshooting

**Answer:** Site coordinates come from the Site Report, falling back to the 'Default LATITUDE_LONGITUDE' sheet (never for Core sites). Missing or invalid GPS also blocks geo-based searches. Check the GPS Accuracy Audit and GPS Suggestion for that site and correct the source coordinates.

**Also asked as:** "Site not on map" / "Wrong site location" / "Missing coordinates"

**Keywords:** map, site location, GPS, default coordinates, site report

**Source:** NETIQ Solution Document v3.3 §9.10.12, §20.9; NETIQ User Manual v3.5 §4.3.2.2

**Related:** NETIQ-STI-022

---

## Glossary & Definitions (GLO)

_Short definitions of NETIQ and telecom terms used in the documents._

### Q: What does CM dump mean?

**ID:** NETIQ-GLO-001 | **Audience:** All | **Type:** concept

**Answer:** Configuration Management export: the raw configuration data collected from each NMS/EMS each cycle, which NETIQ parses and normalises.

**Also asked as:** "Define CM dump" / "What is a configuration management dump?"

**Keywords:** CM dump, definition

**Source:** NETIQ Solution Document v3.3 Definitions; NETIQ User Manual v3.5 §11

---

### Q: What is an Access POP (L2) and an AGW (L3 POP)?

**ID:** NETIQ-GLO-002 | **Audience:** All | **Type:** concept

**Answer:** L2 (Access POP) is the first Wireline node on a RAN service path that carries the RAN VLAN but not the RAN Gateway IP. AGW (Aggregation Gateway, L3 POP) is the Wireline node whose WAN IP equals the RAN Gateway IP.

**Also asked as:** "Define L2 POP" / "What is AGW?" / "What is the L3 POP?"

**Keywords:** L2, L3, AGW, access POP, aggregation gateway, definition

**Source:** NETIQ Solution Document v3.3 Definitions; NETIQ User Manual v3.5 §11

**Related:** NETIQ-STI-015, NETIQ-OPS-003, NETIQ-STI-001

---

### Q: What do SRAN, BTS, eNodeB, gNodeB, RU and RRU mean?

**ID:** NETIQ-GLO-003 | **Audience:** All | **Type:** concept

**Answer:** BTS/eNodeB/gNodeB are 2G/4G/5G base stations; SRAN is Single RAN, a combined multi-technology radio node; RU/RRU is the (Remote) Radio Unit serving cells.

**Also asked as:** "Define SRAN" / "What is RRU?"

**Keywords:** SRAN, BTS, eNodeB, gNodeB, RU, RRU, definition

**Source:** NETIQ Solution Document v3.3 Definitions; NETIQ User Manual v3.5 §11

**Related:** NETIQ-AUD-012

---

### Q: What do CGI, TAC, LAC, EARFCN and FDD/TDD mean?

**ID:** NETIQ-GLO-004 | **Audience:** All | **Type:** concept

**Answer:** CGI is Cell Global Identity (CGI = MCC-MNC-TAC/LAC-CI); TAC/LAC are Tracking/Location Area Codes; EARFCN is the carrier frequency channel number of an LTE cell; FDD/TDD are Frequency/Time Division Duplexing.

**Also asked as:** "Define EARFCN" / "What is TAC?" / "What is CGI?"

**Keywords:** CGI, TAC, LAC, EARFCN, FDD, TDD, definition

**Source:** NETIQ User Manual v3.5 §11, §12.3; NETIQ Solution Document v3.3 Definitions

**Related:** NETIQ-INV-004, NETIQ-AIN-006, NETIQ-AUD-014

---

### Q: What do MW, UBR, FTTH and Wireline refer to in NETIQ?

**ID:** NETIQ-GLO-005 | **Audience:** All | **Type:** concept

**Answer:** MW is Microwave transport links; UBR is Ultra Broadband Radio links; FTTH is fibre-access (ONT/OLT) nodes and links; Wireline is the fixed-line backhaul/aggregation domain with nodes, ports, logical inventory, VLANs and links.

**Also asked as:** "Define UBR" / "What is Wireline in NETIQ?"

**Keywords:** MW, UBR, FTTH, wireline, transport, definition

**Source:** NETIQ Solution Document v3.3 §3.1.1; NETIQ User Manual v3.5 §11

**Related:** NETIQ-GEN-004, NETIQ-STI-004, NETIQ-AIN-004

---

### Q: What is BOQ in the Service Path Explorer?

**ID:** NETIQ-GLO-006 | **Audience:** All | **Type:** concept

**Answer:** Bill of Quantity: a consolidated count of discovered assets shown as KPI cards (Total Sites, Fully Stitched, Partial, Unresolved, Suggested and Stitch %).

**Also asked as:** "Define BOQ" / "What are BOQ cards?"

**Keywords:** BOQ, bill of quantity, KPI cards

**Source:** NETIQ User Manual v3.5 §4.2.1, §11

---

### Q: What do RBAC, KPI, SLA, RPO and RTO mean in the documents?

**ID:** NETIQ-GLO-007 | **Audience:** Admin | **Type:** concept

**Answer:** RBAC: Role-Based Access Control; KPI: Key Performance Indicator; SLA: Service Level Agreement; RPO/RTO: Recovery Point / Recovery Time Objective.

**Also asked as:** "Define RBAC" / "What is RPO?"

**Keywords:** RBAC, KPI, SLA, RPO, RTO, definition

**Source:** NETIQ Solution Document v3.3 Definitions

**Related:** NETIQ-OPS-005

---

### Q: What is VLAN Match % and Deployment Compliance?

**ID:** NETIQ-GLO-008 | **Audience:** Planning | **Type:** concept

**Answer:** VLAN Match % = common VLANs between a port VLAN trunk and the RAN VLAN group, divided by the RAN VLAN group size, x 100. Deployment Compliance = planned links deployed and matched divided by total planned links x 100.

**Also asked as:** "Define VLAN match percent" / "Define deployment compliance"

**Keywords:** VLAN match, deployment compliance, definition, formula

**Source:** NETIQ Solution Document v3.3 Definitions; NETIQ User Manual v3.5 §11

---
