#!/usr/bin/env python   # if on Linux
#-*- coding: utf-8 -*-

"""  WikiGraphCrawler.py

With python 2.7

Adapted from an idea found in Mitchell2015: Web Scraping with Python, Chap 3 : Starting to Crawl. 

A simple wikipedia Crawler that starts from an initial wikipedia article and 
recursively builds the set of all wikipedia articles that are accessible for a given maximum depth of recursivity
"""

from __future__ import unicode_literals # à activer si en python2.7

import requests  
from bs4 import BeautifulSoup
import time  # for performance testing
import re
import os
from selenium import webdriver # in case of some cases of url redirection:  Maybe useless

# to select the article pages on a wikipedia page ( they do not contain colons), and filter the file that contain colons in the URL
rx=re.compile("^(/wiki/[^:]+$)")   # if we want to include /wiki/  in each link.   OK 

def divContent_soup(HTML):
     ### processing HTML page with BeautifulSoup
    soup=BeautifulSoup(HTML, "lxml")  
    if soup is None: 
        printLog("The website %s responded but the response is not HTML (and not in XML or any text). ")

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
    r = None   ;  soup = None  
    divContent =None;            divBodyContent=None
    divOutput  =None; title = None; redirected =None
    try: 
        r=requests.get(pageUrl)
    except NewConnectionError, error:    
        printLog(error)
    except: 
        printLog('Error: requests cannot find url %s'%pageUrl)
    else:
        
        ### processing HTML page with BeautifulSoup
        divContent, divBodyContent,divOutput, title, redirected= divContent_soup(r.text) 
        if divOutput is None:     
            printLog( " Did not find a wikipedia article this url: %s \n (But maybe a wikipedia page nevertheless exists)"% r.url    )
         
        #---   after requests :
        noArticleText  = divBodyContent.find("table",{"id":"noarticletext"})
        
        if divBodyContent is not None:    
            noArticleText  = divBodyContent.find("table",{"id":"noarticletext"})
        
            if noArticleText is None:
                noArticle = False # i.e. an article exists
            elif noArticleText is not None:
                noArticle =  True
                printLog(noArticleText.get_text())
       
        
    
    return divContent, divBodyContent,divOutput, title, redirected, noArticle

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
    ###  linkList     
    # a list of sublists of "a" tags that satisfy the regex :
    aList=[e.findAll("a", { 'href':rx}) for e in divOutput.findAll('p') ]  
        
    # the list of links (in href attribute of a tag), 
    #via nested list comprehension , i.e. [item for sublist in lst for item in sublist]      
    linkList1=[aTagRx.get('href') for sublist in aList for aTagRx in sublist]   # with the wiki part of links
        
    # if a subsection is indicated in one of the wikipedia links, we discard it and keep only the page link
    #   ***** would maybe be faster with a compiled regular expression 
    linkList2 = [ toSearch.split('#')[0] if "#" in toSearch else toSearch for toSearch in linkList1]   
        
    # links are like paths. We split them for keeping the file part of the path. This part correspond to the page title
    linkList = [os.path.split(e)[1] for e in linkList2]
    # Can be rewrite in one line, but would  arguably be less readable.
    # Could be test if it provides better performances in case we eventually meet a bottleneck here
    
    # linkList = [ os.path.split(l.split('#')[0] )[1] if "#" in e else os.path.split(l)[1] for l in linkList]   
    
    printLog(linkList)
     
    if verbose:           printLog( "The page has %d (possibly identical) page links" % len(linkList)   )
    
    return linkList
        
    
def getNewNode(toSearch, verbose):
    global rx 
    # This function returns the (eventually redundant) list of all page links that are found on the current page and satisfy regex pattern
    
    pageUrl= ("https://en.wikipedia.org/wiki/"   +   toSearch)#.encode('utf-8')   # str utf-8
    # example  "https://en.wikipedia.org/wiki/Machine_learning"  
    
    # when the current page is an article page: then divOutput is not None
    divContent, divBodyContent, divOutput, title, redirected, noArticle = divContent_requests(pageUrl)
    
    # noArticle = True : a wikipedia page telling there is no article to this exact url has been found and no further redirection can take place.
    # noArticle = False: no page has been found that explicitely says there is no article at this exact url
    if divOutput is None and not noArticle:
        # i.e. in the last case:   NOT FOUND ANY CASE THAT MEETS THIS CONDITION.... SEEMS TO BE USELESS. 
        
        # Just in case requests gets HTML page but (because of javascript code) the page is transformed and redirected to an actual page:
        # But we do not know if this kind of redirection actually applies to Wikipedia (since it exists the redirection referred above)
        printLog('Trying to use selenium')
        divContent, divBodyContent, divOutput, title, redirected, noArticle = divContent_selenium(pageUrl)
        if divOutput is None:
            return []
        else: 
            # if we get a wikipedia page nevertheless it is a redirection
            redirected = True 
            
    ### At this point:  divOutput is not None and is now known (i.e. there is an actual wikipedia page: )        
    if redirected is None: redirected =False
    
    ## linkList, assuming divOutput exists
    linkList = getLinkList_2(divOutput)
             
    ### newNode 
    # the newNode returned has no id and is not added to the nodelist yet
    #      a new node : a list an Id,  a wikipedia link , a title, is it a lexical unit or a proper noun , eventually other fields (statistics on words, ....)
    #   {id: , link: , title: , redirection: True or False, stats}
    
    newNode  =dict()
    newNode['link'] = toSearch
    newNode['title']= title
    newNode['redirection'] = redirected
    newNode['id']=None
    newNode['stats']=None
    return newNode, linkList        


def depthAddNode(node0, linkList0, depth0, depthMax,NodeList, NodeLinkSet, edgeList,verbose= True):
    # returns NodeList and edgeList
    #  edgeList :  list of 2-tuples (a,b) that denotes directed edge between nodes a and b. 
    # i.e. there exists a link to b in the page a. 
    # NodeList :  list of nodes, each node is a dictionary about a wikipedia page. 
    
    # depth0 : level of recursivity treated,
    # To be at a distance of depth0 means to be accessible for a search depth of depth0

    # verbose =True :  print everything in details in a logfile and on screen
    # verbose=False:  print in less details
    
    
    # We separately keep track of the NodeLinkSet which is used to know if a given page Title has been added by the past, 
    #                     and  of the NodeList, which contains node dictionaries and whose length give us the id number of a newNode 
    # It is because we expect this double data structure to be much faster to use 
    # than multiple comparisons of inclusion of elements based on lists, or than repeated transformation a the NodeList into a set 
    # And we only need the node Title for testing inclusion, so the expected memory overhead is less worse :  BUT IT IS STILL TO MEASURE TO BE SURE
      
    def AddNodeCondition(node,NodeList):
        ### method 1 :  simple to write, no additional data structure, but surely much slower:
        '''if not node['redirection'] or node['title'] in NodeTitleSet :
             return True
        '''
        ###  method 2 : faster and without additional data structure, but is a non-elegant complicated test
        # but the short condition written above would need much more useless computation and must be slower : STILL TO TEST 
        
        AddNodeCond = False
        if node['redirection'] is True:
            #check if the Title of newNode is already present in NodeLinkSet
            # Because several links may be redirected to a same page (that has a given title )
            
            # we want to compute NodeTitleSet only when really needed. 
            NodeTitleSet ={s['title'] for s in NodeList} 
            if node['title'] not in NodeTitleSet:
                AddNodeCondit = True
            # else: AddNodeCondition =False                     
        else: 
            AddNodeCond= True  
        return AddNodeCond
    
        ### method 3  :   like method 1, but with NodeTitleSet as a new permanent data structure 
        
        
    ### ===== add the current node0 (if it exists) to the node list and node set================
    if node0 is not None:
        id0 =len(NodeLinkSet  )  # or len(newNodeTitle  )
        link0 = node0['link']
        node0['id'] =id0 
    
        
        NodeList.append(node0)            
        NodeLinkSet.add(link0) 
        
        #NodeTitleSet.add(node0['title'])   # the condition for entrying in depthAddNode() would be much simpler .
        # the distinction between NodeLinkSet and NodeTitleSet would take account for the redirected pages (which have same titles but not same initial links )
        
        printLog( '\nNode # %d), %s at depth %d '% (id0, link0, depth0))
        printLog( "%s "% linkList0)
            
        if (depth0 < depthMax):  #  deep search on the graph of links
            for link1 in linkList0:
                if link1 in NodeLinkSet:
                    # the node already exists
                    node1=key2Node('link',link1, NodeList)
                        
                else: # link1 not in NodeLinkSet
                    node1, linkList1 = getNewNode(link1, verbose)   
                    # node1 has no id yet, and is not added to the nodelist yet
                    # linkList1:  an eventually redundant list of page links that are found on the current page
                    
                    if AddNodeCondition(node1,NodeList):
                        NodeList, NodeLinkSet, edgeList, node1 = depthAddNode(node1, linkList1, depth0+1, depthMax,NodeList, NodeLinkSet,edgeList, verbose)
                        # provides an id to the same node1, where node1 = NodeList[-1]   .                                
                       
                        
                    else: 
                        # finally the node already exists
                        node1=key2Node('link', link1, NodeList)
            
                id1=node1['id']
                newEdge = (id0,  id1  )    # edge from node0 to node1, denoted by the couple of their id. 
                if id0 !=id1:
                    edgeList.append(newEdge)
                else: 
                    printLog('error in the condition under which we must add a new node.\nIf two nodes are the same, they must be merge, obviously.' )
        else:
            if verbose: 
                printLog( "On this branch, maxDepth is reached at the page untitled: %s"% linkUrl.replace('_', ' ')    )
    return NodeList, NodeLinkSet, edgeList, node0         
    
    
def key2Node(key, value, NodeList):
    # key is link, title or id
    
    if key in {'link', 'title', 'id'}:
        node = [n for n in NodeList if n[key]==value]
    else:
        print '%s is not a valid key' % key
        node =[]
    if len(node)==0: id1 = None
    elif len(node)==1: node = node[0]
    elif len(mode)>1:  
        print 'ambiguity: The following nodes must be merged: \n %s '% '; '.join([str(n) for n in node]) 
    return node

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
    
    # Everythong must be encoded in utf-8 but not encoded twice.. because it would yield an unicodeerror.  
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
        f.write(  what+'\n'.encode('utf-8')  )     #        
        
        ### Printing to the screen 
        print what 
       
    if 'c' in code:
        f.close()
        
if __name__ =='__main__':
    ### param
    maxDepth = 2
    verbose=False
      
    ### initialisation
    # example of relevant url to extract 
    # <a href="/wiki/Online_algorithm" title="Online algorithm">online updating</a>
    # The strings between "" in href and title attributes are of type str (i.e. encoded in utf-8), but the text in title is in unicode. 

    initialSearch ="Machine learning" # first letter must be capitalized 
    link0 = initialSearch.replace(' ', '_') 
    # ex: 'Machine learning' -----> link0 = 'Machine_learning'
    # ex: url = "https://en.wikipedia.org/wiki/ "+link0 

    NodeList = list()
    NodeLinkSet =set()
    edgeList=list()  
    
    ### filenames 
    name='Wiki_'+initialSearch.encode('utf-8') + '_Depth'+str(maxDepth)
    logFile  = name+'Log.txt'  # for usage in printLog, logFile is global
    jsonFile = name+'.json'    # local only
    
    ### initial node
    newNode0, linkList0 = getNewNode(link0, verbose)   
    # linkList0: the (eventually redundant) list of all page links that are found on the current wikipedia page 
    # newNode0 : # the returned newNode  has no id (yet) and is not added to the nodelist yet : it happens in depthAddNode
    
    ### graph construction via Depth-first traversal
    nodeList, NodeTitleSet  , edgeList, node   =depthAddNode(newNode0, linkList0, 0, maxDepth,NodeList, NodeLinkSet, edgeList,verbose)
    # node =  last node of nodeList, now with with its id 
    
    ### save in json 
    jsonName = '.json'
    with open(jsonName, 'wb') as f:
        json.dump([nodeList, edgeList], f )
        
        
'''     
        Node # 690), E-mail at depth 2 
        
            Did not find a wikipedia article this url: https://en.wikipedia.org/wiki/IEC_27040 
            (But maybe a wikipedia page nevertheless exists)
        Trying to use selenium        '''