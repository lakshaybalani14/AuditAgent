export function isMetric(value) {
  return typeof value === "number" && Number.isFinite(value);
}

export function formatMetric(value, digits = 2) {
  return isMetric(value) ? value.toFixed(digits) : "—";
}

export function formatPercent(value, digits = 3) {
  return isMetric(value) ? `${(value * 100).toFixed(digits)}%` : "—";
}
