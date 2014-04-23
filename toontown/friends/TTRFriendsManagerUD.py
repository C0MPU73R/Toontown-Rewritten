from direct.distributed.DistributedObjectGlobalUD import DistributedObjectGlobalUD
from direct.distributed.PyDatagram import PyDatagram
from direct.task import Task
from direct.directnotify.DirectNotifyGlobal import directNotify
from direct.fsm.FSM import FSM
import functools
from time import time
import cPickle

class GetToonDataFSM(FSM):
    """
    A quick implementation to fetch a toon's fields from the
    database and return it back to the TTRFMUD via a callback.
    """
    
    def __init__(self, mgr, requesterId, avId, callback):
        FSM.__init__(self, 'GetToonDataFSM')
        self.mgr = mgr
        self.requesterId = requesterId
        self.avId = avId
        self.callback = callback
        
    def start(self):
        self.demand('QueryDB')
        
    def enterQueryDB(self):
        self.mgr.air.dbInterface.queryObject(self.mgr.air.dbId, self.avId, self.__queryResponse)
        
    def __queryResponse(self, dclass, fields):
        if dclass != self.mgr.air.dclassesByName['DistributedToonUD']:
            self.demand('Failure', 'Invalid dclass for avId %s!' % self.avId)
            return
        self.fields = fields
        self.fields['ID'] = self.avId
        self.demand('Finished')
        
    def enterFinished(self):
        # We want to cache the basic information we got for GetFriendsListFSM.
        self.mgr.avBasicInfoCache[self.avId] = {
            'expire' : time() + simbase.config.GetInt('friend-detail-cache-expire', 3600),
            'toonInfo' : [self.avId, self.fields['setName'][0], self.fields['setDNAString'][0], self.fields['setPetId'][0]],
        }
        self.callback(success=True, requesterId=self.requesterId, fields=self.fields)
            
    def enterFailure(self, reason):
        self.mgr.notify.warning(reason)
        self.callback(success=False, requesterId=None, fields=None)
        
class UpdateToonFieldFSM(FSM):
    """
    A quick implementation to update a toon's fields in the
    database and return a callback to the TTRFMUD.
    """
    
    def __init__(self, mgr, requesterId, avId, callback):
        FSM.__init__(self, 'UpdateToonDataFSM')
        self.mgr = mgr
        self.requesterId = requesterId
        self.avId = avId
        self.callback = callback
        
    def start(self, field, value):
        self.field = field
        self.value = value
        self.demand('GetToonOnline')
        
    def enterGetToonOnline(self):
        self.mgr.air.getActivated(self.avId, self.__toonOnlineResp)
        
    def __toonOnlineResp(self, avId, activated):
        if self.state != 'GetToonOnline':
            self.demand('Failure', 'Received __toonOnlineResp while not in GetToonOnline state.')
            return
        self.online = activated
        self.demand('UpdateDB')
       
    def enterUpdateDB(self):
        if self.online:
            dg = self.mgr.air.dclassesByName['DistributedToonUD'].aiFormatUpdate(
                    self.field, self.avId, self.avId, self.mgr.air.ourChannel, [self.value]
                )
            self.mgr.air.send(dg)
        else:
            self.mgr.air.dbInterface.updateObject(
                self.mgr.air.dbId,
                self.avId,
                self.mgr.air.dclassesByName['DistributedToonUD'],
                { self.field : [self.value] }
            )
        self.demand('Finished')
        
    def enterFinished(self):
        self.callback(success=True, requesterId=self.requesterId, online=self.online)
    
    def enterFailure(self, reason):
        self.mgr.notify.warning(reason)
        self.callback(success=False)
        
class GetFriendsListFSM(FSM):
    """
    This is an FSM class to fetch all the friends on a toons list
    and return their name, dna and petId to the requester. Currently,
    this may have a huge performance impact on the TTRFMUD as it may
    have to search up to 200 friends fields from the database.
    
    This also checks the cache to check for any existing, non-expired
    data the TTRFMUD has about a toon.
    """
    
    def __init__(self, mgr, requesterId, callback):
        FSM.__init__(self, 'GetFriendsListFSM')
        self.mgr = mgr
        self.requesterId = requesterId
        self.callback = callback
        self.friendsDetails = []
        self.iterated = 0
        self.getFriendsFieldsFSMs = {}
        
    def start(self):
        self.demand('GetFriendsList')
        
    def enterGetFriendsList(self):
        self.mgr.air.dbInterface.queryObject(self.mgr.air.dbId, self.requesterId, self.__gotFriendsList)
        
    def __gotFriendsList(self, dclass, fields):
        if self.state != 'GetFriendsList':
            # We're not currently trying to get our friends list.
            self.demand('Failure', '__gotFriendsList called when looking for friends list, avId %d' % self.requesterId)
            return
        if dclass != self.mgr.air.dclassesByName['DistributedToonUD']:
            # We got an invalid class from the database, eww.
            self.demand('Failure', 'Invalid dclass for toonId %d' % self.requesterId)
            return
        self.friendsList = fields['setFriendsList'][0]
        self.demand('GetFriendsDetails')
       
    def enterGetFriendsDetails(self):
        for friendId, tf in self.friendsList:
            details = self.mgr.avBasicInfoCache.get(friendId)
            if details:
                # We have the toons details in cache.
                expire = details.get('expire')
                toonInfo = details.get('toonInfo')
                if expire and toonInfo:
                    if details.get('expire') > time():
                        # These details haven't expired, use 'em!
                        self.friendsDetails.append(toonInfo)
                        self.iterated += 1
                        self.__testFinished()
                        continue
                    else:
                        # It's expired, delete and continue.
                        del self.mgr.avBasicInfoCache[friendId]
            # We need to fetch their details
            fsm = GetToonDataFSM(self.mgr, self.requesterId, friendId, self.__gotAvatarInfo)
            fsm.start()
            self.getFriendsFieldsFSMs[friendId] = fsm
            
    def __gotAvatarInfo(self, success, requesterId, fields):
        # We no longer need the FSM!
        if fields['ID'] in self.getFriendsFieldsFSMs:
            del self.getFriendsFieldsFSMs[fields['ID']]
        if self.state != 'GetFriendsDetails':
            self.demand('Failure', '__gotAvatarInfo while not looking for friends details, avId=%d' % self.requesterId)
            return
        if requesterId != self.requesterId:
            self.demand('Failure', '__gotAvatarInfo response for wrong requester. wrongId=%d, rightId=%d' % (self.requesterId, requesterId))
            return
        self.iterated += 1
        self.friendsDetails.append([fields['ID'], fields['setName'][0], fields['setDNAString'][0], fields['setPetId'][0]])
        self.__testFinished()
        
    def __testFinished(self):
        if self.iterated >= len(self.friendsList) and len(self.getFriendsFieldsFSMs) == 0:
            # We've finished! We can now continue.
            self.demand('Finished')
            
    def enterFinished(self):
        self.callback(success=True, requesterId=self.requesterId, friendsDetails=self.friendsDetails)
            
    def enterFailure(self, reason):
        self.mgr.notify.warning(reason)
        self.callback(success=False, requesterId=self.requesterId, friendsDetails=None)

class TTRFriendsManagerUD(DistributedObjectGlobalUD):
    """
    The Toontown Rewritten Friends Manager UberDOG, or TTRFMUD for short.
    
    This object is responsible for all requests related to global friends, such as
    friends coming online, friends going offline, fetching a friends data etc.
    """
    
    notify = directNotify.newCategory('TTRFriendsManagerUD')
    
    def __init__(self, air):
        DistributedObjectGlobalUD.__init__(self, air)
        self.fsms = {}
        # TODO: Maybe get the AI to refresh the cache?
        self.avBasicInfoCache = {}
        self.tpRequests = {}
        
    def deleteFSM(self, requesterId):
        fsm = self.fsms.get(requesterId)
        if not fsm:
            # Just print debug incase we ever have issues.
            self.notify.debug('%d tried to delete non-existent FSM!' % requesterId)
            return
        if fsm.state != 'Off':
            fsm.demand('Off')
        del self.fsms[requesterId]
        
    def removeFriend(self, avId):
        requesterId = self.air.getAvatarIdFromSender()
        if requesterId in self.fsms:
            # Looks like the requester already has an FSM running. In the future we
            # may want to handle this, but for now just ignore it.
            return
        # We need to get the friends list of the requester.
        fsm = GetToonDataFSM(self, requesterId, requesterId, functools.partial(self.__rfGotToonFields, avId=avId))
        fsm.start()
        self.fsms[requesterId] = fsm
        
    def __rfGotToonFields(self, success, requesterId, fields, avId=None, final=False):
        # We no longer need the FSM.
        self.deleteFSM(requesterId)
        if not (success and avId):
            # Something went wrong... abort.
            return
        if fields['ID'] not in [requesterId, avId]:
            # Wtf? We got a db response for a toon that we didn't want
            # to edit! DEFCON 5!
            self.notify.warning('TTRFMUD.__rfGotToonFields received wrong toon fields from db, requesterId=%d' % requesterId)
            return
        friendsList = fields['setFriendsList'][0]
        searchId = requesterId if final else avId
        for index, friend in enumerate(friendsList):
            if friend[0] == searchId:
                del friendsList[index]
                break
        fsm = UpdateToonFieldFSM(self, requesterId, avId if final else requesterId, functools.partial(self.__removeFriendCallback, avId=avId, final=final))
        fsm.start('setFriendsList', friendsList)
        self.fsms[requesterId] = fsm
        
    def __removeFriendCallback(self, success, requesterId, online=False, avId=None, final=False):
        # We no longer need the FSM.
        self.deleteFSM(requesterId)
        if not (success and avId):
            # Something went wrong... abort.
            return
        if not final:
            # Toon was deleted from the friends list successfully! Now we need to modify
            # the other toons friends list...
            fsm = GetToonDataFSM(self, requesterId, avId, functools.partial(self.__rfGotToonFields, avId=avId, final=True))
            fsm.start()
            self.fsms[requesterId] = fsm
        else:
            # We're finished with everything!
            if online:
                # Lets notify their friend that they went bye bye!
                # Sad times for this toon. :(...
                dg = self.air.dclassesByName['DistributedToonUD'].aiFormatUpdate(
                    'friendsNotify', avId, avId, self.air.ourChannel, [requesterId, 1]
                )
                self.air.send(dg)
            # We are now finished, woo!
            
    def requestAvatarInfo(self, avIds):
        requesterId = self.air.getAvatarIdFromSender()
        if requesterId in self.fsms:
            # Looks like the requester already has an FSM running. In the future we
            # may want to handle this, but for now just ignore it.
            return
        if not avIds:
            # The list is empty. This is suspicious as the client shouldn't send
            # a blank list.
            self.notify.warning('Received blank list of avIds for requestAvatarInfo from avId %d' % requesterId)
            self.air.writeServerEvent('suspicious', requesterId, 'Sent a blank list of avIds for requestAvatarInfo in TTRFMUD')
            return
        fsm = GetToonDetailsFSM(self, requesterId, avIds[0], functools.partial(self.__avInfoCallback, avIds=avIds[1:]))
        fsm.start()
        self.fsms[requesterId] = fsm
        
    def __avInfoCallback(self, success, requesterId, fields, avIds):
        # We no longer need the FSM.
        self.deleteFSM(requesterId)
        if not success:
            # Something went wrong... abort.
            return
        self.sendUpdateToAvatarId(
            requesterId, 'friendInfo',
            [ fields['ID'], fields['setName'][0], fields['setDNAString'][0], fields['setPetId'][0] ]
        )
        if avIds:
            # We still have more to go... oh boy.
            fsm = GetToonDetailsFSM(self, requesterId, avIds[0], functools.partial(self.__avInfoCallback, avIds=avIds[1:]))
            fsm.start()
            self.fsms[requesterId] = fsm
            
    def requestFriendsList(self):
        requesterId = self.air.getAvatarIdFromSender()
        if requesterId in self.fsms:
            # Looks like the requester already has an FSM running. In the future we
            # may want to handle this, but for now just ignore it.
            return
        fsm = GetFriendsListFSM(self, requesterId, self.__gotFriendsList)
        fsm.start()
        self.fsms[requesterId] = fsm
        
    def __gotFriendsList(self, success, requesterId, friendsDetails):
        # We no longer need the FSM.
        self.deleteFSM(requesterId)
        if not success:
            # Something went wrong... abort.
            return
        # Ship it!
        self.sendUpdateToAvatarId(requesterId, 'friendList', [friendsDetails])
        
    def getAvatarDetails(self, friendId):
        requesterId = self.air.getAvatarIdFromSender()
        if requesterId in self.fsms:
            # Looks like the requester already has an FSM running. In the future we
            # may want to handle this, but for now just ignore it.
            return
        fsm = GetToonDataFSM(self, requesterId, friendId, self.__gotAvatarDetails)
        fsm.start()
        self.fsms[requesterId] = fsm
        
    def __gotAvatarDetails(self, success, requesterId, fields):
        # We no longer need the FSM.
        self.deleteFSM(requesterId)
        if not success:
            # Something went wrong... abort.
            return
        details = [
            ['setExperience' , fields['setExperience'][0]],
            ['setTrackAccess' , fields['setTrackAccess'][0]],
            ['setTrackBonusLevel' , fields['setTrackBonusLevel'][0]],
            ['setInventory' , fields['setInventory'][0]],
            ['setHp' , fields['setHp'][0]],
            ['setMaxHp' , fields['setMaxHp'][0]],
            ['setDefaultShard' , fields['setDefaultShard'][0]],
            ['setLastHood' , fields['setLastHood'][0]],
            ['setDNAString' , fields['setDNAString'][0]],
        ]
        self.sendUpdateToAvatarId(requesterId, 'friendDetails', [fields['ID'], cPickle.dumps(details)])
    
    def routeTeleportQuery(self, toId):
        fromId = self.air.getAvatarIdFromSender()
        self.tpRequests[fromId] = toId
        self.sendUpdateToAvatarId(toId, 'teleportQuery', [fromId])
        taskMgr.doMethodLater(5, self.giveUpTeleportQuery, 'tp-query-timeout-%d' % fromId, extraArgs=[fromId, toId])
        
    def giveUpTeleportQuery(self, fromId, toId):
        # The client didn't respond to the query within the set time,
        # So we will tell the query sender that the toon is unavailable.
        if fromId in self.tpRequests:
            del self.tpRequests[fromId]
            self.sendUpdateToAvatarId(fromId, 'teleportResponse', [toId, 0, 0, 0, 0])
            self.notify.warning('Teleport request that was sent by %d to %d timed out.' % (fromId, toId))
        
    def routeTeleportResponse(self, toId, available, shardId, hoodId, zoneId):
        # Here is where the toId and fromId swap (because we are now sending it back)
        fromId = self.air.getAvatarIdFromSender()
        
        # We got the query response, so no need to give up!
        if taskMgr.hasTaskNamed('tp-query-timeout-%d' % toId):
            taskMgr.remove('tp-query-timeout-%d' % toId)
            
        if toId not in self.tpRequests:
            return
        if self.tpRequests.get(toId) != fromId:
            self.air.writeServerEvent('suspicious', fromId, 'toon tried to send teleportResponse for a query that isn\'t theirs!')
            return
        self.sendUpdateToAvatarId(toId, 'teleportResponse', [fromId, available, shardId, hoodId, zoneId])
        del self.tpRequests[toId]
        
    def whisperSCTo(self, toId, msgIndex):
        fromId = self.air.getAvatarIdFromSender()
        self.sendUpdateToAvatarId(toId, 'setWhisperSCFrom', [fromId, msgIndex])
        
    def whisperSCCustomTo(self, toId, msgIndex):
        fromId = self.air.getAvatarIdFromSender()
        self.sendUpdateToAvatarId(toId, 'setWhisperSCCustomFrom', [fromId, msgIndex])
        
    def whisperSCEmoteTo(self, toId, msgIndex):
        fromId = self.air.getAvatarIdFromSender()
        self.sendUpdateToAvatarId(toId, 'setWhisperSCEmoteFrom', [fromId, msgIndex])
        
    def sendTalkWhisper(self, toId, message):
        fromId = self.air.getAvatarIdFromSender()
        self.sendUpdateToAvatarId(toId, 'receiveTalkWhisper', [fromId, message])
        self.air.writeServerEvent('whisper-said', fromId, toId, message)
        