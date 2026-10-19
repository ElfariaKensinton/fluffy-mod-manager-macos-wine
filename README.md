# Fluffy Mod Manager Wine launcher patch

Creates a one-click Windows launcher **inside the Fluffy Mod Manager folder**. Run that generated `FluffyModManager-Mesa.exe` from the same Wine/Proton/CrossOver prefix/container as the game. The launcher sets Mesa's software renderer and native OpenGL DLL override for Fluffy, then starts the adjacent `Modmanager.exe`. It does not install Fluffy into a bottle or alter game files.

## Quick use on macOS

1. Download this repository (Code → Download ZIP) and unzip it.
2. In Terminal, run:

   ```sh
   chmod +x patch-fluffy.sh
   ./patch-fluffy.sh "/path/to/Fluffy Mod Manager folder"
   ```

3. The script creates `FluffyModManager-Mesa.exe` in that exact folder. Launch that EXE using the same Wine/NotProton/CrossOver environment that runs your game.

If the Fluffy folder does not already contain a matching Mesa runtime, provide its folder as a second argument:

```sh
./patch-fluffy.sh "/path/to/Fluffy Mod Manager folder" "/path/to/Mesa-runtime-x64"
```

The Mesa folder must contain `opengl32.dll` and `libgallium_wgl.dll`. Companion `dxil.dll` and `spirv_to_dxil.dll` are copied if present. DLLs with the same names in the Fluffy folder are backed up as `.bak` before replacement. Use all DLLs from one Mesa build.

## What the generated EXE does

- Sets `WINEDLLOVERRIDES=opengl32=n,b` and `GALLIUM_DRIVER=llvmpipe` for Fluffy.
- Starts `Modmanager.exe` from the same folder and inherits the caller's Wine prefix/container environment.
- Does not modify the game or any CrossOver bottle.

The generated launcher is a small, statically linked Windows x64 executable. Source is in `src/launcher.c`. The patch script uses the included launcher binary and requires no compiler. To rebuild it, install `mingw-w64` and run `./build.sh`.

## Requirements and limits

- macOS for the patch script; the resulting launcher runs under Wine, Proton, CrossOver, or NotProton.
- Fluffy Mod Manager x64 extracted to a folder containing `Modmanager.exe`.
- A compatible Mesa runtime beside `Modmanager.exe` (already present or supplied to the script).
- Start the generated EXE from the same Wine prefix/container as the target game if it needs to interact with that game. If the game launcher terminates child processes, start Fluffy after the game.

This project does not redistribute Fluffy Mod Manager or Mesa. Launcher code and script are MIT licensed.
