def get_node_and_surfaceshader():
    ss_node =  bpy.data.node_groups['MX_Uber'].nodes['Standard surface']
    nd_surfaceshader = ss_node.nd_surfaceshader
    return ss_node, nd_surfaceshader


def default_settings():
    ss_node, nd_surfaceshader = get_node_and_surfaceshader()

    ss_node.f_base = True
    ss_node.f_coat = False
    ss_node.f_emission = False
    ss_node.f_geometry = False
    ss_node.f_sheen = False
    ss_node.f_specular = False
    ss_node.f_subsurface = False
    ss_node.f_thin_film = False
    ss_node.f_transmission = False

    nd_surfaceshader.in_base = 0.96
    nd_surfaceshader.in_base_color = (0.219, 1, 0.081)
    nd_surfaceshader.in_diffuse_roughness = 0
    nd_surfaceshader.in_metalness = 0

    nd_surfaceshader.in_specular = 0
    nd_surfaceshader.in_specular_color = (1, 1, 1)
    nd_surfaceshader.in_specular_roughness = 0
    nd_surfaceshader.in_specular_IOR = 0
    nd_surfaceshader.in_specular_anisotropy = 0
    nd_surfaceshader.in_specular_rotation = 0

    nd_surfaceshader.in_transmission = 0
    nd_surfaceshader.in_transmission_color = (0, 0, 0)
    nd_surfaceshader.in_transmission_depth = 0
    nd_surfaceshader.in_transmission_scatter = (0.4, 0, 0.4)
    nd_surfaceshader.in_transmission_scatter_anisotropy = 0
    nd_surfaceshader.in_transmission_dispersion = 0
    nd_surfaceshader.in_transmission_extra_roughness = 0

    nd_surfaceshader.in_subsurface = 0
    nd_surfaceshader.in_subsurface_color = (1, 1, 1)
    nd_surfaceshader.in_subsurface_radius = (0.686, 0, 0)
    nd_surfaceshader.in_subsurface_scale = 0.84
    nd_surfaceshader.in_subsurface_anisotropy = 0

    nd_surfaceshader.in_sheen = 0
    nd_surfaceshader.in_sheen_color = (0, 1, 1)
    nd_surfaceshader.in_sheen_roughness = 0.3

    nd_surfaceshader.in_coat = 0
    nd_surfaceshader.in_coat_color = (0.157, 1, 0.164)
    nd_surfaceshader.in_coat_roughness = 0.1
    nd_surfaceshader.in_coat_anisotropy = 0
    nd_surfaceshader.in_coat_rotation = 0
    nd_surfaceshader.in_coat_IOR = 1.5
    nd_surfaceshader.in_coat_affect_color = 0
    nd_surfaceshader.in_coat_affect_roughness = 0

    nd_surfaceshader.in_thin_film_thickness = 57.78
    nd_surfaceshader.in_thin_film_IOR = 3

    nd_surfaceshader.in_emission = 10
    nd_surfaceshader.in_emission_color = (0, 0.1, 0)
    
    nd_surfaceshader.in_opacity = (1, 1, 1)
    nd_surfaceshader.in_thin_walled = False


def create_texture2d_image(filename, node_name, attr):
    node = bpy.data.node_groups['MX_Uber'].nodes[node_name]
    image = bpy.data.node_groups['MX_Uber'].nodes.new('hdusd.MxNode_STD_image')
    image.prop.p_file = os.path.join(RES_PATH, 'Maps', filename)
    bpy.data.node_groups['MX_Uber'].links.new(node.inputs[attr], image.outputs['out'])


def delete_texture2d_image():
    image = bpy.data.node_groups['MX_Uber'].nodes['Image']
    bpy.data.node_groups['MX_Uber'].nodes.remove(image)
    