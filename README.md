# wikipedia-Crawler

Uses requests, BeautifulSoup, eventually selenium, with python 2.7

wikiCrawler: 
A basic wikipedia Crawler that starts from an initial wikipedia article and recursively builds the set of all wikipedia articles that are accessible for a given maximum depth of recursivity

We print the results both on screen and in a file. 

wikiGraphCrawler.py:
Like wikiCrawler, but it moreover produces a directed graph (in graph theory sense) that links Wikipedia articles regarded as nodes. 

NodeList:  a (non-redundant) list of nodes
Each node is a dictionary associated with a given article.  A node has the following fields: 
     link       : A (non-redundant) list of url links all leading to the same article, 
     title      : The title of the article,
     depth      : The depth (i.e. recursivity level) where the node is lying 
     redirection:  A boolean value indicating whether a redirection of webpage happenned 
                  (In particular it means that the title and the followed url link do not correspond)
     stats: in the future we plan to compute some aggregated data that for some (or each) article. 

edgeSet : the set of edges (in graph theory sense). Each of them is a link between two articles
