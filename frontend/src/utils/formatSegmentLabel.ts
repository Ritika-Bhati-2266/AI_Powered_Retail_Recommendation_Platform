export function formatSegmentLabel(segment: string): string {
  return segment
    .replace(/_/g, ' ')
    .replace(/\b\w/g, (c) => c.toUpperCase());
}
