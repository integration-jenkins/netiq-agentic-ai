# ADR 0001: API-first routing, SQL as fallback (sample)

- Status: Proposed
- Context: Approved NETIQ report APIs give governed, auditable data; direct SQL is riskier.
- Decision: The orchestrator tries the report APIs first and uses the SQL Agent only when no approved API fits.
- Consequences: Fewer SQL paths to secure; the report catalogue must stay current.
