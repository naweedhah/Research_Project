import { cva, type VariantProps } from "class-variance-authority";
import { cn } from "@/utils/utils";
import { ButtonHTMLAttributes, forwardRef } from "react";

const buttonVariants = cva(
  "inline-flex items-center justify-center gap-2 rounded-2xl text-sm font-medium transition active:scale-[0.98] disabled:opacity-50 disabled:pointer-events-none min-h-11 px-4 motion-safe-only",
  {
    variants: {
      variant: {
        primary: "bg-[#102A4C] text-white hover:bg-[#173D6B]",
        secondary: "bg-white/90 text-[#102A4C] border border-line hover:bg-white",
        ghost: "text-ink hover:bg-white/80",
        danger: "bg-[#C45A52] text-white hover:bg-[#A84842]",
      },
    },
    defaultVariants: { variant: "primary" },
  },
);

export const Button = forwardRef<HTMLButtonElement, ButtonHTMLAttributes<HTMLButtonElement> & VariantProps<typeof buttonVariants>>(
  ({ className, variant, ...props }, ref) => (
    <button ref={ref} className={cn(buttonVariants({ variant }), className)} {...props} />
  ),
);
Button.displayName = "Button";
