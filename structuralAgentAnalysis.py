
import numpy as np
import pyphi
import networkx as nx
import copy
import pandas as pd
from utils import get_graph
from networkx.algorithms import degree_centrality, betweenness_centrality, flow_hierarchy

#####################################################################################################################
### Collection of functions to assess the structural properties of an agent based on its connectivity matrix (cm) ###

# Todo: 
# - Number of connections includes all nodes, not just connected nodes. Make option.
# - spectral density (Banerjee and Jost, 2009)? --> Too complicated.
# - density of connections and weight distributions (the latter for ANNs)

#####################################################################################################################

def number_of_connected_sensors(cm,sensor_ixs):
    # Sensors with outputs
    return np.sum(np.sum(cm[sensor_ixs,:],1)>0)

def number_of_connected_motors(cm,motor_ixs):
    # Motors with inputs
    return np.sum(np.sum(cm[:,motor_ixs],0)>0)

def number_of_densely_connected_nodes(cm_agent,allow_self_loops=False):
    # num hidden nodes with inputs and outputs
    cm = copy.copy(cm_agent)
    if not allow_self_loops:
        for i in range(len(cm)):
            cm[i,i] = 0
    return np.sum((np.sum(cm,0)*np.sum(cm,1))>0)

def connected_nodes(agent):
    #Sensors with outputs, motors with inputs, and hidden with both
    cm = copy.copy(agent.cm)
    # kill self loops
    for i in range(len(cm)):
        cm[i,i] = 0
    
    S = np.array(agent.sensor_ixs)
    cS_ind = np.where(np.sum(cm[S,:],1)>0)[0]
    cS = list(S[cS_ind])

    M = np.array(agent.motor_ixs)
    cM_ind = np.where(np.sum(cm[:,M],0)>0)[0]
    cM = list(M[cM_ind])
    
    cH = list(densely_connected_nodes(cm))
    return np.sort(cS + cM +cH)

def number_of_connected_nodes_by_type(agent):
    cm = agent.cm
    cS = number_of_connected_sensors(cm,agent.sensor_ixs)
    cH = number_of_densely_connected_nodes(cm)
    cM = number_of_connected_motors(cm,agent.motor_ixs)
    num_connected_nodes = {
        'cN': sum([cS, cH, cM]),
        'cS': cS,
        'cH': cH,
        'cM': cM
        }
    return pd.DataFrame(num_connected_nodes, index = [1])

def densely_connected_nodes(cm_agent,allow_self_loops=False):
    # Hidden nodes with inputs and outputs
    cm = copy.copy(cm_agent)
    if not allow_self_loops:
        for i in range(len(cm)):
            cm[i,i] = 0
    return np.where((np.sum(cm,0)*np.sum(cm,1))>0)[0]

def number_of_connections(cm,a_ixs,b_ixs):
    return np.sum(cm[np.ix_(a_ixs,b_ixs)]>0)

def number_of_connections_by_type(agent, connected_only = True):
    cm = agent.cm
    if connected_only:
        ind = set(connected_nodes(agent))
    else:
        ind = set(range(agent.n_nodes))

    S = list(ind.intersection(agent.sensor_ixs))
    M = list(ind.intersection(agent.motor_ixs))
    H = list(ind.intersection(agent.hidden_ixs))

    num_connections = {
        's_m': number_of_connections(cm, S, M),
        's_h': number_of_connections(cm, S, H),
        'h_h': number_of_connections(cm, H, H),
        'h_m': number_of_connections(cm, H, M)
        }
    return pd.DataFrame(num_connections, index = [1])

def LSCC(G):
    # largest strongly connected component using networkx graph
    LSCC = max(nx.strongly_connected_components(G), key=len)
    if len(LSCC) < 2:
        return None
    else:
        return LSCC

def len_LSCC(G):
    LSCC = max(nx.strongly_connected_components(G), key=len)
    return len(LSCC)

def len_LWCC(G):
    LWCC = max(nx.weakly_connected_components(G), key=len)
    return len(LWCC)

def average_betweenness_centrality(G, connected_only = True):
    # Betweenness centrality of a node v is the sum of the fraction of all-pairs 
    # shortest paths that pass through v.
    # Only densely connected hidden nodes can have positive betweenness_centrality
    HBC = betweenness_centrality(G)
    if connected_only:
        cm = np.array(nx.adjacency_matrix(G).todense())
        num_hidden = number_of_densely_connected_nodes(cm)
    else:
        num_hidden = len(agent.hidden_ixs)

    avHBC = sum([HBC[b] for b in HBC])/num_hidden
    return avHBC

def average_degree_centrality(G, connected_only = True):
    #The degree centrality for a node v is the fraction of nodes it is connected to.
    DC = degree_centrality(G)
    DC_list = [DC[d] for d in DC]
    avDC = sum(DC_list)/len(DC_list)
    return avDC

def fullStructuralAnalysis(agent, connected_only = True):
    df = number_of_connected_nodes_by_type(agent)
    df = df.join(number_of_connections_by_type(agent, connected_only = connected_only))
    # Components
    if connected_only == True:
        ind_con = connected_nodes(agent)
        cm_connected = agent.cm[np.ix_(ind_con, ind_con)]
        G = nx.from_numpy_matrix(cm_connected, create_using=nx.DiGraph())
    else:
        G = get_graph(agent)

    components = {
        'len_LSCC': len_LSCC(G),
        'len_LWCC': len_LWCC(G),
        'flow_hierarchy': flow_hierarchy(G), #Flow hierarchy is defined as the fraction of edges not participating in cycles in a directed graph
        'av_betweenness_centrality': average_betweenness_centrality(G, connected_only), 
        'av_degree_centrality': average_degree_centrality(G) 
        }

    df = df.join(pd.DataFrame(components, index = [1]))

    return df

def emptyStructuralAnalysis(index_num = 1):
    df = pd.DataFrame(dtype=float, columns = ['cN','cS', 'cH', 'cM', 's_m', 's_h', 'h_h', 'h_m', 'len_LSCC', 'len_LWCC', 
                'flow_hierarchy', 'av_betweenness_centrality', 'av_degree_centrality'], index = range(index_num))
    return df