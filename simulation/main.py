from simFunc import *
import openpyxl

#  main procedure
newUE(200)
for currTime in range(p.simTime):

    # create the UEs
    """if not currTime % 1000:
        newUE(np.random.poisson(3))"""

    # a new CSA Period -> reset the MSA
    if p.eMBMS_triggerTime != -1 and not currTime % (p.csaPeriod*10) - p.eMBMS_triggerTime :
        p.MSA = copy.deepcopy(p.cost)  # reset the amount of resource for each eMBMS session

    # ue changes the site
    if not currTime % 50:
        for ue in p.UeList:
            changeSite(ue)

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
        if p.UeList[i].buffLen:  # to assign the priority to UE having transmission requirement
            p.priority[i] = ExpPf(p.UeList[i])

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

    calRou(currTime)  # calculate the rou of the time"

    # improving the streaming quality of unicast UE
    if not currTime % 3000 and currTime:
        for ue in p.UeList:
            if ue.numInvPkt == 0 and ue.srvQ < 7 and not ue.srv in p.setEmbmsSess:  # improve the streaming quality
                ue.srvQ += 1
            ue.numInvPkt = ue.numPkt = 0

    # trigger eMBMS if there any UE's IPR exceeds its tolerate and reduce the streaming quality of the UE
    if not currTime % 2000 and currTime:
        for ue in p.UeList:
            if ue.numInvPkt / (ue.numPkt + 1) >= p.Tolerate[ue.srv]:
                p.incFlag = True
                if ue.srvQ > 0:
                    ue.srvQ -= 1
                if p.eMBMS_triggerTime == -1:
                    p.eMBMS_triggerTime = int(currTime/10) * 10 % 5120

    # modifying the resource for eMBMS
    if p.eMBMS_triggerTime != -1 and not currTime % (p.mcchModificationPeriod * 10) - p.eMBMS_triggerTime:
        calAvgDifRou(p.eMBMS_triggerTime)  # calculate the equation (10)
        if p.time_unusedRB != -1:  # if unused RB event was happened in the period
            calAvgDifRou(p.time_unusedRB)  # calculate the equation (13)
        if p.incFlag:  # increasing the resource for eMBMS
            modResourceAlloSchemeforeMBMS(0.01)
            print(p.setEmbmsSess)
        elif p.decFlag and p.rateEmbmsRs:  # decreasing the resource for eMBMS
            modResourceAlloSchemeforeMBMS(-0.01)
            print(p.setEmbmsSess)
        else:
            modResourceAlloSchemeforeMBMS(0)
        modResourceAlloSchemeforeMBMS(0)
        p.time_unusedRB = -1
        allocSf2eMBMS(currTime)

UeThroughput = 0
for ue in p.UeList:
    UeThroughput += ue.throughput
ADR = (UeThroughput/p.simTime*1000) / p.numUE
IPR = p.numInvPkt / p.pktId
URR = p.unusedRB / (p.NumRbsPerSf*p.simTime)
Throughput = p.sysThroughput/p.simTime*1000

workbook = openpyxl.load_workbook('../../Desktop/SimulationReport.xlsx')
worksheet = workbook.worksheets[0]
row = str(worksheet.max_row+1)
sheet = workbook.active
sheet['A'+row] = ADR
sheet['B'+row] = IPR
sheet['C'+row] = URR
sheet['D'+row] = Throughput
workbook.save('../../Desktop/SimulationReport.xlsx')
workbook.close()