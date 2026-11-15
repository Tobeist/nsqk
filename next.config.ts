import type { NextConfig } from "next";
const analysisFiles = ["./scripts/*.py", "./requirements-analysis.txt", "./config/study-boxes.json", "./data/results/**/*.json", "./data/external/enso/*", "./docs/APP_TREND_PROTOCOL.md"];
const config: NextConfig = {
  transpilePackages: ["three"],
  devIndicators: false,
  outputFileTracingIncludes: {
    "/api/analysis": analysisFiles,
    "/api/chat": analysisFiles,
  },
  outputFileTracingExcludes: {
    "/api/analysis": ["./.venv/**/*", "./.cache/**/*"],
    "/api/chat": ["./.venv/**/*", "./.cache/**/*"],
  },
};
export default config;
