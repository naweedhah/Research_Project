import * as React from 'react'
import { Slot } from '@radix-ui/react-slot'
import { cva, type VariantProps } from 'class-variance-authority'
import { cn } from '../../lib/utils'

const variants = cva('inline-flex min-h-11 items-center justify-center gap-2 rounded-xl px-4 text-sm font-semibold transition focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-cyan-400 disabled:pointer-events-none disabled:opacity-50', {
  variants: { variant: {
    default: 'bg-cyan-400 text-slate-950 hover:bg-cyan-300 shadow-lg shadow-cyan-500/10',
    outline: 'border border-[var(--line)] bg-[var(--surface)] text-[var(--text)] hover:border-cyan-400/50',
    ghost: 'text-[var(--muted)] hover:bg-[var(--surface)] hover:text-[var(--text)]',
  } }, defaultVariants: { variant: 'default' },
})
type Props = React.ButtonHTMLAttributes<HTMLButtonElement> & VariantProps<typeof variants> & { asChild?: boolean }
export function Button({ asChild, variant, className, ...props }: Props) {
  const Component = asChild ? Slot : 'button'
  return <Component className={cn(variants({ variant }), className)} {...props} />
}
