"""Payments module — records money received (subscriptions, POS, other) and reports revenue.

Subscription payments are recorded reactively: the module subscribes to the membership
``SUBSCRIPTION_CREATED`` event, so it stays decoupled from the membership module (Part 2).
"""
