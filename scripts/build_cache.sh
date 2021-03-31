#!/bin/bash
TOOL=${1:-2.93}

rm cache_build.py
echo "import os" >> cache_build.py
echo "import bpy" >> cache_build.py
echo "bpy.context.scene.render.image_settings.file_format = 'JPEG'" >> cache_build.py
echo "bpy.data.scenes['Scene'].hdusd.final.delegate = 'HdRprPlugin'" >> cache_build.py
echo "bpy.context.scene.render.filepath = os.path.join(os.getcwd(), '..', 'Work', 'Results', 'BlenderUSDHydra', 'cache_building')" >> cache_build.py
echo "bpy.ops.render.render(write_still=True)" >> cache_build.py

blender"$TOOL" -b -E HdUSD -P "cache_build.py"