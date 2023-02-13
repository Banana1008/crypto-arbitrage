import asyncio
from collections import deque
import time
import networkx as nx 
import ccxt
import yaml
import math
from numpy import Inf
from yaml.loader import SafeLoader
import matplotlib.pyplot as plt
from concurrent.futures import ThreadPoolExecutor

class PathFinder:
    
    def __init__(self):
        self.currencies=list(self.init_currencies())
        self.paires=self.init_paires()
        self.exchanges=self.init_exchanges(self.paires)
        self.rates_graph=nx.MultiDiGraph()
        
        self.pred={}
        self.distances={}
        
        self.new_graph=None
    
    #fonction qui renvoie la liste des cryptos
    def init_currencies(self):
        with open('currencies.txt') as config:
            for line in config.readlines():
                yield line.strip()
    
    #fonction qui renvoie la liste des paires
    def init_paires(self):
        with open(self.config) as file_paires:
            for line in file_paires.readlines():
                yield line        

    # fonction pour initialiser les échanges que vous souhaitez utiliser
    def init_exchanges(self, paires):
        with open('exchanges.yml') as config:
            data = yaml.load_all(config, Loader=SafeLoader)
            data=list(data)[0]
        retour=[]
        
        for exchange in data:
            if data[exchange]['use']!=None and data[exchange]['use']:
                ex=ccxt.__getattribute__(exchange)()
                ex.load_markets()
                ex.apiKey=data[exchange]['api_key']
                ex.secret=data[exchange]['api_secret']
                retour.append(ex)
                
        return retour
    
    def _proceed_exchange(self, graph, exchange, paires):
        tps1=time.time_ns()
        
        for market in exchange.symbols:
            
            self._proceed_market(graph, exchange, paires, market)
                
        tps2=time.time_ns()
        
        print((tps2-tps1)*10**(-9), " secondes pour ", exchange.name)
    
    def _proceed_market(self, graph, exchange, paires, market):
        try:
            currency2, currency1 = market.split("/")
            if currency1 in self.currencies and currency2 in self.currencies:
                try:
                    ticker=exchange.fetch_ticker(market)
                except Exception as e:
                    print(e)
                        
                ask=ticker["ask"]
                bid=ticker["bid"]
                    
                if ask!=None and bid!=None:
                            
                    #les nodes sont ajoutées si elles y sont pas déjà
                    graph.add_edge(currency1, currency2, name=exchange.name, weight=-math.log(bid), market=market)
                    graph.add_edge(currency2, currency1, name=exchange.name, weight=math.log(ask), market=market) 
                        
        except ValueError as e:
            return
    
    def init_multi_graph(self, graph: nx.MultiDiGraph, exchanges: list[ccxt.Exchange], paires):
        """ market_prices: dict de markets (pour chaque exchange, en gros: liste de exchange.load_markets()"""
        for exchange in exchanges:
            self._proceed_exchange(graph, exchange, paires)
            
    
    def init_multi_graph_async(self, graph: nx.MultiDiGraph, exchanges: list[ccxt.Exchange], paires):
        """ market_prices: dict de markets (pour chaque exchange, en gros: liste de exchange.load_markets(), de manière asynchrone"""
        
        with ThreadPoolExecutor(len(exchanges)) as executor:
            executor.map(self._proceed_exchange, [graph for _ in range(len(exchanges))], exchanges, [paires for _ in range(len(exchanges))])
        
        
        
        
        
        
        
        
    
    def init_digraph(self, multi_graph: nx.MultiDiGraph):
        """transforme un multigraph en un digraph en prenant le poids le plus faible"""
        edges=multi_graph.edges
        
        self.new_graph=nx.DiGraph()
        
        for u,v,data in multi_graph.edges(data=True):
            w = data['weight'] if 'weight' in data else 1.0
            if self.new_graph.has_edge(u,v) and self.new_graph[u][v]['weight'] > w:
                self.new_graph[u][v]['weight'] = w
                self.new_graph[u][v]["name"] = data["name"]
            else:
                self.new_graph.add_edge(u, v, weight=w, name=data['name'], market=data['market'])

    def bellman_ford(self, G, sources, weight, pred, dist=None):
        
        for s in sources:
            if s not in G:
                raise nx.NodeNotFound(f"Source {s} not in G")

        if pred is None:
            pred = {v: [] for v in sources}

        if dist is None:
            dist = {v: 0 for v in sources}

        # Heuristic Storage setup. je l'ai pris sur internet ça je comprends pas de fou
        nonexistent_edge = (None, None)
        pred_edge = {v: None for v in sources}
        recent_update = {v: nonexistent_edge for v in sources}

        G_succ = G._adj  # For speed-up (and works for both directed and undirected graphs)
        inf = float("inf")
        n = len(G)

        count = {}
        q = deque(sources)
        in_q = set(sources)
        while q:
            u = q.popleft()
            in_q.remove(u)

            if all(pred_u not in in_q for pred_u in pred[u]):
                dist_u = dist[u]
                for v, e in G_succ[u].items():
                    dist_v = dist_u + weight(u, v, e)

                    if dist_v < dist.get(v, inf):
                        if v in recent_update[u]:
                            #trouvé letsgooo
                            pred[v].append(u)
                            return v

                        if v in pred_edge and pred_edge[v] == u:
                            recent_update[v] = recent_update[u]
                        else:
                            recent_update[v] = (u, v)

                        if v not in in_q:
                            q.append(v)
                            in_q.add(v)
                            count_v = count.get(v, 0) + 1
                            if count_v == n:
                                #cycle trouvé
                                return v

                            count[v] = count_v
                        dist[v] = dist_v
                        pred[v] = [u]
                        pred_edge[v] = u

                    elif dist.get(v) is not None and dist_v == dist.get(v):
                        pred[v].append(u)

        #pas de cycle 
        return None
    
    def get_negative_cycle(self, G, source, weight="weight"):
        """renvoie un cycle de poids négatif s'il y en a un, None sinon"""
        weight = self.get_poids(G)
        self.pred = {source: []}
        self.distances= {source: 0}

        v = self.bellman_ford(G, [source], weight, pred=self.pred, dist=self.distances)

        if v is None:
            raise nx.NetworkXError("nonnnnononn")

        #il y a un cycle négatif ;)
        neg_cycle = []
        stack = [(v, list(self.pred[v]))]
        seen = {v}
        while stack:
            node, preds = stack[-1]
            if v in preds:
                #cycle trouvé
                neg_cycle.extend([node, v])
                neg_cycle = list(reversed(neg_cycle))
                return neg_cycle

            if preds:
                nbr = preds.pop()
                if nbr not in seen:
                    stack.append((nbr, list(self.pred[nbr])))
                    neg_cycle.append(node)
                    seen.add(nbr)
            else:
                stack.pop()
                if neg_cycle:
                    neg_cycle.pop()
                else:
                    if v in G[v] and weight(G, v, v) < 0:
                        return [v, v]
                    continue
        return [] 
    
    def get_poids(self, G):
        return lambda u, v, data: data.get("weight", 1)
        
  
def test_init_digraph():
    pf=PathFinder()
    pf.init_multi_graph(pf.rates_graph, pf.exchanges, pf.init_paires())
    pf.init_digraph(pf.rates_graph)
    
    print(pf.new_graph.edges.data())
    
    print(pf.pred, pf.distances)
    
    assert pf.new_graph.number_of_nodes()==pf.rates_graph.number_of_nodes()
    nx.draw(pf.new_graph, with_labels=True, font_weight='bold', node_size=1000, node_color="skyblue", font_size=8, width=2, edge_color="red", arrowsize=20, arrowstyle="->")
    nx.draw_networkx_edge_labels(pf.new_graph, pos=nx.shell_layout(pf.new_graph), edge_labels=nx.get_edge_attributes(pf.new_graph, 'weight'), font_size=8)

    plt.show()
    
def test_init_exchanges():
    pf=PathFinder()
    exchanges=pf.init_exchanges(pf.paires)
    
def test_bellman_ford():
    pf=PathFinder()
    pf.init_multi_graph(pf.rates_graph, pf.exchanges, pf.init_paires())
    pf.init_digraph(pf.rates_graph)
    
    cycle=pf.get_negative_cycle(pf.new_graph, source="TRX")
    
    #print(pf.new_graph.edges.data())
    
    print(cycle)
    
    argent=1 #1 cycle[0]
    
    print(argent, " ", cycle[0])
    
    for i in range(len(cycle)-1):
        edge=pf.new_graph[cycle[i]][cycle[i+1]]
        print(cycle[i], " -> ", cycle[i+1], " : ", math.exp(-edge["weight"]), " on ", edge["name"])
        argent*=math.exp(-edge["weight"])
    
    print(argent, " ", cycle[0])

if __name__ == "__main__":
    test_bellman_ford()
    # test_init_digraph()
    # test_init_exchanges()
            