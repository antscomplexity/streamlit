import streamlit as st
# To make things easier later, we're also importing numpy and pandas for
# working with sample data.
import numpy as np
import pandas as pd
import time
import backboning
import networkx as nx
from bokeh.transform import transform



def get_network_weighted(path_to_net):
    G = nx.read_edgelist(path_to_net)
    edgelist=nx.to_pandas_edgelist(G)
    table, nnodes, nnedges = backboning.read(edgelist, 'weight', undirected=True, sep=' ')
    nc_table = backboning.noise_corrected(table, undirected=True)
    nc_backbone = backboning.thresholding(nc_table, 0.5)
    #nc_backbone.rename(columns={'src': 'source', 'trg': 'target', 'nij': 'weight'}, inplace=True)
    nx.from_pandas_edgelist(nc_backbone, edge_attr=['weight'])

    return nc_backbone, nx.from_pandas_edgelist(nc_backbone, edge_attr=['weight'])

def get_network_unweighted(path_to_net):
    G = nx.read_edgelist(path_to_net)
    return G


def bokeh_plot(G, title='Word network around #lockdown and #pandemia', layout='spring',
                        savefile=False, show_labels=False):
    # function to plot interactive network
    # arguments:
    # G: the network
    # communities: a dictionary that contains the morbidities as a key and the community it belongs to as a value, eg dict={'hypertension':0}
    # title: the title of the plot. (optional)
    # layout: 'spring' or 'circular' (optional, 'spring' by default)
    # savefile: True if you want to export a png of the network. The name of the file is the same as the title. (optional)
    # show_labels: True if you want to visualise morbidity names over the node WARNING: this disables highlight when hovering

    from bokeh.io import output_notebook, show, save, export_png
    from bokeh.models import Range1d, Circle, ColumnDataSource, MultiLine, EdgesAndLinkedNodes, NodesAndLinkedEdges, \
        LabelSet
    from bokeh.plotting import figure
    from bokeh.plotting import from_networkx
    from bokeh.palettes import Spectral8, Spectral4, Pastel1, Blues8
    from bokeh.palettes import Viridis256 as palette
    from bokeh.models import LinearColorMapper, LogColorMapper
    from bokeh.transform import linear_cmap
    from bokeh.embed import file_html
    from bokeh.resources import CDN
    from community import community_louvain
    from bokeh.models import ColorBar
    import random


    k = st.slider(
        "Number of sampled nodes (the more nodes you add the slower the visualisation)", min_value=10, max_value=len(G.nodes), value=100, step=1
    )
    sampled_nodes = random.sample(G.nodes, k)
    G = G.subgraph(sampled_nodes)
    # # create empty dictionaries
    # modularity_class = {}
    # modularity_color = {}
    # # loop through each community in the network
    # for comm in communities:
    #     # For each member of the community, add their community number and a distinct color
    #     for name in comm:
    #         modularity_class[comm] = communities[comm]
    #         modularity_color[comm] = Pastel1[8][communities[comm] % 8]
    # # add modularity class and color as attributes from the network above
    # nx.set_node_attributes(G, modularity_class, 'modularity_class')
    # nx.set_node_attributes(G, modularity_color, 'modularity_color')
    # color by centrality
    betweenness = nx.betweenness_centrality(G)
    nx.set_node_attributes(G, name='betweenness', values=betweenness)

    # set attributes
    degrees = dict(nx.degree(G))
    nx.set_node_attributes(G, name='degree', values=degrees)

    # set size by node weighted degree
    number_to_adjust_by = 0.5
    adjusted_node_size = dict(
        [(node, degree * number_to_adjust_by + 10) for node, degree in nx.degree(G)])
    nx.set_node_attributes(G, name='adjusted_node_size', values=adjusted_node_size)

    # choose attributes from G network to size and color by — setting manual size (e.g. 10) or color (e.g. 'skyblue') also allowed
    size_by_this_attribute = 'adjusted_node_size'
    color_by_this_attribute = 'betweenness'

    # establish which categories will appear when hovering over each node
    HOVER_TOOLTIPS = [
        ("Word", "@index"),
        ("Degree", "@degree"),
        ("Centrality", "@betweenness"),
    ]

    # create a plot — set dimensions, toolbar, and title
    plot = figure(tooltips=HOVER_TOOLTIPS,
                  tools="pan,wheel_zoom,save,reset, tap", active_scroll='wheel_zoom',
                  x_range=Range1d(-10.1, 10.1), y_range=Range1d(-10.1, 10.1), title=title, height_policy='max',
                  width_policy='max')

    plot.axis.visible = False
    plot.xgrid.grid_line_color = None
    plot.ygrid.grid_line_color = None

    # create a network graph object
    if layout == 'spring':
        network_graph = from_networkx(G,
                                      nx.fruchterman_reingold_layout,
                                      seed=9,
                                      scale=20,
                                      k=0.5,
                                      center=(0, 0))
    else:
        network_graph = from_networkx(G,
                                      nx.circular_layout,
                                      scale=9,
                                      center=(0, 0))

    # set node sizes and colors according to node degree (color as category from attribute)
    mapper = linear_cmap(color_by_this_attribute, Blues8, min(betweenness.values()), max(betweenness.values()))
    network_graph.node_renderer.glyph = Circle(size=size_by_this_attribute, fill_color=mapper)

    # set edge attributes
    network_graph.edge_renderer.data_source.data["line_width"] = [
        max(0.5, 0.001) for a, b in G.edges()]
    network_graph.edge_renderer.glyph = MultiLine(line_color="#CCCCCC", line_alpha=0.8)
    network_graph.edge_renderer.glyph.line_width = {'field': 'line_width'}
    network_graph.edge_renderer.selection_glyph = MultiLine(line_color='#dd0034',
                                                            line_width=1)
    network_graph.edge_renderer.hover_glyph = MultiLine(line_color='#dd0034', line_width=1)

    # highlight nodes and edges
    network_graph.selection_policy = NodesAndLinkedEdges()
    network_graph.inspection_policy = NodesAndLinkedEdges()
    color_bar = ColorBar(color_mapper=mapper['transform'], width=8)
    plot.add_layout(color_bar, 'right')
    # add labels
    if show_labels:
        x, y = zip(*network_graph.layout_provider.graph_layout.values())
        node_labels = list(G.nodes())
        source = ColumnDataSource({'x': x, 'y': y, 'name': [node_labels[i] for i in range(len(x))]})
        labels = LabelSet(x='x', y='y', text='name', source=source, background_fill_color='white',
                          text_font_size='10px', background_fill_alpha=.7)
        plot.renderers.append(labels)

    plot.renderers.append(network_graph)
    #show(plot)
    st.bokeh_chart(plot)

    # save png if savefile==True
    if savefile:
        export_png(plot, filename='{}/code/out/{}.png'.format(PATH_TO_FOLDER, title))
        #html = file_html(plot, CDN, title='Multimorbidity network')
        #print(html)

def main():

    expander = st.beta_expander("Description")
    expander.write("This is the word network related the hashtags '#lockdown' and '#pandemia' (Italian for 'pandemic'). ")
    expander = st.beta_expander("How to use the graph")
    expander.write("Use the menu on the left to change the number of nodes which are sampled. \n You can also change the layout parameters to better fit the current network.")

    net = get_network_unweighted("/Users/valerio/Desktop/lockdownANDPandemia.txt")
    bokeh_plot(net)


if __name__ == "__main__":
    main()

