# Superseded preflight

This check was superseded by `preflight-20261020-02`.

Reason: the manifest's file/directory summary counts were wrong because the
manifest script counted `file`/`dir` entries under `files`/`dirs` keys. The probe
outputs and the integrity booleans were otherwise valid, but the corrected
script was rerun under a new check-id rather than overwriting this directory.
Use `preflight-20261020-02` as the authoritative preflight.
