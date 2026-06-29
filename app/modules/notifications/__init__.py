"""Notifications module — surfaces actionable alerts aggregated from other modules.

A read-only aggregator: it queries memberships (expiring subscriptions) and inventory
(low stock) to produce alerts. Depends on those modules' repositories (allowed dependency
direction — it sits above them).
"""
