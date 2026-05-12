"""BT-aware classifier: upgrades to_be_booked lines to pending_in_bt when
the same vendor+invoice combo appears in the Bravotran waiting queue.
"""
from app.recon.engine import ReconResult, recompute_totals
from app.recon.normalize import normalize_invno


def classify(result: ReconResult, vendor_name: str, bt_lines) -> ReconResult:
    """Attach BT context and upgrade statuses where appropriate.

    bt_lines: iterable of BTLine ORM objects.
    """
    # Index BT by normalized invoice number, filtered to this vendor.
    by_inv: dict = {}
    for bt in bt_lines:
        if not bt.vendor or bt.vendor.strip().lower() != vendor_name.strip().lower():
            continue
        inv = bt.norm_invno or normalize_invno(bt.invoice_number)
        if not inv:
            continue
        by_inv.setdefault(inv, []).append(bt)

    for line in result.lines:
        if line.status != "to_be_booked":
            continue
        ninv = normalize_invno(line.vendor_inv_no)
        candidates = by_inv.get(ninv, [])
        if not candidates:
            continue
        # Prefer the one whose Invoice Total matches the vendor amount, else first.
        chosen = None
        if line.vendor_amount is not None:
            for c in candidates:
                if c.invoice_total is not None and abs(c.invoice_total - line.vendor_amount) < 0.01:
                    chosen = c
                    break
        if chosen is None:
            chosen = candidates[0]

        line.status = "pending_in_bt"
        line.bt_label = chosen.bt_label
        line.bt_labels = chosen.labels
        line.bt_note = chosen.note
        line.bt_link = chosen.link_to_item
        line.bt_owner = chosen.request_sent_to

    return recompute_totals(result)
