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
          Reusable AI agent skills — install independently or as a curated collection.
        </div>
        <div
          style={{
            marginTop: "auto",
            fontSize: 22,
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
