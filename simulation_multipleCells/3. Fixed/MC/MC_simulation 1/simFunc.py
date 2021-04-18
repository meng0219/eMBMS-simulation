import copy
import numpy as np
from simCls import *


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


def changeSite(ue, currTime):
    if ue.site < 1:  # if the UE has left
        return
    ue.site += ue.speed  # the site of ue changes each 50ms
    if ue.site > 9.9999:
        ue.site = 19.9998 - ue.site
        ue.speed = -1 * ue.speed  # the ue turn the direction of movement
    elif ue.site < 1:
        UEleave(ue.Id, currTime)
    ue.TbsIndex = int(math.log(ue.site, 10) / 0.037037)


def newUE(numUE, currTime):  # creating some new UEs in the cell (number of new UEs)
    for i in range(numUE):  # create the UE receiving RT in the cell
        ue = UE(p.UeId, choseSrv(p.UeId), rdm.uniform(1, 9.9999), currTime)
        p.UeList.append(ue)
        if ue.srv in p.setEmbmsSess:
            ue.srvQ = p.SessQ[ue.srv]
            ue.join_eMBMS_time = currTime
        p.priority.append(0)  # the priority of resource allocation for UEs
        p.UeId += 1


def UEleave(id, currTime):
    ue = p.UeList[id]
    if ue.srv in p.setEmbmsSess:
        ue.eMBMS_during_time += (currTime - ue.join_eMBMS_time)
    p.listSuber[ue.srv].remove(id)
    ue.speed = 0
    ue.srv = -1
    ue.pktList = []
    ue.buffLen = 0
    ue.during_time = currTime-ue.enter_time


def buildEvent(srv, currTime):  # creating a new packet arrived event (service, current time)
    if not srv in p.setEmbmsSess:
        for i in p.listSuber[srv]:
            x = np.random.pareto(1.2, 8) + 2.5  # alpha = 1.2; number of variable: 8; baseline: 2.5ms
            x = x[x < 40][:4]  # the upper bound is 100ms, and each video frame has 4 packet
            for offsetTime in x:
                t = currTime + int(offsetTime)
                if p.eventList.get(t):  # if there is any event in the time, adding a new event with it
                    p.eventList[t].append(i)
                else:  # if there is no event, creating the time point and adding a new event
                    p.eventList.update({currTime + int(offsetTime): [i]})
    else:
        x = np.random.pareto(1.2, 8) + 2.5  # alpha = 1.2; number of variable: 8; baseline: 2.5ms
        x = x[x < 40][:4]  # the upper bound is 100ms, and each video frame has 4 packet
        for offsetTime in x:
            t = currTime + int(offsetTime)
            if p.eventList.get(t):  # if there is any event in the time, adding a new event with it
                p.eventList[t].append("s"+str(srv))
            else:  # if there is no event, creating the time point and adding a new event
                p.eventList.update({currTime + int(offsetTime): ["s"+str(srv)]})


def pktCret(arrEvent):  # creating a packet in buffer (the packets arrival event)
    for i in arrEvent:  # the arrEvent is a list which records the UE's Id
        if type(i) == int:
            if i == -1:  # the UE has leaven the cell
                continue
            ue = p.UeList[i]
            if ue.srv in p.setEmbmsSess:
                continue
            if ue.srv == 0:  # if the service is NRT
                pktSize = (np.random.lognormal(0.8568, 2.00256, 1) + 0.001) * 100000
                p.numNrtPkt += 1
            else:  # if the service is RT
                pktSize = p.pktSizeTable[ue.srvQ]  # the packet size according to the streaming quality that the UE receives
                p.numRtPkt += 1
                p.amountPkt_U += 1
            pkt = packet(p.pktId, pktSize, p.DelayThr[ue.srv])
            ue.numPkt += 1
            ue.buffLen += pktSize
            ue.pktList.append(pkt)
        else:
            srv = int(i[1])
            if srv in p.eMBMSpkt.keys():
                pktSize = p.pktSizeTable[p.SessQ[srv]]  # the packet size according to the streaming quality of eMBMS session
                p.numEmbmsPkt += 1
                p.amountPkt_M += 1
                pkt = packet(p.pktId, pktSize, p.DelayThr[srv])
                p.eMBMSpktLen[list(p.eMBMSpkt.keys()).index(srv)] += pktSize
                p.eMBMSpkt[srv].append(pkt)
        p.pktId += 1


def addDelay():  # adding the delay time of each packet
    p.MaxDelayThr = 0
    for ue in p.UeList:
        for pkt in ue.pktList:  # increasing the delay time of each packet
            pkt.delay += 1
            p.MaxDelayThr = max(p.MaxDelayThr, pkt.delay)
            if pkt.delay > pkt.DelayThr:  # checking is there any invalid packet
                c = ue.pktList.pop(0)  # remove the invalid packets
                ue.buffLen -= c.size
                ue.numInvPkt += 1
                p.numInvPkt += 1
                p.numInvPkt_U += 1
                p.numRtPkt -= 1

    for srv, pktList in p.eMBMSpkt.items():
        for pkt in pktList:
            pkt.delay += 1
            if pkt.delay > pkt.DelayThr:  # checking is there any invalid packet
                c = pktList.pop(0)  # remove the invalid packets
                p.eMBMSpktLen[list(p.eMBMSpkt.keys()).index(srv)] -= c.size
                p.numInvPkt += 1
                p.numInvPkt_M += 1


def calAvgDelay(ue):  # modifying the average DRC of each UE
    ue.avgDRC = np.round((0.71 * ue.avgDRC) + (0.29 * ue.lastThr), 7)


def ExpPf(ue):  # the packet scheduler (EXP/PD algorithm) for assinged priority
    calAvgDelay(ue)
    if ue.buffLen == 0 or ue.srv == -1:  # if packetList is empty
        return 0
    elif ue.srv == 0:  # PF algorithm for NRT service
        return (p.pNRT / p.avgPktDelay) * (ue.DRC / ue.avgDRC)
    else:  # EXP rule algorithm for RT service
        val = min(((ue.alpha * ue.pktList[0].delay - p.AvgAlphaDelay) / (1 + (p.AvgAlphaDelay ** 0.5))), 709)
        return math.exp(val) * (ue.DRC / ue.avgDRC)


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
        p.times_M += 1
        if not any(p.MSA):
            resourceAllocation(0)
            return
        for i in range(len(p.MSA)):
            if p.MSA[i]:
                if p.eMBMSpktLen[i] == 0:
                    p.MSA[i] -= 1
                    resourceAllocation(0)
                    return
                else:
                    cdelay, costRB = AllocResource2Embms(nRB, i)
                    cutDelay += cdelay
                    nRB = nRB - costRB
                    p.MSA[i] -= 1
                break
    else:    # allocate the resource to UEs
        p.times_U += 1
        while nRB and any(p.priority):
            index = p.priority.index(max(p.priority))  # find the maximum priority UE
            cdelay, costRB = AllocResource2UE(min(nRB, p.MaxRbAssigned), p.UeList[index])
            cutDelay += cdelay
            nRB = nRB - costRB
            p.priority[index] = 0
        if p.numRtPkt:
            p.avgPktDelay = ((p.avgPktDelay * pktNum) - cutDelay) / p.numRtPkt
    if nRB:
        p.unusedRB += nRB
        if mod:
            p.numUnRS_M += nRB
        else:
            p.numUnRS_U += nRB


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
            ue.throughput_uc += pkt.size
            ue.lastThr = pkt.size
            p.sysThroughput += pkt.size
            p.Throughput_U += pkt.size
            if ue.srv:
                p.numRtPkt -= 1
            else:
                p.numNrtPkt -= 1

        ue.pktList[0].size -= expData  # the rest expData just can  carry a part of packet
        ue.buffLen -= expData
        p.sysThroughput += expData
        p.Throughput_U += expData
        ue.throughput += expData
        ue.throughput_uc += expData
        ue.lastThr = expData
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
            ue.throughput_uc += pkt.size
            ue.lastThr = pkt.size
            p.sysThroughput += pkt.size
            p.Throughput_U += pkt.size
            if ue.srv:
                p.numRtPkt -= 1
            else:
                p.numNrtPkt -= 1
        return cdelay, numRB


def AllocResource2Embms(nRB, i):  # allocating the resource to eMBMS
    srv = list(p.eMBMSpkt.keys())[i]
    expData = p.TbsTable[nRB][p.SessTbs[srv]]  # the amount of bits can be carried
    cdelay = 0  # the amount of cutting delay
    sumThroughput = 0

    sum = 0
    for pkt in p.eMBMSpkt[srv]:
        sum += pkt.size

    if p.eMBMSpktLen[i] > expData:  # the expData cannot carry all packets
        while expData-p.eMBMSpkt[srv][0].size >= 0:  # the expData can carry a entire packet
            pkt = p.eMBMSpkt[srv].pop(0)
            cdelay += pkt.delay
            expData -= pkt.size
            sumThroughput += pkt.size
            p.sysThroughput += pkt.size
            p.Throughput_M += pkt.size
            p.eMBMSpktLen[i] -= pkt.size
            p.numEmbmsPkt -= 1

        p.eMBMSpkt[srv][0].size -= expData  # the rest expData just can  carry a part of packet
        p.eMBMSpktLen[i] -= expData
        p.sysThroughput += expData
        p.Throughput_M += expData
        sumThroughput += expData

        for i in p.listSuber[srv]:
            p.UeList[i].throughput += sumThroughput
            p.UeList[i].throughput_eMBMS += sumThroughput
            p.UeList[i].lastThr = sumThroughput
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
            p.Throughput_M += pkt.size
            sumThroughput += pkt.size
            p.numEmbmsPkt -= 1

        for i in p.listSuber[srv]:
            p.UeList[i].throughput += sumThroughput
            p.UeList[i].throughput_eMBMS += sumThroughput
            p.UeList[i].lastThr = sumThroughput
        return cdelay, numRB


# ! proposal method 1 !
def calRou(currTime):  # calculate the rou value of each time point
    sum = 0
    num = 1
    for ue in p.UeList:
        if ue.srv and len(ue.pktList) and not ue.srv in p.setEmbmsSess:
            sum += ue.alpha * ue.pktList[0].delay * ue.TbsIndex / 26
            num += 1
    p.rou[currTime % 5120] = sum / num


def calAvgDifRou(init):
    initRou = p.rou[init]
    avgDifRou = p.rou[(init + 1) % (p.mcchModificationPeriod * 10)] - initRou
    for i in range(init + 2, p.mcchModificationPeriod*10 + p.eMBMS_triggerTime):
        avgDifRou = 0.65 * avgDifRou + 0.35 * (p.rou[i % (p.mcchModificationPeriod * 10)] - initRou)
    if avgDifRou > -0.003 and init == p.eMBMS_triggerTime:
        p.incFlag = True
    if avgDifRou <= 0.1 and init == p.time_unusedRB:
        p.decFlag = True


def modResourceAlloSchemeforeMBMS(mod, currTime):  # modify the resource allocation Scheme for eMBMS (0.01:increase/-0.01:de-/0:no modify)
    for i in range(1, p.numSrv):
        p.SessQ[i], p.SessTbs[i] = slcSessQnTbs(i)
    p.incFlag = p.decFlag = False
    currSetEmbmsSess = p.setEmbmsSess
    multSwUni(p.setEmbmsSess, p.eMBMSpkt, p.eMBMSpktLen, currTime)

    while True:
        if (0.0 < p.rateEmbmsRs and 0 > mod) or (p.rateEmbmsRs < 0.6 and mod > 0):
            p.rateEmbmsRs = np.round(p.rateEmbmsRs + mod, 2)
        KSS()
        if not mod or p.rateEmbmsRs >= 0.6 or p.rateEmbmsRs <= 0.0:
            break
        if set(p.setEmbmsSess) != set(currSetEmbmsSess):  # until the set is different from original set
            break
    p.MSA = copy.deepcopy(p.cost)
    LRCSAPG()
    uniSwMult(currTime)


def uniSwMult(currTime):  # switching unicast communication to multicast
    p.eMBMSpkt = {}
    p.eMBMSpktLen = []
    for srv in p.setEmbmsSess:
        pktLen = 0
        pktBuf = []
        for i in p.listSuber[srv]:
            ue = p.UeList[i]
            if pktLen < ue.buffLen and ue.srvQ == p.SessQ[srv]:
                pktLen = ue.buffLen
                pktBuf = copy.deepcopy(ue.pktList)
            p.numRtPkt -= len(ue.pktList)
            ue.join_eMBMS_time = currTime
            ue.pktList = []
            ue.srvQ = p.SessQ[srv]
            ue.buffLen = 0
        p.numRtPkt += len(pktBuf)
        p.eMBMSpkt.update({srv: pktBuf})
        sum = 0
        for pkt in p.eMBMSpkt[srv]:
            sum += pkt.size
        p.eMBMSpktLen.append(pktLen)

def multSwUni(setEmbmsSess, embmsPkt, embmsPktLen, currTime):
    for srv in setEmbmsSess:
        p.numRtPkt -= len(embmsPkt[srv])
        for i in p.listSuber[srv]:
            ue = p.UeList[i]
            ue.eMBMS_during_time += (currTime - ue.join_eMBMS_time)
            ue.pktList = copy.deepcopy(embmsPkt[srv])
            ue.buffLen = embmsPktLen[setEmbmsSess.index(srv)]
            p.numRtPkt += len(ue.pktList)



# ! proposal method 2 !
def calValue(ue):
    datasize = p.pktSizeTable[ue.srvQ]
    numRB = 0
    while datasize - p.TbsTable[30][ue.TbsIndex] > 0:
        datasize -= p.TbsTable[30][ue.TbsIndex]
        numRB += 30
    for k in range(0, 30):
        if p.TbsTable[k][ue.TbsIndex] >= datasize:
            break

    return numRB+k


def slcSessQnTbs(srv):  # selecting the quality and TBS Index of eMBMS sessions
    minTbsIndex = 26
    numSrvQ = [0] * len(p.pktSizeTable)
    p.value[srv] = 0
    for i in p.listSuber[srv]:
        ue = p.UeList[i]
        p.value[srv] += calValue(ue)
        numSrvQ[ue.srvQ] += 1
        if ue.TbsIndex < minTbsIndex:
            minTbsIndex = ue.TbsIndex
    SessQ = numSrvQ.index(max(numSrvQ))

    if srv in p.setEmbmsSess:
        cost = math.ceil((p.pktSizeTable[p.SessQ[srv]] * 100) / p.TbsTable[p.NumRbsPerSf][
            p.SessTbs[srv]] * p.csaPeriod / 100)
        for i in range(len(p.pktSizeTable)):
            if math.ceil((p.pktSizeTable[i] * 100) / p.TbsTable[p.NumRbsPerSf][
                minTbsIndex] * p.csaPeriod / 100) <= cost:
                SessQ = i
    return SessQ, minTbsIndex


def KSS():  # selecting the eMBMS sessions
    Vmax = 0
    for csaPeriod in p.CsaPeriodVal:
        EmbmsRs = int(p.rateEmbmsRs * 10 * csaPeriod)
        if EmbmsRs == 0:
            continue
        setMMS = []
        value = []
        cost = []
        for i in range(1, p.numSrv):
            if p.DelayThr[i] >= csaPeriod * 10:
                setMMS.append(i)
                ct = math.ceil((p.pktSizeTable[p.SessQ[i]] * 100) / p.TbsTable[p.NumRbsPerSf][
                    p.SessTbs[i]] * csaPeriod / 100)
                cost.append(ct)  # the required resource per CSA Period
                value.append((p.value[i] * csaPeriod - ct) * p.mcchModificationPeriod / csaPeriod)
        if len(setMMS):
            Vt, setEmbmsSess, setEmbmsSessCost = knapSack(EmbmsRs, cost, value, setMMS)
            if Vt > Vmax:
                Vmax = Vt
                p.setEmbmsSess = setEmbmsSess
                p.csaPeriod = csaPeriod
                p.cost = setEmbmsSessCost


def knapSack(EmbmsRs, cost, value, setMMS):
    benefit = 0
    setEmbmsSess = []
    setEmbmsSessCost = []
    while EmbmsRs > 0 and any(setMMS):
        k = cost.index(min(cost))
        if EmbmsRs - cost[k] >= 0:
            EmbmsRs -= cost[k]
            benefit += value[k]
            setEmbmsSess.append(setMMS[k])
            setEmbmsSessCost.append(cost[k])
            del setMMS[k]
            del cost[k]
            del value[k]
        else:
            break
    return benefit, setEmbmsSess, setEmbmsSessCost


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