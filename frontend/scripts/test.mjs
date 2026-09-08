import { mkdirSync, mkdtempSync, readdirSync, rmSync, symlinkSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { dirname, join, resolve } from "node:path";
import { spawnSync } from "node:child_process";
import { fileURLToPath } from "node:url";

const projectRoot = resolve(dirname(fileURLToPath(import.meta.url)), "..");
const buildDirectory = mkdtempSync(join(tmpdir(), "opsguard-frontend-tests-"));

try {
  const testConfig = join(buildDirectory, "tsconfig.json");
  writeFileSync(testConfig, JSON.stringify({
    extends: join(projectRoot, "tsconfig.json"),
    compilerOptions: {
      noEmit: false, outDir: buildDirectory, rootDir: projectRoot, module: "commonjs",
      target: "ES2020", moduleResolution: "node", jsx: "react-jsx", incremental: false,
      typeRoots: [join(projectRoot, "node_modules/@types")]
    },
    include: [
      "lib/dashboard-data.ts", "lib/safety-status.ts", "lib/api.ts",
      "components/dashboard/tool-registry-groups.tsx", "components/dashboard/harness-results-panel.tsx",
      "components/dashboard/tool-attempts-panel.tsx", "components/dashboard/tool-calls-panel.tsx", "components/dashboard/watchdog-findings-panel.tsx",
      "components/dashboard/evaluation-summary-card.tsx", "components/dashboard/agent-run-trace.tsx"
    ].map((file) => join(projectRoot, file)),
    exclude: [join(projectRoot, "node_modules")]
  }));
  const compile = spawnSync(process.execPath, [
    join(projectRoot, "node_modules/typescript/bin/tsc"), "--project", testConfig
  ], { cwd: projectRoot, stdio: "inherit" });
  if (compile.status !== 0) {
    process.exitCode = compile.status ?? 1;
  } else {
    symlinkSync(join(projectRoot, "node_modules"), join(buildDirectory, "node_modules"), "junction");
    // Resolve the same @/* aliases used by the production TypeScript configuration.
    mkdirSync(join(buildDirectory, "@"));
    for (const directory of ["components", "lib"]) {
      symlinkSync(join(buildDirectory, directory), join(buildDirectory, "@", directory), "junction");
    }
    const testFiles = readdirSync(join(projectRoot, "tests")).filter((file) => file.endsWith(".test.cjs")).map((file) => join("tests", file));
    const tests = spawnSync(process.execPath, ["--test", ...testFiles], {
      cwd: projectRoot,
      stdio: "inherit",
      env: { ...process.env, NODE_PATH: buildDirectory, OPSGUARD_TEST_BUILD_DIRECTORY: buildDirectory }
    });
    process.exitCode = tests.status ?? 1;
  }
} finally {
  rmSync(buildDirectory, { recursive: true, force: true });
}
