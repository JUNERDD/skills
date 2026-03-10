const [
  ReactModule,
  ReactDomModule,
  htmModule,
  swrModule,
  reactVirtualModule,
] = await Promise.all([
  import('https://esm.sh/react@18.3.1'),
  import('https://esm.sh/react-dom@18.3.1/client'),
  import('https://esm.sh/htm@3.1.1'),
  import('https://esm.sh/swr@2.2.5?deps=react@18.3.1'),
  import('https://esm.sh/@tanstack/react-virtual@3.10.8?deps=react@18.3.1'),
])

const React = ReactModule.default
const html = htmModule.default.bind(React.createElement)

export const { useCallback, useEffect, useMemo, useRef, useState } = ReactModule
export const { createRoot } = ReactDomModule
export const useSWR = swrModule.default
export const { useVirtualizer } = reactVirtualModule
export { React, html }
