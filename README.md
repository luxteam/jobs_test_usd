# Autotests for USD plugin for Blender

## Install
 1. Clone this repo
 2. Get `jobs_launcher` as git submodule, using next commands
 `git submodule init`
 `git submodule update`
 3. Check that `usd_blender_autotests` scenes placed in `C:/TestResources`
 4. Run `scripts/run.bat` with customised `--cmd_variables`. For example:

     > --cmd_variables Tool "C:\Program Files\Blender Foundation\Blender\blender.exe" RenderDevice 'gpu' TestsFilter small
     * Tool define path to Blender
     * RenderDevice define what hardware will be used.
         'gpu' - GPU
         'cpu' - CPU
     * TestsFilter takes only `small` or `full`, and define count of scenes that will be send ot render.
