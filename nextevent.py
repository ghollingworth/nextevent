import gi
import threading
import time
from googlecal import GoogleCalendar
from dateutil.parser import parse
import datetime
import cairo
import math
import os
import ssl
import sys

def secs_to_string(s, days):
    hours = int(s / 3600)
    s = s - (hours * 3600)
    mins = int(s / 60)
    s = s - (mins * 60)
    secs = int(s)
    return "{} days {:02d} Hours {:02d} Minutes".format(days,hours,mins)

gi.require_version("Gtk", "3.0")
from gi.repository import Gtk, Gdk, GLib, GObject

class MyWindow(Gtk.Window):
    def __init__(self):
        Gtk.Window.__init__(self, title="Next event")
        self.set_default_size(1000,480)
        
        self.box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        self.add(self.box)
        
        self.drawing = Gtk.DrawingArea()
        self.drawing.connect('draw', self.OnDraw)
        self.box.pack_start(self.drawing, True, True, 0)
        
        #self.button = Gtk.Button(label="Click here")
        #self.button.connect("clicked", self.on_button_clicked)
        
        self.bottom_box = Gtk.Box(spacing=6)
        self.box.pack_start(self.bottom_box, False, True, 0)
        
        #self.bottom_box.pack_start(self.button, True, False, 0)
        
        self.running=True
        self.thread = threading.Thread(target=self.test)
        self.thread.daemon = True
        self.thread.start()
        self.diff = datetime.timedelta(1)
        self.events = []
        self.FONT_SIZE = 20
        
    def handleState(self, evs):
        for ev in evs:
            diff = ev["start"] - datetime.datetime.now(ev["start"].tzinfo)
            
            if diff < datetime.timedelta(minutes=5) and ev["state"] == 0:
                os.system("aplay ding.wav")
                ev["state"] = 1
            if diff < datetime.timedelta(minutes=1) and ev["state"] == 1:
                os.system("aplay ding.wav")
                os.system("aplay ding.wav")
                ev["state"] = 2
            if diff < datetime.timedelta(minutes=0) and ev["state"] == 2:
                os.system("aplay ding.wav")
                os.system("aplay ding.wav")
                os.system("aplay ding.wav")
                os.system("aplay ding.wav")
                ev["state"] = 3


    def OnDraw(self, w, cr):
        in_order = sorted(self.events, key = lambda i : i['start'].timestamp())
        
        self.handleState(in_order)
                
        width = w.get_allocated_width()
        height = w.get_allocated_height()
        
        cr.set_source_rgb(0,0.9,0)
        cr.rectangle(0, 0, width, height)
        cr.fill_preserve()
        
        cr.set_source_rgb(0,0,0)
        cr.select_font_face("Georgia", cairo.FONT_SLANT_NORMAL, cairo.FONT_WEIGHT_NORMAL)
        cr.set_font_size(self.FONT_SIZE)
        
        text_max = 0
        for i in range(len(in_order)):
            text = in_order[i]["summary"]
            fx, fy, fw, fh = cr.text_extents(text)[:4]
            if fw > text_max:
                text_max = fw
        
        fx,fy,fw,fh = cr.text_extents("00 days 00 Hours 00 minutes")[:4]
        time_width = fw + self.FONT_SIZE
        
        first_offset_h = width/2 - (time_width/2 + text_max/2)
        first_offset_v = height/2 - (fh * 1.5 * len(in_order))/2
        vertical_dist = fh * 1.5
            
        for i in range(len(in_order)):
            if in_order[i]["state"] != 0:
                cr.set_source_rgb(1.0,0,0)
            else:
                cr.set_source_rgb(0,0,0)
                
            offset = first_offset_v + (vertical_dist * i)
            diff = in_order[i]["start"] - datetime.datetime.now(in_order[i]["start"].tzinfo)
            diff_str = secs_to_string(diff.seconds, diff.days)
            cr.move_to(first_offset_h, offset)
            cr.show_text(diff_str)
            cr.move_to(first_offset_h + time_width, offset)
            cr.show_text(in_order[i]["summary"])
        
    def test(self):
        while True:
            try:
                cal = GoogleCalendar()
                while True:
                    events = cal.get_upcoming_events()
                    for ev in events:
                        seen = False
                        for known_ev in self.events:
                            if known_ev["id"] == ev["id"]:
                                seen = True
                        if not seen:
                                start_dt = parse(ev['start'].get('dateTime', ev['start'].get('date')))
                                self.events.append({'id':ev['id'], 'summary':ev['summary'], 'start':start_dt, 'state':0})  
                    for ev in self.events:
                        seen = False
                        for known_ev in events:
                            if known_ev["id"] == ev["id"]:
                                seen = True
                        if not seen:
                            self.events.remove(ev)
                        
                    GLib.idle_add(self.drawing.queue_draw)
                    time.sleep(10)
            except:
                print("Update failed, retrying")
                time.sleep(10)
        print("Exiting polling thread")

if sys.version_info.major < 3:
    print("Must be run with python 3")
    exit()
        
win = MyWindow()
win.connect("destroy", Gtk.main_quit)
win.show_all()
Gtk.main()

        
