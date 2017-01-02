################################
#  - Ben Dews
#  - bendews.com
#  - 30/12/2016
#  - Script to get IPMI statistics and insert to InfluxDB
################################
import subprocess
import requests
import re

def sizeInGB(totalSize,allocSize):
	result = (totalSize*allocSize)/1024/1024/1024
	result = "%.4f" % result
	return result
	pass

def writeData(influxServerData,measurementData,timeStamp):
	INFLUX_SERVER = str(influxServerData["hostname"])
	INFLUX_PORT = str(influxServerData["port"])
	INFLUX_DB = str(influxServerData["database"])

	host = str(measurementData[0]).replace(" ", "")
	device = str(measurementData[1]).replace(" ", "")
	item = str(measurementData[2]).replace(" ", "")
	value = str(measurementData[3]).replace(" ", "")

	url = "http://"+INFLUX_SERVER+":"+INFLUX_PORT+"/write?db="+INFLUX_DB+"&precision=s"
	data = "snmp_data,device="+device+",host="+host+",sensor="+item+" value="+value+" "+str(timeStamp)
	requests.post(url, data=data,headers={'Content-Type': 'application/octet-stream'},timeout = 3)
	pass

def snmpWalk(hostData,oid):
	SNMP_SERVER = hostData['hostname']
	SNMP_COMMUNITY = hostData['community']

	p = subprocess.run(["snmpwalk", "-O", "fn", "-v", "2c", "-c", SNMP_COMMUNITY, SNMP_SERVER, oid], stdout=subprocess.PIPE)
	output = p.stdout.decode('utf8').splitlines()
	return output
	pass

def diskUsage(influxData,hostData,timeStamp):
	storageInfoOID = ".1.3.6.1.2.1.25.2.3.1"
	storageLabelOID = storageInfoOID+".3"
	storageAllocOID = storageInfoOID+".4"
	storageTotalOID = storageInfoOID+".5"
	storageUsedOID = storageInfoOID+".6"
	disks = []
	allocationSize = []
	storageSize = []
	storageUsed = []

	output = snmpWalk(hostData,".1.3.6.1.2.1.25.2.3.1")

	for line in output:
		# Storage Label
		if ".1.3.6.1.2.1.25.2.3.1.3" in line:
			result = re.findall(r'\: (.*)',line)
			disks.append(str(result[0]))
			pass
		# Allocation Size
		if ".1.3.6.1.2.1.25.2.3.1.4" in line:
			result = re.findall(r'\: (\d*)',line)
			allocationSize.append(int(result[0]))
			pass
		# Storage total size
		if ".1.3.6.1.2.1.25.2.3.1.5" in line:
			result = re.findall(r'\: (\d*)',line)
			storageSize.append(int(result[0]))
			pass
		# Storage used
		if ".1.3.6.1.2.1.25.2.3.1.6" in line:
			result = re.findall(r'\: (\d*)',line)
			storageUsed.append(int(result[0]))
			pass
		pass

	for disk,allocSize,storSize,storUsed in zip(disks,allocationSize,storageSize,storageUsed):
		totalInTB = sizeInGB(storSize,allocSize)
		usedInTB = sizeInGB(storUsed,allocSize)
		for volume in hostData['volumes']:
			if volume in disk:
				data_totalInTB = [hostData['hostname'],volume,"total_storage",totalInTB]
				data_usedInTB = [hostData['hostname'],volume,"used_storage",usedInTB]
				writeData(influxData,data_totalInTB,timeStamp)
				writeData(influxData,data_usedInTB,timeStamp)
				# print(volume,totalInTB,usedInTB)
				pass
			pass
	pass

def diskTemp(influxData,hostData,timeStamp):
	diskInfoOID = ".1.3.6.1.4.1.6574.2.1.1"
	diskLabelOID = diskInfoOID+".2"
	diskTempOID = diskInfoOID+".6"
	disks = []
	temps = []

	output = snmpWalk(hostData,diskInfoOID)

	for line in output:
		if diskLabelOID in line:
			result = re.findall(r'\"(.*)\"',line)
			disks.append(result[0])
			pass
		if diskTempOID in line:
			result = re.findall(r'\: (\d*)',line)
			temps.append(result[0])
			pass
		pass
	for disk,temp in zip(disks,temps):
		data_diskTemp = [hostData['hostname'],disk,"temperature",temp]
		writeData(influxData,data_diskTemp,timeStamp)
		# print(disk,temp)
	pass
