import { ImageResponse } from "next/og";

export const runtime = "edge";

export const alt = "JUNERDD Skills — reusable agent skills";
export const size = { width: 1200, height: 630 };
export const contentType = "image/png";

export default function OpenGraphImage() {
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
          background: "linear-gradient(145deg, #0a0d12 0%, #121820 52%, #0c1018 100%)",
          color: "#c8e6c9",
          fontFamily:
            'ui-monospace, SFMono-Regular, "SF Mono", Menlo, Monaco, Consolas, monospace',
        }}
      >
        <div style={{ fontSize: 56, fontWeight: 700, letterSpacing: "-0.04em", color: "#e8ffef" }}>
          JUNERDD Skills
        </div>
        <div
          style={{
            marginTop: 28,
            fontSize: 30,
            lineHeight: 1.35,
            maxWidth: 900,
            opacity: 0.92,
            color: "#9cd4a9",
          }}
        >
          Reusable AI agent skills — install independently or as a curated collection.
        </div>
        <div
          style={{
            marginTop: "auto",
            fontSize: 22,
            letterSpacing: "0.12em",
            textTransform: "uppercase",
            opacity: 0.55,
          }}
        >
          skills · agents · repos
        </div>
      </div>
    ),
    { ...size }
  );
}
