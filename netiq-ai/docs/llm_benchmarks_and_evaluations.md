# NETIQ Agentic AI — Local LLM Benchmarks & Evaluations

**Document Status:** Verified Against Genuine Model Weights  
**Target Hardware:** NVIDIA RTX 5050 Laptop GPU (~8 GB VRAM)  
**Inference Runtime:** Local Ollama Daemon (`127.0.0.1:11434`)  
**Last Updated:** November 2026  

---

## 1. Root Cause of Prior Model Identity Mismatches

Earlier benchmark runs had an identity mismatch caused by `ollama cp` aliases that pointed Qwen3 tags to different underlying model architectures:
- `qwen3:4b-instruct-2507` (digest `357c53fb659c`) was copied from `qwen2.5:3b` (`qwen2`, `3.1B`).
- `qwen3-embedding:0.6b` (digest `0a109f422b47`) was copied from `nomic-embed-text:latest` (`nomic-bert`, `137M`, `768` dim).

Both misleading aliases have been replaced with genuine pulled models, and strict physical identity validation (`IDENTITY_MISMATCH`, `CAPABILITY_MISMATCH`, `MODEL_NOT_FOUND`, `VERIFICATION_UNAVAILABLE`, `UNAPPROVED_MODEL`) is enforced at startup in `app/llms/model_manager.py`.

---

## 2. Verified Genuine Model Identities (Ollama `/api/show` & `/api/tags`)

| Agent / Component | Configured Tag (`configs/models.yaml`) | Detected Architecture | Parameter Size | Quantization | Digest Prefix | Capabilities | Status |
| :--- | :--- | :---: | :---: | :---: | :---: | :--- | :---: |
| **Intent Classifier** | `qwen3:4b-instruct-2507-q4_K_M` | `qwen3` | `4.0B` | `Q4_K_M` | `0edcdef34593` | `completion`, `tools`, `thinking` | **VERIFIED** |
| **Report Selector** | `qwen3:4b-instruct-2507-q4_K_M` | `qwen3` | `4.0B` | `Q4_K_M` | `0edcdef34593` | `completion`, `tools`, `thinking` | **VERIFIED** |
| **Orchestrator / Planner** | `qwen3:4b-instruct-2507-q4_K_M` | `qwen3` | `4.0B` | `Q4_K_M` | `0edcdef34593` | `completion`, `tools`, `thinking` | **VERIFIED** |
| **Knowledge Agent** | `qwen3:4b-instruct-2507-q4_K_M` | `qwen3` | `4.0B` | `Q4_K_M` | `0edcdef34593` | `completion`, `tools`, `thinking` | **VERIFIED** |
| **Knowledge Retriever** | `qwen3-embedding:0.6b` | `qwen3` | `595.78M` (~0.6B) | `Q8_0` | `ac6da0dfba84` | `embedding`, `tools`, `thinking` | **VERIFIED (1024 Dim)** |
| **SQL Agent (optional)** | `qwen2.5-coder:7b` | `qwen2` | `7.6B` | `Q4_K_M` | `dae161e27b0e` | `completion`, `tools`, `insert` | **VERIFIED (Live Gate Disabled)** |

---

## 3. Genuine Model Live Benchmarks (NVIDIA RTX 5050, 8 GB VRAM)

| Component / Test | Genuine Model | Cold / Warm | Eval Speed | Latency | VRAM (`/api/ps`) | Output Quality |
| :--- | :--- | :---: | :---: | :---: | :---: | :--- |
| **Intent Classifier** | `qwen3:4b-instruct-2507-q4_K_M` | Cold | **31.42 tok/s** | **5.178s** | `3.18 GB` | Classified `"4G cell availability..."` $\to$ `REPORT` |
| **Intent Classifier (5 runs)** | `qwen3:4b-instruct-2507-q4_K_M` | Warm | **50.47 tok/s** (avg) | **$p50 = 0.216\text{s}$**, **$p95 = 0.387\text{s}$** | `3.18 GB` | Deterministic single-label classification |
| **Report Selector** | `qwen3:4b-instruct-2507-q4_K_M` | Warm | **30.54 tok/s** | **0.519s** | `3.18 GB` | Selected `RAN_CELL_4G` |
| **Orchestrator / Planner** | `qwen3:4b-instruct-2507-q4_K_M` | Warm | **26.92 tok/s** | **1.398s** | `3.18 GB` | `json_valid=True` (`format="json"`) |
| **Knowledge Agent** | `qwen3:4b-instruct-2507-q4_K_M` | Warm | — | — | `3.18 GB` | `status=GROUNDED`, `has_sev1=False` (`SOP-RAN-402` $\to$ `Severity-2`) |
| **Knowledge Retriever** | `qwen3-embedding:0.6b` | Index Rebuild | — | **38.328s** (4 docs + cold load) | `2.37 GB` | **1024-dimensional** vectors; index saved to `data/indexes/knowledge_index_meta.json` |
| **SQL Agent** | `qwen2.5-coder:7b` | Cold Switch | **18.19 tok/s** | **15.206s** | `4.75 GB` | Valid Oracle `SELECT` query; Ollama evicted 4B model to stay within 8 GB VRAM |

---

## 4. Automated Evaluation Dataset & Guardrail Benchmarks

Executed via `tests/benchmark/test_netiq_benchmark_dataset.py`:

| Evaluation Metric | Measured Result | Scope / Target |
| :--- | :---: | :--- |
| **Report Selection Accuracy** | **96.67% (29/30)** | Deterministic catalog matching (`RAN`, `MW`, `AI`, `Wireline`, `AMBIGUOUS`, `NO_MATCH`) |
| **SQL Structural & Business Validity** | **100.00% (4/4)** | Oracle 19c AST validation via `sqlglot` |
| **Execution Plan Validity** | **100.00% (24/24)** | Pre-flight `ExecutionPlan` validation |
| **Deterministic Planning Latency** | **$p50 = 0.47\text{ ms}$, $p95 = 1.19\text{ ms}$** | Sub-millisecond pre-flight checks |
| **Unsupported Assertion Rate** | **0.00% (0/4)** | `SOP-RAN-402` anti-hallucination guard |

---

## 5. Historical Measurements (Deprecated — Identity Mismatch Warning)

> **WARNING:** Measurements collected prior to November 26, 2026 under `qwen3:4b-instruct-2507` (`357c53fb659c`, actually `qwen2.5:3b` 3.1B) and `qwen3-embedding:0.6b` (`0a109f422b47`, actually `nomic-embed-text` 137M, 768-dim) were recorded on mislabelled weights and must not be used for Qwen3 production sizing.
> - Historical mislabelled `qwen2.5:3b`: 33.3–35.1 tok/s warm.
> - Historical mislabelled `nomic-embed-text`: 768 dimensions.
