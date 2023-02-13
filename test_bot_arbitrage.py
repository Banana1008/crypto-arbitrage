import math
from time import sleep
import time
import nest_asyncio
import yaml
from yaml.loader import SafeLoader

from PathFinder import PathFinder

ARBITRAGE_PERCENTAGE=1.1

def main():
    
    nest_asyncio.apply()
    
    pf=PathFinder()
    
    paires=pf.init_paires()
    exchanges=pf.init_exchanges(paires)
    
    argent=1 #1 cycle[0]
    
    with open("config.yml") as config:
        data = yaml.load_all(config, Loader=SafeLoader)
        data=list(data)[0]
    
    while True:
        tps1 = time.time_ns()
        
        if data["async"]:
            pf.init_multi_graph_async(pf.rates_graph, exchanges, paires)
        else:
            pf.init_multi_graph(pf.rates_graph, exchanges, paires)
        
        pf.init_digraph(pf.rates_graph)
        
        liste_arb=[]
        
        for curr in pf.currencies:
            if curr in pf.new_graph.nodes:
                cycle=pf.get_negative_cycle(pf.new_graph, source=curr)
            
                #print(pf.new_graph.edges.data())
                
                argent2=argent
                
                for i in range(len(cycle)-1):
                    edge=pf.new_graph[cycle[i]][cycle[i+1]]
                    #print(cycle[i], " -> ", cycle[i+1], " : ", math.exp(-edge["weight"]), " on ", edge["name"])
                    argent2*=math.exp(-edge["weight"])
                
                if argent2>=argent*ARBITRAGE_PERCENTAGE and cycle not in liste_arb and cycle!=[]:
                    print("\n\n\nArbitrage possible !")
                    print("On achète ", argent, " ", cycle[0], " et on vend ", argent2, " ", cycle[-1])
                    print("On gagne ", argent2-argent, " ", cycle[-1])
                    
                    for i in range(len(cycle)-1):
                        edge=pf.new_graph[cycle[i]][cycle[i+1]]
                        print(cycle[i], " -> ", cycle[i+1], math.exp(-edge["weight"]), " on ", edge["name"])
                        argent2*=math.exp(-edge["weight"])
                        
                    liste_arb.append(cycle)
            
        tps2 = time.time_ns()
        #print("En ", (tps2 - tps1)*10**(-9), " secondes")
        
        sleep(10)

if __name__ == "__main__":
    main()