'use client';

import { useEffect, useRef, useState } from 'react';
import { AppButton } from '@/components/ui/Button';
import type { AppButtonVariant } from '@/components/ui/Button';
import { notify } from '@/components/ui/AppToaster';
import { AGENT_INSTALL_INSTRUCTION } from '@/lib/skills-data';

type CopyAgentInstallButtonProps = {
  className?: string;
  copiedLabel?: string;
  failedLabel?: string;
  idleLabel: string;
  variant?: AppButtonVariant;
};

function copyTextWithTextarea(text: string) {
  const textarea = document.createElement('textarea');
  textarea.value = text;
  textarea.setAttribute('readonly', 'true');
  textarea.style.position = 'fixed';
  textarea.style.top = '0';
  textarea.style.opacity = '0';
  document.body.appendChild(textarea);
  textarea.focus({ preventScroll: true });
  textarea.select();
  textarea.setSelectionRange(0, textarea.value.length);
  const copied = document.execCommand('copy');
  document.body.removeChild(textarea);

  if (!copied) {
    throw new Error('Copy command failed');
  }
}

async function copyText(text: string) {
  try {
    copyTextWithTextarea(text);
    return;
  } catch (error) {
    if (navigator.clipboard?.writeText) {
      await navigator.clipboard.writeText(text);
      return;
    }

    throw error;
  }
}

export function CopyAgentInstallButton({
  className,
  copiedLabel = 'Copied',
  failedLabel = 'Copy failed',
  idleLabel,
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
      notify({ title: 'Agent install prompt copied' });
    } catch {
      setState('failed');
      notify({
        description: 'The browser rejected the clipboard write.',
        title: 'Copy failed',
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
