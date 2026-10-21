import * as SelectPrimitive from '@radix-ui/react-select'
import { Check, ChevronDown } from 'lucide-react'
import { cn } from '../../lib/utils'

export function Select({ value, onValueChange, options, label }: { value: string; onValueChange: (value: string) => void; options: readonly { value: string; label: string }[]; label: string }) {
  return <SelectPrimitive.Root value={value} onValueChange={onValueChange}>
    <SelectPrimitive.Trigger aria-label={label} className="field flex w-full items-center justify-between gap-2 text-left">
      <SelectPrimitive.Value /><SelectPrimitive.Icon><ChevronDown size={16} /></SelectPrimitive.Icon>
    </SelectPrimitive.Trigger>
    <SelectPrimitive.Portal>
      <SelectPrimitive.Content position="popper" sideOffset={6} className="z-50 min-w-[var(--radix-select-trigger-width)] overflow-hidden rounded-xl border border-[var(--line)] bg-[var(--surface-solid)] p-1 text-[var(--text)] shadow-2xl">
        <SelectPrimitive.Viewport>{options.map(option => <SelectPrimitive.Item key={option.value} value={option.value} className={cn('relative cursor-pointer rounded-lg py-2.5 pl-9 pr-4 text-sm outline-none data-[highlighted]:bg-cyan-400/15', option.value === value && 'text-cyan-400')}>
          <SelectPrimitive.ItemIndicator className="absolute left-3 top-3"><Check size={14} /></SelectPrimitive.ItemIndicator>
          <SelectPrimitive.ItemText>{option.label}</SelectPrimitive.ItemText>
        </SelectPrimitive.Item>)}</SelectPrimitive.Viewport>
      </SelectPrimitive.Content>
    </SelectPrimitive.Portal>
  </SelectPrimitive.Root>
}
