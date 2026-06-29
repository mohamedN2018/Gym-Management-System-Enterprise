"""Inventory module — products, stock, and point-of-sale (POS) sales.

POS checkouts decrement stock, persist a sale with line items, and record the takings as a
POS payment through the payments service (modules communicate via services, Part 2).
"""
