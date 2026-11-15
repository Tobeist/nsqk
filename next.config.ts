import type { NextConfig } from "next";
const config: NextConfig = {
  transpilePackages: ["three"],
  devIndicators: false,
  outputFileTracingIncludes: {
    "/api/analysis": ["./scripts/*.py", "./requirements-analysis.txt", "./config/study-boxes.json", "./data/results/**/*.json", "./data/external/enso/*", "./docs/APP_TREND_PROTOCOL.md"],
  },
  outputFileTracingExcludes: { "/api/analysis": ["./.venv/**/*", "./.cache/**/*"] },
};
export default config;
