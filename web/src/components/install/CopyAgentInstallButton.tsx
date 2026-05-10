'use client';

import { useEffect, useRef, useState } from 'react';
import { toast } from 'sonner';
import { AGENT_INSTALL_INSTRUCTION } from '@/lib/skills-data';

type CopyAgentInstallButtonProps = {
  className: string;
  copiedLabel?: string;
  failedLabel?: string;
  idleLabel: string;
};

async function copyText(text: string) {
  if (navigator.clipboard?.writeText) {
    try {
      await navigator.clipboard.writeText(text);
      return;
    } catch {
      // Fall through to the textarea path for browsers that expose the API but
      // reject writes in embedded or permission-restricted contexts.
    }
  }

  const textarea = document.createElement('textarea');
  textarea.value = text;
  textarea.setAttribute('readonly', 'true');
  textarea.style.position = 'fixed';
  textarea.style.opacity = '0';
  document.body.appendChild(textarea);
  textarea.select();
  const copied = document.execCommand('copy');
  document.body.removeChild(textarea);

  if (!copied) {
    throw new Error('Copy command failed');
  }
}

export function CopyAgentInstallButton({
  className,
  copiedLabel = 'Copied',
  failedLabel = 'Copy failed',
  idleLabel,
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
      toast.success('Agent install prompt copied');
    } catch {
      setState('failed');
      toast.error('Copy failed');
    }

    timeoutRef.current = window.setTimeout(() => setState('idle'), 1800);
  };

  return (
    <button
      type="button"
      onClick={handleCopy}
      className={className}
      aria-live="polite"
    >
      {state === 'copied' ? copiedLabel : state === 'failed' ? failedLabel : idleLabel}
    </button>
  );
}
