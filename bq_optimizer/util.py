"""Shared AST helpers used across optimization rules."""

from __future__ import annotations

from typing import Dict, List, Set

import sqlglot.expressions as exp


def table_fqn(table: exp.Table) -> str:
    """Return the dotted, unquoted fully-qualified name of a table node.

    ``\\`proj.ds.tbl\\``` -> ``proj.ds.tbl``. Falls back to whatever parts exist.
    """
    parts = [table.catalog, table.db, table.name]
    return ".".join(p for p in parts if p)


def table_short_name(table: exp.Table) -> str:
    """Return just the table identifier (last component), lower-cased."""
    return (table.name or "").lower()


def cte_names(expression: exp.Expression) -> Set[str]:
    """Collect the names defined by WITH (CTE) clauses, lower-cased.

    CTE references are represented as ``exp.Table`` nodes too, so callers that
    care about *physical* table scans must exclude these names.
    """
    names: Set[str] = set()
    for cte in expression.find_all(exp.CTE):
        alias = cte.alias_or_name
        if alias:
            names.add(alias.lower())
    return names


def physical_tables(expression: exp.Expression) -> List[exp.Table]:
    """Return all table references that are not CTE aliases."""
    ctes = cte_names(expression)
    return [t for t in expression.find_all(exp.Table) if table_short_name(t) not in ctes]


def build_alias_map(select: exp.Select) -> Dict[str, str]:
    """Map each source alias (or bare table name) to its fully-qualified name.

    Used to resolve which table a qualified column (``a.col``) belongs to so
    that column metadata can be looked up.
    """
    alias_map: Dict[str, str] = {}
    for table in select.find_all(exp.Table):
        fqn = table_fqn(table)
        if not fqn:
            continue
        alias = (table.alias or table.name or "").lower()
        if alias:
            alias_map[alias] = fqn
        # Also register by short name so unqualified single-table queries resolve.
        alias_map.setdefault(table_short_name(table), fqn)
    return alias_map


def insert_target(insert: exp.Insert) -> str:
    """Return the fully-qualified name of an INSERT target table."""
    target = insert.this
    table = target.find(exp.Table) if target else None
    return table_fqn(table) if table else ""
