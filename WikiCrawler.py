#!/usr/bin/env python   # if on Linux
#-*- coding: utf-8 -*-

"""  WikiCrawler.py

With python 2.7

Adapted from an idea found in Mitchell2015: Web Scraping with Python, Chap 3 : Starting to Crawl. 

A simple wikipedia Crawler that starts from an initial wikiepdia article and 
recursively builds the set of all wikipedia articles that are accessible for a given maximum depth of recursivity
"""

from __future__ import unicode_literals # à activer si en python2.7

import requests  
from bs4 import BeautifulSoup
import random
import datetime# for seeding the random generator
import time  # for performance testing
import re
import os
from selenium import webdriver # in case of some cases of url redirection:  Maybe useless
random.seed(datetime.datetime.now())

# to select the article pages on a wikipedia page ( they do not contain colons), and filter the file that contain colons in the URL
rx=re.compile("^(/wiki/[^:]+$)")   # if we want to include /wiki/  in each link.   OK 

'''m=rx.search(l2)
if m : print m.group(0)'''

'''
def getLinks(WikiUrl):
    # where WikiUrl is the part of the url that contains the topics. 
    
    #html = urlopen("http://en.wikipedia.org/wiki/"+WikiUrl)
    
    return soup.find("div", {"id":"bodyContent"}).findAll("a",href=rx)
'''
def getLinkList(toSearch, verbose):
    global rx 
    # This function returns the (eventually redundant) list of all page links that are found on the current page and satisfy regex pattern
    
    
    pageUrl= ("https://en.wikipedia.org/wiki/"   +   toSearch)#.encode('utf-8')   # str utf-8
    # example  "https://en.wikipedia.org/wiki/Machine_learning"  
    
    if verbose: print "pageUrl Type : %s " % type(pageUrl )  # str utf-8 
    
    # initialisation in case of request failure, or if the response is not HTML  
    r = None   ;  soup = None  

    r=requests.get(pageUrl)
    if r is None:
        printLog("HTTP request fails: Internet is probably not connected.")
        return None
    soup = BeautifulSoup(r.text, "lxml")
    if soup is None: 
        printLog("The website %s responded but the response is not HTML (and nor in XML actually). ")
        return None
            
    #  limited to the body content of the wikipedia article   
    divContent =soup.find("div",{"id":"content"})
    divBodyContent=divContent.find("div",{"id":"bodyContent"})
    
    divOutput = divBodyContent.find("div",{"id":"mw-content-text"}).find('div', {'class':'mw-parser-output'})
    
    
    # when the current page is an article page,  divContent contains <div class='class':'mw-parser-output'.....>, i.e. divOutput is not None
    if divOutput is None:
    #if divContentText.find('div', {'class':'noarticletext mw-content-ltr'}):    
        printLog( "No article found ..."   )

        # Maybe an URL Redirection would take place with a browser, but has failed with "requests package" ?
        # ex: https://en.wikipedia.org/wiki/GPU should be redirected to https://en.wikipedia.org/wiki/Graphics_processing_unit
        
        if verbose: printLog(  "We try using selenium Browser:  (but it is very slow compared with requests, is there any faster solution ?)")
        browser = webdriver.Firefox()
        browser.get(pageUrl) 
        innerHTML = browser.execute_script("return document.body.innerHTML")
        soup=BeautifulSoup(innerHTML, "lxml")     
        if verbose: printLog( "Check: The type of soup is %s" %type(soup)   )
        
        browser.close()
        divContent =soup.find("div",{"id":"content"})
        divOutput=divContent.find("div",{"id":"bodyContent"}).find("div",{"id":"mw-content-text"}).find('div', {'class':'mw-parser-output'})
        if divOutput is None:     
            printLog( "Cannot find <'div', class:'mw-parser-output'...> in page %s"% r.url    )
            return [] 
        else: 
            if verbose: printLog('OK a wikipedia article has finally been found')
            
    # At this point:  divOutput is not None and is now known (i.e. there is an actual wikipedia page: )
    title =divContent.find("h1",{"id":"firstHeading"}).get_text()
    if verbose: printLog(title)  
    
    
    redirected = divBodyContent.find('span', {'class', 'mw-redirectedfrom'})
    if redirected:
        # it means we have just been redirected to a new page. 
        # We look for the actual title and the actual new url of the page should be:
        
        actualUrl = title.replace(' ', '_')   # works only if title is unicode (or an ascii-accepted string) (not if it is some non-ascii string)
        # we should actually encode this url after 
        
        if verbose: 
            printLog("The request to page %s has been redirected \nto the current page with url:%s:" %(pageUrl, actualUrl) ) 
        
        
    # a list of sublists of "a" tags that satisfy the regex :
    aList=[e.findAll("a", { 'href':rx}) for e in divOutput.findAll('p') ]  
        
    # the list of links (in href attribute of a tag), 
    #via nested list comprehension , i.e. [item for sublist in lst for item in sublist]      
    linkList=[aTagRx.get('href') for sublist in aList for aTagRx in sublist]   # OK, but with the wiki part
        
    # if a subsection is indicated in one of the wikipedia links, we discard it and keep only the pages
    #   ***** would maybe be faster with a compiled regular expression 
    linkList2 = [ toSearch.split('#')[0] if "#" in toSearch else toSearch for toSearch in linkList]   
        
    # links are like paths. We split them for keeping the file part of the path. This part correspond to the page title
    ll=[os.path.split(e)[1] for e in linkList2]
        
    # equivalent in one line: for better performance in case we eventually meet a bottleneck here ( it is to test)
    # But arguably less readable indeed 
    # ll = [ os.path.split(l.split('#')[0] )[1] if "#" in e else os.path.split(l)[1] for l in linkList]   
     
    if verbose: printLog( "The page has %d (possibly identical) page links" % len(ll)   )
        
    return ll        
  
    
def getLinkSet(toSearch, v):
    # getLinkSet(toSearch) : returns the (non-redundant) set of all page links that are found on the current page and satisfy regex pattern
    
    linkList = getLinkList(toSearch, v)
    # getlinkList(toSearch) : returns the (eventually redundant) list of all page links that are found on the current page and satisfy regex pattern
    
    # linkSet:  the set of page links found in the current page
    linkSet = set()
    
    # This comprehension loop adds each link to the set of linkSet only if  not already in linkSet
    { linkSet.add(link) for link in linkList if link not in linkSet}    
    return linkSet       

    
def getRecursivLinks(linkUrl, depth0, depthMax, verbose= True):
    # returns the set of wikipedia page links that are at a distance of depthMax from the current page "linkUrl" 
    # depth0 : level of recursivity treated,
    # To be at a distance of depth0 means to be accessible for a search depth of depth0

    # verbose =True :  print everything in details in a logfile and on screen
    # verbose=False:  print in less details
    
    if verbose: 
        printLog( '\nProcessing "%s"'%linkUrl    )
        printLog( 'Current depth is: %d' % depth0    )

        #print 'linkUrl type is: %s '%type(linkUrl)   #string utf-8
    else: 
        printLog( '\n%s at depth %d'% (linkUrl, depth0))
    
    #setLinks: set of wikipedia page links in the current page "linkUrl"
    setLinks = getLinkSet(linkUrl, verbose ) 
    
    
    if verbose: 
        printLog( 'The size of the set of page links on page %s is: %d'% (linkUrl, len(setLinks) )   )
    else:printLog( '%d links'%len(setLinks))     
    printLog( setLinks)    
    
    newSetLinks=set() #set of page Links found in pages that are accessible from this page (for a given search depth )
    
    if (depth0 < depthMax):  #  deep search on the graph of links
        for link in setLinks:
            if verbose: print 'link type is: %s'%type(linkUrl)
            
            newSetLinks |= getRecursivLinks(link,depth0+1, depthMax,verbose)
        setLinks |= newSetLinks 
        if verbose: 
            printLog( "The set of links that are accessible from %s has cardinality = %d" %(linkUrl, len(setLinks))    )
    else: 
        if verbose: 
            printLog( "On this branch, maxDepth is reached at the page untitled: %s"% linkUrl.replace('_', ' ')    )
    return setLinks   

'''
def  wikiRandomWalk():
    while searchDepth:
        #Random choice among a list of link
        #newPage = links[random.randint(0, len(links)-1)].attrs["href"]
        
        
        # Random choice of a link among a set of link:   A FAIRE 
        newPage = links[random.randint(0, len(links)-1)].attrs["href"]
        print(newArticle)
        links = getLinks(newPage)
'''    

def printLog(what, code=' '):
    # logFile and f : Not created before assignment below in this fct
    # what is to print on the console and on a log file .
    # There exists a logging module 
    # but here is a temporary simpler solution
    
    # code= c if we need to close the file. Default is no closing 
    # We close it only a the end of the program so the logFile stays open in append mode for faster access 
   
    # To remember:  unicode + str = unicode when unicode is default
    
    global f, logFile  
    
    logFile = 'logWiki_'+initialSearch.encode('utf-8') + '_Depth'+str(maxDepth)+'.txt' # str 
    
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
                printLog(';   '.join(what))
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
    
    allPages = set()  
    
    # example of relevant url to extract 
    # <a href="/wiki/Online_algorithm" title="Online algorithm">online updating</a>
    # The strings between "" in href and title attributes are of type str (i.e. encoded in utf-8), but the text in title is in unicode. 

    initialSearch ="Machine learning" # first letter must be capitalized 
    searchUrl = initialSearch.replace(' ', '_') 
    # ex: 'Machine learning' -----> searchUrl = 'Machine_learning'
    # ex: url = "https://en.wikipedia.org/wiki/ "+searchUrl 

    '''
    linkSet = getLinkSet(searchUrl )
    print linkSet
    print len(linkSet)
    '''
    
       
    # returns  all the wikipedia pages reached by the crawler for a specified maximum depth of recursivity
    maxDepth = 2
    verbose=False
    allPages= getRecursivLinks(searchUrl, 0, maxDepth, verbose)
    printLog( len(allPages)  )
    
    # 
    printLog("The final set of all page links is: \n %s" %'\n'.join(list(allPages)), 'c')
    
        
                
    #-------           
