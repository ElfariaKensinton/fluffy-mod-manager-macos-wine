# Fluffy Mod Manager Wine launcher patch

Replaces Fluffy’s unsafe trainer memory scanner with bounded reads, downloads the Mesa runtime, and creates a one-click Windows launcher **inside the Fluffy Mod Manager folder**. Run that generated `FluffyModManager-Mesa.exe` from the same Wine/Proton/CrossOver prefix/container as the game. The launcher sets Mesa's software renderer and native OpenGL DLL override for Fluffy, then starts the adjacent `Modmanager.exe`. It does not install Fluffy into a bottle or alter game files.

## Quick use on macOS

1. Download this repository (Code → Download ZIP) and unzip it.
2. In Terminal, run:

   ```sh
   chmod +x patch-fluffy.sh
   ./patch-fluffy.sh "/path/to/Fluffy Mod Manager folder"
   ```

3. The script creates `FluffyModManager-Mesa.exe` in that exact folder. Launch that EXE using the same Wine/NotProton/CrossOver environment that runs your game.

The script checks for all four required Mesa DLLs in the target folder first. If they are already present, it skips the Mesa download and leaves them untouched. If any are missing, it downloads the pinned official Mesa 26.2.4 MinGW x64 release, verifies its SHA-256, extracts the runtime, and installs the required DLLs beside Fluffy. Existing DLLs are backed up as `.bak` before replacement. macOS's built-in `tar` is used for extraction; if unavailable for this archive, install 7-Zip with `brew install sevenzip` and rerun.

The trainer patch now recognizes the real scanner shared by stock **3.083 and 3.084**. The old 13-byte signature in this repository was absent from both stock executables; its error message did not mean the displayed version was wrong. Recognition now checks the complete scanner structure, its API imports, its game-context references, and x64 unwind metadata while allowing relocated addresses to differ. This permits supported rebuilds without depending on fixed code addresses or version labels.

The replacement uses one 1 MiB buffer and reads at most 1 MiB per call. It skips reserved, inaccessible and guarded regions, checks query/read results, bounds pattern comparisons to the bytes actually read, overlaps chunks so signatures crossing a chunk boundary remain detectable, and preserves wildcard and requested-occurrence matching. It no longer allocates the entire region reported by `VirtualQueryEx`, and it can still scan readable regions larger than 256 MiB. The original EXE receives a one-time `Modmanager.exe.pre-trainer-region-size-guard.bak` backup; repeated runs detect the replacement.

The patch changes the scanner function and extends its existing unwind range by five bytes into verified alignment padding. The original prologue, stack frame and saved registers are preserved. Source is in `src/trainer_scan.S`; `build.sh` builds the included `bin/trainer_scan.bin` and relocation metadata using `build_trainer.py`. No compiler is needed to apply the included patch. Unknown scanner layouts are refused with the executable hash rather than guessed from a version string.

Validation runs the **actual patched functions from both stock EXEs** under Wine, against controlled memory fixtures: wildcard and nth-occurrence matching, a signature crossing a 1 MiB boundary, the last legal match position, sparse reserved regions, guard-page preservation, invalid lengths, and a readable region larger than 256 MiB. Both pass; observed maximum allocation and read size are each 1,048,576 bytes. The fixture is `tests/trainer_scan.c`. These checks exercise the trainer scanner; they do not establish that every game-specific trainer signature still matches a particular game update.

To apply just the trainer fix without downloading Mesa again:

```sh
python3 patch_trainer_guard.py "/path/to/Fluffy Mod Manager/Modmanager.exe"
```

Run Fluffy and the game in the **same Wine prefix/bottle**. A trainer reporting “Process not found” is a separate process-visibility issue; this memory-scanner patch does not connect different prefixes.

## What the generated EXE does

- Writes `opengl32=native,builtin` to the prefix's `HKCU\Software\Wine\AppDefaults\Modmanager.exe\DllOverrides` before launch, and passes `WINEDLLOVERRIDES=opengl32=native,builtin` plus `GALLIUM_DRIVER=llvmpipe` to Fluffy.
- Starts `Modmanager.exe` from the same folder and inherits the caller's Wine prefix/container environment.
- Does not modify the game or any CrossOver bottle.

The generated launcher is a small, statically linked Windows x64 executable. Source is in `src/launcher.c`. The patch script uses the included launcher binary and requires no compiler. To rebuild it, install `mingw-w64` and run `./build.sh`.

## Requirements and limits

- macOS for the patch script; the resulting launcher runs under Wine, Proton, CrossOver, or NotProton.
- Fluffy Mod Manager x64 extracted to a folder containing `Modmanager.exe`.
- Internet access during patching so the script can fetch the Mesa runtime.
- A verified trainer scanner layout, currently tested in stock Fluffy 3.083 and 3.084. Other builds with the same normalized scanner are accepted; different layouts need analysis before patching.
- Start the generated EXE from the same Wine prefix/container as the target game if it needs to interact with that game. If the game launcher terminates child processes, start Fluffy after the game.

This project does not redistribute Fluffy Mod Manager or Mesa; the patch script downloads Mesa directly from its [official Windows distribution release](https://github.com/pal1000/mesa-dist-win/releases/tag/26.2.4) when run. Launcher code and script are MIT licensed.
