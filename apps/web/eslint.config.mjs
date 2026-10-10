import coreWebVitals from "eslint-config-next/core-web-vitals";
import typescript from "eslint-config-next/typescript";
const config = [...coreWebVitals, ...typescript, { ignores: [".next/**", ".next-production/**", "node_modules/**", "src/lib/api/schema.d.ts", "next-env.d.ts", "playwright-report/**", "test-results/**"] }];

export default config;
