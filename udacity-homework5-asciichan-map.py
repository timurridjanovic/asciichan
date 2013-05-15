import os
import re
import sys
import webapp2
import jinja2
import time
import urllib2
from xml.dom import minidom
from google.appengine.ext import db
from string import letters

import logging

template_dir = os.path.join(os.path.dirname(__file__), 'templates')
jinja_env = jinja2.Environment(loader = jinja2.FileSystemLoader(template_dir), autoescape = True)

art_key = db.Key.from_path('ASCIIChan', 'arts')

IP_URL = "http://api.hostip.info/?ip="
def get_coords(ip):
    #ip = "4.2.2.2"
    url = IP_URL + ip
    content = None
    try:
        content = urllib2.urlopen(url).read()
    except URLError:
        return

    if content:
        #parse the xml and find the coordinates
        d = minidom.parseString(content)
        coords = d.getElementsByTagName("gml:coordinates")
        if coords and coords[0].childNodes[0].nodeValue:
            lon, lat = coords[0].childNodes[0].nodeValue.split(',')
            return db.GeoPt(lat, lon)



GMAPS_URL = "http://maps.googleapis.com/maps/api/staticmap?size=380x263&maptype=hybrid&sensor=false&"

def gmaps_img(points):
    markers = '&'.join('markers=%s,%s' % (p.lat, p.lon)
			for p in points)

    return GMAPS_URL + markers


class Handler(webapp2.RequestHandler):
    def write(self, *a, **kw):
        self.response.out.write(*a, **kw)

    def render_str(self, template, **params):
        t = jinja_env.get_template(template)
        return t.render(params)

    def render(self, template, **kw):
        self.write(self.render_str(template, **kw))

class Art(db.Model):
    title = db.StringProperty(required = True) #the way you create datatypes for an entity in Google Data Store
    art = db.TextProperty(required = True)
    created = db.DateTimeProperty(auto_now_add = True) #Check GDS docs
    coords = db.GeoPtProperty()
    


class MainPage(Handler):
    def render_front(self, title="", art="", error=""):
        arts = db.GqlQuery("SELECT * FROM Art WHERE ANCESTOR IS :1 ORDER BY created DESC LIMIT 10", art_key)

        #prevent the running of multiple queries
        arts = list(arts)

        """for a in arts:
            if arts.coords:
                points.append(a.coords)"""#another way of doing what is done below...

        points = filter(None, (a.coords for a in arts))
        #debugging
        #self.write(repr(points))


        #find which arts have coords
        # if we have any arts coords, make an image url
        # display the image url
        img_url = None
        if points:
            img_url = gmaps_img(points)

        self.render("front.html", title=title, art=art, error=error, arts=arts, img_url = img_url)

    def get(self):
        #db.delete(db.Query(keys_only=True))
        return self.render_front()
        
        

    def post(self):
        title = self.request.get("title")
        art = self.request.get("art")

        if title and art:
            a = Art(parent = art_key, title = title, art = art) #creates an obj instance of art

	    #lookup the user's coordinates from their IP
            #if we have coordinates, add them to the Art
            
            coords = get_coords(self.request.remote_addr)
            
	    
            if coords == None:
                coords = get_coords("57.67.154.0")
            

            if coords:
                a.coords = coords
            
            a.put() #stores art obj into database
            time.sleep(1) # sleep for 1 second
            self.redirect("/")
        else:
            error = "we need both a title and some artwork!"
            self.render_front(title, art, error)

app = webapp2.WSGIApplication([('/', MainPage)],
                              debug=True)
