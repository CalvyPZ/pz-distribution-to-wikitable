# Project Zomboid Distributions to Wikitable

This script is used to generate wikitable files for [PZwiki](pzwiki.net)

## How to use this repository:
Requires python3.7 and tqdm

1. Create the `resources` folder and put the following lua files into it, all are found within `ProjectZomboid\projectzomboid\media\lua\`:
   - `shared\Distributions.lua`
   - `shared\ProceduralDistributions.lua`
   - `shared\Foraging\forageDefinitions.lua`
   - `server\Vehicles\VehicleDistributions.lua`
   - `shared\Definitions\AttachedWeaponDefinitions.lua`
2. Install requirements
3. For Windows, run `run.bat`, otherwise run `Main.py`.
4. Completed wiki tables will be in `output/complete` with the file name being `itemID.txt`.

**NOTICE FOR THOSE SUBMITTING MERGE REQUESTS: DO NOT INCLUDE LUA FILES FROM PROJECT ZOMBOID!**
