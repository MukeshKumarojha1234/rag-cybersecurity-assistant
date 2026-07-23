# SOP-IR-014 — Ransomware Containment Procedure

On suspected ransomware activity:

1. Isolate affected hosts from the network immediately (disable network
   interfaces or pull the switch port; do not rely on remote shutdown).
2. Preserve volatile memory and disk state for forensics before any
   remediation — do not power off encrypted systems.
3. Notify the incident response (IR) lead and open a P1 incident ticket.
4. Identify patient zero and lateral movement paths using EDR telemetry.
5. Do not pay ransom or communicate with attackers without legal and
   executive sign-off.
6. Begin restoration from known-good backups only after the environment
   has been confirmed clean.
