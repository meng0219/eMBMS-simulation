import math
import random as rdm
import simParams as p


class UE:
    def __init__(self, Id, srv, site, enter_time):
        self.Id = Id
        self.srv = srv
        self.site = site
        self.speed = rdm.uniform(0.0125, 0.0166666667)
        self.TbsIndex = int(math.log(self.site, 10)/0.037037) # the Tbs is base on lognormal distribution
        self.srvQ = 7  # the highest streaming quality (for RT)
        self.pktList = []
        self.buffLen = 0
        self.alpha = -1 * (math.log(p.Tolerate[srv]) / p.DelayThr[srv])
        self.lastThr = 0
        self.throughput = 0
        self.throughput_uc = 0
        self.throughput_eMBMS = 0
        self.enter_time = enter_time
        self.during_time = p.simTime-1
        self.eMBMS_during_time = 0
        self.join_eMBMS_time = 0
        self.DRC = p.pktSizeTable[self.srvQ]*100
        self.avgDRC = 1
        self.numPkt = 0
        self.numInvPkt = 0

class packet:
    def __init__(self, Id, size, DelayThr):
        self.Id = Id
        self.size = size
        self.DelayThr = DelayThr
        self.delay = 0