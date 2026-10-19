# Fluffy Mod Manager Wine launcher patch

Patches the Fluffy 3.084 trainer scan guard, downloads the Mesa runtime, and creates a one-click Windows launcher **inside the Fluffy Mod Manager folder**. Run that generated `FluffyModManager-Mesa.exe` from the same Wine/Proton/CrossOver prefix/container as the game. The launcher sets Mesa's software renderer and native OpenGL DLL override for Fluffy, then starts the adjacent `Modmanager.exe`. It does not install Fluffy into a bottle or alter game files.

## Quick use on macOS

1. Download this repository (Code → Download ZIP) and unzip it.
2. In Terminal, run:

   ```sh
   chmod +x patch-fluffy.sh
   ./patch-fluffy.sh "/path/to/Fluffy Mod Manager folder"
   ```

3. The script creates `FluffyModManager-Mesa.exe` in that exact folder. Launch that EXE using the same Wine/NotProton/CrossOver environment that runs your game.

The script automatically downloads the pinned official Mesa 26.2.4 MinGW x64 release, verifies its SHA-256, extracts the runtime, and installs the required DLLs beside Fluffy. Existing DLLs are backed up as `.bak` before replacement. macOS's built-in `tar` is used for extraction; if unavailable for this archive, install 7-Zip with `brew install sevenzip` and rerun.

It also applies the trainer crash fix from this project: Fluffy's trainer memory scanner now checks `MEMORY_BASIC_INFORMATION.RegionSize` and skips address-space regions at least 256 MiB, instead of testing the unrelated `Type` field. This lets the scan include the game's image region while avoiding oversized mappings. The patcher accepts only the known Fluffy 3.084 instruction signature, verifies it occurs exactly once, makes a one-time `Modmanager.exe.pre-trainer-region-size-guard.bak` backup, and is safe to rerun. Other Fluffy builds are refused without modifying the EXE.

## What the generated EXE does

- Sets `WINEDLLOVERRIDES=opengl32=n,b` and `GALLIUM_DRIVER=llvmpipe` for Fluffy.
- Starts `Modmanager.exe` from the same folder and inherits the caller's Wine prefix/container environment.
- Does not modify the game or any CrossOver bottle.

The generated launcher is a small, statically linked Windows x64 executable. Source is in `src/launcher.c`. The patch script uses the included launcher binary and requires no compiler. To rebuild it, install `mingw-w64` and run `./build.sh`.

## Requirements and limits

- macOS for the patch script; the resulting launcher runs under Wine, Proton, CrossOver, or NotProton.
- Fluffy Mod Manager x64 extracted to a folder containing `Modmanager.exe`.
- Internet access during patching so the script can fetch the Mesa runtime.
- Fluffy Mod Manager 3.084; other EXE builds need their trainer scan signature mapped before the binary patch can be applied.
- Start the generated EXE from the same Wine prefix/container as the target game if it needs to interact with that game. If the game launcher terminates child processes, start Fluffy after the game.

This project does not redistribute Fluffy Mod Manager or Mesa; the patch script downloads Mesa directly from its [official Windows distribution release](https://github.com/pal1000/mesa-dist-win/releases/tag/26.2.4) when run. Launcher code and script are MIT licensed.
