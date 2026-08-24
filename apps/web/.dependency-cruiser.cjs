/** @type {import("dependency-cruiser").IConfiguration} */
module.exports = {
  forbidden: [
    {
      name: "not-to-unresolvable",
      severity: "error",
      comment:
        "Every import must resolve through Node, package.json, or tsconfig paths.",
      from: {},
      to: {
        couldNotResolve: true,
      },
    },
    {
      name: "no-runtime-circular",
      severity: "error",
      comment:
        "Runtime circular dependencies make feature boundaries and server/client behavior harder to reason about.",
      from: {},
      to: {
        circular: true,
        viaOnly: {
          dependencyTypesNot: ["type-only"],
        },
      },
    },
    {
      name: "not-to-app-from-non-app",
      severity: "error",
      comment:
        "The Next.js app tree is an interface/composition edge; components, hooks, and lib code must not import it.",
      from: {
        path: "^src/(components|hooks|lib|messages)/",
      },
      to: {
        path: "^src/app/",
      },
    },
    {
      name: "not-to-components-from-lib",
      severity: "error",
      comment:
        "Lib modules contain types, adapters, API clients, and pure functions; they must not depend on React component trees.",
      from: {
        path: "^src/lib/",
        pathNot: "[.](?:spec|test)[.](?:ts|tsx)$",
      },
      to: {
        path: "^src/(app|components)/",
      },
    },
    {
      name: "not-to-other-feature-components",
      severity: "error",
      comment:
        "Feature components may use shared UI primitives and shared system-catalog components, but must not import other feature component internals.",
      from: {
        path: "^src/components/([^/]+)/",
      },
      to: {
        path: "^src/components/(?!$1/|ui/|system-catalogs/)",
      },
    },
    {
      name: "not-to-feature-from-ui",
      severity: "error",
      comment:
        "Shared UI primitives must not depend on app routes, feature components, messages, or feature lib modules.",
      from: {
        path: "^src/components/ui/",
      },
      to: {
        path: "^src/(app|components/(?!ui/)|lib/(?!utils[.]ts$)|messages/)",
      },
    },
    {
      name: "not-to-test-from-production",
      severity: "error",
      comment:
        "Production source must not import test modules or browser smoke-test fixtures.",
      from: {
        path: "^src/",
        pathNot: "[.](?:spec|test)[.](?:ts|tsx)$",
      },
      to: {
        path: "(^tests/|[.](?:spec|test)[.](?:ts|tsx)$)",
      },
    },
    {
      name: "not-to-dev-dependency-from-production",
      severity: "error",
      comment:
        "Production source must not depend on devDependencies, except for type-only imports.",
      from: {
        path: "^src/",
        pathNot: "[.](?:spec|test)[.](?:ts|tsx)$",
      },
      to: {
        dependencyTypes: ["npm-dev"],
        dependencyTypesNot: ["type-only"],
        pathNot: "node_modules/@types/",
      },
    },
    {
      name: "no-orphan-feature-code",
      severity: "error",
      comment:
        "Feature, hook, and lib source should be reachable from an entry point or test. shadcn/ui primitives are excluded because they can be installed before use.",
      from: {
        orphan: true,
        path: "^src/(components|hooks|lib)/",
        pathNot: [
          "^src/components/ui/",
          "[.](?:spec|test)[.](?:ts|tsx)$",
          "[.]d[.]ts$",
        ],
      },
      to: {},
    },
  ],
  options: {
    doNotFollow: {
      path: "node_modules",
      dependencyTypes: [
        "npm",
        "npm-dev",
        "npm-optional",
        "npm-peer",
        "npm-bundled",
        "npm-no-pkg",
      ],
    },
    exclude: {
      path: "^(?:[.]next|coverage|playwright-report|test-results)/",
    },
    tsConfig: {
      fileName: "tsconfig.json",
    },
    tsPreCompilationDeps: "specify",
    moduleSystems: ["es6"],
    enhancedResolveOptions: {
      exportsFields: ["exports"],
      conditionNames: ["import", "require", "node", "default", "types"],
      extensions: [".ts", ".tsx", ".js", ".jsx", ".mjs", ".cjs", ".json"],
      mainFields: ["module", "main", "types"],
    },
    skipAnalysisNotInRules: true,
    reporterOptions: {
      text: {
        highlightFocused: true,
      },
    },
  },
};
