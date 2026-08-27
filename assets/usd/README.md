# USD assets

Isaac Sim USD for the XLeRobot, converted from the source-of-truth URDF in
[`ros2_ws/src/klara_description/urdf/`](../../ros2_ws/src/klara_description/urdf/).

## Import

The importer targets Isaac Sim 6.0.1. Run it with Isaac Sim's bundled Python
launcher; the script itself remains in this repository:

```bash
<isaac-sim>/python.sh <repo>/assets/usd/import_klara.py
```

For example, if Isaac Sim is extracted at `~/isaacsim`:

```bash
~/isaacsim/python.sh /home/justin/klara/assets/usd/import_klara.py
```

This reads `klara_description/urdf/xlerobot.urdf`, resolves its
`package://klara_description/...` mesh paths, and writes one flattened asset
to `assets/usd/klara.usd`. The source URDF's fixed base, link structure, and
authored collision geometry are preserved. Existing output is not replaced
unless `--force` is passed.

Use `--urdf` or `--output` to override either path; `--windowed` shows Isaac
Sim while the conversion runs. Add `--help` to the command above to list all
options without starting Isaac Sim.

Convention:

- The URDF (and its meshes) in `klara_description` remain the single source of
  truth for robot geometry. Never hand-edit kinematics in USD; fix the URDF
  and re-convert.
- Convert with this script and Isaac Sim 6.0.1; note the Isaac Sim version
  used in the commit message.
- Commit converted USD here if it stays small (a few MB); larger scene assets
  go to `data/` (gitignored) with a download note here.
- Joint drive gains / physics tuning applied on top of the import live here in
  USD and are experiment-relevant: record changes in the commit history, since
  sim fidelity is a defensible-question topic.
