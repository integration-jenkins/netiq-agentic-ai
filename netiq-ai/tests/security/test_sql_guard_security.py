"""Security tests for Oracle 19c SQL Guard covering all Phase 7 mandatory cases."""

import pytest
from src.schemas.user import UserContext
from src.security.circle_access import UnauthorizedCircleError
from src.security.sql_guard import OracleSQLGuard, SQLSecurityError


def test_missing_table_raises_sql_security_error():
    """Referencing an unapproved or missing table must be blocked."""
    sql = "SELECT * FROM non_existent_table WHERE circle = 'DL' FETCH FIRST 10 ROWS ONLY"
    with pytest.raises(SQLSecurityError, match="not in the approved NETIQ schema"):
        OracleSQLGuard.validate_query(sql)


def test_missing_column_raises_sql_security_error():
    """Referencing an unapproved or hallucinated column must be blocked."""
    sql = "SELECT cell_id, hallucinated_revenue FROM ran_cells WHERE circle = 'DL' FETCH FIRST 10 ROWS ONLY"
    with pytest.raises(SQLSecurityError, match="does not exist in approved schema"):
        OracleSQLGuard.validate_query(sql)


def test_unapproved_schema_object_raises():
    """Referencing system tables or views (e.g. all_users, dual, v$session) must be blocked."""
    sql = "SELECT username FROM all_users FETCH FIRST 10 ROWS ONLY"
    with pytest.raises(SQLSecurityError, match="not in the approved NETIQ schema"):
        OracleSQLGuard.validate_query(sql)


def test_multiple_sql_statements_rejected():
    """Executing multiple statements separated by semicolons must be blocked."""
    sql = "SELECT cell_id FROM ran_cells FETCH FIRST 10 ROWS ONLY; DROP TABLE ran_cells"
    with pytest.raises(SQLSecurityError, match="Multiple SQL statements"):
        OracleSQLGuard.validate_query(sql)


def test_sql_injection_tautology_attempt_rejected():
    """Tautological SQL injections (e.g. 1=1) must be rejected."""
    sql = "SELECT cell_id FROM ran_cells WHERE circle = 'DL' OR 1=1 FETCH FIRST 10 ROWS ONLY"
    with pytest.raises(SQLSecurityError, match="Tautological SQL injection"):
        OracleSQLGuard.validate_query(sql)


def test_sql_comment_injection_rejected():
    """SQL comments used to bypass query clauses must be rejected."""
    sql = "SELECT cell_id FROM ran_cells WHERE circle = 'DL' -- bypass FETCH FIRST 10 ROWS ONLY"
    with pytest.raises(SQLSecurityError, match="SQL comments"):
        OracleSQLGuard.validate_query(sql)


def test_unauthorized_circle_rejected():
    """Querying an unauthorized circle must raise UnauthorizedCircleError."""
    user = UserContext(
        username="delhi_operator",
        roles=["analyst"],
        permitted_circles=["DL"],
        is_admin=False,
    )
    # User attempts to query MUMBAI (MH)
    sql = "SELECT cell_id, circle FROM ran_cells WHERE circle = 'MH' FETCH FIRST 10 ROWS ONLY"
    with pytest.raises(UnauthorizedCircleError, match="Access denied: Query targets unauthorized circle"):
        OracleSQLGuard.validate_query(sql, user=user)


def test_query_without_row_limit_rejected():
    """Queries omitting row limit syntax (FETCH FIRST or ROWNUM) must be blocked."""
    sql = "SELECT cell_id, cell_name FROM ran_cells WHERE circle = 'DL'"
    with pytest.raises(SQLSecurityError, match="Query missing mandatory row limit"):
        OracleSQLGuard.validate_query(sql)


def test_row_limit_ceiling_enforced():
    """If user asks for top 10, limit > 10 must be rejected."""
    sql = "SELECT cell_id FROM ran_cells WHERE circle = 'DL' FETCH FIRST 50 ROWS ONLY"
    with pytest.raises(SQLSecurityError, match="Requested row limit 50 exceeds permitted limit of 10"):
        OracleSQLGuard.validate_query(sql, max_rows=10)


def test_valid_parameterized_read_only_query_succeeds():
    """A valid read-only SELECT query against approved schema with valid circle passes."""
    user = UserContext(
        username="bihar_operator",
        roles=["analyst"],
        permitted_circles=["BR"],
        is_admin=False,
    )
    sql = (
        "SELECT cell_id, cell_name, circle, operational_status, last_down_timestamp "
        "FROM ran_cells "
        "WHERE circle = 'BR' AND operational_status = 'DOWN' "
        "ORDER BY last_down_timestamp DESC "
        "FETCH FIRST 10 ROWS ONLY"
    )
    normalized = OracleSQLGuard.validate_query(sql, user=user, max_rows=10)
    assert "RAN_CELLS" in normalized.upper()
    assert "FETCH FIRST 10 ROWS ONLY" in normalized.upper() or "FETCH" in normalized.upper()


def test_state_changing_operations_prohibited():
    """INSERT, UPDATE, DELETE, DROP must be rejected immediately."""
    mutations = [
        "INSERT INTO ran_cells (cell_id) VALUES ('NEW_01')",
        "UPDATE ran_cells SET operational_status = 'UP' WHERE cell_id = '01'",
        "DELETE FROM ran_cells WHERE circle = 'DL'",
        "DROP TABLE ran_cells",
        "ALTER TABLE ran_cells ADD (new_col VARCHAR2(10))",
    ]
    for m in mutations:
        with pytest.raises(SQLSecurityError, match="Only read-only SELECT queries are permitted"):
            OracleSQLGuard.validate_query(m)
