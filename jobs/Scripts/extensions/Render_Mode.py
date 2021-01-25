def resetContour():
    bpy.data.scenes['Scene'].rpr.contour_use_object_id = True
    bpy.data.scenes['Scene'].rpr.contour_use_material_id = True
    bpy.data.scenes['Scene'].rpr.contour_use_shading_normal = True
    bpy.data.scenes['Scene'].rpr.contour_object_id_line_width = 1
    bpy.data.scenes['Scene'].rpr.contour_material_id_line_width = 1
    bpy.data.scenes['Scene'].rpr.contour_shading_normal_line_width = 1
    bpy.data.scenes['Scene'].rpr.contour_normal_threshold = 45
    bpy.data.scenes['Scene'].rpr.contour_antialiasing = 1
    