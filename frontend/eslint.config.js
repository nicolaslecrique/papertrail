import js from "@eslint/js";
import eslintConfigPrettier from "eslint-config-prettier";
import pluginQuery from "@tanstack/eslint-plugin-query";
import pluginRouter from "@tanstack/eslint-plugin-router";
import betterTailwind from "eslint-plugin-better-tailwindcss";
import react from "eslint-plugin-react";
import reactHooks from "eslint-plugin-react-hooks";
import globals from "globals";
import tseslint from "typescript-eslint";

export default tseslint.config(
  {
    // Generated (owned by codegen) and vendored (owned by shadcn) code is not
    // ours to lint — the client is regenerated, the ui/ folder is updated from
    // the shadcn reference.
    ignores: [
      "src/client/**",
      "src/components/ui/**",
      "src/routeTree.gen.ts",
      ".output/**",
      ".nitro/**",
      ".tanstack/**",
      "dist/**",
      "nitro.json",
    ],
  },
  js.configs.recommended,
  ...tseslint.configs.strictTypeChecked,
  ...tseslint.configs.stylisticTypeChecked,
  {
    languageOptions: {
      parserOptions: {
        projectService: true,
        tsconfigRootDir: import.meta.dirname,
      },
      globals: { ...globals.browser },
    },
  },
  react.configs.flat.recommended,
  react.configs.flat["jsx-runtime"],
  {
    plugins: { "react-hooks": reactHooks },
    rules: reactHooks.configs["recommended-latest"].rules,
  },
  ...pluginRouter.configs["flat/recommended"],
  ...pluginQuery.configs["flat/recommended"],
  {
    files: ["**/*.{ts,tsx}"],
    plugins: { "better-tailwindcss": betterTailwind },
    // Only the correctness rules (unregistered/conflicting/duplicate classes);
    // class ordering is owned by prettier-plugin-tailwindcss.
    rules: betterTailwind.configs["correctness-error"].rules,
    settings: {
      "better-tailwindcss": { entryPoint: "src/styles.css" },
    },
  },
  { settings: { react: { version: "detect" } } },
  // Root config files (eslint.config.js, .dependency-cruiser.js) aren't part of
  // the TS project, so skip type-aware linting for plain JS.
  { files: ["**/*.js"], extends: [tseslint.configs.disableTypeChecked] },
  // Must be last: turns off rules that conflict with Prettier's formatting.
  eslintConfigPrettier,
);
