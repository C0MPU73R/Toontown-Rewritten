from Nametag import *
import NametagGlobals
from NametagConstants import *
from pandac.PandaModules import *

class Nametag3d(Nametag):
    CONTENTS_SCALE = 0.17
    BILLBOARD_OFFSET = 3.0
    SHOULD_BILLBOARD = True

    def __init__(self):
        Nametag.__init__(self)

        self.contents = self.CName|self.CSpeech|self.CThought

        self.bbOffset = self.BILLBOARD_OFFSET
        self._doBillboard()

        self.innerNP.setScale(self.CONTENTS_SCALE)

    def _doBillboard(self):
        if self.SHOULD_BILLBOARD:
            self.innerNP.setEffect(BillboardEffect.make(
                Vec3(0,0,1),
                True,
                False,
                self.bbOffset,
                NametagGlobals.camera,
                Point3(0,0,0)))

    def setBillboardOffset(self, bbOffset):
        self.bbOffset = bbOffset
        self._doBillboard()

    def getSpeechBalloon(self):
        return NametagGlobals.speechBalloon3d

    def getThoughtBalloon(self):
        return NametagGlobals.thoughtBalloon3d

    def setChatWordwrap(self, todo1):
        pass
