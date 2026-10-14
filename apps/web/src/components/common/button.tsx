import { cva, type VariantProps } from "class-variance-authority";
import { cn } from "@/utils/utils";
import { ButtonHTMLAttributes, forwardRef } from "react";

const buttonVariants = cva(
  "inline-flex items-center justify-center gap-2 rounded-xl text-sm font-medium transition disabled:opacity-50 disabled:pointer-events-none min-h-11 px-4",
  {
    variants: {
      variant: {
        primary: "bg-[#0E3A67] text-white hover:bg-[#0A2748]",
        secondary: "bg-white text-[#0A2748] border border-line hover:bg-[#EAF2FA]",
        ghost: "text-ink hover:bg-white/80",
        danger: "bg-clinical-danger text-white hover:bg-red-800",
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
