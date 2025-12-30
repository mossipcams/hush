import resolve from "@rollup/plugin-node-resolve";
import terser from "@rollup/plugin-terser";
import typescript from "@rollup/plugin-typescript";

const isProduction = process.env.NODE_ENV === "production";

const plugins = [
  resolve(),
  typescript({
    tsconfig: "./tsconfig.json",
  }),
  isProduction && terser(),
].filter(Boolean);

export default [
  {
    input: "src/hush-history-card.ts",
    output: {
      file: "../custom_components/hush/hush-history-card.js",
      format: "es",
      sourcemap: !isProduction,
    },
    plugins,
  },
  {
    input: "src/hush-settings-panel.ts",
    output: {
      file: "../custom_components/hush/hush-panel.js",
      format: "es",
      sourcemap: !isProduction,
    },
    plugins,
  },
];
