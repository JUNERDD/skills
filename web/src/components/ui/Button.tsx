'use client';

import { Button as BaseButton } from '@base-ui/react/button';
import type { ButtonProps as BaseButtonProps } from '@base-ui/react/button';
import { cx } from '@/lib/classnames';

export type AppButtonVariant = 'primary' | 'compact';

type AppButtonProps = Omit<BaseButtonProps, 'className'> & {
  className?: string;
  variant?: AppButtonVariant;
};

const baseClassName =
  'inline-flex items-center justify-center font-mono transition disabled:cursor-not-allowed disabled:opacity-55 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-white';

const variantClassNames: Record<AppButtonVariant, string> = {
  primary:
    'min-h-11 rounded-lg bg-[color:var(--crt-accent)] px-6 py-3 text-sm font-semibold text-black hover:bg-white/90',
  compact:
    'min-h-9 rounded-md bg-transparent px-4 text-xs font-semibold text-white/[0.58] hover:bg-white/[0.2] hover:text-white focus-visible:bg-white/[0.2]',
};

export function AppButton({
  className,
  type = 'button',
  variant = 'primary',
  ...props
}: AppButtonProps) {
  return (
    <BaseButton
      type={type}
      className={cx(baseClassName, variantClassNames[variant], className)}
      {...props}
    />
  );
}
