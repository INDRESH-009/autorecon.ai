"""Canonical SOA field dictionary + alias library.

The mapping module is generic — it takes any vendor's SOA headers and resolves
each to one of these canonical fields. For MVP we only need three fields, but
the structure scales when we add more later.
"""

# Canonical fields
INVOICE_NO = "invoice_no"
INVOICE_DATE = "invoice_date"
AMOUNT = "amount"

CANONICAL_FIELDS = [INVOICE_NO, INVOICE_DATE, AMOUNT]

REQUIRED_FIELDS = [INVOICE_NO, INVOICE_DATE, AMOUNT]

# Alias library: lower-cased phrases that strongly indicate a field.
ALIASES = {
    INVOICE_NO: [
        "inv number", "inv no", "invoice number", "invoice no", "invoice #",
        "invoice", "inv#", "inv. no", "bill no", "bill number", "doc no",
        "document no", "reference no", "ref no",
    ],
    INVOICE_DATE: [
        "inv date", "invoice date", "bill date", "doc date", "document date",
        "date", "issued on", "issued",
    ],
    AMOUNT: [
        "outstanding amount", "outstanding", "balance", "open balance",
        "amount", "amt", "amount due", "total", "invoice total",
        "invoice amount", "gross", "gross amount", "balance due", "due amount",
    ],
}

# Columns we explicitly do NOT want to match — these are the AP team's
# worksheet helpers from vendor_soa_quicklogi (and similar).
NEGATIVE_KEYWORDS = [
    "look up", "lookup", "todays date", "today's date", "ageing", "aging",
    "amount-ajww", "od to pay", "remarks", "concan", "approved", "unapproved",
    "request send", "ops person", "bt link",
]
