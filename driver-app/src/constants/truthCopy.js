export const MONEY_TRUTH_COPY = {
  calculatedEarningLabel: "Calculated driver earning",
  recordedObligationLabel: "Recorded obligation",
  pricingLockedLabel: "Pricing is locked by the server",
  noPayoutSentLabel: "No payout has been sent",
  noMoneyMovedSentence:
    "This is a server-calculated record. Pricing is locked by the server. No payout has been sent.",
  microNoMoneyMoved: "Calculated by server. No payout sent.",
  microPricingLocked: "Locked by server.",
  microRecordedObligation: "Recorded obligation, not paid.",
  clarifier:
    "Numbers shown are calculation records only. Do not interpret them as paid out, cash out, wallet balance, or bank-settled funds.",
};

export const MISLEADING_MONEY_PHRASES = [
  "paid out",
  "cash out",
  "wallet",
  "available balance",
  "instant pay",
  "payment processed",
  "bank settled",
  "deposit sent",
  "bank transfer complete",
];

export function hasMisleadingMoneyPhrase(value) {
  const text = String(value || "").toLowerCase();
  return MISLEADING_MONEY_PHRASES.some((phrase) => text.includes(phrase));
}
