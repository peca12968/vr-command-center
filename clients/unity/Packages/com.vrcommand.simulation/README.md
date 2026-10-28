# VR Command Simulation

Shared server rules for the VR Command project. The same Runtime C# files are compiled by Unity as this embedded package and by `src/VrCommand.Simulation` against .NET Standard 2.1 with C# 9. No Unity engine, management credential, transport or persistence dependency is included.

`ArenaWorld` provides a fixed 20 Hz simulation, geometric hitscan against rotated cover and body boxes, finite ammunition/reload, grid patrol/advance, automatic attacks and immutable snapshots/events. It is a single-owner server component; callers must authenticate commands and poses before invoking it.

The .NET build and headless checks are verified. Unity package import, engine compilation, IL2CPP, rendering, input and Quest/VIVE hardware remain unverified. The existing Unity scene does not instantiate this world yet. See the repository's `docs/SIMULATION.md` for rules, evidence and integration work.
