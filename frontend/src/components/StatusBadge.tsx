const LABELS: Record<string, string> = {
  ok_to_pay: "OK to Pay",
  not_due: "Not Due",
  pending_in_bt: "Pending in BT",
  to_be_booked: "To Be Booked",
  missing_in_vendor: "Missing in Vendor",
  amount_dispute: "Amount Dispute",
  paid: "Paid",
};

export default function StatusBadge({ status }: { status: string }) {
  return (
    <span className={`inline-flex items-center px-2 py-0.5 rounded text-xs font-medium status-${status}`}>
      {LABELS[status] || status}
    </span>
  );
}
