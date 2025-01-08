#!/usr/bin/env python3

# sudo apt install python3-pygame python3-numpy

import ctypes
import numpy as np
import pygame
import sys
from ctypes import CDLL, CFUNCTYPE, POINTER, Structure, c_void_p, c_char_p, c_int, c_long

# Load DeckLink SDK library
try:
    decklink = CDLL("/usr/lib/libDeckLinkAPI.so")
except OSError:
    sys.exit("Error: DeckLink SDK not found. Please install the Blackmagic Desktop Video SDK.")

# DeckLink SDK structures and constants
class BMDPixelFormat(ctypes.c_uint32):
    bmdFormat8BitYUV = 0x32767579  # '2vuy' in reverse

class IDeckLinkVideoInputFrame(Structure):
    _fields_ = [
        ('GetWidth', CFUNCTYPE(c_long)),
        ('GetHeight', CFUNCTYPE(c_long)),
        ('GetRowBytes', CFUNCTYPE(c_long)),
        ('GetPixelFormat', CFUNCTYPE(BMDPixelFormat)),
        ('GetFlags', CFUNCTYPE(c_long)),
        ('GetBytes', CFUNCTYPE(POINTER(c_void_p)))
    ]

class SDICapture:
    def __init__(self, width=1920, height=1080):
        pygame.init()
        self.width = width
        self.height = height
        self.screen = pygame.display.set_mode((width, height))
        pygame.display.set_caption("SDI Video Viewer")
        
        # Initialize DeckLink device
        self.init_decklink()
        
    def init_decklink(self):
        # Create DeckLink iterator
        iterator = decklink.CreateDeckLinkIterator()
        if iterator is None:
            sys.exit("Error: No DeckLink devices found")
            
        # Get first device
        self.decklink = POINTER(c_void_p)()
        if iterator.Next(ctypes.byref(self.decklink)) != 0:
            sys.exit("Error: Failed to get DeckLink device")
            
        # Configure reference input for Mini Recorder
        self.decklink.SetReferenceSource(bmdReferenceSourceInternal)
        
        # Enable input video format detection
        self.decklink.EnableVideoInput(
            bmdModeHD1080i5994,  # 1080i 59.94
            bmdFormat8BitYUV,    # YUV format
            bmdVideoInputEnableFormatDetection  # Enable format detection
        )
        
        # Start streaming
        if self.decklink.StartStreams() != 0:
            sys.exit("Error: Failed to start video stream")
        
    def capture_frame(self):
        # Get frame from DeckLink
        frame = POINTER(IDeckLinkVideoInputFrame)()
        result = self.decklink.GetVideoInputFrame(ctypes.byref(frame))
        
        if result != 0:
            return None
            
        # Get frame data
        frame_bytes = frame.GetBytes()
        row_bytes = frame.GetRowBytes()
        
        # Convert YUV to RGB
        yuv = np.frombuffer(frame_bytes, dtype=np.uint8)
        yuv = yuv.reshape((self.height, row_bytes))
        
        # Basic YUV to RGB conversion
        rgb = np.empty((self.height, self.width, 3), dtype=np.uint8)
        y = yuv[:, 0::2]
        u = yuv[:, 1::4]
        v = yuv[:, 3::4]
        
        rgb[:, :, 0] = y + 1.402 * (v - 128)                # R
        rgb[:, :, 1] = y - 0.344136 * (u - 128) - 0.714136 * (v - 128)  # G
        rgb[:, :, 2] = y + 1.772 * (u - 128)                # B
        
        return rgb
        
    def run(self):
        running = True
        clock = pygame.time.Clock()
        
        try:
            while running:
                for event in pygame.event.get():
                    if event.type == pygame.QUIT:
                        running = False
                
                # Capture and display frame
                frame = self.capture_frame()
                if frame is not None:
                    surface = pygame.surfarray.make_surface(frame)
                    self.screen.blit(surface, (0, 0))
                    pygame.display.flip()
                
                clock.tick(60)
                
        finally:
            self.cleanup()
            
    def cleanup(self):
        if hasattr(self, 'decklink'):
            self.decklink.StopStreams()
            self.decklink.DisableVideoInput()
        pygame.quit()

if __name__ == '__main__':
    capture = SDICapture()
    capture.run()
