const command = process.argv[2] || "npm";
const allowed = process.env.ALLOW_NPM_COMMANDS === "1";

if (!allowed) {
  console.error(
    [
      `Blocked npm command: ${command}`,
      "This project restricts direct npm execution. Use Docker Compose for normal build/deploy commands.",
      "If you intentionally need to run it locally, set ALLOW_NPM_COMMANDS=1 for this command only."
    ].join("\n")
  );
  process.exit(1);
}
