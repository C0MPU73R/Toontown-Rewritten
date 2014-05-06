from direct.distributed.AstronInternalRepository import AstronInternalRepository
from otp.distributed.OtpDoGlobals import *
from direct.distributed.PyDatagram import PyDatagram
from direct.distributed.MsgTypes import *
from panda3d.core import *
import pymongo, urlparse

# HACKFIX TODO: Have the dev server's panda3d installation update properly?
# Currently, it doesn't have the new message types required for the
# DBSS_OBJECT_GET_ACTIVATED MsgType, so for now we will hard-code it in.

mongodb_url = ConfigVariableString('mongodb-url', 'mongodb://localhost',
                                   'Specifies the URL of the MongoDB server that'
                                   'stores all gameserver data.')

class ToontownInternalRepository(AstronInternalRepository):
    GameGlobalsId = OTP_DO_ID_TOONTOWN
    dbId = 4003
    
    def __init__(self, baseChannel, serverId=None, dcFileNames = None,
                 dcSuffix='AI', connectMethod=None, threadedNet=None):
        AstronInternalRepository.__init__(self, baseChannel, serverId, dcFileNames,
                                 dcSuffix, connectMethod, threadedNet)
        self._callbacks = {}

        mongourl = mongodb_url.getValue()
        db = (urlparse.urlparse(mongourl).path or '/test')[1:]
        self.mongo = pymongo.Connection(mongourl)
        self.mongodb = self.mongo[db]
    
    def getAvatarIdFromSender(self):
        return self.getMsgSender() & 0xFFFFFFFF

    def getAccountIdFromSender(self):
        return (self.getMsgSender()>>32) & 0xFFFFFFFF

    def _isValidPlayerLocation(self, parentId, zoneId):
        if zoneId < 1000 and zoneId != 1:
            return False

        return True
        
    def getActivated(self, doId, callback):
        ctx = self.contextAllocator.allocate()
        self._callbacks[ctx] = callback
        
        dg = PyDatagram()
        dg.addServerHeader(doId, self.ourChannel, 2207)#DBSS_OBJECT_GET_ACTIVATED)
        dg.addUint32(ctx)
        dg.addUint32(doId)
        self.send(dg)
        
    def handleGetActivatedResp(self, di):
        ctx = di.getUint32()
        doId = di.getUint32()
        activated = di.getUint8()
        
        if ctx not in self._callbacks:
            self.notify.warning('Received unexpected DBSS_OBJECT_GET_ACTIVATED_RESP (ctx: %d)' %ctx)
            return
            
        try:
            if self._callbacks[ctx]:
                self._callbacks[ctx](doId, activated)
                return
        finally:
            del self._callbacks[ctx]
            self.contextAllocator.free(ctx)
        
    def handleDatagram(self, di):
        msgType = self.getMsgType()
        if msgType == 2208:#DBSS_OBJECT_GET_ACTIVATED_RESP:
            self.handleGetActivatedResp(di)
        else:
            AstronInternalRepository.handleDatagram(self, di)
