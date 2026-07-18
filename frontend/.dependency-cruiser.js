/** @type {import('dependency-cruiser').IConfiguration} */
export default {
  forbidden: [
    {
      name: "no-circular",
      severity: "error",
      comment: "Circular dependencies make code hard to reason about.",
      from: {},
      to: { circular: true },
    },
    {
      name: "no-orphans",
      severity: "error",
      comment: "Every module should be reachable from a route or config.",
      from: {
        orphan: true,
        pathNot: [
          "\\.d\\.ts$",
          "(^|/)routeTree\\.gen\\.ts$",
          "(^|/)src/client/",
          // Consumed by the generated client (which is excluded from the cruise).
          "(^|/)src/lib/api-config\\.ts$",
        ],
      },
      to: {},
    },
    {
      name: "ui-is-vendored",
      severity: "error",
      comment:
        "The shadcn ui/ folder is vendored: it may use lib/utils but must not depend on app code (routes, client, features).",
      from: { path: "^src/components/ui/" },
      to: {
        path: "^src/(routes|client)/",
      },
    },
  ],
  options: {
    doNotFollow: { path: "node_modules" },
    exclude: { path: "(^|/)src/client/|(^|/)routeTree\\.gen\\.ts$" },
    tsConfig: { fileName: "tsconfig.json" },
    tsPreCompilationDeps: true,
    enhancedResolveOptions: {
      exportsFields: ["exports"],
      conditionNames: ["import", "require", "node", "default", "types"],
    },
  },
};
