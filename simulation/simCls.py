import math
import random as rdm
import parameter as p

class UE:
    def __init__(self, Id, srv):
        self.Id = Id
        self.srv = srv
        self.site = rdm.uniform(1, 10)
        self.speed = rdm.choice(p.speed)
        self.TbsIndex = int(math.log(self.site, 10)/0.037037) # the Tbs is base on lognormal distribution
        self.srvQ = 7  # the highest streaming quality (for RT)
        self.pktList = []
        self.buffLen = 0
        self.alpha = -1 * (math.log(p.Tolerate[srv]) / p.DelayThr[srv])
        self.throughput = 0
        self.DRC = p.TbsTable[1][self.TbsIndex]
        self.avgDRC = self.DRC
        self.numPkt = 0
        self.numInvPkt = 0

class packet:
    def __init__(self, Id, size, DelayThr):
        self.Id = Id
        self.size = size
        self.DelayThr = DelayThr
        self.delay = 0