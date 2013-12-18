from toontown.dna.DNAParser import DNAVisGroup, DNALandmarkBuilding
from toontown.fishing.DistributedFishingPondAI import DistributedFishingPondAI
from toontown.safezone.DistributedFishingSpotAI import DistributedFishingSpotAI
from toontown.fishing.DistributedFishingTargetAI import DistributedFishingTargetAI
from toontown.fishing.DistributedPondBingoManagerAI import DistributedPondBingoManagerAI
from toontown.building.DistributedToonInteriorAI import DistributedToonInteriorAI
from toontown.building.DistributedHQInteriorAI import DistributedHQInteriorAI
from toontown.fishing import FishingTargetGlobals
from toontown.building import DoorTypes
from toontown.building.DistributedDoorAI import DistributedDoorAI
from toontown.toon import NPCToons
from toontown.hood import ZoneUtil

from toontown.dna.DNASpawnerAI import DNASpawnerAI

class StreetAI:
    """
    AI-side representation of everything in a single street.

    One subclass of this class exists for every neighborhood in the game.
    StreetAIs are responsible for spawning all SuitPlanners,ponds, and other
    street objects, etc.
    """
    
    def __init__(self, air, zoneId):
        self.air = air
        self.zoneId = zoneId
    
    def spawnObjects(self, filename):
        DNASpawnerAI().spawnObjects(filename, self.zoneId)
