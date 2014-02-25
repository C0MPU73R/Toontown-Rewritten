from direct.interval.IntervalGlobal import *
from otp.nametag.NametagConstants import *
from pandac.PandaModules import *

FLIPPY_WHEELBARROW_PIES = [
    # Format: posHprScale
    [1.16, 11.24, 7.00, 246.80, 351.25, 0.00, 1.60, 1.40, 1.8],
    [2.27, 8.02, 6.35, 104.04, 311.99, 9.46, 1.35, 1.35, 1],
    [-1.23, 7.33, 6.88, 276.34, 28.61, 350.54, 1.41, 1.41, 1.6],
    [0.27, 8.24, 6.42, 198.15, 351.87, 355.24, 1.93, 2, 2],
    [0.06, 5.23, 6.78, 63.43, 355.91, 15.26, 1.3, 1.6, 1.8],
    [-0.81, 11.37, 6.82, 326.31, 5.19, 19.98, 1.76, 1.86, 1.5],
    [1.35, 10.09, 5.92, 35.54, 353.66, 343.30, 1.50, 1.90, 1.8],
    [1.9, 5.59, 6.5, 75.96, 326.31, 8, 1.76, 1.56, 1.5],
    [-1.74, 5.42, 6.28, 327.53, 318.81, 4.76, 1.8, 2, 2],
    [-1.55, 9.22, 5.72, 266.53, 341.57, 0.00, 2.09, 1.68, 1.81],
]
BalloonBasePosition = [-15, 33, 1.1]
BalloonScale = 2.5
SlappySpeeches = [
    'Keep your hands and feet in the basket at all times',
    'Hold on tight! Here we Go!',
    'Remember, don\'t be wacky and vote for slappy!',
    'Ready to soar through the sky?'
]
SLAPPY_RIDE_START = 'Off we go!'
SLAPPY_VIEW = 'How about that view?'
SLAPPY_WEIGHT_MISSED = 'Rats! The weight missed the gag shop!'
SLAPPY_PODIUM = 'Hey look! The Beatles are playing!'
SLAPPY_RIDE_DONE = 'Hope you enjoyed the Ride!'
SLAPPY_BALLOON_NUM_PATHS = 1

def generateFlightPaths(balloon):
    # This is quite messy imo... but I didn't have much time to think about it.
    # For each sequence, you basically copy and paste this whole section and edit
    # the sequence. When you add a new sequence here, you MUST edit the 
    # SLAPPY_BALLOON_NUM_PATHS constant.
    flightPaths = []
    flightPaths.append(
        Sequence(
            Func(balloon.slappy.setChatAbsolute, SLAPPY_RIDE_START, CFSpeech | CFTimeout),
            # Lift Off
            Wait(0.5),
            balloon.balloon.posHprInterval(1.0, Point3(-19, 35, 3), (0, 3, 3)),
            balloon.balloon.posHprInterval(1.0, Point3(-23, 38, 5), (0, -2, -2)),
            balloon.balloon.posHprInterval(6.0, Point3(-43, 78, 26), (0, 0, 0)),

            # To the tunnel we go
            Func(balloon.slappy.setChatAbsolute, SLAPPY_VIEW, CFSpeech | CFTimeout),
            balloon.balloon.posHprInterval(5.0, Point3(-125, 33, 54), (0, -2, -2)),

            # Lets drop a weight on the gag shop
            balloon.balloon.posInterval(4.0, Point3(-100, -60, 54)),
            Func(balloon.slappy.setChatAbsolute, SLAPPY_WEIGHT_MISSED, CFSpeech | CFTimeout), 

            # Rats, we missed! Lets checkout the podium
            balloon.balloon.posInterval(7.0, Point3(60, -10, 54)),
            Func(balloon.slappy.setChatAbsolute, SLAPPY_PODIUM, CFSpeech | CFTimeout),

            # Back to the Launchpad
            balloon.balloon.posInterval(4.0, Point3(-15, 33, 54)),
            Func(balloon.slappy.setChatAbsolute, SLAPPY_RIDE_DONE, CFSpeech | CFTimeout),

            # Set her down; gently
            balloon.balloon.posInterval(5.0, Point3(-15, 33, 1.1)),
        )
    )
    
    # Return the flight paths back to the HotAirBalloon...
    return flightPaths

def generateToonFlightPaths(balloon):
    # This is quite messy imo... but I didn't have much time to think about it.
    # For each sequence, you basically copy and paste this whole section and edit
    # the sequence. When you add a new sequence here, you MUST edit the 
    # SLAPPY_BALLOON_NUM_PATHS constant.
    toonFlightPaths = []
    toonFlightPaths.append(
        Sequence(
            # Lift Off
            Wait(0.5),
            base.localAvatar.posInterval(1.0, Point3(-19, 35, 3)),
            base.localAvatar.posInterval(1.0, Point3(-23, 38, 5)),
            base.localAvatar.posInterval(6.0, Point3(-43, 78, 26)),
            base.localAvatar.posInterval(5.0, Point3(-125, 33, 54)),
            # Lets drop a weight on the gag shop
            base.localAvatar.posInterval(4.0, Point3(-100, -60, 54)),       
            # Rats, we missed! Lets checkout the podium
            base.localAvatar.posInterval(7.0, Point3(60, -10, 54)),
            # Back to the Launchpad
            base.localAvatar.posInterval(4.0, Point3(-15, 33, 54)),
            # Set her down; gently
            base.localAvatar.posInterval(5.0, Point3(-15, 33, 1.1)),
        )
    )
    
    # Return the flight paths back to the HotAirBalloon...
    return toonFlightPaths
