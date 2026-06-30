"""Employees module event topics."""

from __future__ import annotations


class EmployeeEvents:
    CREATED = "employees.employee.created"
    UPDATED = "employees.employee.updated"
    DELETED = "employees.employee.deleted"
