import type { HTMLAttributes } from 'react'
import { cn } from '../../lib/utils'

export function Card({ className, ...props }: HTMLAttributes<HTMLDivElement>) {
  return <div className={cn('surface rounded-2xl border border-[var(--line)] p-5 shadow-[0_12px_38px_rgba(0,0,0,.08)]', className)} {...props} />
}
