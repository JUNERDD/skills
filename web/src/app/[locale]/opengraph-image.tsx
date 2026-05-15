import { ImageResponse } from "next/og";
import { routing, type Locale } from "@/i18n/routing";

export const alt = "JUNERDD Skills — reusable agent skills";
export const size = { width: 1200, height: 630 };
export const contentType = "image/png";

const copy: Record<Locale, { footer: string; subtitle: string }> = {
  en: {
    footer: "skills · agents · repos",
    subtitle:
      "Reusable AI agent skills — install independently or as a curated collection.",
  },
  "zh-CN": {
    footer: "skills · agents · repos",
    subtitle: "可复用 AI agent skills，可单独安装，也可作为精选集合使用。",
  },
};

type OpenGraphImageProps = {
  params: Promise<{ locale: string }>;
};

export default async function OpenGraphImage({ params }: OpenGraphImageProps) {
  const { locale: requestedLocale } = await params;
  const locale = routing.locales.includes(requestedLocale as Locale)
    ? (requestedLocale as Locale)
    : routing.defaultLocale;
  const labels = copy[locale];

  return new ImageResponse(
    (
      <div
        style={{
          width: "100%",
          height: "100%",
          display: "flex",
          flexDirection: "column",
          justifyContent: "center",
          padding: 72,
          background: "linear-gradient(145deg, #050505 0%, #151515 54%, #080808 100%)",
          color: "#f4f4f1",
          fontFamily:
            'ui-monospace, SFMono-Regular, "SF Mono", Menlo, Monaco, Consolas, monospace',
        }}
      >
        <div style={{ fontSize: 56, fontWeight: 700, color: "#f8f8f4" }}>
          JUNERDD Skills
        </div>
        <div
          style={{
            marginTop: 28,
            fontSize: 30,
            lineHeight: 1.35,
            maxWidth: 900,
            opacity: 0.92,
            color: "#b6b6b2",
          }}
        >
          {labels.subtitle}
        </div>
        <div
          style={{
            marginTop: "auto",
            fontSize: 22,
            textTransform: "uppercase",
            opacity: 0.55,
          }}
        >
          {labels.footer}
        </div>
      </div>
    ),
    { ...size }
  );
}
