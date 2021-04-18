from simFunc import *
import sys
import openpyxl

ueInc = int(sys.argv[1])
IncSec = int(sys.argv[2])
p.rateEmbmsRs = float(sys.argv[3])
sht = int(sys.argv[4])

#  main procedure
newUE(29, 0)
for currTime in range(p.simTime):
    if not currTime and not currTime % (60*1000):  # there are normal number of UEs entering the cell
        ueInc = 1
        IncSec = 3

    elif not currTime % (30*1000):  # there are huge number of UEs entering the cell
        ueInc = int(sys.argv[1])
        IncSec = int(sys.argv[2])

    if not currTime % (IncSec*1000):
        newUE(ueInc, currTime)

    # a new CSA Period -> reset the MSA
    if not (currTime - p.eMBMS_triggerTime) % (p.csaPeriod * 10):
        p.MSA = copy.deepcopy(p.cost)  # reset the amount of resource for each eMBMS session

    # ue changes the site
    if not currTime % 50:
        for ue in p.UeList:
            changeSite(ue, currTime)

    # create a sequential packets arrival event of a new video frame (25FPS video,i.e., 1 video frame per 40ms)
    if not currTime % 40 and currTime:
        for i in range(1, p.numSrv):  # create the event of RT packets arriving
            buildEvent(i, currTime)

    # there are packets arrived at this moment
    while p.eventList.get(currTime):
        pktCret(p.eventList.pop(currTime))
    modfPara()  # modify the scheduler's parameter

    # calculate resource allocation priority for each UE
    for i in range(len(p.UeList)):
        p.priority[i] = ExpPf(p.UeList[i])  # to assign the priority to UE having transmission requirement
        p.UeList[i].lastThr = 0

    # assign resource to eMBMS
    if len(p.sf2eMBMS) and currTime == p.sf2eMBMS[0]:  # the time is reserved to eMBMS
        resourceAllocation(1)
        p.sf2eMBMS.remove(p.sf2eMBMS[0])
    # assign resource to unicast UE
    else:
        resourceAllocation(0)

    # if there is no data needs to transmit which is first time in the period
    if not p.numRtPkt + p.numNrtPkt and p.time_unusedRB == -1 and p.sysThroughput:
        p.time_unusedRB = currTime % 5120

    addDelay()  # add the delay time of each packet

    # trigger eMBMS if there any UE's IPR exceeds its tolerate and reduce the streaming quality of the UE
    if not currTime % 2000 and currTime:
        for ue in p.UeList:
            if ue.numInvPkt / (ue.numPkt + 1) >= p.Tolerate[ue.srv]:
                if ue.srvQ > 0:
                    ue.srvQ -= 1
                    ue.DRC = p.pktSizeTable[ue.srvQ] * 100
                if p.eMBMS_triggerTime == -1:
                    p.incFlag = True
                    p.eMBMS_triggerTime = int(currTime/10) * 10 % 5120
            if ue.numInvPkt == 0 and ue.srvQ < 7 and not ue.srv in p.setEmbmsSess:  # improve the streaming quality
                ue.srvQ += 1
                ue.DRC = p.pktSizeTable[ue.srvQ] * 100
            ue.numInvPkt = ue.numPkt = 0

    # modifying the resource for eMBMS
    if p.eMBMS_triggerTime != -1 and not currTime % (p.mcchModificationPeriod * 10) - p.eMBMS_triggerTime:
        modResourceAlloSchemeforeMBMS(0, currTime)
        p.time_unusedRB = -1
        allocSf2eMBMS(currTime)

multSwUni(p.setEmbmsSess, p.eMBMSpkt, p.eMBMSpktLen, currTime)

ADR = ADR_U = ADR_M = 0
numUE = numUE_UC = numUE_eMBMS = 0
for ue in p.UeList:
    ADR += (ue.throughput / ue.during_time)
    ADR_U += (ue.throughput_uc / max(1, (ue.during_time-ue.eMBMS_during_time)))
    ADR_M += (ue.throughput_eMBMS / max(1, ue.eMBMS_during_time))
    if ue.throughput:
        numUE += 1
    if ue.throughput_uc:
        numUE_UC += 1
    if ue.throughput_eMBMS:
        numUE_eMBMS += 1

ADR = float(ADR/numUE)
ADR_U = float(ADR_U/numUE_UC)
ADR_M = float(ADR_M/numUE_eMBMS)
IPR = float(p.numInvPkt / p.pktId)
IPR_U = float(p.numInvPkt_U / p.amountPkt_U)
IPR_M = float(p.numInvPkt_M / max(1, p.amountPkt_M))
URR = float(p.unusedRB / (p.NumRbsPerSf*p.simTime))
URR_U = float(p.numUnRS_U / (p.NumRbsPerSf*p.times_U))
URR_M = float(p.numUnRS_M / max(1, (p.NumRbsPerSf*p.times_M)))
THR = float((p.sysThroughput/p.simTime))
THR_U = float((p.Throughput_U/p.simTime))
THR_M = float((p.Throughput_M/p.simTime))

workbook = openpyxl.load_workbook('../SimulationReport.xlsx')
sheet = workbook.worksheets[sht]
row = str(sheet.max_row+1)
sheet['A'+row] = ADR
sheet['B'+row] = ADR_U
sheet['C'+row] = ADR_M
sheet['D'+row] = IPR
sheet['E'+row] = IPR_U
sheet['F'+row] = IPR_M
sheet['G'+row] = URR
sheet['H'+row] = URR_U
sheet['I'+row] = URR_M
sheet['J'+row] = THR
sheet['K'+row] = THR_U
sheet['L'+row] = THR_M
workbook.save('../SimulationReport.xlsx')
workbook.close()