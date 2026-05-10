import { mkdtemp, rm } from "node:fs/promises";
import { tmpdir } from "node:os";
import path from "node:path";
import { spawn } from "node:child_process";
import * as esbuild from "esbuild";

const outDir = await mkdtemp(path.join(tmpdir(), "proofflow-vscode-tests-"));
const testFiles = [
  "test/policyGateDecision.test.ts",
  "test/approveAction.test.ts",
];

const vscodeMockPlugin = {
  name: "vscode-mock",
  setup(build) {
    build.onResolve({ filter: /^vscode$/ }, () => ({
      path: path.resolve("test/vscodeMock.ts"),
    }));
  },
};

try {
  const outfiles = [];
  for (const testFile of testFiles) {
    const outfile = path.join(
      outDir,
      `${path.basename(testFile, ".ts")}.cjs`
    );
    outfiles.push(outfile);
    await esbuild.build({
      entryPoints: [testFile],
      bundle: true,
      format: "cjs",
      platform: "node",
      target: "node18",
      outfile,
      plugins: [vscodeMockPlugin],
    });
  }

  await new Promise((resolve, reject) => {
    const child = spawn(process.execPath, ["--test", ...outfiles], {
      stdio: "inherit",
    });
    child.on("error", reject);
    child.on("exit", (code) => {
      if (code === 0) {
        resolve(undefined);
      } else {
        reject(new Error(`tests failed with exit code ${code}`));
      }
    });
  });
} finally {
  await rm(outDir, { recursive: true, force: true });
}
