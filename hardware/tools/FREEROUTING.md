# Freerouting 2.4.1 (headless)

Run both commands from `hardware/`.

Fetch: `gh release download v2.4.1 --repo freerouting/freerouting --pattern freerouting-2.4.1.jar --dir tools`

Route:

    java -jar tools/freerouting-2.4.1.jar -de in.dsn -do out.ses -mp 100 \
      --gui.enabled=false --api_server.enabled=false \
      --usage_and_diagnostic_data.disable_analytics=true

- `-de` input DSN, `-do` output SES, `-mp` max passes (from `--help`).
- `--<section>.<key>=<value>` overrides settings. The keys above are not in `--help`;
  they come from the jar's settings classes. Unknown keys log `WARN Unknown settings property`,
  and these three log nothing, so they are accepted. `-de` plus `-do` switches on batch (CLI) mode.
- Checked on 2026-09-28: a nonexistent input exits 1 in the terminal ("Couldn't load the input file").
