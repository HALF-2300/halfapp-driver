/** Map backend notification list fields to read state (Slice 04). */

export function isNotificationRead(item) {
  if (!item) return false
  if (item.read === true || item.is_read === true) return true
  return Boolean(item.read_at)
}

export function normalizeNotification(item, index = 0) {
  const id = item?.id ?? item?.notification_id ?? index
  const title = item?.title ?? item?.subject ?? `Notification ${index + 1}`
  const message = item?.message ?? item?.body ?? item?.detail ?? ''
  const createdAt = item?.created_at ?? item?.time ?? item?.sent_at ?? null
  const type = item?.type ?? item?.kind ?? 'system'
  return {
    id,
    title,
    message,
    createdAt,
    type,
    isRead: isNotificationRead(item),
  }
}

export function formatNotificationTime(iso) {
  if (!iso) return '—'
  const d = new Date(iso)
  if (Number.isNaN(d.getTime())) return String(iso)
  return d.toLocaleString()
}
