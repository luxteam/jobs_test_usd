
def deactivate_all_aovs(view_layer):
    for number in range(1, 30):
        view_layer.rpr.enable_aovs[number] = False


def deleteOldRenderLayerNodes(nodes):
    for node in nodes:
        if node.type in ("R_LAYERS", "COMPOSITE", "OUTPUT_FILE"):
            try:
                nodes.remove(node)
            except Exception as e:
                print('Error while removing node: ' + str(e))

def connect_nodes(out_node_name, out_attr, input_node_name, input_attr):
    nodes = bpy.data.scenes["Scene"].node_tree.nodes
    bpy.data.scenes["Scene"].node_tree.links.new(nodes[out_node_name].outputs[out_attr], 
        nodes[input_node_name].inputs[input_attr])

def nodes():
    return bpy.data.scenes["Scene"].node_tree.nodes
