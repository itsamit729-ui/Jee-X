// The permanent student user ID, matching /api/classrooms and OMR scanning.
// Never derive this from the username, classroom, paper, or authentication account.
export function formatOmrId(studentId) {
  const value = String(studentId ?? '')
  if (!/^\d{1,10}$/.test(value) || Number(value) < 1) return null
  return value.padStart(10, '0')
}
