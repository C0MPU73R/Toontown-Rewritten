from direct.distributed.DistributedObjectGlobalUD import DistributedObjectGlobalUD
from direct.distributed.PyDatagram import *
from direct.directnotify.DirectNotifyGlobal import directNotify
from PartyGlobals import *
from datetime import datetime

class GlobalPartyManagerUD(DistributedObjectGlobalUD):
    notify = directNotify.newCategory('GlobalPartyManagerUD')

    # This uberdog MUST be up before the AIs, as AIs talk to this UD
    
    def announceGenerate(self):
        DistributedObjectGlobalUD.announceGenerate(self)
        self.senders2Mgrs = {}
        self.host2Party = {}
        PARTY_TIME_FORMAT = '%Y-%m-%d %H:%M:%S'
        startTime = datetime.strptime('2014-01-20 11:50:00', PARTY_TIME_FORMAT)
        endTime = datetime.strptime('2014-01-20 12:20:00', PARTY_TIME_FORMAT)
        #self.host2Party[100000001] = {'hostId': 100000001, 'start': startTime, 'end': endTime, 'partyId': 1717986918400000, 'decorations': [[3,5,7,6]], 'activities': [[10,13,6,18],[7,8,7,0]],'inviteTheme':1,'isPrivate':0,'inviteeIds':[]}

        # Setup tasks
        self.runAtNextInterval()

    # GPMUD -> PartyManagerAI messaging
    def _makeAIMsg(self, field, values, recipient):
        return self.air.dclassesByName['DistributedPartyManagerUD'].getFieldByName(field).aiFormatUpdate(recipient, recipient, simbase.air.ourChannel, values)

    def sendToAI(self, field, values, sender=None):
        if not sender:
            sender = self.air.getAvatarIdFromSender()
        dg = self._makeAIMsg(field, values, self.senders2Mgrs[sender])
        self.air.send(dg)
        
    # GPMUD -> toon messaging
    def _makeAvMsg(self, field, values, recipient):
        return self.air.dclassesByName['DistributedToonUD'].getFieldByName(field).aiFormatUpdate(recipient, recipient, simbase.air.ourChannel, values)

    def sendToAv(self, avId, field, values):
        dg = self._makeAvMsg(field, values, avId)
        self.air.send(dg)
        
    # Task stuff
    def runAtNextInterval(self):
        now = datetime.now()
        howLongUntilAFive = (60 - now.second) + 60 * (4 - (now.minute % 5))
        taskMgr.doMethodLater(howLongUntilAFive, self.__checkPartyStarts, 'GlobalPartyManager_checkStarts')

    def __checkPartyStarts(self, task):
        print 'Checkstarts invoked!<#'
        now = datetime.now()
        for hostId in self.host2Party:
            party = self.host2Party[hostId]
            if party['start'] < now:
                # Time to start party
                self.sendToAv(hostId, 'setHostedParties', [[self._formatParty(party, status=PartyStatus.CanStart)]])
                self.sendToAv(hostId, 'setPartyCanStart', [party['partyId']])
        self.runAtNextInterval()

    # Format a party dict into a party struct suitable for the wire
    def _formatParty(self, partyDict, status=PartyStatus.Pending):
        start = partyDict['start']
        end = partyDict['end']
        return [partyDict['partyId'],
                partyDict['hostId'],
                start.year,
                start.month,
                start.day,
                start.hour,
                start.minute,
                end.year,
                end.month,
                end.day,
                end.hour,
                end.minute,
                partyDict['isPrivate'],
                partyDict['inviteTheme'],
                partyDict['activities'],
                partyDict['decorations'],
                status]

    # Avatar joined messages, invoked by the CSMUD
    def avatarJoined(self, avId):
        party = self.host2Party.get(avId, None)
        if party:
            print 'avId %s has a party that i am telling them about' % avId
            self.sendToAv(avId, 'setHostedParties', [[self._formatParty(party)]])
            # For now, he can start instantly
            self.sendToAv(avId, 'setPartyCanStart', [party['partyId']])
        
    def __updateAIs(self):
        # I'm pretty sure the UD is single-threaded, so it won't end up updating AIs while a new party is added, messing things up
        partyIds = self.host2Party.keys()
        for s in self.senders2Mgrs.keys():
            pass#self.sendToAI('updateToPublicPartyCountUdToAllAi', [

        
    def partyManagerAIHello(self, channel):
        # Upon AI boot, DistributedPartyManagerAIs are supposed to say hello. 
        # They send along the DPMAI's doId as well, so that I can talk to them later.
        print 'AI with base channel %s, will send replies to DPM %s' % (simbase.air.getAvatarIdFromSender(), channel)
        self.senders2Mgrs[simbase.air.getAvatarIdFromSender()] = channel
        self.sendToAI('partyManagerUdStartingUp', [])
        
        # In addition, set up a postRemove where we inform this AI that the UD has died
        self.air.addPostRemove(self._makeAIMsg('partyManagerUdLost', [], channel))
        
    def addParty(self, avId, partyId, start, end, isPrivate, inviteTheme, activities, decorations, inviteeIds):
        PARTY_TIME_FORMAT = '%Y-%m-%d %H:%M:%S'
        print 'start time: %s' % start
        startTime = datetime.strptime(start, PARTY_TIME_FORMAT)
        endTime = datetime.strptime(end, PARTY_TIME_FORMAT)
        print 'start year: %s' % startTime.year
        if avId in self.host2Party:
            # Sorry, one party at a time
            self.sendToAI('addPartyResponseUdToAi', [partyId, AddPartyErrorCode.TooManyHostedParties])
        self.host2Party[avId] = {'partyId': partyId, 'hostId': avId, 'start': startTime, 'end': endTime, 'isPrivate': isPrivate, 'inviteTheme': inviteTheme, 'activities': activities, 'decorations': decorations, 'inviteeIds': inviteeIds}
        self.sendToAI('addPartyResponseUdToAi', [partyId, AddPartyErrorCode.AllOk, self._formatParty(self.host2Party[avId])])
        taskMgr.remove('GlobalPartyManager_checkStarts')
        taskMgr.doMethodLater(15, self.__checkPartyStarts, 'GlobalPartyManager_checkStarts')
        return
        
    def queryParty(self, hostId):
        # An AI is wondering if the host has a party. We'll tell em!
        if hostId in self.host2Party:
            # Yep, he has a party.
            party = self.host2Party[hostId]
            self.sendToAI('partyInfoOfHostResponseUdToAi', [self._formatParty(party), party.get('inviteeIds', [])])
            return
        print 'query failed, av %s isnt hosting anything' % hostId
