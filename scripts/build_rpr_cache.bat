set TOOL_VERSION=%1
if not defined TOOL_VERSION set TOOL_VERSION=2.91

del cache_build.py
echo import os >> cache_build.py
echo import bpy >> cache_build.py
echo from rprblender import material_library >> cache_build.py
echo import os >> cache_build.py
echo bpy.context.scene.render.image_settings.file_format = 'JPEG' >> cache_build.py
echo bpy.context.scene.render.filepath = os.path.join(os.getcwd(), '..', 'Work', 'Results', 'Blender28', 'cache_building') >> cache_build.py
echo xml_path = os.path.join(material_library.path.get_library_path(), 'Wood_Wenge_Glossy', 'Wood_Wenge_Glossy' + '.xml') >> cache_build.py
echo material = bpy.data.materials['Material'] >> cache_build.py
echo material_library.import_xml_material(material, 'Material', xml_path, False) >> cache_build.py
echo bpy.ops.render.render(write_still=True) >> cache_build.py

"C:\\Program Files\\Blender Foundation\\Blender %TOOL_VERSION%\\blender.exe" -b "C:\TestResources\Blender2.8Assets\Materials\Test_Scene.blend" -E RPR -P "cache_build.py"