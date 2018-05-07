#!/usr/bin/env python   # if on Linux
#-*- coding: utf-8 -*-

"""  WikiGraphCrawler.py

With python 2.7
A more complex variant of WikiCrawler.py.
It creates the directed graph of the links between Wikipedia articles that are accessible for a given maximum depth of recursivity. 
We build a list of dictionary of nodes and a list of edges represented by couples of node
Each node is a dictionary associated with a specific wikipedia article:  {id, url, title, redirected, stats}
The keyword stats is still empty but is create for future applications of NLP methods. 

"""

from __future__ import unicode_literals # à activer si en python2.7

import requests  
from bs4 import BeautifulSoup
import time  # for performance testing
import re
from selenium import webdriver # in case of some cases of url redirection:  Maybe useless
import json

# to select the article pages on a wikipedia page ( they do not contain colons), and filter the file that contain colons in the URL
rx=re.compile("^(/wiki/[^:]+$)")   # if we want to include /wiki/  in each link.   OK 

def divContent_soup(HTML):
     ### processing HTML page with BeautifulSoup
    soup=BeautifulSoup(HTML, "lxml")  
    if soup is None: 
        printLog("\nThe website %s responded but the response is not HTML (and not in XML or any text). ")

    divContent =soup.find("div",{"id":"content"})
    
    divBodyContent=divContent.find("div",{"id":"bodyContent"})
    divContentText   =   divBodyContent.find("div",{"id":"mw-content-text"})
    
    divOutput=divContentText.find('div', {'class':'mw-parser-output'})    
    
    redirected = divBodyContent.find('span', {'class', 'mw-redirectedfrom'}) 
    
    title =divContent.find("h1",{"id":"firstHeading"}).get_text()
    if verbose and title is not None: printLog(title)  
    
    # all of these outputs are None if nothing is found    
    return divContent, divBodyContent,divOutput, title , redirected

def divContent_requests(pageUrl):
    # extracts the following subsections of HTML: 
    # divContent : the subsection <'div', class:'bodyContent'...> 
    # divOutput:  the subsection <'div', class:'mw-parser-output'...> 
    # via requests and BeautifulSoup packages
    
    # initialisation in case of request failure, or if the response is not HTML  
    r = None;            soup = None  
    divContent =None;    noArticle =None;     divBodyContent=None
    divOutput  =None;    title = None;        redirected =None
    noResponse= None
    try: 
        r=requests.get(pageUrl)
        '''except NewConnectionError, error:    
        printLog(error)
        #NameError: global name 'NewConnectionError' is not defined'''
    except: 
        printLog('\nError: requests cannot find url %s'%pageUrl)
        noResponse = True
    else:
        noResponse = False
        ### processing HTML page with BeautifulSoup
        divContent, divBodyContent,divOutput, title, redirected= divContent_soup(r.text) 
        if divOutput is None:     
            printLog( "\nDid not find a wikipedia article this url: %s \n (But maybe a wikipedia page nevertheless exists)"% r.url    )
         
        #---   after requests :
        noArticleText  = divBodyContent.find("table",{"id":"noarticletext"})
        
        if divBodyContent is not None:    
            noArticleText  = divBodyContent.find("table",{"id":"noarticletext"})
        
            if noArticleText is None:
                noArticle = False # i.e. an article exists
            elif noArticleText is not None:
                noArticle =  True
                printLog(noArticleText.get_text())
       
        
    
    return divContent, divBodyContent,divOutput, title, redirected, noArticle, noResponse

def divContent_selenium(pageUrl):
    # extracts the following subsections of HTML via the selenium browser : 
    # divContent : the subsection <'div', class:'bodyContent'...> 
    # divOutput:  the subsection <'div', class:'mw-parser-output'...> 
    
    if verbose: printLog(  "We try using selenium Browser")
    
    browser = webdriver.Firefox()
    browser.get(pageUrl) 
    innerHTML = browser.execute_script("return document.body.innerHTML")
    browser.close()
    
    divContent=None;  divBodyContent=None; divOutput=None; 
    noArticle =None;  title=None; redirected =None
    
    ### processing the HTML page with BeautifulSoup
    divContent, divBodyContent,divOutput, title, redirected= divContent_soup(innerHTML) 
    
    
    if divBodyContent is not None:    
        noArticleText  = divBodyContent.find("table",{"id":"noarticletext"})
        
        if noArticleText is None:
            noArticle = False # i.e. an article exists
        elif noArticleText is not None:
            noArticle =  True
            printLog(noArticleText.get_text())
        
        
    if divOutput is None:     
        printLog( " Did not find a wikipedia article for sure with this url: %s \n (Maybe a wikipedia error page though...)"%pageUrl   )
    else: 
        if verbose: printLog(' wikipedia article has finally been found')    
        
    return divContent, divBodyContent,divOutput, title, redirected, noArticle

def getLinkList_2(divOutput):
    # not needed but clearer IMO
    global rx 
     
    ###  linkList     
    # a list of sublists of "a" tags that satisfy the regex rx:
    aList=[e.findAll("a", { 'href':rx}) for e in divOutput.findAll('p') ]  
        
    # the list of links (in href attribute of a tag), 
    #via nested list comprehension , i.e. [item for sublist in lst for item in sublist]      
    linkList1=[aTagRx.get('href') for sublist in aList for aTagRx in sublist]   # with the wiki part of links
        
    # if a subsection is indicated in one of the wikipedia links, we discard it and keep only the page link
    linkList2 = [ toSearch.split('#')[0] if "#" in toSearch else toSearch for toSearch in linkList1]   
    linkList = [    e.split('/wiki/')[-1] for e in linkList2]
     
    if verbose:     printLog( "The page has %d (possibly identical) page links" % len(linkList)   )
    
    return linkList
        
 
def constructNode(toSearch, title,redirected):
    ### newNode 
    # the newNode returned has no id and is not added to the nodelist yet
    #      a new node : a list an Id,  a wikipedia link , a title, is it a lexical unit or a proper noun , eventually other fields (statistics on words, ....)
    #   {id: , link: [a list of one or more links ] , title: , redirection: True or False, stats}
    
    newNode  =dict()
    newNode['link'] = [toSearch]
    newNode['title']= title
    newNode['redirection'] = redirected
    newNode['id']=None
    newNode['stats']=None
    newNode['depth']=None
    
    return newNode    


def getNewNode(toSearch,noNodeList, verbose):
   
    newNode =None;     noNodeList=None;    divOutput = None 
    pageUrl= ("https://en.wikipedia.org/wiki/"   +   toSearch)#.encode('utf-8')   # str utf-8
    # example  "https://en.wikipedia.org/wiki/Machine_learning"  
    
    # when the current page is an article page: then divOutput is not None
    divContent, divBodyContent, divOutput, title, redirected, noArticle , noResponse = divContent_requests(pageUrl)
    if noResponse: 
        printLog("No internet connection or no webpage at this url. ")
    else:     
        ### if divOutput is None and noArticle = True : 
        # noArticle = a wikipedia page telling there is no article to this exact url is found and no redirection take place.
        # returns None to everything
        
        ### if noArticle = False: no page has been found that explicitely says there is no article at this exact url, and (in theory) it could have a page 
        if divOutput is None and not noArticle:
            # i.e. in the last case:  ACTUALLY: DID NOT FIND ANY CASE THAT MEETS THIS CONDITION.... SEEMS TO BE USELESS. 
            
            # Just in case requests gets HTML page but (because of javascript code) the page is transformed and redirected to an actual page:
            # But we do not know if this kind of redirection actually applies to Wikipedia (since it exists the redirection referred above)
            printLog('Trying to use selenium')
            divContent, divBodyContent, divOutput, title, redirected, noArticle = divContent_selenium(pageUrl)
            
        ### At this point:   there is an actual wikipedia page
        if divOutput is not None:        
            if redirected is None: redirected =False
            else:                  redirected =True
            
            newNode = constructNode(toSearch, title,redirected)
        else: 
            # divOutput is None , i.e. "there is no article"  <==>  noArticle is True or noArticle is None 
            noNodeList.append(toSearch)
    return newNode, noNodeList,divOutput        
   

def addEdge(node0, node1, edgeSet):
    # in all cases if node1 exists, an edge from node0 to node1 is added to the set of edges(unless this edge already exists)
    id0=node0['id']
    id1=node1['id']
    newEdge = (id0,  id1  )    
    
    if id0 !=id1 and newEdge not in edgeSet:
        edgeSet.add(newEdge)
        printLog( 'New edge: %s' % str(newEdge )  )
    elif id0 ==id1: 
        printLog('Error: The two nodes of the edge are identical and must be merged.' )
    return edgeSet

def addLink2ExistingNode(linkValue, NodeList, toMerge):
    # the node already exists, and we search for which node it is        
    # Then we add linkValue to the links associated with this node.

    node1, toMerge=key2Node('link',linkValue, NodeList,toMerge)    
    # node1 returned by key2Node is usually a node but can also be a list of node, or None. 
    if node1 is not None: 
        if len(node1)>1:
            # in case node1 is a list of nodes that will need to be merge: we take the first of them as the unique node
            node1 = node1[0]    
        if linkValue not in node1['link']:    
            (node1['link']).append(linkValue)  
    return node1, toMerge 


def depthAddLink(linkList0, depth0,depthMax, NodeTitleSet, edgeSet, NodeList, noNodeList, toMerge,  leafLinkSet, node0, verbose):
    
    for link1 in linkList0:
        # The probable title associated with link1 is linkTitle
        linkTitle= link1.replace( '_', ' ')
        if linkTitle in NodeTitleSet:
            # the node already exists, and we search for which node it is
            node1, toMerge = addLink2ExistingNode('title',linkTitle, NodeList,toMerge)
        else: 
            # Search the wikipedia page at link1, and return a node with link, title, redirection , ...
            # We also return divOutput which is the HTML relevant to the scraping of wikipedia links on the current link1 page
            if depth0 == depthMax:
                # We do not want to scrape the wikipedia links in the link1 page, but only want to build a node for link1
                # node1 is a terminal node: the node for link1, has no title since the title has to be searched on the webpage
                node1 = constructNode(link1, None,None)
                if node1 is not None:     
                    linkList1=[] 
                    if link1 not in leafLinkSet:
                        NodeList, NodeTitleSet, edgeSet,toMerge,leafLinkSet, noNodeList,node1 = depthAddNode(node1, linkList1, depth0+1, depthMax,NodeList, NodeTitleSet,edgeSet, noNodeList,toMerge, leafLinkSet, verbose)
                    else: 
                        # the node already exists, and we search for which node it is
                        node1, toMerge = addLink2ExistingNode('link',link1, NodeList,toMerge)
                        
            elif depth0 < depthMax: 
                node1, noNodeList,divOutput= getNewNode(link1, noNodeList, verbose) 
                if node1 is not None:
                    # extract the link list from the wikipedia link1 page and return a node associated with the page (it the page exists.).
                    linkList1 = getLinkList_2(divOutput)  
                    # node1 has no id yet, and is not added to the nodelist yet
                    # linkList1:  an eventually redundant list of page links that are scraped from the link1 page
            
                    if not node1['redirection'] :
                        # In case there is no redirection, title has the same name as the link, it is known to being not in NodeTitleSet
                        # Then node1 becomes an actual node and gets an id
                        NodeList, NodeTitleSet, edgeSet,noNodeList,toMerge,leafLinkSet, node1 = depthAddNode(node1, linkList1, depth0+1, depthMax,NodeList, NodeTitleSet,edgeSet, noNodeList, toMerge,leafLinkSet,  verbose)
                        
                    else: #if node1['redirection']:
                        # In case of redirection: we test if the actual title (now known) is already in NodeTitleSet:
                        # in case it is not, then node1 becomes an actual new node and gets an id
                        if node1['title'] not in NodeTitleSet: 
                            NodeList, NodeTitleSet, edgeSet,noNodeList,toMerge,leafLinkSet, node1 = depthAddNode(node1, linkList1, depth0+1, depthMax,NodeList, NodeTitleSet,edgeSet, noNodeList,toMerge, leafLinkSet, verbose)
                        else: 
                            # the node already exists, and we search for which node it is
                            node1, toMerge = addLink2ExistingNode(node1['title'], NodeList,toMerge)
               
        if node1 is not None:
            edgeSet=addEdge(node0, node1, edgeSet)
                
    return NodeList, NodeTitleSet, edgeSet, noNodeList, toMerge ,leafLinkSet       



def depthAddNode(node0, linkList0, depth0, depthMax,NodeList, NodeTitleSet, edgeSet,noNodeList, toMerge,leafLinkSet, verbose= True):
    # returns NodeList and edgeSet
    #  edgeSet :  list of 2-tuples (a,b) that denotes directed edge between nodes a and b. 
    # i.e. there exists a link to b in the page a. 
    # NodeList :  list of nodes, each node is a dictionary about a wikipedia page. 
    
    # depth0 : level of recursivity treated,
    # To be at a distance of depth0 means to be accessible for a search depth of depth0

    # verbose =True :  print everything in details in a logfile and on screen
    # verbose=False:  print in less details
    
    
    # We separately keep track of the NodeTitleSet which is used to know if a given page Title has already been added, 
    #                     and  of the NodeList, which contains node dictionaries and whose length give us the id number of a newNode 
    # It is because we expect this double data structure to be much faster to use 
    # than multiple comparisons of inclusion of elements based on lists, or than repeated transformation a the NodeList into a set 
    # And we only need the node Title for testing inclusion, so the expected memory overhead is less worse :  BUT IT IS STILL TO MEASURE TO BE SURE
        
    ### ===== add the current node0 (if it exists) to the node list and node set================
    if node0 is not None:
        id0 = len(NodeTitleSet  ) + len(leafLinkSet)
        link0 = node0['link'][-1]# the last link of node0['link'], which is a list of links. 
        
        node0['id'] =id0 
        node0['depth']=depth0
        
        NodeList.append(node0)            
        printLog( '\nNode #%d (at depth %d ): %s'% (id0, depth0,link0))

        if depth0==depthMax: 
            leafLinkSet.add(link0)
            printLog( "it is a terminal node.")   
            # remember node0['title'] ==None if node0 is a new node built from link0
        
        if (depth0 < depthMax):  #  deep search on the tree of wikipedia pages
            title0 =node0['title']
            NodeTitleSet.add(title0) 
            printLog(linkList0)
            
            # scraping of wikipedia link when depth0 < depthMax , not when depth0 == depthMax 
            NodeList, NodeTitleSet, edgeSet, noNodeList, toMerge, leafLinkSet =depthAddLink(linkList0, depth0,depthMax, NodeTitleSet, edgeSet, NodeList, noNodeList,toMerge, leafLinkSet, node0, verbose)
           
    return NodeList, NodeTitleSet, edgeSet, noNodeList,toMerge, leafLinkSet,node0         
    
    
def key2Node(key, value, NodeList,toMerge):
    # key is link, title or id
    # We assume the node that has key=value already exists, and we search for which node it is
    # If key is link, then we add link=value to the list of links that describe this node.    
    # node['link'] is the list of links that describe the node.
    
    if key in {'title', 'id'}:
        nodeL = [n for n in NodeList if n[key]==value]
        if nodeL ==[]: node=None
    elif key is 'link':    
        # node[key] is a list
        nodeL = [n for n in NodeList if (value in n['link']) ]
        if nodeL ==[]: node=None     
    else:
        print '%s is not a valid key' % key
        node =None
    
    if node is not None:    
        if len(node)==1:  
            node = node[0]
            printLog( "title node =%s, id = %d" % (node['title'], node['id'] )   )
        
        elif len(node)>1:  
            # node is a list of nodes that are supposed to be merged but are not
            print 'Bug: The following nodes must be merged: \n %s '% '; '.join([str(n) for n in node]) 
            toMerge.append(node)    #toMerge is the list of all the list of nodes that are supposed to be merged but are not, 
    return node , toMerge

def printLog(what, code=' '):
    # logFile and f : Not created before assignment below in this fct
    # what is to print on the console and on a log file .
    # There exists a logging module 
    # but here is a temporary simpler solution
    
    # code= c if we need to close the file. Default is no closing 
    # We close it only a the end of the program so the logFile stays open in append mode for faster access 
   
    # To remember:  unicode + str = unicode when unicode is default
    
    global f, logFile  
    
    if ( 'f' not in globals() ):
        # if the file does not exist, create it
        f = open(logFile, 'a' )
    
    # Everything must be encoded in utf-8 but not encoded twice.. because it would yield an unicodeerror.  
    if type(what) is unicode:
        what = what.encode('utf-8') 
    # At this point every unicode string have been encoded in utf-8 (str):
    
    if type(what) is not str:
        if type(what) is set:
            what = list(what)
        if (type(what) is list and len(what)>0):
            if type(what[0]) in [str, unicode ]: 
                printLog(';   '.join(what))     # would be prettier in columns 
    else: 
        ### Printing in the text file 
        # It is an utf-8 string 
        
        #print type(what+'\n'  )   # unicode even if "what" is encoded in utf-8, since unicode is default because of the import 
        #f.write(  what+'\n'  )    # Cannot write an unicode "string" in a text file when there is non-ascii characters
        #example:      p–n junction   

        #print type(what+'\n'.encode('utf-8')   )   # utf-8 
        try: 
            f.write(  what+'\n'.encode('utf-8')  )     #        
        except IOError, error:     
            print error
            
        ### Printing to the screen 
        print what 
       
    if 'c' in code:
        f.close()
        
if __name__ =='__main__':
    ### param
    maxDepth = 3
    verbose=False
      
    ### initialisation
    # example of relevant url to extract 
    # <a href="/wiki/Online_algorithm" title="Online algorithm">online updating</a>
    # The strings between "" in href and title attributes are of type str (i.e. encoded in utf-8), but the text in title is in unicode. 

    initialSearch ="Interface_(computing)"
    #"Machine learning" # first letter must be capitalized 
    link0 = initialSearch.replace(' ', '_') 
    # ex: 'Machine learning' -----> link0 = 'Machine_learning'
    # ex: url = "https://en.wikipedia.org/wiki/ "+link0 

    NodeList = list()
    NodeTitleSet =set()
    edgeSet=set()  
    noNodeList=list()
    toMerge =list()  
    leafLinkSet =set()
    
    ### filenames 
    name='Wiki_'+initialSearch.encode('utf-8') + '_Depth'+str(maxDepth)
    logFile  = name+'Log.txt'  # for usage in printLog, logFile is global
    #global logFile
    
    jsonFile = name+'.json'    # local only
    
    ### initial node
    newNode0, noNodeList,divOutput= getNewNode(link0, noNodeList, verbose) 
    linkList0 = getLinkList_2(divOutput) 

    # linkList0: the (eventually redundant) list of all page links that are found on the current wikipedia page 
    # newNode0 : # the returned newNode  has no id (yet) and is not added to the nodelist yet : it happens in depthAddNode
    
    ### graph construction via Depth-first traversal
    nodeList, NodeTitleSet  , edgeSet, noNodeList, toMerge, leafLinkSet, node   =depthAddNode(newNode0, linkList0, 0, maxDepth,NodeList, NodeTitleSet, edgeSet,noNodeList, toMerge, leafLinkSet, verbose)
    # node =  last node of nodeList, now with with its id 
    
    ### save in json 
    
    with open(jsonFile, 'wb') as f:
        #sets are not JSON serializable 
        json.dump([nodeList, list(edgeSet)], f )
        
    printLog('Done: \n%d nodes, %d directed edges'%(len(nodeList), len(edgeSet) ), 'c')
    
    ###  
    ''' - a simple case of redirection: 
        link = 'Procedure_(computer_science)' ---->  title="subroutine"
    
        - a case of page not found : IEC_27040
    
        - a case of several redirection: there is several links for one single node: (one title , one id..)
        Feasible_set redirected to Feasible_region
        Candidate_solution also redirected to Feasible_region

    '''
    
   

    ''' LIMITATION:  
    When a node that is already added at depth 2 is also found at dept 1 , it is NOT treated recursively as a node of depth 1, but just as a node of depth 2.
    WE CAN REGARD IT AS A CONSEQUENCE OF DEPT-FIRST TRAVERSAL and the principle that the first detection of the node dictates its depth level and its title. 
    
    WOULD BE BETTER WITH A BREADTH-FIRST TRAVERSAL instead of a DEPTH-FIRST ONE.
    
  
    '''


    ''' Performance problem:
    it seems slower after 
                 - transforming node['link'] in a list rather than a string, 
                 - replace....  in depthAddNode()
    
    WHY IS IT SO SLOW even for terminal nodes without any web scraping: 
         only comparisons 
         add element to a set
         append element to a list 
    
    '''
   
