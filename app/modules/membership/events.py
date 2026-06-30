"""Membership module event topics."""

from __future__ import annotations


class MembershipEvents:
    PLAN_CREATED = "membership.plan.created"
    PLAN_UPDATED = "membership.plan.updated"
    PLAN_DELETED = "membership.plan.deleted"
    SUBSCRIPTION_CREATED = "membership.subscription.created"
    SUBSCRIPTION_CANCELLED = "membership.subscription.cancelled"
    SUBSCRIPTION_DELETED = "membership.subscription.deleted"
