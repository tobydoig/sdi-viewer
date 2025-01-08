#!/usr/bin/env python3

#sudo apt update
#sudo apt install python3-gi python3-gi-cairo gir1.2-gtk-3.0 gstreamer1.0-tools \
#    gstreamer1.0-plugins-base gstreamer1.0-plugins-good \
#    gstreamer1.0-plugins-bad gstreamer1.0-plugins-ugly \
#    gstreamer1.0-libav gstreamer1.0-decklink

import sys
import gi
gi.require_version('Gst', '1.0')
gi.require_version('GstVideo', '1.0')
gi.require_version('Gtk', '3.0')
from gi.repository import Gst, GstVideo, Gtk, GLib
import signal

class SDIViewer:
    def __init__(self):
        # Initialize GStreamer
        Gst.init(None)
        
        # Create the main window
        self.window = Gtk.Window(title="SDI Video Viewer")
        self.window.connect('destroy', self.quit)
        self.window.set_default_size(1920, 1080)
        
        # Create a drawing area for video display
        self.video_widget = Gtk.DrawingArea()
        self.window.add(self.video_widget)
        
        # Create GStreamer pipeline
        self.create_pipeline()
        
        # Show all widgets
        self.window.show_all()
        
    def create_pipeline(self):
        # Create pipeline elements
        self.pipeline = Gst.Pipeline.new('sdi-pipeline')
        
        # SDI source (assuming DeckLink card)
        self.source = Gst.ElementFactory.make('decklinkvideosrc', 'sdi-source')
        if not self.source:
            sys.stderr.write("Error: Could not create decklinkvideosrc\n")
            sys.exit(1)
            
        # Set SDI input properties
        self.source.set_property('mode', "1080i5994")  # 1080i 59.94Hz
        self.source.set_property('connection', 'sdi')
        
        # Create video conversion elements
        videoconvert = Gst.ElementFactory.make('videoconvert', 'converter')
        videoscale = Gst.ElementFactory.make('videoscale', 'scaler')
        
        # Create video sink
        self.sink = Gst.ElementFactory.make('gtksink', 'video-output')
        
        # Add elements to pipeline
        self.pipeline.add(self.source)
        self.pipeline.add(videoconvert)
        self.pipeline.add(videoscale)
        self.pipeline.add(self.sink)
        
        # Link elements
        self.source.link(videoconvert)
        videoconvert.link(videoscale)
        videoscale.link(self.sink)
        
        # Connect to the sink's widget
        self.video_widget.destroy()
        self.video_widget = self.sink.props.widget
        self.window.add(self.video_widget)
        
        # Add watch for messages
        bus = self.pipeline.get_bus()
        bus.add_signal_watch()
        bus.connect('message', self.on_message)
        
    def start(self):
        # Start the pipeline
        self.pipeline.set_state(Gst.State.PLAYING)
        
    def quit(self, *args):
        # Stop the pipeline and quit
        self.pipeline.set_state(Gst.State.NULL)
        Gtk.main_quit()
        
    def on_message(self, bus, message):
        t = message.type
        
        if t == Gst.MessageType.ERROR:
            self.pipeline.set_state(Gst.State.NULL)
            err, debug = message.parse_error()
            sys.stderr.write(f"Error: {err}\nDebug: {debug}\n")
            Gtk.main_quit()
            
        elif t == Gst.MessageType.EOS:
            self.pipeline.set_state(Gst.State.NULL)
            sys.stderr.write("End of stream\n")
            Gtk.main_quit()

def main():
    # Handle Ctrl+C gracefully
    signal.signal(signal.SIGINT, signal.SIG_DFL)
    
    # Create and start the viewer
    viewer = SDIViewer()
    viewer.start()
    
    # Start GTK main loop
    Gtk.main()

if __name__ == '__main__':
    main()
