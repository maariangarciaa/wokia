import { spawnSync } from "node:child_process";

function run(label, args) {
  const result = spawnSync(process.execPath, args, {
    stdio: "inherit",
    shell: false,
  });

  if (result.status !== 0) {
    process.exit(result.status ?? 1);
  }
}

run("TypeScript", ["./node_modules/typescript/lib/tsc.js"]);
run("Vite", ["./node_modules/vite/bin/vite.js", "build"]);
