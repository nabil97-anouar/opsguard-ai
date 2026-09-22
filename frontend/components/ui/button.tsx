import * as React from "react";

import { cn } from "@/lib/utils";

type ButtonVariant = "primary" | "secondary" | "ghost";
type ButtonSize = "default" | "lg";

const variantClasses: Record<ButtonVariant, string> = {
  primary:
    "border border-accent/50 bg-accent text-slate-950 shadow-glow hover:bg-accentSoft",
  secondary:
    "border border-slate-700 bg-white/5 text-slate-100 hover:border-slate-500 hover:bg-white/10",
  ghost: "border border-transparent bg-transparent text-slate-200 hover:bg-white/5"
};

const sizeClasses: Record<ButtonSize, string> = {
  default: "h-10 px-4 text-xs",
  lg: "h-11 px-5 text-sm"
};

export function buttonVariants({
  variant = "primary",
  size = "default",
  className
}: {
  variant?: ButtonVariant;
  size?: ButtonSize;
  className?: string;
} = {}): string {
  return cn(
    "inline-flex items-center justify-center rounded-sm font-mono font-medium transition-colors duration-200 disabled:cursor-not-allowed disabled:opacity-40 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent focus-visible:ring-offset-2 focus-visible:ring-offset-ink",
    variantClasses[variant],
    sizeClasses[size],
    className
  );
}

export interface ButtonProps
  extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: ButtonVariant;
  size?: ButtonSize;
}

export const Button = React.forwardRef<HTMLButtonElement, ButtonProps>(
  ({ className, variant, size, ...props }, ref) => {
    return (
      <button
        className={buttonVariants({ variant, size, className })}
        ref={ref}
        {...props}
      />
    );
  }
);

Button.displayName = "Button";
