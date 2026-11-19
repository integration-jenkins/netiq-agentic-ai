# Runbook: restart the service (sample)

1. Check health: `GET /health`
2. Review recent logs for the failing correlation ID.
3. Restart the service unit and re-check `/health`.
4. If the model is unavailable, verify `models/local_llm/` and `configs/models.yaml`.
