import { mkdtempSync, rmSync, symlinkSync } from "node:fs";
import { tmpdir } from "node:os";
import { dirname, join, resolve } from "node:path";
import { spawnSync } from "node:child_process";
import { fileURLToPath } from "node:url";

const projectRoot = resolve(dirname(fileURLToPath(import.meta.url)), "..");
const buildDirectory = mkdtempSync(join(tmpdir(), "opsguard-frontend-tests-"));

try {
  const compile = spawnSync(process.execPath, [
    join(projectRoot, "node_modules/typescript/bin/tsc"),
    "lib/dashboard-data.ts", "lib/safety-status.ts", "components/dashboard/tool-registry-groups.tsx",
    "--outDir", buildDirectory, "--rootDir", ".", "--module", "commonjs",
    "--target", "ES2020", "--moduleResolution", "node", "--jsx", "react-jsx",
    "--esModuleInterop", "--strict", "--skipLibCheck"
  ], { cwd: projectRoot, stdio: "inherit" });
  if (compile.status !== 0) {
    process.exitCode = compile.status ?? 1;
  } else {
    symlinkSync(join(projectRoot, "node_modules"), join(buildDirectory, "node_modules"), "junction");
    const tests = spawnSync(process.execPath, ["--test", "tests/evidence-integrity.test.cjs"], {
      cwd: projectRoot,
      stdio: "inherit",
      env: { ...process.env, OPSGUARD_TEST_BUILD_DIRECTORY: buildDirectory }
    });
    process.exitCode = tests.status ?? 1;
  }
} finally {
  rmSync(buildDirectory, { recursive: true, force: true });
}
