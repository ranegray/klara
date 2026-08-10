"""klara-sim-isaac: Isaac Sim implementation of the klara-core contract.

Runs inside Isaac Sim's bundled Python (see docs/SETUP.md). Keep this package
as thin as possible — scene setup, the RobotAPI/EnvAPI adapters, and the
joint-level stressor application point. Omniverse APIs churn between
releases; the less code that touches omni.*, the less breaks on upgrade.

Import rule: this is the ONLY package in the workspace allowed to import
omni/isaacsim modules, and imports happen inside functions so that merely
importing klara_sim_isaac (e.g. in CI) does not require Isaac.
"""
