---
name: ticket-triage
description: Triage customer support tickets, identify SLA and escalation risk, and recommend routing using the support-ticket MCP server. Use for queue review, incident escalation, priority assessment, and weekly support operations reporting.
license: MIT
---

# Ticket Triage

1. Confirm queue, SLA policy, time window, and whether the user wants read-only recommendations.
2. Call `list_tickets` with filters before making a recommendation.
3. Call `find_sla_risks` for overdue or near-breach tickets.
4. Separate ticket facts, SLA interpretation, and proposed action.
5. Return ticket ID, customer, severity, age, SLA evidence, owner, and next action.
6. Never update, close, or reassign a ticket without an explicit write-capable workflow and confirmation.
