from pandac.PandaModules import *
from otp.nametag.NametagConstants import *
from direct.distributed.ClockDelta import *
from direct.interval.IntervalGlobal import *
from direct.distributed.DistributedObject import DistributedObject
from direct.fsm.FSM import FSM
from direct.actor import Actor
from direct.task import Task
from toontown.toon import NPCToons
from toontown.suit import DistributedSuitBase, SuitDNA
from toontown.toonbase import ToontownGlobals
from toontown.battle import BattleProps
from otp.margins.WhisperPopup import *
import ElectionGlobals
from direct.directnotify import DirectNotifyGlobal
from random import choice

# Interactive Flippy
from otp.speedchat import SpeedChatGlobals

class DistributedElectionEvent(DistributedObject, FSM):
    notify = DirectNotifyGlobal.directNotify.newCategory("DistributedElectionEvent")
    
    def __init__(self, cr):
        DistributedObject.__init__(self, cr)
        FSM.__init__(self, 'ElectionFSM')
        self.cr.election = self
        self.interactiveOn = False

        self.showFloor = NodePath('ShowFloor')
        self.showFloor.setPos(80, 0, 4)

        #Stage
        stage = loader.loadModel('phase_4/models/events/election_stage')
        stage.reparentTo(self.showFloor)
        stage.setHpr(270, 0, 0)
        stage.setScale(2.0, 1.8, 1.5)
        podium = loader.loadModel('phase_4/models/events/election_stagePodium')
        podium.reparentTo(self.showFloor)
        podium.setPosHpr(-6, 0, 3, 270, -2, 5)
        podium.setScale(0.65)
        counterLeft = loader.loadModel('phase_4/models/events/election_counterLeft')
        counterLeft.reparentTo(self.showFloor)
        counterLeft.setPosHpr(13.5, 10, 2.95, 270, 0, 0)
        counterLeft.setScale(2.0)
        counterRight = loader.loadModel('phase_4/models/events/election_counterRight')
        counterRight.reparentTo(self.showFloor)
        counterRight.setPosHpr(13.5, -10, 3.25, 270, 0, 0)
        counterRight.setScale(2.0)
        rope = loader.loadModel('phase_4/models/events/election_rope')
        rope.reparentTo(self.showFloor)
        rope.setPosHpr(-34, 18, 0.46, 270, 0, 0)
        rope.setScale(2, 2, 2)
        rope.find('**/collide').setPosHprScale(0.31, 1.10, 0.00, 0.00, 0.00, 0.00, 0.89, 1.00, 1.25)

        #Campaign stands
        self.flippyStand = Actor.Actor('phase_4/models/events/election_flippyStand-mod', {'idle': 'phase_4/models/events/election_flippyStand-idle'})
        self.flippyStand.reparentTo(self.showFloor)
        self.flippyStand.setPosHprScale(-43.6, -24.5, 0.01, 200, 0, 0, 0.55, 0.55, 0.55)
        self.flippyStand.exposeJoint(None,"modelRoot", "LInnerShoulder")
        flippyTable = self.flippyStand.find('**/LInnerShoulder')
        self.flippyStand.exposeJoint(None,"modelRoot", "Box_Joint")
        wheelbarrowJoint = self.flippyStand.find('**/Box_Joint').attachNewNode('Pie_Joint')
        wheelbarrow = self.flippyStand.find('**/Box')
        wheelbarrow.setPosHprScale(-2.39, 0.00, 1.77, 0.00, 0.00, 6.00, 1.14, 1.54, 0.93)

        self.slappyStand = Actor.Actor('phase_4/models/events/election_slappyStand-mod', {'idle': 'phase_4/models/events/election_slappyStand-idle'})
        self.slappyStand.reparentTo(self.showFloor)
        self.slappyStand.setPosHprScale(-62.45, 14.39, 0.01, 325, 0, 0, 0.55, 0.55, 0.55)

        #Let's give FlippyStand a bunch of pies.
        # Pies on/around the stand.
        pie = loader.loadModel('phase_3.5/models/props/tart')
        pieS = pie.copyTo(flippyTable)
        pieS.setPosHprScale(-2.61, -0.37, -1.99, 355.60, 90.00, 4.09, 1.6, 1.6, 1.6)
        # Pies in the wheelbarrow.
        for pieSettings in ElectionGlobals.FlippyWheelbarrowPies:
            pieModel = pie.copyTo(wheelbarrowJoint)
            pieModel.setPosHprScale(*pieSettings)
        # This currently causes placement problems with the animation
        wheelbarrowJoint.setPosHprScale(3.94, 0.00, 1.06, 270.00, 344.74, 0.00, 1.43, 1.12, 1.0)
        self.restockSfx = loader.loadSfx('phase_9/audio/sfx/CHQ_SOS_pies_restock.ogg')
        self.splashSfx = loader.loadSfx('phase_9/audio/sfx/CHQ_FACT_paint_splash.ogg')
            

        # Find FlippyStand's collision to give people pies.
        # The new animated model doesn't have any collisions, so this needs to be replaced with a collision box. Harv did it once, just need to look back in the commit history.
        cs = CollisionBox(Point3(7, 0, 0), 12, 5, 18)
        self.pieCollision = self.flippyStand.attachNewNode(CollisionNode('wheelbarrow_collision'))
        self.pieCollision.node().addSolid(cs)
        self.accept('enter' + self.pieCollision.node().getName(), self.handleWheelbarrowCollisionSphereEnter)
        
        csSlappy = CollisionBox(Point3(-4.2, 0, 0), 9.5, 5.5, 18)
        self.goopCollision = self.slappyStand.attachNewNode(CollisionNode('goop_collision'))
        self.goopCollision.node().addSolid(csSlappy)

        # Hi NPCs!
        self.alec = NPCToons.createLocalNPC(2022)
        self.slappy = NPCToons.createLocalNPC(2021)
        self.flippy = NPCToons.createLocalNPC(2001)
        # Sometimes they all need to do the same thing.
        self.characters = [self.alec, self.slappy, self.flippy]
        # We need some Minor Characters too
        self.surlee = NPCToons.createLocalNPC(20191)
        # We want Surlee to use Prepostera's animation since he is the star, but Surlee is a different size.
        # Since Disney didn't include Prepostera's animation for Surlee's size, we have to make him small an painstakingly scale him
        self.surlee.useLOD(1000)
        self.surlee.find('**/250').remove()
        self.surlee.find('**/500').remove()
        surleeLegs = self.surlee.find('**/legs')
        surleeLegs.setScale(1, 1, 1.5)
        surleeLegs.setZ(-0.26)
        self.surlee.find('**/__Actor_torso').setZ(1.1)
        self.surlee.find('**/torso-top').setPosHprScale(0.00, 0.00, -0.45, 0.00, 0.00, 0.00, 1.00, 0.98, 1.96)
        self.surlee.find('**/__Actor_head').setZ(0.7)
        self.surlee.find('**/neck').setZ(0.7)
        self.surlee.find('**/sleeves').setZ(0.7)
        self.surlee.find('**/arms').setZ(0.7)
        self.surlee.find('**/hands').setZ(0.7)
        self.surlee.setPos(-22, 7, 0)
        self.surlee.setH(110)
        rHand = self.surlee.find('**/def_joint_right_hold')
        clipBoard = loader.loadModel('phase_4/models/props/tt_m_prp_acs_clipboard')
        placeholder = rHand.attachNewNode('ClipBoard')
        clipBoard.instanceTo(placeholder)
        placeholder.setH(180)
        placeholder.setScale(render, 1.0)
        placeholder.setPos(0.5, 0.6, -0.1)
        placeholder.setScale(1.3)
        # And now for the real Surlee
        self.surleeR = NPCToons.createLocalNPC(2019)
        self.surleeR.useLOD(1000)
        self.surleeR.setPos(-22, 7, 0)
        self.surleeR.setH(110)
        self.surleeR.head = self.surleeR.find('**/__Actor_head')
        self.surleeR.initializeBodyCollisions('toon')
        # Now the same for Prepostera
        self.prepostera = NPCToons.createLocalNPC(20201)
        self.prepostera.useLOD(1000)
        self.prepostera.find('**/250').remove()
        self.prepostera.find('**/500').remove()
        preposteraLegs = self.prepostera.find('**/legs')
        preposteraLegs.setScale(1, 1, 0.5)
        self.prepostera.find('**/__Actor_torso').setZ(-0.9)
        self.prepostera.find('**/torso-top').setPosHprScale(0.00, 0.00, 0.2, 0.00, 0.00, 0.00, 1.00, 0.98, 0.5)
        self.prepostera.find('**/__Actor_head').setZ(-0.7)
        self.prepostera.find('**/neck').setZ(-0.7)
        self.prepostera.find('**/sleeves').setZ(-0.7)
        preposteraArms = self.prepostera.find('**/arms')
        preposteraArms.setZ(-0.4)
        preposteraArms.setScale(1, 1, 0.8)
        preposteraHands = self.prepostera.find('**/hands')
        preposteraHands.setZ(-0.4)
        preposteraHands.setScale(1, 1, 0.8)
        self.prepostera.setPos(-70, 10, 0.0)
        self.prepostera.setH(-50)
        self.prepostera.initializeBodyCollisions('toon')
        rHand = self.prepostera.find('**/def_joint_right_hold')
        clipBoard = loader.loadModel('phase_4/models/props/tt_m_prp_acs_clipboard')
        placeholder = rHand.attachNewNode('ClipBoard')
        clipBoard.instanceTo(placeholder)
        placeholder.setH(180)
        placeholder.setScale(render, 1.0)
        placeholder.setPos(0, -0.3, 0.3)
        # And his buddies
        self.dimm = NPCToons.createLocalNPC(2018)
        self.dimm.useLOD(1000)
        self.dimm.find('**/250').remove()
        self.dimm.find('**/500').remove()
        self.dimm.setPos(-72.36, 10.46, 0.00)
        self.dimm.setH(-50)
        self.dimm.initializeBodyCollisions('toon')
        rHand1 = self.dimm.find('**/def_joint_right_hold')
        sillyReader = loader.loadModel('phase_4/models/props/tt_m_prp_acs_sillyReader')
        placeholder1 = rHand1.attachNewNode('SillyReader')
        sillyReader.instanceTo(placeholder1)
        placeholder1.setH(180)
        placeholder1.setScale(render, 1.0)
        placeholder1.setPos(0, 0, 0.1)

        self.surlee.reparentTo(self.showFloor)
        self.surleeR.reparentTo(self.showFloor)
        self.prepostera.reparentTo(self.showFloor)
        self.dimm.reparentTo(self.showFloor)
        self.surlee.hide()
        self.surleeR.hide()
        self.prepostera.hide()
        self.dimm.hide()

        self.suit = DistributedSuitBase.DistributedSuitBase(cr)
        suitDNA = SuitDNA.SuitDNA()
        suitDNA.newSuit('ym')
        self.suit.setDNA(suitDNA)
        self.suit.setDisplayName('Yesman\nBossbot\nLevel 3')
        self.suit.setPickable(0)

        self.flippyStand.loop('idle')
        self.slappyStand.loop('idle')

    def handleWheelbarrowCollisionSphereEnter(self, collEntry):
        if base.localAvatar.numPies >= 0 and base.localAvatar.numPies < 20:
            # We need to give them more pies! Send a request to the server.
            self.sendUpdate('wheelbarrowAvatarEnter', [])
            self.restockSfx.play()
            
    def handleSlappyCollisionSphereEnter(self, collEntry):
        if base.localAvatar.savedCheesyEffect != 15:
            # We need to give them more pies! Send a request to the server.
            self.sendUpdate('slappyAvatarEnter', [])
            self.splashSfx.play()

    def startInteractiveFlippy(self):
        self.flippy.reparentTo(self.showFloor)
        self.flippy.setPosHpr(-40.6, -18.5, 0.01, 20, 0, 0)
        self.flippy.initializeBodyCollisions('toon')
        self.interactiveOn = True
        self.flippyPhrase = None
        self.accept(SpeedChatGlobals.SCStaticTextMsgEvent, self.phraseSaidToFlippy)

    def stopInteractiveFlippy(self):
        self.ignore(SpeedChatGlobals.SCStaticTextMsgEvent)
        self.interactiveOn = False

    def phraseSaidToFlippy(self, phraseId):
        # Check distance...
        if self.flippy.nametag.getChat() != '':
            # Flippy is already responding to someone, ignore them.
            return
        if Vec3(base.localAvatar.getPos(self.flippy)).length() > 10:
            # Too far away.
            return
        # Check if the phrase is something that Flippy should respond to.
        for phraseIdList in ElectionGlobals.FlippyPhraseIds:
            if phraseId in phraseIdList:
                self.sendUpdate('phraseSaidToFlippy', [phraseId])
                break
    
    def flippySpeech(self, avId, phraseId):
        av = self.cr.doId2do.get(avId)
        if not av:
            # An avatar we don't know about interacted with Flippy... odd.
            self.notify.warning("Received unknown avId in flippySpeech from the AI.")
            return
        if not self.interactiveOn:
            self.notify.warning("Received flippySpeech from AI while Interactive Flippy is disabled on our client.")
            return
        if self.flippy.nametag.getChat() != '':
            # Flippy is alredy responding to someone, ignore.
            return
        if phraseId == 1: # Someone requested pies... Lets pray that we don't need phraseId 1...
            taskMgr.doMethodLater(ElectionGlobals.FlippyDelayResponse, self.flippy.setChatAbsolute, 'interactive-flippy-chat-task',
                                  extraArgs = [choice(ElectionGlobals.FlippyGibPies).replace("__NAME__", av.getName()), CFSpeech | CFTimeout])
            return
        if len(ElectionGlobals.FlippyPhraseIds) != len(ElectionGlobals.FlippyPhrases):
            # There is a mismatch in the number of phrases and the phraseIds we're looking out for...
            # If this ever occurs on the live client, then clearly this wasn't tested and someone needs a slap.
            raise Exception("There is a mismatch in the number of phraseIds and the number of phrases for Flippy Interactive!")
            return
        for index, phraseIdList in enumerate(ElectionGlobals.FlippyPhraseIds):
            for pid in phraseIdList:
                if pid == phraseId:
                    # This could potentially lead to a crash if there is a mismatch in the number (indexes) of
                    # phraseIdLists and phrases. Could possibly use a python dict ( { key : value } ) to
                    # prevent this...
                    taskMgr.doMethodLater(ElectionGlobals.FlippyDelayResponse, self.flippy.setChatAbsolute, 'interactive-flippy-chat-task',
                                          extraArgs = [ElectionGlobals.FlippyPhrases[index].replace("__NAME__", av.getName()), CFSpeech | CFTimeout])
                    return 

    def delete(self):
        self.demand('Off', 0.)
        
        # Clean up everything...
        self.showFloor.removeNode()
        self.stopInteractiveFlippy()
        self.ignore('enter' + self.pieCollision.node().getName())
        

        DistributedObject.delete(self)
    
    def setState(self, state, timestamp):
        self.request(state, globalClockDelta.localElapsedTime(timestamp))

    def enterOff(self, offset):
        base.cr.parentMgr.unregisterParent(ToontownGlobals.SPSlappysBalloon)
        self.showFloor.reparentTo(hidden)

    def exitOff(self):
        self.showFloor.reparentTo(render)


    def enterIdle(self, offset):
        # Spawn Surlee and Friends
        self.surlee.show()
        self.surlee.addActive()
        self.surlee.startBlink()
        self.surlee.loop('scientistEmcee')
        self.prepostera.show()
        self.prepostera.addActive()
        self.prepostera.startBlink()
        self.prepostera.loop('scientistWork')
        self.dimm.show()
        self.dimm.addActive()
        self.dimm.startBlink()
        self.dimm.loop('scientistWork')
        self.surleeIntroInterval = Sequence(
            Wait(10),
            Func(self.surlee.setChatAbsolute, 'Oh, uh, Hello! I suppose it\'s election time already?', CFSpeech|CFTimeout),
            Wait(5),
            Func(self.surlee.setChatAbsolute, 'We\'re just minutes away from the most important event in the history of our town.', CFSpeech|CFTimeout),
            Wait(8),
            Func(self.surlee.setChatAbsolute, 'Alec Tinn is inside Toon Hall right now with the two candidates preparing for the announcement.', CFSpeech|CFTimeout),
            Wait(8),
            Func(self.surlee.setChatAbsolute, 'When the clock strikes two we\'ll see them march through those doors and onto the stage. Are you toons ready?', CFSpeech|CFTimeout),
            Wait(8),
            Func(self.surlee.setChatAbsolute, 'I must say, surprisingly, the silliness around here couldn\'t be higher at this time.', CFSpeech|CFTimeout), 
            Wait(8),
            Func(self.surlee.setChatAbsolute, 'My fellow scientists of silliness, Professor Prepostera and Doctor Dimm, are over there tracking the amount of silliness being taken in from the campaign stands.', CFSpeech|CFTimeout),
            Wait(8),
            Func(self.surlee.setChatAbsolute, 'At least, I think they are. You never know with those goofs.', CFSpeech|CFTimeout),
            Wait(8),
            Func(self.surlee.setChatAbsolute, 'I hope you haven\'t been standing here long, because I\'m going to have to start repeating myself soon.', CFSpeech|CFTimeout),
        )
        self.surleeIntroInterval.loop()
        self.surleeIntroInterval.setT(offset)

    def exitIdle(self):
        self.surleeIntroInterval.finish()

    def enterEvent(self, offset):
        base.cr.playGame.hood.loader.music.stop()

    def enterPreShow(self, offset):
        # And now for the Pre-election sequence
        self.surleeLeaveInterval = Sequence(
            Func(base.localAvatar.setSystemMessage, 0, 'TOON HQ: We just got word from Alec Tinn that the Toon Council Presidential Elections will be starting any second.', whisperType=WTSystem),
            Wait(5),
            Func(base.localAvatar.setSystemMessage, 0, 'TOON HQ: Please silence your Shtickerbooks and keep any Oinks, Squeaks, and Owooos to a minimum.', whisperType=WhisperPopup.WTSystem),
            Wait(2),
            # Let's do a quick swap for the real Surlee, now that his animation is done
            Parallel(Func(self.surlee.removeActive), Func(self.surlee.hide), Func(self.surleeR.show), Func(self.surleeR.addActive), Func(self.surleeR.startBlink)),
            Wait(3),
            Func(self.surleeR.setChatAbsolute, 'Hrm, you heard the HQ. I better get out of the way before Alec arrives.', CFSpeech|CFTimeout),
            Wait(1),
            Parallel(Func(self.surleeR.loop, 'walk'), self.surleeR.posHprInterval(4, (-20, 0, 0), (190, 0, 0)), Func(base.cr.cameraManager.tvFlyIn.start)),
            # TV Flies down behind Surlee
            Parallel(Func(self.surleeR.loop, 'neutral'), self.surleeR.head.hprInterval(1, (75, 30, 0), blendType='easeInOut')),
            Wait(1),
            Func(self.surleeR.setChatAbsolute, 'Oh, do you like it? Designed it myself. Don\'t worry about getting close to the ropes; the TV will be showing a live feed for everyone to get a great view.', CFSpeech|CFTimeout),
            Func(self.surleeR.loop, 'walk'),
            Parallel(self.surleeR.hprInterval(1, (80, 0, 0)), self.surleeR.head.hprInterval(1, (0, 0, 0), blendType='easeInOut')),
            Func(self.surleeR.loop, 'neutral'),
            Wait(8),
            Func(self.surleeR.setChatAbsolute, 'I know you all will keep trying to jump on top of each other for a better view anyway, though, so try not to hurt anyone.', CFSpeech|CFTimeout),
            Wait(3),
            Func(self.surleeR.loop, 'run'),
            self.surleeR.posHprInterval(2, (-17, -7, 0), (180, 0, 0)),
            self.surleeR.posHprInterval(1.5, (-15, -15, 0), (190, 0, 0)),
            Func(self.surleeR.loop, 'walk'),
            self.surleeR.posHprInterval(2, (-20, -18, 0), (90, 0, 0)),
            self.surleeR.posHprInterval(3.5, (-32, -19, 0), (35, 0, 0)),
            self.surleeR.posHprInterval(1, (-34, -17, 0), (0, 0, 0)),
            self.surleeR.posHprInterval(1.5, (-32, -15, 0), (-40, 0, 0)),
            Func(self.surleeR.loop, 'neutral')
        )
        self.surleeLeaveInterval.start()
        self.surleeLeaveInterval.setT(offset)

    def enterBegin(self, offset):
        # Oh boy, here come the candidates
        for character in self.characters:
            character.reparentTo(self.showFloor)
            character.setPosHpr(35, -0.3, 0, 90, 0, 0)
            character.useLOD(1000)
            character.addActive()
            character.startBlink()
        musicIntro = base.loadMusic(ElectionGlobals.IntroMusic)
        self.ignore('enter' + self.pieCollision.node().getName())
        self.alecHallInterval = Sequence(
            Parallel(Func(self.alec.loop, 'walk'), Func(base.playMusic, musicIntro, looping=0, volume=0.8)),
            self.alec.posInterval(3, (12.96, -0.38, 0)),
            self.alec.posInterval(2, (4.2, -0.25, 3.13)),
            self.alec.posInterval(2, (-4.5, -0.14, 3.13)),
            Func(self.alec.loop, 'neutral'),
        )
        self.slappyHallInterval = Sequence(
            Wait(1),
            Func(self.slappy.loop, 'walk'),
            self.slappy.posInterval(2.5, (12.96, -0.38, 0)),
            self.slappy.posHprInterval(2, (4.3, 2.72, 3.13), (70, 0, 0)),
            self.slappy.posHprInterval(1, (2.36, 5.18, 3.08), (40, 0, 0)),
            self.slappy.posHprInterval(1, (1, 9, 3.03), (90, 0, 0)),
            Func(self.slappy.loop, 'neutral'),
        )
        self.flippyHallInterval = Sequence(
            Wait(2),
            Func(self.flippy.loop, 'walk'),
            self.flippy.posInterval(3, (12.96, -0.38, 0)),
            self.flippy.posHprInterval(1, (3.3, -2.39, 3.13), (120, 0, 0)),
            self.flippy.posHprInterval(1, (2.49, -6.09, 3.17), (155, 0, 0)),
            self.flippy.posHprInterval(1, (2, -10, 3.23), (90, 0, 0)),
            Func(self.flippy.loop, 'neutral'),
        )
        self.alecHallInterval.start()
        self.alecHallInterval.setT(offset)
        self.slappyHallInterval.start()
        self.slappyHallInterval.setT(offset)
        self.flippyHallInterval.start()
        self.flippyHallInterval.setT(offset)

    def exitBegin(self):
        self.alecHallInterval.finish()
        self.slappyHallInterval.finish()
        self.flippyHallInterval.finish()

    def enterAlecSpeech(self, offset):
        # For some reason, the sound only plays on their first message. Can anyone look into that?
        self.alecSpeech = Sequence(
            Func(self.alec.setChatAbsolute, 'Hellooo Toontown~!', CFSpeech|CFTimeout),
            Wait(5),
            Func(self.alec.setChatAbsolute, 'As many of you know, I\'m your Hilarious Host and Eccentric Elector: Alec Tinn!', CFSpeech|CFTimeout),
            Wait(8.5),
            Func(self.alec.setChatAbsolute, 'And of course, we can\'t forget about our two toonerific toons who have been selected to fight for the Presidency...', CFSpeech|CFTimeout),
            Wait(9),
            Func(self.alec.setChatAbsolute, 'Slappy Quackintosh, and Flippy Doggenbottom!', CFSpeech|CFTimeout),
            Wait(6.5),
            Func(self.alec.setChatAbsolute, 'I must say, this turnout is absolutely, positivley, extra-tooneriffically, astounding!', CFSpeech|CFTimeout),
            Wait(6),
            Func(self.alec.setChatAbsolute, 'It\'s truly an honor to be here on this day, and I''m sure I speak for all of us when I thank you for coming.', CFSpeech|CFTimeout),
            Wait(8),
            Func(self.alec.setChatAbsolute, 'Now, the votes are almost ready to be tallied! Flippy, Slappy, do either of you have anything to say before the moment of truth?', CFSpeech|CFTimeout),
            Wait(10),
            Func(self.slappy.setChatAbsolute, 'The only thing I have to say, no matter who wins...', CFSpeech|CFTimeout),
            Wait(6.5),
            Func(self.slappy.setChatAbsolute, 'I know that Toontown is going to grow to be even more... "Toontastic" than ever before.', CFSpeech|CFTimeout),
            Wait(8),
            Func(self.slappy.setChatAbsolute, 'All of you are truer-than-truly the best!', CFSpeech|CFTimeout),
            Wait(10),
            Func(self.flippy.setChatAbsolute, 'Like Slappy said, I can''t even begin to thank all of you Toontastic toons for this.', CFSpeech|CFTimeout),
            Wait(8),
            Func(self.flippy.setChatAbsolute, 'Even after all of this terrific time together, I''m still speechless that I''m here today.', CFSpeech|CFTimeout),
            Wait(8),
            Func(self.flippy.setChatAbsolute, 'Here\'s to Toontown, Slappy, and all of you!', CFSpeech|CFTimeout),
            Wait(7),
            Func(self.alec.setChatAbsolute, 'Well said, the both of you!', CFSpeech|CFTimeout),
            Wait(5),
            Func(self.alec.setChatAbsolute, 'Ooh, I\'m just jittering with excitement. Are you toons ready to hear the winners?', CFSpeech|CFTimeout),
            Wait(10),
            Func(self.alec.setChatAbsolute, 'Hmm, I\'m not sure if you are. Let me ask again: Are you toons ready to hear the winners?!', CFSpeech|CFTimeout),
            Wait(8),
            Func(self.alec.setChatAbsolute, 'WOAH! Woah! No need to yell! I\'m right here, I get it. You guys want to hear them.', CFSpeech|CFTimeout),
            Wait(8),
            Func(self.alec.setChatAbsolute, 'So, without further ado...', CFSpeech|CFTimeout),
            Wait(4),
            Func(self.alec.setChatAbsolute, 'I will now pull the GRAND ELECTORAL LEVER!', CFSpeech|CFTimeout),
        )
        self.alecSpeech.start()
        self.alecSpeech.setT(offset)

    def exitAlecSpeech(self):
        self.alecSpeech.finish()

    def enterVoteBuildup(self, offset):
        musicAnnouncement = base.loadMusic(ElectionGlobals.AnnouncementMusic)
        self.buildupSequence = Sequence(
            Func(self.alec.setChatAbsolute, 'And the winner is...', CFSpeech|CFTimeout),
            Wait(4),
            Func(base.playMusic, musicAnnouncement, looping=0, volume=0.8),
            Wait(1),
            Func(self.alec.setChatAbsolute, 'SLAPPYYYY~ QUACKINTOSH!', CFSpeech|CFTimeout),
            Wait(2),
            ActorInterval(self.slappy, 'good-putt'),
            ActorInterval(self.slappy, 'happy-dance'),
            Func(self.slappy.loop, 'neutral'),
        )
        self.buildupSequence.start()
        self.buildupSequence.setT(offset)

    def enterWinnerAnnounce(self, offset):
        # Slappy won! Lets give him some victory time before his rude interruption.
        musicVictory = base.loadMusic(ElectionGlobals.VictoryMusic)
        self.victorySequence = Sequence(
            Func(base.playMusic, musicVictory, looping=0, volume=0.8),
            Wait(0.3),
            Func(self.slappy.setChatAbsolute, 'Holy smokes... I don\'t even know where to begin!', CFSpeech|CFTimeout),
            Wait(4),
            Func(self.slappy.setChatAbsolute, 'I know without any doubt that I hereby accept my duty as your President...', CFSpeech|CFTimeout),
            Wait(5),
            Func(self.slappy.setChatAbsolute, '...and will Presently Preside with full Presidential Priorities of this Presidentliness!', CFSpeech|CFTimeout),
        )
        self.victorySequence.setT(offset)
        self.victorySequence.start()

    def exitWinnerAnnounce(self):
        self.victorySequence.finish()

    def enterCogLanding(self, offset):
        musicSad = base.loadMusic(ElectionGlobals.SadMusic)
        sfxSad = loader.loadSfx('phase_5/audio/sfx/ENC_Lose.ogg')
        mtrack = self.suit.beginSupaFlyMove(Point3(65, 3.6, 4.0), 1, 'fromSky', walkAfterLanding=False)
        self.pieHold = Sequence(
            ActorInterval(self.flippy, 'throw', startFrame=32, endFrame=47),
            ActorInterval(self.flippy, 'throw', startFrame=46, endFrame=33),
        )
        self.pie = BattleProps.globalPropPool.getProp('creampie')
        self.cogSequence = Sequence(
            Parallel(Func(self.suit.reparentTo, render), Func(self.suit.addActive), Func(mtrack.start, offset)),
            Wait(3),
            Func(self.slappy.setChatAbsolute, 'I will ensure- Uhh...', CFSpeech|CFTimeout),
            Wait(2),
            Func(self.surleeR.sadEyes),
            Wait(3),
            Func(self.alec.setChatAbsolute, 'Wha- What is that...?', CFSpeech|CFTimeout),
            Wait(5),
            Func(self.slappy.setChatAbsolute, 'Err... Hey there, fella!', CFSpeech|CFTimeout),
            Func(self.slappy.loop, 'walk'),
            self.slappy.posHprInterval(1, (-4, 8.5, 3.03), (110, 0, 0)),
            Func(self.slappy.play, 'jump'),
            Wait(0.45),
            self.slappy.posInterval(0.2, (-7.5, 8.3, 3.5)),
            self.slappy.posHprInterval(0.4, (-13, 8, 0), (125, 0, 0)),
            Wait(0.8),
            Func(self.slappy.loop, 'neutral'),
            Wait(0.5),
            Func(self.slappy.setChatAbsolute, 'My name is Slappy, the newly elected President of the Toon Council in this Toonerrific Town.', CFSpeech|CFTimeout),
            Wait(5),
            Func(self.suit.setChatAbsolute, 'President, you say? Just the Toon I need to speak with.', CFSpeech|CFTimeout),
            Wait(5),
            Func(self.slappy.setChatAbsolute, "Boy, that's some propeller you have there! You know, it looks a lot like the one on that TV.", CFSpeech|CFTimeout),
            Wait(5),
            Func(self.suit.setChatAbsolute, 'Yes. Now as I began to-', CFSpeech|CFTimeout),
            Wait(1),
            Func(self.slappy.setChatAbsolute, "Ooh, and the suit too. Where did you come from, anyway? It can't be Loony Labs, they're off today.", CFSpeech|CFTimeout),
            Wait(5),
            Func(self.suit.setChatAbsolute, 'See here, Toon. I am-', CFSpeech|CFTimeout),
            Wait(1),
            Func(self.slappy.setChatAbsolute, "No, don't tell me. Let me guess. Errrr... Montana. Final answer. No, no, nevermind. They wouldn't have that fancy of a suit there. Hrmm...", CFSpeech|CFTimeout),
            Wait(1),
            ActorInterval(self.slappy, 'think', startFrame=0, endFrame=46),
            ActorInterval(self.slappy, 'think', startFrame=46, endFrame=0),
            Func(self.slappy.loop, 'neutral'),
            Wait(1),
            Func(self.suit.setChatAbsolute, 'STOP!', CFSpeech|CFTimeout),
            Wait(4),
            Func(self.suit.setChatAbsolute, 'I like your lingo, Toon. You know how to schmooze.', CFSpeech|CFTimeout),
            Wait(6),
            Func(self.suit.setChatAbsolute, 'However, you seem to need a smear of Positive Reinforcement.', CFSpeech|CFTimeout),
            Wait(5),
            Func(self.slappy.play, 'lose'),
            Wait(2),
            Func(base.playSfx, sfxSad, volume=0.6),
            Wait(1.8),
            Func(base.playMusic, musicSad, looping=0),
            Wait(0.5),
            Func(self.flippy.setChatAbsolute, "Slappy, NO!", CFSpeech|CFTimeout),
            Wait(0.5),
            Func(self.alec.setChatAbsolute, "Oh my goodness- he...", CFSpeech|CFTimeout),
            self.slappy.scaleInterval(1.5, VBase3(0.01, 0.01, 0.01), blendType='easeInOut'),
            Wait(2),
            Parallel(Func(self.alec.setChatAbsolute, "No. Nonono, no. This isn't happening.", CFSpeech|CFTimeout), Func(self.alec.loop, 'walk')),
            Parallel(self.alec.posInterval(2, (-1.5, -0.14, 3.13))),
            Func(self.alec.loop, 'neutral'),
            Parallel(Func(self.flippy.setChatAbsolute, "What have you done?!", CFSpeech|CFTimeout), Func(self.flippy.loop, 'run')),
            self.flippy.posHprInterval(0.5, (-4.2, -9.5, 3.23), (70, 0, 0)),
            Wait(0.45),
            Func(self.flippy.play, 'jump'),
            self.flippy.posInterval(0.2, (-7.5, -9.2, 3.5)),
            self.flippy.posHprInterval(0.4, (-14, -9, 0), (50, 0, 0)),
            Wait(0.2),
            Func(self.flippy.loop, 'run'),
            Func(self.suit.loop, 'walk'),
            Parallel(self.suit.hprInterval(1, (180, 0, 0)), self.flippy.posHprInterval(1, (-15, -1, 0), (0, 0, 0))),
            Func(self.suit.loop, 'neutral'),
            Parallel(Func(self.flippy.setChatAbsolute, "Where did you send him?! Where is he?!", CFSpeech|CFTimeout), Func(self.flippy.loop, 'neutral')),
            Wait(2.5),
            Func(self.alec.setChatAbsolute, "Flippy, NO! Get away from it!", CFSpeech|CFTimeout),
            Wait(6),
            Func(self.flippy.setChatAbsolute, "What... What are you?", CFSpeech|CFTimeout),
            Wait(4),
            Func(self.suit.setChatAbsolute, 'I don\'t like your tone. Perhaps you need a drop of Positive Reinforcement as well.', CFSpeech|CFTimeout),
            Wait(3),
            Parallel(Func(self.flippy.setChatAbsolute, "No.. No, get away. I don't need your help.", CFSpeech|CFTimeout), ActorInterval(self.flippy, 'walk', loop=1, playRate=-1, duration=3), self.flippy.posInterval(3, (-15, -7, 0))),
            Func(self.flippy.loop, 'neutral'),
            Wait(1.5),
            Func(self.suit.loop, 'walk'),
            Parallel(Func(self.suit.setChatAbsolute, 'Let me confirm our meeting to discuss this. I won\'t take no for an answer.', CFSpeech|CFTimeout), self.suit.posInterval(2, (65, -1, 4.0))),
            Func(self.suit.loop, 'neutral'),
            Parallel(Func(self.flippy.setChatAbsolute, "Stop it, this isn't fun!", CFSpeech|CFTimeout), ActorInterval(self.flippy, 'walk', loop=1, playRate=-1, duration=3), self.flippy.posInterval(3, (-15, -12, 0))),
            Func(self.flippy.loop, 'neutral'),
            Func(self.suit.setChatAbsolute, 'Fun cannot exist without order.', CFSpeech|CFTimeout),
            Wait(2),
            Parallel(ActorInterval(self.flippy, 'throw', startFrame=0, endFrame=46), Func(self.flippy.setChatAbsolute, "I'm warning you, stay back. Please.", CFSpeech|CFTimeout), Func(self.pie.reparentTo, self.flippy.rightHand)),
            Wait(1),
            Func(self.suit.setChatAbsolute, 'Don\'t worry, I haven\'t been wrong yet.', CFSpeech|CFTimeout),
            Wait(1.5),
            Parallel(Sequence(ActorInterval(self.flippy, 'throw', startFrame=47, endFrame=91), Func(self.flippy.loop, 'neutral')), Func(self.flippy.setChatAbsolute, "Stay AWAY from me!", CFSpeech|CFTimeout), Func(self.surleeR.normalEyes), Sequence(Wait(0.8), Func(self.pie.wrtReparentTo, render), Parallel(ProjectileInterval(self.pie, endPos=Point3(65, 3.6, 6.0), duration=0.7)))),
            Parallel(Func(self.suit.hide), Func(self.suit.removeActive), Func(self.setSuitDamage, 36), Func(self.pie.removeNode)) 
        )
        self.cogSequence.setT(offset)
        self.cogSequence.start()

    def exitCogLanding(self):
        self.cogSequence.finish()
        del self.suit

    def enterInvasion(self, offset):
        self.accept('enter' + self.pieCollision.node().getName(), self.handleWheelbarrowCollisionSphereEnter)
        self.surleeIntroInterval = Sequence(
            Func(self.surleeR.loop, 'walk'),
            Func(self.surleeR.setChatAbsolute, 'Everyone, listen. There\'s no time to explain!', CFSpeech|CFTimeout),
            self.surleeR.posHprInterval(1, (-32, -15, 0), (30, 0, 0)),
            Func(self.surleeR.loop, 'neutral'),
            Wait(5),
            Func(self.surleeR.setChatAbsolute, 'Grab the pies, they seem to be the weakness of these...', CFSpeech|CFTimeout),
            Wait(5),
            Func(self.surleeR.setChatAbsolute, '..."Cogs."', CFSpeech|CFTimeout),
            Wait(3),
            Func(self.surleeR.setChatAbsolute, 'Now take up arms, there\'s more on the way!', CFSpeech|CFTimeout),
            Wait(5),
            Func(self.surleeR.setChatAbsolute, 'Fight for our town. Fight for Slappy!', CFSpeech|CFTimeout),
        )
        self.surleeIntroInterval.start()
        self.surleeIntroInterval.setT(offset)
        
    def enterInvasion(self, offset):
        self.accept('enter' + self.pieCollision.node().getName(), self.handleWheelbarrowCollisionSphereEnter)
        self.surleeIntroInterval = Sequence(
            Func(self.surleeR.loop, 'walk'),
            Func(self.surleeR.setChatAbsolute, 'Everyone, listen. There\'s no time to explain!', CFSpeech|CFTimeout),
            self.surleeR.posHprInterval(1, (-32, -15, 0), (30, 0, 0)),
            Func(self.surleeR.loop, 'neutral'),
            Wait(5),
            Func(self.surleeR.setChatAbsolute, 'Grab the pies, they seem to be the weakness of these...', CFSpeech|CFTimeout),
            Wait(5),
            Func(self.surleeR.setChatAbsolute, '..."Cogs."', CFSpeech|CFTimeout),
            Wait(3),
            Func(self.surleeR.setChatAbsolute, 'Now take up arms, there\'s more on the way!', CFSpeech|CFTimeout),
            Wait(5),
            Func(self.surleeR.setChatAbsolute, 'Fight for our town. Fight for Slappy!', CFSpeech|CFTimeout),
        )
        self.surleeIntroInterval.start()
        self.surleeIntroInterval.setT(offset)

    def setSuitDamage(self, hp):
        self.sendUpdate('setSuitDamage', [hp])
