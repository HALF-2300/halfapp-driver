export const DISPATCH_TRUTH_COPY = {
  header: "Open board dispatch",
  line1: "Open board: rides may appear to multiple drivers.",
  line2: "First claim wins.",
  line3: "If another driver claims first, this ride becomes unavailable.",
  line4: "This is not nearest-driver matching.",
};

export const FORBIDDEN_DISPATCH_CLAIMS = [
  "closest driver",
  "matched to the nearest",
  "auto-matched",
  "geo-match",
  "nearest-driver matching",
];

export function hasForbiddenDispatchClaim(value) {
  const text = String(value || "").toLowerCase();
  return FORBIDDEN_DISPATCH_CLAIMS.some((phrase) => text.includes(phrase));
}
