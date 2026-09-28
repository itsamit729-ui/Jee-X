// Anchor the display to server time, even when a student's device clock is wrong.
// The backend remains authoritative about which saved answers meet the deadline.
export function assignmentDeadline(deadline, serverNow, clientNow = Date.now()) {
  const remaining = Date.parse(deadline) - Date.parse(serverNow)
  if (!Number.isFinite(remaining)) throw new Error('The test timer could not be read. Reload your saved attempt.')
  return clientNow + remaining
}
