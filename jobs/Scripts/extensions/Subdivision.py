def setSubdivision(adaptive_level = 1, crease_weight = 1, subdivision_type = 'EDGE_CORNER'):
    objects = [
        bpy.data.objects["Cube.002"].rpr,
        bpy.data.objects["Torus"].rpr,
        bpy.data.objects["Cone"].rpr,
        bpy.data.objects["Suzanne"].rpr
    ]
    for object in objects:
        object.subdivision_factor = adaptive_level
        object.subdivision_crease_weight = crease_weight
        object.subdivision_boundary_type = subdivision_type
