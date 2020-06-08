import gi
gi.require_version("Gtk", "3.0")
from gi.repository import Gtk, Gdk, GLib, GObject
import cairo

import threading
import time
from googlecal import GoogleCalendar
from dateutil.parser import parse
import datetime
import math
import os
import sys

# Function to convert a number of seconds to a time
def secs_to_string(s, days):
    hours = int(s / 3600)
    s = s - (hours * 3600)
    mins = int(s / 60)
    s = s - (mins * 60)
    secs = int(s)
    return "{} days {:02d} Hours {:02d} Minutes".format(days,hours,mins)


class MainWindow(Gtk.Window):
    def __init__(self):
        Gtk.Window.__init__(self, title="Next event")
        self.set_default_size(1000,480)
        
        self.drawing = Gtk.DrawingArea()
        self.drawing.connect('draw', self.OnDraw)
        self.add(self.drawing)
        
        self.STATE_NOTHING     = 0
        self.STATE_5_MIN       = 1
        self.STATE_1_MIN       = 2
        self.STATE_IN_PROGRESS = 3
        
        self.thread = threading.Thread(target=self.event_thread)
        self.thread.daemon = True
        self.thread.start()
        self.events = []
        self.FONT_SIZE = 20

    # Each event has a state, progress the state and notify the user at
    # the right time, return boolean which indicates whether there is
    # something coming up
    def handleState(self, evs):
        red = False
        for ev in evs:
            diff = ev["start"] - datetime.datetime.now(ev["start"].tzinfo)
            
            if diff < datetime.timedelta(minutes=5) and ev["state"] == self.STATE_NOTHING:
                os.system("aplay ding.wav")
                ev["state"] = self.STATE_5_MIN
            if diff < datetime.timedelta(minutes=1) and ev["state"] == self.STATE_5_MIN:
                os.system("aplay ding.wav")
                os.system("aplay ding.wav")
                ev["state"] = self.STATE_1_MIN
            if diff < datetime.timedelta(minutes=0) and ev["state"] == self.STATE_1_MIN:
                os.system("aplay ding.wav")
                os.system("aplay ding.wav")
                os.system("aplay ding.wav")
                os.system("aplay ding.wav")
                ev["state"] = self.STATE_IN_PROGRESS
            if ev["state"] != self.STATE_NOTHING:
                red = True
        return red

    # Function to draw the window
    def OnDraw(self, w, cr):
        # Sort the events by timestamp
        in_order = sorted(self.events, key = lambda i : i['start'].timestamp())
        
        # Process the events to notify the user
        red = self.handleState(in_order)

        # Window width and height
        width = w.get_allocated_width()
        height = w.get_allocated_height()

        # Set background colour
        if red:
            cr.set_source_rgb(1.0,0.4,0.4)
        else:
            cr.set_source_rgb(0.3,0.8,0.9)

        # Draw background
        cr.rectangle(0, 0, width, height)
        cr.fill_preserve()
        
        # Text in black
        cr.set_source_rgb(0,0,0)
        cr.select_font_face("Georgia", cairo.FONT_SLANT_NORMAL, cairo.FONT_WEIGHT_NORMAL)
        cr.set_font_size(self.FONT_SIZE)
        
        # Search for the widest bit of text, try to keep everthing centered
        text_max = 0
        for i in range(len(in_order)):
            text = in_order[i]["summary"]
            fx, fy, fw, fh = cr.text_extents(text)[:4]
            if fw > text_max:
                text_max = fw
        
        # Get maximum width of the time column
        fx,fy,fw,fh = cr.text_extents("00 days 00 Hours 00 minutes")[:4]
        time_width = fw + self.FONT_SIZE
        
        # first_offset_* is top left of the output box
        first_offset_h = width/2 - (time_width/2 + text_max/2)
        first_offset_v = height/2 - (fh * 1.5 * len(in_order))/2
        # Distance between lines is 1.5 spacing
        vertical_dist = fh * 1.5
            
        for i in range(len(in_order)):
            # Change text colour if event coming up 
            if in_order[i]["state"] != self.STATE_NOTHING:
                cr.set_source_rgb(1.0,1.0,0)
            else:
                cr.set_source_rgb(0,0,0)

            offset = first_offset_v + (vertical_dist * i)
            diff = in_order[i]["start"] - datetime.datetime.now(in_order[i]["start"].tzinfo)
            if in_order[i]["state"] == self.STATE_IN_PROGRESS:
                diff_str = "In progress"
            else:
                diff_str = secs_to_string(diff.seconds, diff.days)
            cr.move_to(first_offset_h, offset)
            cr.show_text(diff_str)
            cr.move_to(first_offset_h + time_width, offset)
            cr.show_text(in_order[i]["summary"])
        
    def event_thread(self):
        while True:
            try:
                cal = GoogleCalendar()
                while True:
                    events = cal.get_upcoming_events()
                    # Search for each event in the internal event list, if it was not found then
                    # add it to the list, setting its state to longer than 5min away
                    for ev in events:
                        seen = False
                        for known_ev in self.events:
                            if known_ev["id"] == ev["id"]:
                                seen = True
                        if not seen:
                                start_dt = parse(ev['start'].get('dateTime', ev['start'].get('date')))
                                self.events.append({'id':ev['id'], 'summary':ev['summary'], 'start':start_dt, 'state':self.STATE_NOTHING})
                    # Remove events that are no longer in the next up list
                    for ev in self.events:
                        seen = False
                        for known_ev in events:
                            if known_ev["id"] == ev["id"]:
                                seen = True
                        if not seen:
                            self.events.remove(ev)
                        
                    # Trigger the main window to redraw itself
                    GLib.idle_add(self.drawing.queue_draw)
                    # Just poll once every ten seconds
                    time.sleep(10)
            except:
                # If the network drops out then retry (will also happen if API key times out and needs
                # re-authorising
                print("Update failed, retrying")
                time.sleep(10)

if sys.version_info.major < 3:
    print("Must be run with python 3")
    exit()
        
win = MainWindow()
win.connect("destroy", Gtk.main_quit)
win.show_all()
Gtk.main()

        
