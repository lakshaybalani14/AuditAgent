export function formatProcessId(pid) {
  if (pid === null || pid === undefined) return "—";
  const id = String(pid);
  return /^p/i.test(id) ? id : `P${id}`;
}
