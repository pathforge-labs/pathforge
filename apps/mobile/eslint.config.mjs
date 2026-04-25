// PathForge Mobile — ESLint v9 flat config.
// Closes https://github.com/pathforge-labs/pathforge/issues/20.
//
// Mirrors the spirit of apps/web/eslint.config.mjs (TS + React) but adds
// the React Native plugin and adjusts globals/parser for an Expo + RN
// codebase. Intentionally pragmatic — we want a working baseline that
// catches real bugs, not a strict gate that requires a multi-day refactor
// of the existing Sprint 31 mobile foundation.

import js from "@eslint/js";
import reactPlugin from "eslint-plugin-react";
import reactHooks from "eslint-plugin-react-hooks";
import reactNative from "eslint-plugin-react-native";
import globals from "globals";
import tseslint from "typescript-eslint";

export default tseslint.config(
  // ── Global ignores ──────────────────────────────────────────
  {
    ignores: [
      "node_modules/**",
      ".expo/**",
      "ios/**",
      "android/**",
      "dist/**",
      "build/**",
      "babel.config.js",
      "*.config.js",
    ],
  },

  // ── Base recommended rules ──────────────────────────────────
  js.configs.recommended,
  ...tseslint.configs.recommended,

  // ── TS / TSX source ────────────────────────────────────────
  {
    files: ["**/*.{ts,tsx}"],
    plugins: {
      react: reactPlugin,
      "react-hooks": reactHooks,
      "react-native": reactNative,
    },
    languageOptions: {
      ecmaVersion: 2022,
      sourceType: "module",
      parserOptions: {
        ecmaFeatures: { jsx: true },
      },
      globals: {
        ...globals.browser,
        ...globals.node,
        ...globals["react-native"],
        __DEV__: "readonly",
      },
    },
    settings: {
      react: { version: "detect" },
    },
    rules: {
      // React 17+ JSX transform — no need to import React in scope
      "react/react-in-jsx-scope": "off",
      "react/prop-types": "off",
      // Hooks: keep these on, they catch real bugs
      "react-hooks/rules-of-hooks": "error",
      "react-hooks/exhaustive-deps": "warn",
      // RN: only the rules that catch genuine issues
      "react-native/no-unused-styles": "warn",
      "react-native/split-platform-components": "off",
      "react-native/no-inline-styles": "off",
      "react-native/no-color-literals": "off",
      "react-native/no-raw-text": "off",
      // TS: relax `any` to a warning. The codebase has Sprint-31-era
      // `any`s that don't justify blocking CI yet; tracker issues can
      // tighten this back to "error" later.
      "@typescript-eslint/no-explicit-any": "warn",
      "@typescript-eslint/no-unused-vars": [
        "warn",
        {
          argsIgnorePattern: "^_",
          varsIgnorePattern: "^_",
          caughtErrorsIgnorePattern: "^_",
        },
      ],
    },
  },

  // ── Jest test files ────────────────────────────────────────
  {
    files: ["**/__tests__/**/*.{ts,tsx}", "**/*.test.{ts,tsx}"],
    languageOptions: {
      globals: {
        ...globals.jest,
      },
    },
    rules: {
      // Tests legitimately use `any` for mocks and partial fixtures
      "@typescript-eslint/no-explicit-any": "off",
      "@typescript-eslint/no-non-null-assertion": "off",
    },
  },
);
