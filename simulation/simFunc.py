import numpy as np
from simCls import *
import copy


def choseSrv(i):  # choosing a RT service for UE <0: NRT; others: RT>
    srv = 0
    j = rdm.uniform(0, 1)
    for rat in p.ratSrv:
        if rat > j:
            break
        else:
            j -= rat
            srv += 1
    p.listSuber[srv].append(i)
    if i != 0:
        p.RtUeList.append(i)
    return srv


def changeSite(ue):
    if ue.site > 9.998:  # the ue is close the upper bound of cell
        ue.speed = -1 * abs(ue.speed)  # the ue turn the direction of movement
    if ue.site < 1.0012:  # the ue is close the lower bou d of cell
        ue.speed = abs(ue.speed)  # the ue turn the direction of movement
    ue.site += ue.speed / (60 * 60 * 20)  # the site of ue changes each 50ms
    ue.TbsIndex = int(math.log(ue.site, 10) / 0.037037)


def newUE(numUE):  # creating some new UEs in the cell (number of new UEs)
    for i in range(p.numUE, p.numUE + numUE):  # create the UE receiving RT in the cell
        p.UeList.append(UE(i, choseSrv(i)))
    p.numUE += numUE
    p.priority = [-1] * p.numUE  # the priority of resource allocation for UEs


def buildEvent(srv, currTime):  # creating a new packet arrived event (service, current time)
    if not srv in p.setEmbmsSess:
        for i in p.listSuber[srv]:
            x = np.random.pareto(1.2, 8) + 2.5  # alpha = 1.2; number of variable: 8; baseline: 2.5ms
            x = x[x < 100][:4]  # the upper bound is 100ms, and each video frame has 4 packet
            for offsetTime in x:
                t = currTime + int(offsetTime) + srv
                if p.eventList.get(t):  # if there is any event in the time, adding a new event with it
                    p.eventList[t].append(i)
                else:  # if there is no event, creating the time point and adding a new event
                    p.eventList.update({currTime + int(offsetTime): [i]})
    else:
        x = np.random.pareto(1.2, 8) + 2.5  # alpha = 1.2; number of variable: 8; baseline: 2.5ms
        x = x[x < 100][:4]  # the upper bound is 100ms, and each video frame has 4 packet
        for offsetTime in x:
            t = currTime + int(offsetTime) + srv
            if p.eventList.get(t):  # if there is any event in the time, adding a new event with it
                p.eventList[t].append("s"+str(srv))
            else:  # if there is no event, creating the time point and adding a new event
                p.eventList.update({currTime + int(offsetTime): ["s"+str(srv)]})


def pktCret(arrEvent):  # creating a packet in buffer (the packets arrival event)
    for i in arrEvent:  # the arrEvent is a list which records the UE's Id
        if type(i) == int:
            ue = p.UeList[i]
            if ue.srv in p.setEmbmsSess:
                continue
            if ue.srv == 0:  # if the service is NRT
                pktSize = (np.random.lognormal(0.8568, 2.00256, 1) + 0.001) * 100000
                p.numNrtPkt += 1
            else:  # if the service is RT
                pktSize = p.pktSizeTable[ue.srvQ]  # the packet size according to the streaming quality that the UE receives
                p.numRtPkt += 1
            pkt = packet(p.pktId, pktSize, p.DelayThr[ue.srv])
            ue.numPkt += 1
            ue.buffLen += pktSize
            ue.pktList.append(pkt)
        else:
            srv = int(i[1])
            if srv in p.eMBMSpkt.keys():
                pktSize = p.pktSizeTable[p.SessQ[srv]]  # the packet size according to the streaming quality of eMBMS session
                p.numRtPkt += 1
                pkt = packet(p.pktId, pktSize, p.DelayThr[srv])
                p.eMBMSpktLen[list(p.eMBMSpkt.keys()).index(srv)] += pktSize
                p.eMBMSpkt[srv].append(pkt)
        p.pktId += 1


def addDelay():  # adding the delay time of each packet
    for ue in p.UeList:
        for pkt in ue.pktList:  # increasing the delay time of each packet
            pkt.delay += 1
            if pkt.delay > pkt.DelayThr:  # checking is there any invalid packet
                ue.buffLen -= pkt.size
                ue.pktList.pop(0)  # remove the invalid packets
                ue.numInvPkt += 1
                p.numInvPkt += 1
    for srv, pktList in p.eMBMSpkt.items():
        for pkt in pktList:
            pkt.delay += 1
            if pkt.delay > pkt.DelayThr:  # checking is there any invalid packet
                p.eMBMSpktLen[list(p.eMBMSpkt.keys()).index(srv)] -= pkt.size
                pktList.pop(0)  # remove the invalid packets
                p.numInvPkt += 1


def calAvgDelay(ue):  # modifying the average DRC of each UE
    ue.avgDRC = (0.7 * ue.avgDRC) + (0.3 * p.TbsTable[1][ue.TbsIndex])


def ExpPf(ue):  # the packet scheduler (EXP/PD algorithm) for assinged priority
    calAvgDelay(ue)
    if len(ue.pktList) == 0:  # if packetList is empty
        return -1
    elif ue.srv == 0:  # PF algorithm for NRT service
        return (p.pNRT / p.avgPktDelay) * (ue.DRC / ue.avgDRC)
    else:  # EXP rule algorithm for RT service
        return math.exp((ue.alpha * ue.pktList[0].delay - p.AvgAlphaDelay) / (1 + (p.AvgAlphaDelay ** 0.5))) * (
                ue.DRC / ue.avgDRC)


def modfPara():  # modifying the parameter of EXP/PF
    # calculating the average alphaDelay of RT packets
    alphaDelay = 0
    for i in p.RtUeList:
        ue = p.UeList[i]
        if len(ue.pktList) == 0:
            continue
        alphaDelay = ue.alpha * ue.pktList[0].delay
    p.AvgAlphaDelay = alphaDelay / len(p.RtUeList)

    # calculating the NRT weight
    if p.AvgAlphaDelay > p.MaxDelayThr:
        p.pNRT -= 1
    elif p.AvgAlphaDelay < p.MaxDelayThr:
        p.pNRT += 1 / 2


def resourceAllocation(mod):  # allocating the subframe's resource
    nRB = p.NumRbsPerSf
    pktNum = p.numRtPkt
    cutDelay = 0
    if mod:  # allocate the resource to eMBMS sessions
        for i in range(len(p.MSA)):
            if p.MSA[i]:
                cdelay, costRB = AllocResource2Embms(nRB, i)
                cutDelay += cdelay
                nRB = nRB - costRB
                p.MSA[i] -= 1
                break
    else:    # allocate the resource to UEs
        while nRB and max(p.priority)!=-1:
            index = p.priority.index(max(p.priority))  # find the maximum priority UE
            cdelay, costRB = AllocResource2UE(min(nRB, p.MaxRbAssigned), p.UeList[index])
            cutDelay += cdelay
            nRB = nRB - costRB
            p.priority[index] = -1
    if nRB:
        p.unusedRB += nRB
    if p.numRtPkt:
        p.avgPktDelay = ((p.avgPktDelay * pktNum) - cutDelay) / p.numRtPkt


def AllocResource2UE(nRB, ue):  # allocating the resource to the UE
    expData = p.TbsTable[nRB][ue.TbsIndex]  # the amount of bits can be carried
    cdelay = 0  # the amount of cutting delay
    if ue.buffLen > expData:  # the expData cannot carry all packets
        while expData-ue.pktList[0].size >= 0:  # the expData can carry a entire packet
            pkt = ue.pktList.pop(0)
            cdelay += pkt.delay
            expData -= pkt.size
            ue.buffLen -= pkt.size
            ue.throughput += pkt.size
            p.sysThroughput += pkt.size

            if ue.srv:
                p.numRtPkt -= 1
            else:
                p.numNrtPkt -= 1

        ue.pktList[0].size -= expData  # the rest expData just can  carry a part of packet
        ue.buffLen -= expData
        p.sysThroughput += expData
        ue.throughput += expData
        return cdelay, nRB

    else:  # the expData can carry all packets
        for numRB in range(1, nRB+1):
            if p.TbsTable[numRB][ue.TbsIndex] >= ue.buffLen:
                break
        while ue.pktList:
            pkt = ue.pktList.pop(0)
            cdelay += pkt.delay
            ue.buffLen -= pkt.size
            ue.throughput += pkt.size
            p.sysThroughput += pkt.size
            if ue.srv:
                p.numRtPkt -= 1
            else:
                p.numNrtPkt -= 1
        return cdelay, numRB


def AllocResource2Embms(nRB, i):  # allocating the resource to the UE
    srv = list(p.eMBMSpkt.keys())[i]
    expData = p.TbsTable[nRB][p.SessTbs[srv]]  # the amount of bits can be carried
    cdelay = 0  # the amount of cutting delay
    sumThroughput = 0

    if p.eMBMSpktLen[i] > expData:  # the expData cannot carry all packets
        while expData-p.eMBMSpkt[srv][0].size >= 0:  # the expData can carry a entire packet
            pkt = p.eMBMSpkt[srv].pop(0)
            cdelay += pkt.delay
            expData -= pkt.size
            sumThroughput += pkt.size
            p.sysThroughput += pkt.size
            p.eMBMSpktLen[i] -= pkt.size
            p.numRtPkt -= 1

        p.eMBMSpkt[srv][0].size -= expData  # the rest expData just can  carry a part of packet
        p.eMBMSpktLen[i] -= expData
        p.sysThroughput += expData
        sumThroughput += expData

        for i in p.listSuber[srv]:
            p.UeList[i].throughput += sumThroughput
        return cdelay, nRB

    else:  # the expData can carry all packets
        for numRB in range(1, nRB+1):
            if p.TbsTable[numRB][p.SessTbs[srv]] >= p.eMBMSpktLen[i]:
                break
        while p.eMBMSpkt[srv]:
            pkt = p.eMBMSpkt[srv].pop(0)
            cdelay += pkt.delay
            p.eMBMSpktLen[i] -= pkt.size
            p.sysThroughput += pkt.size
            sumThroughput += pkt.size
            p.numRtPkt -= 1

        for i in p.listSuber[srv]:
            p.UeList[i].throughput += sumThroughput
        return cdelay, numRB


# ! proposal method 1 !
def calRou(currTime):  # calculate the rou value of each time point
    sum = 0
    num = 1
    for ue in p.UeList:
        if ue.srv and len(ue.pktList) and ue.srv in p.setEmbmsSess:
            sum += ue.alpha * ue.pktList[0].delay * ue.TbsIndex / 26
            num += 1
    p.rou[currTime % 5120] = sum / num


def calAvgDifRou(init):
    initRou = p.rou[init]
    avgDifRou = p.rou[init + 1] - initRou
    for i in range(init + 2, len(p.rou)):
        avgDifRou = 0.89 * avgDifRou + 0.11 * (p.rou[i] - initRou)
    if avgDifRou > 0 and init == 0:
        p.incFlag = True
    if avgDifRou <= 0 and p.unusedRbHappend:
        p.unusedRbHappend = False
        p.decFlag = True


def modResourceAlloSchemeforeMBMS(mod):  # modify the resource allocation Scheme for eMBMS (0.01:increase/-0.01:de-)
    for i in range(1, p.numSrv):
        p.SessQ[i], p.SessTbs[i] = slcSessQnTbs(i)
    p.incFlag = p.decFlag = False
    currSetEmbmsSess = p.setEmbmsSess
    while p.rateEmbmsRs < 0.6 and (p.numSrv - 1) - len(p.setEmbmsSess):
        p.rateEmbmsRs += mod
        KPS()
        p.setEmbmsSess.sort()
        if not mod:
            break
        if p.setEmbmsSess != currSetEmbmsSess:  # until the set is different from original set
            break
    p.MSA = copy.deepcopy(p.cost)
    LRCSAPG()
    uniSwMult()


def uniSwMult():  # switching unicast communication to multicast
    p.eMBMSpkt = {}
    p.eMBMSpktLen = []
    for srv in p.setEmbmsSess:
        p.eMBMSpkt.update({srv:[]})
        p.eMBMSpktLen.append(0)
        for i in range(3):
            pktSize = p.pktSizeTable[
                p.SessQ[srv]]  # the packet size according to the streaming quality of eMBMS session
            p.numRtPkt += 1
            pkt = packet(p.pktId, pktSize, p.DelayThr[srv])
            p.eMBMSpkt[srv].append(pkt)
            p.eMBMSpktLen[list(p.eMBMSpkt.keys()).index(srv)] += pktSize
            p.pktId += 1
        for i in p.listSuber[srv]:
            p.UeList[i].pktList = []
            p.UeList[i].srvQ = p.SessQ[srv]
            p.UeList[i].buffLen = 0


# ! proposal method 2 !
def slcSessQnTbs(srv):  # selecting the quality and TBS Index of eMBMS sessions
    minTbsIndex = 26
    numSrvQ = [0] * 8
    for i in p.listSuber[srv]:
        numSrvQ[p.UeList[i].srvQ] += 1
        if p.UeList[i].TbsIndex < minTbsIndex:
            minTbsIndex = p.UeList[i].TbsIndex
    SessQ = numSrvQ.index(max(numSrvQ))

    if srv in p.setEmbmsSess:
        cost = math.ceil((p.pktSizeTable[p.SessQ[srv]] * 100) / p.TbsTable[p.NumRbsPerSf][
            p.SessTbs[srv]] * p.csaPeriod / 100)
        for i in range(len(p.pktSizeTable)):
            if math.ceil((p.pktSizeTable[i] * 100) / p.TbsTable[p.NumRbsPerSf][
                minTbsIndex] * p.csaPeriod / 100) <= cost:
                SessQ = i
    return SessQ, minTbsIndex


def KPS():  # selecting the eMBMS sessions
    Vmax = 0
    for csaPeriod in p.CsaPeriodVal:
        EmbmsRs = int(p.rateEmbmsRs * 10 * csaPeriod)
        if EmbmsRs == 0:
            continue
        setMMS = []
        value = []
        cost = []
        for i in range(1, p.numSrv):
            if p.DelayThr[i] >= csaPeriod:
                setMMS.append(i)
                value.append(len(p.listSuber[i]) * p.pktSizeTable[p.SessQ[i]] * 100)
                cost.append(math.ceil((p.pktSizeTable[p.SessQ[i]] * 100) / p.TbsTable[p.NumRbsPerSf][
                    p.SessTbs[i]] * csaPeriod / 100))  # the required resource per CSA Period
        Vt, setEmbmsSess, setEmbmsSessCost = knapSack(EmbmsRs, cost, value, setMMS)
        if Vt > Vmax:
            Vmax = Vt
            p.setEmbmsSess = setEmbmsSess
            p.csaPeriod = csaPeriod
            p.cost = setEmbmsSessCost


def knapSack(EmbmsRs, cost, value, setMMS):
    n = len(setMMS)
    setEmbmsSess = []
    benefit = [0]*(EmbmsRs+1)
    get = []
    setEmbmsSessCost = []
    for i in range(n):
        get.append([])
        for j in range(EmbmsRs+1):
            get[i].append(False)

    for i in range(n):
        j = EmbmsRs
        while j >= cost[i]:
            if benefit[j - cost[i]] + value[i] > benefit[j]:
                benefit[j] = benefit[j - cost[i]] + value[i]
                get[i][j] = True
            j -= 1

        i = n-1
        j = EmbmsRs
    while i >= 0:
        if get[i][j]:
            setEmbmsSess.append(setMMS[i])
            setEmbmsSessCost.append(cost[i])
            j -= cost[i]
        i -= 1
    setEmbmsSessCost.reverse()
    return benefit[EmbmsRs], setEmbmsSess, setEmbmsSessCost


# ! proposal method 3 !
def LRCSAPG():
    R = 0
    for c in p.cost:  # calculate the required amount of radio resource for eMBMS
        R += c
    R *= (p.mcchModificationPeriod/p.csaPeriod)

    p.bitmap = [0 for i in p.bitmap]  # initial the bitmap of each SC

    n = min(int(math.log(p.csaPeriod, 2)), 5)
    for i in range(n+1):  # procedure Equation (15)
        p.bitmap[i] = math.floor(R/(p.mcchModificationPeriod/2**i))
        if not i == 0:
            p.bitmap[i] %= 2

    while sum(p.bitmap) > 6:
        p.bitmap[n] += 1
        for i in range(n):
            if p.bitmap[n-i] > 1:
                p.bitmap[n-i] -= 2
                p.bitmap[n-i-1] += 1


def allocSf2eMBMS(currtime):  # allocate the radio resource to eMBMS
    for t in range(p.mcchModificationPeriod):
        numSf2eMBMS = 0
        for rap in p.RAP:
            if not t%rap:
                numSf2eMBMS += p.bitmap[int(math.log(rap, 2))]
        for i in range(numSf2eMBMS):
             p.sf2eMBMS.append(currtime + t*10 + p.MBSFNsf[i])