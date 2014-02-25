from pandac.PandaModules import *
from otp.nametag.NametagConstants import *
from direct.distributed.ClockDelta import *
from direct.interval.IntervalGlobal import *
from direct.distributed.DistributedObject import DistributedObject
from direct.fsm.FSM import FSM
from toontown.toon import NPCToons
from toontown.toonbase import ToontownGlobals
from direct.task import Task

# TODO: ElectionGlobals C:?
BALLOON_BASE_POS = [-15, 33, 1.1]
BALLOON_SCALE = 2.5

class DistributedHotAirBalloon(DistributedObject, FSM):
    def __init__(self, cr):
        DistributedObject.__init__(self, cr)
        FSM.__init__(self, 'HotAirBalloonFSM')
        self.avId = 0

        # Create the balloon
        self.balloon = loader.loadModel('phase_4/models/events/airballoon.egg') # TODO: Use .bam model
        self.balloon.reparentTo(base.render)
        self.balloon.setPos(*BALLOON_BASE_POS)
        self.balloon.setScale(BALLOON_SCALE)
        # So we can reparent toons to the balloon so they don't fall out
        self.cr.parentMgr.registerParent(ToontownGlobals.SPSlappysBalloon, self.balloon)
        # Balloon collision NodePath (outside)
        self.collisionNP = self.balloon.find('**/BasketOutsideCollision')
        # Slappy
        self.slappy = NPCToons.createLocalNPC(2021)
        self.slappy.reparentTo(self.balloon)
        self.slappy.setScale((1/BALLOON_SCALE)) # We want a normal sized Slappy
        self.slappy.loop('wave')

    def delete(self):
        # Clean up after our mess...
        # This is what happens when you don't clean up:
        # http://puu.sh/77zAm.jpg
        self.demand('Off')
        self.ignore('enter' + self.collisionNP.node().getName())
        self.cr.parentMgr.unregisterParent(ToontownGlobals.SPSlappysBalloon)
        self.balloon.removeNode()
        self.slappy.delete()
        DistributedObject.delete(self)

    def setState(self, state, timestamp, avId):
        if avId != self.avId:
            self.avId = avId
        self.demand(state, globalClockDelta.localElapsedTime(timestamp))

    def enterWaiting(self, offset):
        # Wait for a collision...
        self.accept('enter' + self.collisionNP.node().getName(), self.__handleToonEnter)
        # Mini animation for the balloon hovering near the floor
        self.balloonIdle = Sequence(
            Wait(0.3),
            self.balloon.posInterval(3, (-15, 33, 1.5)),
            Wait(0.3),
            self.balloon.posInterval(3, (-15, 33, 1.1)),
        )
        self.balloonIdle.loop()
        self.balloonIdle.setT(offset)

    def __handleToonEnter(self, collEntry):
        if self.avId != 0:
            # Someone is already occupying the balloon
            return
        if self.state != 'Waiting':
            # The balloon isn't waiting for a toon
            return
        self.sendUpdate('requestEnter', [])

    def exitWaiting(self):
        self.balloonIdle.finish()
        self.ignore('enter' + self.collisionNP.node().getName())

    def enterOccupied(self, offset):
        if self.avId == base.localAvatar.doId:
            # This is us! We need to reparent to the balloon and position ourselves accordingly.
            base.localAvatar.b_setParent(ToontownGlobals.SPSlappysBalloon)
            base.localAvatar.setPos(0, 0, 0.5)
            base.localAvatar.setTeleportAvailable(0)
        # Maybe we want a short speech before we take off?
        self.occupiedSequence = Sequence(
            Func(self.slappy.setChatAbsolute, 'Keep your hands and feet in the basket at all times!', CFSpeech | CFTimeout),
            Wait(3.5),
        )
        self.occupiedSequence.start()
        self.occupiedSequence.setT(offset)

    def exitOccupied(self):
        self.occupiedSequence.finish()

    def enterStartRide(self, offset):
        self.rideSequence = Sequence(
            Func(self.slappy.setChatAbsolute, 'Off we go!', CFSpeech | CFTimeout),
            Wait(0.5),
            self.balloon.posInterval(5.0, Point3(-15, 33, 54)),
            Wait(0.5),
            self.balloon.posInterval(5.0, Point3(-125, 33, 54)),
            Wait(0.5),
            self.balloon.posInterval(5.0, Point3(-15, 33, 54)),
            Wait(0.5),
            self.balloon.posInterval(5.0, Point3(-15, 33, 1.1)),
        )
        self.rideSequence.start()
        self.rideSequence.setT(offset)

    def exitStartRide(self):
        self.rideSequence.finish()

    def enterRideOver(self, offset):
        if self.avId == base.localAvatar.doId:
            # We were on the ride! Better reparent to the render and get out of the balloon...
            base.localAvatar.b_setParent(ToontownGlobals.SPRender)
            base.localAvatar.setPos(-17.178, 6, 43.3134)
            base.localAvatar.setTeleportAvailable(1)
