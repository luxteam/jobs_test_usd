def connect_nodes(out_node_name, out_attr, input_node_name, input_attr):
    nodes = bpy.data.scenes["Scene"].node_tree.nodes
    bpy.data.scenes["Scene"].node_tree.links.new(nodes[out_node_name].outputs[out_attr], 
        nodes[input_node_name].inputs[input_attr])

def create_compositor_node(node_name):
    bpy.data.scenes["Scene"].node_tree.nodes.new("CompositorNode" + node_name)
    nodes = bpy.data.scenes["Scene"].node_tree.nodes

def nodes():
    return bpy.data.scenes["Scene"].node_tree.nodes