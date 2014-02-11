from direct.directnotify import DirectNotifyGlobal
from direct.distributed.ClockDelta import *
from direct.fsm.FSM import FSM
from toontown.suit.DistributedSuitBaseAI import DistributedSuitBaseAI
from toontown.suit import SuitTimings
import SafezoneInvasionConstants
from InvasionSuitBase import InvasionSuitBase
from InvasionSuitBrainAI import InvasionSuitBrainAI

class DistributedInvasionSuitAI(DistributedSuitBaseAI, InvasionSuitBase, FSM):
    notify = DirectNotifyGlobal.directNotify.newCategory("DistributedInvasionSuitAI")

    def __init__(self, air, invasion):
        DistributedSuitBaseAI.__init__(self, air)
        InvasionSuitBase.__init__(self)
        FSM.__init__(self, 'InvasionSuitFSM')
        self.invasion = invasion

        self.stateTime = globalClockDelta.getRealNetworkTime()
        self.spawnPointId = 0

        self.brain = InvasionSuitBrainAI(self)

        self.lastMarchTime = 0.0
        self.__walkTimer = None

    def announceGenerate(self):
        x, y, z, h = SafezoneInvasionConstants.SuitSpawnPoints[self.spawnPointId]
        self.freezeLerp(x, y)

    def delete(self):
        DistributedSuitBaseAI.delete(self)
        self.demand('Off')

    def enterFlyDown(self):
        # We set a delay to wait for the Cog to finish flying down, then switch
        # states.
        self._delay = taskMgr.doMethodLater(SuitTimings.fromSky, self.__flyDownComplete,
                                            self.uniqueName('fly-down-animation'))

    def __flyDownComplete(self, task):
        self.b_setState('Idle')

        if self.invasion.state != 'BeginWave':
            self.start()

    def exitFlyDown(self):
        self._delay.remove()

    def enterIdle(self):
        # We do nothing. We wait for the invasion manager to shift into the
        # 'Wave' state, and we all begin marching at once.
        pass

    def enterMarch(self):
        pass

    def exitMarch(self):
        x, y = self.getCurrentPos()
        self.freezeLerp(x, y)

        self.__stopWalkTimer()

    def walkTo(self, x, y):
        # Begin walking to a given point. It's OK to call this before the suit
        # finishes reaching its old waypoint; if that happens, the AI will
        # calculate the suit's current position and walk from there.
        oldX, oldY = self.getCurrentPos()
        self.b_setMarchLerp(oldX, oldY, x, y)
        self.__startWalkTimer()

        if self.state != 'March':
            self.b_setState('March')

    def idle(self):
        self.b_setState('Idle')

    def __startWalkTimer(self):
        self.__stopWalkTimer()
        self.__walkTimer = taskMgr.doMethodLater(self._lerpDelay, self.__walkTimerOver,
                                                 self.uniqueName('walkTimer'))

    def __stopWalkTimer(self):
        if self.__walkTimer:
            self.__walkTimer.remove()
            self.__walkTimer = None

    def __walkTimerOver(self, task):
        if self.state != 'March':
            self.notify.warning('Walk timer ran out, but not in March state!')
            return

        self.brain.suitFinishedWalking()

    def start(self):
        # Start the brain, if it hasn't been started already:
        self.brain.start()

    def getCurrentPos(self):
        return self.getPosAt(globalClock.getRealTime() - self.lastMarchTime)

    def setSpawnPoint(self, pointId):
        self.spawnPointId = pointId

    def getSpawnPoint(self):
        return self.spawnPointId

    def setMarchLerp(self, x1, y1, x2, y2):
        self.setLerpPoints(x1, y1, x2, y2)
        self.lastMarchTime = globalClock.getRealTime()

    def d_setMarchLerp(self, x1, y1, x2, y2):
        self.sendUpdate('setMarchLerp', [x1, y1, x2, y2,
                                         globalClockDelta.getRealNetworkTime()])

    def b_setMarchLerp(self, x1, y1, x2, y2):
        self.setMarchLerp(x1, y1, x2, y2)
        self.d_setMarchLerp(x1, y1, x2, y2)

    def setState(self, state):
        self.demand(state)

    def d_setState(self, state):
        self.stateTime = globalClockDelta.getRealNetworkTime()
        self.sendUpdate('setState', [state, self.stateTime])

    def b_setState(self, state):
        self.setState(state)
        self.d_setState(state)

    def getState(self):
        return (self.state, self.stateTime)
