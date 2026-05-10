'use client';

import { Toast } from '@base-ui/react/toast';
import type { ReactNode } from 'react';

type AppToastType = 'success' | 'error';

type AppToast = {
  description?: ReactNode;
  title: ReactNode;
  type?: AppToastType;
};

const toastManager = Toast.createToastManager();

export function notify({ description, title, type = 'success' }: AppToast) {
  toastManager.add({
    description,
    priority: type === 'error' ? 'high' : 'low',
    title,
    type,
  });
}

function ToastList() {
  const { toasts } = Toast.useToastManager();

  return (
    <>
      {toasts.map((toast) => (
        <Toast.Root
          key={toast.id}
          toast={toast}
          className="border border-white/14 bg-[color:var(--surface-1)] p-4 text-[color:var(--ink)] shadow-[0_18px_60px_rgba(0,0,0,0.42),inset_0_1px_0_rgba(255,255,255,0.06)] outline-none transition data-[ending]:opacity-0 data-[starting]:opacity-0 data-[type=error]:border-red-300/34"
        >
          <Toast.Content className="grid grid-cols-[1fr_auto] gap-x-4 gap-y-1">
            <Toast.Title className="font-mono text-sm font-semibold text-white">
              {toast.title}
            </Toast.Title>
            <Toast.Close
              aria-label="Dismiss notification"
              className="row-span-2 inline-flex size-6 items-center justify-center border border-white/14 font-mono text-xs text-white/58 transition hover:border-white/38 hover:text-white focus-visible:outline focus-visible:outline-2 focus-visible:outline-white"
            >
              x
            </Toast.Close>
            {toast.description ? (
              <Toast.Description className="font-mono text-xs leading-relaxed text-[color:var(--crt-dim)]">
                {toast.description}
              </Toast.Description>
            ) : null}
          </Toast.Content>
        </Toast.Root>
      ))}
    </>
  );
}

export function AppToaster() {
  return (
    <Toast.Provider limit={3} timeout={2800} toastManager={toastManager}>
      <Toast.Portal>
        <Toast.Viewport className="fixed bottom-4 right-4 z-50 flex w-[min(calc(100vw-2rem),24rem)] flex-col gap-3 outline-none sm:bottom-6 sm:right-6">
          <ToastList />
        </Toast.Viewport>
      </Toast.Portal>
    </Toast.Provider>
  );
}
