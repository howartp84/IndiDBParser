#! /usr/bin/env python
# -*- coding: utf-8 -*-
####################
# Copyright (c) 2016, Perceptive Automation, LLC. All rights reserved.
# http://www.indigodomo.com

import indigo

import os
import os.path


import shutil

import base64

import xmltodict
from pprint import pprint

# Note the "indigo" module is automatically imported and made available inside
# our global name space by the host process.

################################################################################
class Plugin(indigo.PluginBase):
	########################################
	def __init__(self, pluginId, pluginDisplayName, pluginVersion, pluginPrefs):
		super(Plugin, self).__init__(pluginId, pluginDisplayName, pluginVersion, pluginPrefs)
		self.debug = pluginPrefs.get("showDebugInfo", False)
		self.debug = True

	def startup(self):
		self.parseDB(valuesDict=None)

	def parseDB(self, valuesDict=None):
		self.debugLog("Finding Indigo DB")

		liveDB = indigo.server.getDbFilePath()
		tempDB = (indigo.server.getDbFilePath()).replace(".indiDb","_Parser.indiDb")
		liveDBName = indigo.server.getDbName()
		liveDBNameExt = "{}.indiDb".format(liveDBName)
		tempDBNameExt = liveDBNameExt.replace(".indiDb","_Parser.indiDb")

		liveDBPath = liveDB.replace("{}.indiDb".format(indigo.server.getDbName()),"")

		#indigo.server.log("liveDBName: {}".format(liveDBName))
		#indigo.server.log("liveDBFile: {}".format(str(indigo.server.getDbFilePath())))
		#indigo.server.log("liveDBPath: {}".format(str(liveDBPath)))

		#indigo.server.log("getCWD: {}".format(os.getcwd()))
		os.chdir("{}".format(liveDBPath)) #Might not be the getInstallFolderPath()!
		#indigo.server.log("getCWD: {}".format(os.getcwd()))

###############################################################################################

		self.debugLog("Copying Indigo DB for safety")

		#indigo.server.log("cp {} {}".format(liveDBNameExt,tempDBNameExt))
		#os.system('cp {} {}'.format(liveDBNameExt,tempDBNameExt))
		#indigo.server.log("shutil.copy({},{})".format(liveDBNameExt,tempDBNameExt))
		shutil.copy(liveDBNameExt,tempDBNameExt)

		file_exists = os.path.exists(tempDBNameExt)
		if (file_exists):
			self.debugLog("File {} found - continuing".format(tempDBNameExt))
		else:
			self.errorLog("File {} not found - cannot continue".format(tempDBNameExt))
			return

		self.debugLog("Reading Indigo DB into XML")
		with open(tempDBNameExt, 'r', encoding='utf-8') as file:
			xml = file.read()

		self.debugLog("Converting to Dictionary")
		fulldict = xmltodict.parse(xml)
		db = fulldict['Database'] 		#Start at the root

		self.debugLog("Imported {} as XML".format(tempDBNameExt))

		#localActions = indigo.actionGroups	# "Get the actions"
		localDevices = indigo.devices # "Get the actions"

		out = {}
		out['plugins'] = {}
		out['actions'] = {}
		out['devices'] = {}

###############################################################################################

		self.debugLog("Parsing Indigo Actions")
		for a in db['ActionGroupList']['ActionGroup']:		#Loop through Indigo Actions in DB
			actionName = a['Name']['#text']
			actionID = a['ID']['#text']
			if ('Action' in a['ActionSteps']):
				if (isinstance(a['ActionSteps']['Action'],dict)):
					a['ActionSteps']['Action'] = [a['ActionSteps']['Action']]				#Force single Actions to be a list of 1 Action
				for aStep in a['ActionSteps']['Action']:													#Loop through each Step in the Action
					if 'PluginID' in aStep:
						if (isinstance(aStep,dict)):
							pluginID = aStep['PluginID']['#text']
						else:
							pluginID = str(aStep)

						if 'TypeLabelPlugin' in aStep:
							pluginAction = aStep['TypeLabelPlugin']['#text']
						else:
							pluginAction = "[Step has no name; probably builtin Indigo plugin]"

						if 'DeviceID' in aStep:
							deviceID = aStep['DeviceID']['#text']
							pluginAction = "{}  [Device: {}]".format(pluginAction,localDevices[int(deviceID)].name)


						#Build $Plugins
						if pluginID not in out["plugins"]:
							out["plugins"][pluginID] = {}
							out["plugins"][pluginID]["actions"] = {}
						if actionID not in out["plugins"][pluginID]["actions"]:
							out["plugins"][pluginID]["actions"][actionID] = []
						out["plugins"][pluginID]["actions"][actionID].append(pluginAction)

						#Build $Actions
						if actionID not in out["actions"]:
							out["actions"][actionID] = {}
						if pluginID not in out["actions"][actionID]:
							out["actions"][actionID][pluginID] = []
						out["actions"][actionID][pluginID].append(pluginAction)

###############################################################################################

		self.debugLog("Parsing Indigo Devices")
		for d in db['DeviceList']['Device']:		#Loop through Indigo Devices in DB
			deviceName = d['Name']['#text']
			deviceID = d['ID']['#text']
			if 'PluginID' in d:
				if (isinstance(d,dict)):
					pluginID = d['PluginID']['#text']
				else:
					pluginID = str(d)

				if 'PluginUiName' in d:
					if (isinstance(d,dict)):
						pluginName = d['PluginUiName']['#text']
					else:
						pluginName = str(d)

				if 'TypeName' in d:
					deviceType = d['TypeName']['#text']
				else:
					deviceType = "[Unidentified]"

				deviceDesc = "{}  [Type: {}]".format(deviceName,localDevices[int(deviceID)].model)

				#self.debugLog(out["plugins"])
				#Build $Plugins
				if pluginID not in out["plugins"]:
					out["plugins"][pluginID] = {}
				out["plugins"][pluginID]["devices"] = {}
				if actionID not in out["plugins"][pluginID]["devices"]:
					out["plugins"][pluginID]["devices"][deviceID] = []
				out["plugins"][pluginID]["devices"][deviceID].append(deviceDesc)

				#Build $Devices
				if deviceID not in out["devices"]:
					out["devices"][deviceID] = {}
				if pluginID not in out["devices"][deviceID]:
					out["devices"][deviceID][pluginID] = []
				out["devices"][deviceID][pluginID].append(deviceDesc)



		doOut = True
		doOut = False
		if (doOut):

			self.debugLog("Building output for txt files")
			#Set output to Log folder
			os.chdir("{}/Logs/com.howartp.indidbparser".format(indigo.server.getInstallFolderPath()))

			outPluginLines = []

			for pID in out["plugins"]:
				outPluginLines.append("Plugin: {}\n".format(pID))
				outPluginLines.append("|------Actions:\n")
				if ("actions" in ["plugins"][pID]):
					for aID in out["plugins"][pID]["actions"]:
						outPluginLines.append("|------|------{} [{}]\n".format(indigo.actionGroups[int(aID)].name,aID))
						for step in out["plugins"][pID]["actions"][aID]:
							outPluginLines.append("|------|------|------{}\n".format(step))
				if ("devices" in ["plugins"][pID]):
					for dDesc in out["plugins"][pID]["devices"]:
						outPluginLines.append("|------|------{}\n".format(dDesc))

			with open('Plugins.txt','w') as f:
				f.write(''.join(outPluginLines))

			indigo.server.log("Plugin file output to:  {}/Logs/com.howartp.indidbparser/Plugins.txt".format(indigo.server.getInstallFolderPath()))

			outActionLines = []

			for aID in out["actions"]:
				outActionLines.append("Action: {}\n\r".format(indigo.actionGroups[int(aID)].name))
				for pID in out["actions"][aID]:
					outActionLines.append("|------{}\n\r".format(pID))
					for step in out["actions"][aID][pID]:
						outActionLines.append("|------|------{}\n\r".format(step))

			with open('Actions.txt','w') as f:
				f.write(''.join(outActionLines))

			indigo.server.log("Actions file output to:  {}/Logs/com.howartp.indidbparser/Plugins.txt".format(indigo.server.getInstallFolderPath()))


			indigo.server.log("Use menu item \"Plugins > IndiDB Parser > Parse DB\" to refresh files.")













		#STUFF FOR LATER

		actions = indigo.actionGroups	# "Get the actions"

		#for a in actions:
			#indigo.server.log(a.name)


