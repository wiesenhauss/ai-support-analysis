import { clsx, type ClassValue } from 'clsx'
import { twMerge } from 'tailwind-merge'

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs))
}

export function formatNumber(num: number): string {
  return new Intl.NumberFormat().format(num)
}

export function formatPercent(num: number, decimals = 1): string {
  return `${num.toFixed(decimals)}%`
}

export function formatDate(date: string | Date): string {
  const d = typeof date === 'string' ? new Date(date) : date
  return d.toLocaleDateString('en-US', {
    year: 'numeric',
    month: 'short',
    day: 'numeric',
  })
}

export function formatDateRange(start: string | Date | null, end: string | Date | null): string {
  if (!start && !end) return 'All time'
  if (!start) return `Until ${formatDate(end!)}`
  if (!end) return `From ${formatDate(start)}`
  return `${formatDate(start)} - ${formatDate(end)}`
}
