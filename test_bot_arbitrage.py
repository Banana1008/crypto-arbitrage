import math
from time import sleep
import time
import yaml
from yaml.loader import SafeLoader

from PathFinder import PathFinder

def main():
    
    pf=PathFinder()
    
    paires=pf.init_paires()
    
    with open("config.yml") as config:
        data = yaml.load_all(config, Loader=SafeLoader)
        data=list(data)[0]
    
    if data["multi"]["exchange"]: 
        exchanges=pf.init_exchanges(paires)
    
    argent=1 #1 cycle[0]
    
    while True:
        
        if data["multi"]["exchange"]: 
        
            if data["async"]:
                pf.init_multi_graph_async(pf.rates_graph, exchanges, paires)
            else:
                pf.init_multi_graph(pf.rates_graph, exchanges, paires)
        
            tps1 = time.time_ns()
            
            pf._adjust_graph(pf.rates_graph)
            pf.init_digraph_from_multi(pf.rates_graph)
        else:
            pf.init_digraph(data["multi"]["which"], paires)
            tps1=time.time_ns()
        
        liste_arb=[]
        
        for curr in pf.currencies:
            if curr in pf.new_graph.nodes:
                cycle=pf.get_negative_cycle(pf.new_graph, source=curr)
            
                #print(pf.new_graph.edges.data())
                
                argent2=argent
                
                if (type(cycle) == list):
                    for i in range(len(cycle)-1):
                        edge=pf.new_graph[cycle[i]][cycle[i+1]]
                        #print(cycle[i], " -> ", cycle[i+1], " : ", math.exp(-edge["weight"]), " on ", edge["name"])
                        argent2*=math.exp(-edge["weight"])
                
                if type(cycle)==list and (argent2>=argent*data["arbitrage_rate"] and cycle not in liste_arb and cycle!=[]):
                    print("\n\n\nArbitrage possible !")    
                    print("On achète ", argent, " ", cycle[0], " et on vend ", argent2, " ", cycle[-1])
                    print("On gagne ", argent2-argent, " ", cycle[-1])
                    
                    argent2=argent
                    
                    for i in range(len(cycle)-1):
                        
                        edge=pf.new_graph[cycle[i]][cycle[i+1]]
                        
                        print(argent2, " ", cycle[i], " achète ", argent2*math.exp(-edge["weight"]), " ", cycle[i+1], " sur ", edge["name"], " à ", math.exp(-edge["weight"]), " ", cycle[i], " / ", cycle[i+1])
                        
                        #print(cycle[i], " -> ", cycle[i+1], math.exp(-edge["weight"]), " on ", edge["name"])
                        argent2*=math.exp(-edge["weight"])
                        
                    liste_arb.append(cycle)
            
        tps2 = time.time_ns()
        # print("Calcul des cycles en ", (tps2 - tps1)*10**(-9), " secondes")
        
        sleep(2)

if __name__ == "__main__":
    main()