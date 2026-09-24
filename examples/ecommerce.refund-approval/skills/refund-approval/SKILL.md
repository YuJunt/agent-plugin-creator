---
name: refund-approval
description: Review e-commerce refund eligibility, prepare an evidence-based refund preview, and execute a refund only after explicit user confirmation. Use for return, refund, order exception, and customer-service approval workflows.
license: MIT
---

# Refund Approval

1. Confirm order ID, refund reason, amount, currency, policy version, and whether the user requests preview or execution.
2. Call `get_order` and verify order status, payment state, prior refunds, and customer evidence.
3. Call `prepare_refund` to produce a preview with an idempotency key and confirmation token.
4. Present facts, eligibility checks, amount, irreversible effects, and the exact confirmation action.
5. Never call `execute_refund` without explicit user confirmation and the returned confirmation token.
6. After execution, return the audit ID and outcome; if confirmation, authorization, or evidence is missing, stop without changing state.
