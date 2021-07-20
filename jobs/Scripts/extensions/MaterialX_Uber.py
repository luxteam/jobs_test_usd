def get_node_and_surfaceshader():
    rpr_uber =  bpy.data.node_groups['MX_Uber'].nodes['RPR Uber']
    nd_surfaceshader = rpr_uber.nd_surfaceshader
    return rpr_uber, nd_surfaceshader


def default_settings():
    rpr_uber, nd_surfaceshader = get_node_and_surfaceshader()

    rpr_uber.f_diffuse = True
    rpr_uber.f_reflection = False
    rpr_uber.f_refraction = False
    rpr_uber.f_coating = False
    rpr_uber.f_sheen = True
    rpr_uber.f_emission = False
    rpr_uber.f_transparency = False
    rpr_uber.f_subsurface = False

    nd_surfaceshader.in_uber_diffuse_color = (0, 0.4, 0)
    nd_surfaceshader.in_uber_diffuse_weight = 1.0
    nd_surfaceshader.in_uber_diffuse_roughness = 0.0

    nd_surfaceshader.in_uber_reflection_color = (1.0, 1.0, 1.0)
    nd_surfaceshader.in_uber_reflection_weight = 0.0
    nd_surfaceshader.in_uber_reflection_roughness = 0.0
    nd_surfaceshader.in_uber_reflection_anisotropy = 0.0
    nd_surfaceshader.in_uber_reflection_anisotropy_rotation = 0.0
    nd_surfaceshader.in_uber_reflection_mode = 'PBR'
    nd_surfaceshader.in_uber_reflection_ior = 1.5
    nd_surfaceshader.in_uber_reflection_metalness = 0.0

    nd_surfaceshader.in_uber_fresnel_schlick_approximation = 1.0
    nd_surfaceshader.in_uber_sheen = (1.0, 1.0, 1.0)
    nd_surfaceshader.in_uber_sheen_tint = 0.0
    nd_surfaceshader.in_uber_sheen_weight = 0.0

    nd_surfaceshader.in_uber_refraction_color = (1.0, 1.0, 1.0)
    nd_surfaceshader.in_uber_refraction_weight = 0.0
    nd_surfaceshader.in_uber_refraction_roughness = 0.0
    nd_surfaceshader.in_uber_refraction_ior = 1.5
    nd_surfaceshader.in_uber_refraction_thin_surface = False
    nd_surfaceshader.in_uber_refraction_absorption_color = (0.0, 0.0, 1.0)
    nd_surfaceshader.in_uber_refraction_absorption_distance = 0.0
    nd_surfaceshader.in_uber_refraction_caustics = True

    nd_surfaceshader.in_uber_coating_color = (1.0, 1.0, 1.0)
    nd_surfaceshader.in_uber_coating_weight = 0.0
    nd_surfaceshader.in_uber_coating_roughness = 0.0
    nd_surfaceshader.in_uber_coating_mode = 'PBR'
    nd_surfaceshader.in_uber_coating_ior = 1.5
    nd_surfaceshader.in_uber_coating_metalness = 0.0
    nd_surfaceshader.in_uber_coating_thickness = 0.0
    nd_surfaceshader.in_uber_coating_transmission_color = (1.0, 1.0, 1.0)

    nd_surfaceshader.in_uber_emission_color = (1.0, 1.0, 1.0)
    nd_surfaceshader.in_uber_emission_weight = 0.0
    nd_surfaceshader.in_uber_emission_mode = 'Singlesided'

    nd_surfaceshader.in_uber_transparency = 0.0
    nd_surfaceshader.in_uber_sss_scatter_color = (1.0, 1.0, 1.0)
    nd_surfaceshader.in_uber_sss_scatter_distance = 0.0
    nd_surfaceshader.in_uber_sss_scatter_direction = 0.0
    nd_surfaceshader.in_uber_sss_weight = 0.0
    nd_surfaceshader.in_uber_sss_multiscatter = False
    nd_surfaceshader.in_uber_backscatter_weight = 0.0
    nd_surfaceshader.in_uber_backscatter_color = (1.0, 1.0, 1.0)


def create_texture2d_image(filename, node_name, attr):
    node = bpy.data.node_groups['MX_Uber'].nodes[node_name]
    image = bpy.data.node_groups['MX_Uber'].nodes.new('hdusd.MxNode_STD_image')
    image.prop.p_file = os.path.join(RES_PATH, 'Maps', filename)
    bpy.data.node_groups['MX_Uber'].links.new(node.inputs[attr], image.outputs['out'])


def delete_texture2d_image():
    image = bpy.data.node_groups['MX_Uber'].nodes['Image']
    bpy.data.node_groups['MX_Uber'].nodes.remove(image)


def create_rpr_normalmap(node_name, attr):
    node = bpy.data.node_groups['MX_Uber'].nodes[node_name]
    normalmap = bpy.data.node_groups['MX_Uber'].nodes.new('hdusd.MxNode_RPR_rpr_normal_map')
    bpy.data.node_groups['MX_Uber'].links.new(node.inputs[attr], normalmap.outputs['out'])


def delete_rpr_normalmap():
    normalmap = bpy.data.node_groups['MX_Uber'].nodes['RPR Normal Map']
    bpy.data.node_groups['MX_Uber'].nodes.remove(normalmap)
    