"""Audit trail: who did what. Written to logs/audit.log and kept 90 days (configs/logging.yaml).

The HTTP middleware records logins, logouts and refused requests (401/403). Other code adds
its own events the same way, for example:

    audit_log.info("report_exported", extra={"user": user, "report_id": report_id})
"""

import logging

audit_log = logging.getLogger("netiq.audit")
