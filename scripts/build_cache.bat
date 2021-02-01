set TOOL_VERSION=%1
if not defined TOOL_VERSION set TOOL_VERSION=2.91

echo import os >> cache_build.py
echo import bpy >> cache_build.py
echo bpy.context.scene.render.image_settings.file_format = 'JPEG' >> cache_build.py
echo bpy.context.scene.render.filepath = os.path.join(os.getcwd(), '..', 'Work', 'Results', 'Blender28', 'cache_building') >> cache_build.py
echo bpy.ops.render.render(write_still=True) >> cache_build.py

"C:\\Program Files\\Blender Foundation\\Blender %TOOL_VERSION%\\blender.exe" -b -E RPR -P "cache_build.py"