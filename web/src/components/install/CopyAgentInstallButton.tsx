'use client';

import { useEffect, useRef, useState } from 'react';
import { AppButton } from '@/components/ui/Button';
import type { AppButtonVariant } from '@/components/ui/Button';
import { notify } from '@/components/ui/AppToaster';
import { copyText } from '@/lib/clipboard';
import { AGENT_INSTALL_INSTRUCTION } from '@/lib/content/urls';

type CopyAgentInstallButtonProps = {
  className?: string;
  copiedLabel?: string;
  errorDescription?: string;
  errorTitle?: string;
  failedLabel?: string;
  idleLabel: string;
  successTitle?: string;
  variant?: AppButtonVariant;
};

export function CopyAgentInstallButton({
  className,
  copiedLabel = 'Copied',
  errorDescription = 'The browser rejected the clipboard write.',
  errorTitle = 'Copy failed',
  failedLabel = 'Copy failed',
  idleLabel,
  successTitle = 'Agent install prompt copied',
  variant = 'primary',
}: CopyAgentInstallButtonProps) {
  const [state, setState] = useState<'idle' | 'copied' | 'failed'>('idle');
  const timeoutRef = useRef<number | null>(null);

  useEffect(() => {
    return () => {
      if (timeoutRef.current !== null) {
        window.clearTimeout(timeoutRef.current);
      }
    };
  }, []);

  const handleCopy = async () => {
    if (timeoutRef.current !== null) {
      window.clearTimeout(timeoutRef.current);
    }

    try {
      await copyText(AGENT_INSTALL_INSTRUCTION);
      setState('copied');
      notify({ title: successTitle });
    } catch {
      setState('failed');
      notify({
        description: errorDescription,
        title: errorTitle,
        type: 'error',
      });
    }

    timeoutRef.current = window.setTimeout(() => setState('idle'), 1800);
  };

  return (
    <AppButton
      onClick={handleCopy}
      className={className}
      aria-live="polite"
      variant={variant}
    >
      {state === 'copied' ? copiedLabel : state === 'failed' ? failedLabel : idleLabel}
    </AppButton>
  );
}
