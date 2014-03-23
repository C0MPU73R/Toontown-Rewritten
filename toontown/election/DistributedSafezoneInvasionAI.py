import random
from direct.directnotify import DirectNotifyGlobal
from direct.distributed.DistributedObjectAI import DistributedObjectAI
from direct.fsm.FSM import FSM
from otp.ai.MagicWordGlobal import *
from DistributedInvasionSuitAI import DistributedInvasionSuitAI
from InvasionMasterAI import InvasionMasterAI
import SafezoneInvasionGlobals
from DistributedElectionEventAI import DistributedElectionEventAI
from toontown.suit import SuitTimings
from toontown.toonbase import ToontownBattleGlobals

class DistributedSafezoneInvasionAI(DistributedObjectAI, FSM):
    notify = DirectNotifyGlobal.directNotify.newCategory("DistributedSafezoneInvasionAI")

    def __init__(self, air):
        DistributedObjectAI.__init__(self, air)
        FSM.__init__(self, 'InvasionFSM')

        self.master = InvasionMasterAI(self)

        self.waveNumber = 0
        self.spawnPoints = []
        self.suits = []
        self.toons = []
        self.sadToons = []
        self.lastWave = (self.waveNumber == len(SafezoneInvasionGlobals.SuitWaves) - 1)
        self.invasionOn = False

    def announceGenerate(self):
        self.b_setInvasionStarted(True)
        self.demand('BeginWave', 0)
        
        # Kill all the butterflies in Toontown Central.
        #for butterfly in self.air.hoods[0].butterflies:
            #butterfly.requestDelete()

        # Start up the "which Toons are in the area" tracking.
        for toon in self.air.doId2do.values():
            if toon.zoneId != self.zoneId:
                continue # Object isn't here.
            if toon.dclass != self.air.dclassesByName['DistributedToonAI']:
                continue # Object isn't a Toon.
            self._handleToonEnter(toon)
        self.accept('toon-entered-%s' % self.zoneId, self._handleToonEnter)
        self.accept('toon-left-%s' % self.zoneId, self._handleToonExit)
        
    def b_setInvasionStarted(self, started):
        self.setInvasionStarted(started)
        self.d_setInvasionStarted(started)
        
    def setInvasionStarted(self, started):
        self.invasionOn = started
        
    def d_setInvasionStarted(self, started):
        self.sendUpdate('setInvasionStarted', [started])
        
    def getInvasionStarted(self):
        return self.invasionOn

    def _handleToonEnter(self, toon):
        if toon not in self.toons:
            self.toons.append(toon)
            self.acceptOnce(self.air.getAvatarExitEvent(toon.doId),
                            self._handleToonExit,
                            extraArgs=[toon])

            # Don't want those cogs attacking us if we are sad. 
            # Thats just mean
            self.checkToonHp()

    def _handleToonExit(self, toon):
        if toon in self.toons:
            self.toons.remove(toon)
            self.ignore(self.air.getAvatarExitEvent(toon.doId))

        if toon in self.sadToons:
            self.sadToons.remove(toon)

    def getToon(self, toonId):
        for toon in self.toons:
            if toon.doId == toonId:
                return toon
        return None

    def delete(self):
        DistributedObjectAI.delete(self)
        self.demand('Off')

        self.ignoreAll()

    def hitToon(self, doId):
        # Someone hit a Toon!
        avId = self.air.getAvatarIdFromSender()

        toon = self.air.doId2do.get(doId)
        if not toon:
            self.air.writeServerEvent('suspicious', avId, 'Hit a nonexistent Toon with a pie!')
            return

        from toontown.toon.DistributedToonAI import DistributedToonAI
        if not isinstance(toon, DistributedToonAI):
            self.air.writeServerEvent('suspicious', avId, 'Hit a non-Toon with a pie through hitToon()!')
            return

        # Just to be safe, let's check if the Toon has less than 0 laff.
        # Sometimes this happens from multiple cog hits at once.
        if toon.hp < 0:
            # They do! :( Let's give them a little boost before tooning up to make it fair.
            toon.setHp(0)

        # Time to toon up!
        toon.toonUp(SafezoneInvasionGlobals.ToonHealAmount)
        self.checkToonHp()

    def hitSuit(self, doId):
        # Someone hit one of our suits...
        avId = self.air.getAvatarIdFromSender()

        toon = self.air.doId2do.get(avId)
        if not toon:
            self.air.writeServerEvent('suspicious', avId, 'Nonexistent Toon tried to throw a pie!')
            return

        suit = self.air.doId2do.get(doId)
        if suit not in self.suits:
            # N.B. this is NOT suspicious as it can happen as a result of a race condition
            return

        # How much damage does this Throw gag do?
        pieDamageEntry = ToontownBattleGlobals.AvPropDamage[ToontownBattleGlobals.THROW_TRACK][toon.pieType]
        (pieDamage, pieGroupDamage), _ = pieDamageEntry

        suit.takeDamage(pieDamage)

    def takeDamage(self, damage):
        # A Toon got hit!
        avId = self.air.getAvatarIdFromSender()

        toon = self.air.doId2do.get(avId)
        if not toon:
            self.air.writeServerEvent('suspicious', avId, 'Nonexistent Toon tried to get hit!')
            return

        # If the cog's attack is higher than the amount of laff they have, we'll only take away what they have.
        # If the attack is 5 and the toon has 3 laff, we'll only take away 3 laff. This mostly prevents toons going under 0 Laff.
        if damage > toon.hp:
            toon.takeDamage(toon.hp)
        else:
            toon.takeDamage(damage)

        self.checkToonHp()

    def __deleteSuits(self):
        for suit in self.suits:
            suit.requestDelete()

    def spawnOne(self, suitType, levelOffset=0):
        # Pick a spawnpoint:
        pointId = random.choice(self.spawnPoints)
        self.spawnPoints.remove(pointId)

        # Define our suit:
        suit = DistributedInvasionSuitAI(self.air, self)
        suit.dna.newSuit(suitType)
        suit.setSpawnPoint(pointId)
        suit.setLevel(levelOffset)
        suit.generateWithRequired(self.zoneId)

        # Is this a skelecog wave?
        if self.waveNumber in SafezoneInvasionGlobals.SuitSkelecogWaves:
            suit.makeSkelecog()

        # Now send 'em in!
        suit.b_setState('FlyDown')
        self.suits.append(suit)

    def checkToonHp(self):
        # Check all the toons
        for toon in self.toons:
            if toon.hp <= 0:
                # We kicked the bucket
                if toon not in self.sadToons:
                    self.sadToons.append(toon) # They got one of us!

                # Make sure the toon is the invasion before removing it
                if toon in self.master.invasion.toons:
                    self.master.invasion.toons.remove(toon) # Stop attacking us sad toons!
            elif toon.hp > 0:
                # Toon now has some laffs...
                if toon in self.sadToons:
                    self.master.invasion.toons.append(toon) # Add the toon back into the invasion
                    self.sadToons.remove(toon) # Remove the sad toon

    def suitDied(self, suit):
        if self.state == 'Finale':
            self.suits.remove(suit)
            self.demand('Victory')
            return

        if suit not in self.suits:
            self.notify.warning('suitDied called twice for same suit!')
            return

        self.suits.remove(suit)
        if not self.suits:
            self.waveWon()

    def waveWon(self):
        if self.state != 'Wave':
            return

        # Was this the last wave?
        if self.lastWave:
            # self.demand('Victory')
            self.demand('Finale')
        # Should we spawn this one immidiately?
        elif self.waveNumber in SafezoneInvasionGlobals.SuitWaitWaves:
            self.demand('BeginWave', self.waveNumber + 1)
            self.lastWave = (self.waveNumber == len(SafezoneInvasionGlobals.SuitWaves) - 1)
        # No, we'll give an intermission.
        else:
            self.demand('Intermission')

    def enterBeginWave(self, waveNumber):
        # In this state, Cogs rain down from the heavens. We call .spawnOne at
        # regular intervals until the quota for the wave is met.
        self.waveNumber = waveNumber

        if self.waveNumber == 24:
            election.saySurleePhrase('Oh boy... We\'re destroying the Cogs faster than they can be built. Skelecogs inbound!')

        # Reset spawnpoints:
        self.spawnPoints = range(len(SafezoneInvasionGlobals.SuitSpawnPoints))

        # Get the suits to call:
        suitsToCall = SafezoneInvasionGlobals.SuitWaves[self.waveNumber]

        # How long do we have to spread out the suit calldowns?
        # In case some dummkopf set WaveBeginningTime too low:
        delay = max(SafezoneInvasionGlobals.WaveBeginningTime, SuitTimings.fromSky)
        spread = delay - SuitTimings.fromSky
        spreadPerSuit = spread/len(suitsToCall)

        self._waveBeginTasks = []
        for i, (suit, level) in enumerate(suitsToCall):
            self._waveBeginTasks.append(
                taskMgr.doMethodLater(i*spreadPerSuit, self.spawnOne,
                                      self.uniqueName('summon-suit-%s' % i),
                                      extraArgs=[suit, level]))

        # Plus a task to switch to the 'Wave' state:
        self._waveBeginTasks.append(
            taskMgr.doMethodLater(delay, self.demand,
                                  self.uniqueName('begin-wave'),
                                  extraArgs=['Wave']))


    def exitBeginWave(self):
        for task in self._waveBeginTasks:
            task.remove()

    def enterWave(self):
        # This state is entered after all Cogs have been spawned by BeginWave.
        # If the next wave isn't an Intermission or Wait Wave, it will spawn the next one.

        # Send the suits marching!
        for suit in self.suits:
            suit.start()

        # If the wave isn't an Intermission or Wait Wave, send another set of suits out.
        # Otherwise, wait until all suits are dead and let waveWon() decide what to do.
        if self.lastWave:
            return
        else:
            if self.waveNumber not in SafezoneInvasionGlobals.SuitIntermissionWaves and self.waveNumber not in SafezoneInvasionGlobals.SuitWaitWaves:
                self.spawnPoints = range(len(SafezoneInvasionGlobals.SuitSpawnPoints))
                self.demand('BeginWave', self.waveNumber + 1)
                self.lastWave = (self.waveNumber == len(SafezoneInvasionGlobals.SuitWaves) - 1)

        # The first suit on the scene also says a faceoff taunt:
        if self.suits:
            self.suits[0].d_sayFaceoffTaunt()

    def exitWave(self):
        # Clean up any loose suits, in case the wave is being ended by MW.
        if self.waveNumber in SafezoneInvasionGlobals.SuitIntermissionWaves or self.waveNumber in SafezoneInvasionGlobals.SuitWaitWaves:
            self.__deleteSuits()

    def enterIntermission(self):
        # This state is entered after a wave is successfully over. There's a
        # pause in the action until the next wave.
        election = DistributedElectionEventAI(simbase.air)
        if self.waveNumber == 2:
            election.saySurleePhrase('You got them, but that\'s only the first wave. We\'ve got a little break to regroup before they come back.')
        elif self.waveNumber == 5:
            election.saySurleePhrase('Another wave down, very nice. Get ready, more are on the way!')
        elif self.waveNumber == 8:
            election.saySurleePhrase('They\'re getting stronger with each wave... This isn\'t good.')
        elif self.waveNumber == 11:
            election.saySurleePhrase('I\'ve been keeping track of the wave intervals, and we seem to have about 20 seconds between each wave. Hang on tight.')
        elif self.waveNumber == 14:
            election.saySurleePhrase('Stay happy, toons! We can do this!')
        elif self.waveNumber == 17:
            election.saySurleePhrase('We\'re losing toons fast, but our motivation is still high. Don\'t let these metal menaces take over our town!')
        elif self.waveNumber == 20:
            election.saySurleePhrase('These next ones are the hardest yet. Flippy, do you have any bigger pies? We\'re going to need them soon.')
        elif self.waveNumber == 23:
            election.saySurleePhrase('Oof... I... I think we made it. Those must have been the last ones.')
        elif self.waveNumber == 26:
            election.saySurleePhrase('I think this is it, toons. They\'re sending in the boss!')


        self._delay = taskMgr.doMethodLater(SafezoneInvasionGlobals.IntermissionTime,
                                            self.__endIntermission,
                                            self.uniqueName('intermission'))

    def __endIntermission(self, task):
        self.demand('BeginWave', self.waveNumber + 1)
        self.lastWave = (self.waveNumber == len(SafezoneInvasionGlobals.SuitWaves) - 1)

    def exitIntermission(self):
        self._delay.remove()

    def enterFinale(self):
        taskMgr.doMethodLater(1, self.spawnFinaleSuit, self.uniqueName('summon-suit-%s' % 'tbc'), extraArgs=[])
    
    def spawnFinaleSuit(self):
        suit = DistributedInvasionSuitAI(self.air, self)
        suit.dna.newSuit('tbc')
        suit.setSpawnPoint(3) # Point 3 is in front of the MML tunnel
        suit.setLevel(4) # Give it the highest level we can. Requires 200 damage to defeat
        suit.generateWithRequired(self.zoneId)
        suit.makeSkelecog()
        suit.b_setState('FlyDown')
        self.suits.append(suit)

    def setFinaleSuitStunned(self, hp):
        if self.state == 'Finale':
            for suit in self.suits:
                hp = min(hp, suit.currHP) # Don't take more damage than we have...
                suit.b_setHP(suit.currHP - hp)
                suit.b_setState('Stunned')

    def winFinale(self):
        if self.state == 'Finale':
            for suit in self.suits:
                suit.b_setState('Explode')

    def enterVictory(self):
        # self.b_setInvasionStatus(False)
        self.b_setInvasionStarted(False)

    def enterOff(self):
        self.__deleteSuits()

@magicWord(category=CATEGORY_DEBUG, types=[str, str])
def szInvasion(cmd, arg=''):
    if not simbase.config.GetBool('want-doomsday', False):
        simbase.air.writeServerEvent('aboose', spellbook.getInvoker().doId, 'Attempted to initiate doomsday while it is disabled.')
        return 'ABOOSE! Doomsday is currently disabled. Your request has been logged.'
        
    invasion = simbase.air.doFind('SafezoneInvasion')

    if invasion is None and cmd != 'start':
        return 'No invasion has been created'

    if cmd == 'start':
        if invasion is None:
            invasion = DistributedSafezoneInvasionAI(simbase.air)
            invasion.generateWithRequired(2000)
        else:
            return 'An invasion object already exists.'
    elif cmd == 'stop':
        invasion.b_setInvasionStarted(False)
        invasion.requestDelete()
    elif cmd == 'spawn':
        invasion.spawnOne(arg)
    elif cmd == 'wave':
        invasion.demand('BeginWave', int(arg))
    elif cmd == 'endWave':
        invasion.waveWon()
    elif cmd == 'stunFinaleSuit':
        invasion.setFinaleSuitStunned(200)
    elif cmd == 'winFinale':
        invasion.winFinale()
