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
		self.debugLog("Copying Indigo DB for safety")

		indigo.server.log("cp {} {}".format(liveDBNameExt,tempDBNameExt))
		os.system('cp {} {}'.format(liveDBNameExt,tempDBNameExt))

		indigo.server.log("shutil.copy({},{})".format(liveDBNameExt,tempDBNameExt))
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

		self.debugLog("Parsing Indigo Actions")
		for a in db['ActionGroupList']['ActionGroup']:		#Loop through Indigo Actions in DB
			lastPluginID = ""
			lastPluginAction = ""
			actionName = a['Name']['#text']
			actionID = a['ID']['#text']
			if (isinstance(a['ActionSteps']['Action'],dict)):
				a['ActionSteps']['Action'] = [a['ActionSteps']['Action']]				#Force single Actions to be a list of 1 Action
			for aStep in a['ActionSteps']['Action']:													#Loop through each Step in the Action
				if 'PluginID' in aStep:
					print("Action: {}".format(actionName))
					if (isinstance(aStep,dict)):
						pluginID = aStep['PluginID']['#text']
					else:
						pluginID = str(aStep)
					if (pluginID != lastPluginID):
						print("|---{}".format(pluginID))
						lastPluginID = pluginID

					if 'TypeLabelPlugin' in aStep:
#						if (isinstance(aStep,dict)):
#							pluginAction = aStep['TypeLabelPlugin']['#text']
#							indigo.server.log("Here 76 {}".format(pluginAction))
#						else:
#							pluginAction = aStep
#							indigo.server.log("Here 78 {}".format(pluginAction))
#						if (pluginAction != lastPluginAction):
#							print("|---|--{}".format(pluginAction))
#							lastPluginAction = pluginAction
						pluginAction = aStep['TypeLabelPlugin']['#text']
					else:
						pluginAction = "[Step has no name; probably builtin Indigo plugin]"

					if 'DeviceID' in aStep:
#						if (isinstance(aStep,dict)):
#							pluginAction = aStep['TypeLabelPlugin']['#text']
#							indigo.server.log("Here 76 {}".format(pluginAction))
#						else:
#							pluginAction = aStep
#							indigo.server.log("Here 78 {}".format(pluginAction))
#						if (pluginAction != lastPluginAction):
#							print("|---|--{}".format(pluginAction))
#							lastPluginAction = pluginAction
						deviceID = aStep['DeviceID']['#text']
						pluginAction = "{}  [Device: {}]".format(pluginAction,localDevices[int(deviceID)].name)


					#Build $Plugins
					if pluginID not in out["plugins"]:
						out["plugins"][pluginID] = {}
					if actionID not in out["plugins"][pluginID]:
						out["plugins"][pluginID][actionID] = []
					out["plugins"][pluginID][actionID].append(pluginAction)

					#Build $Actions
					if actionID not in out["actions"]:
						out["actions"][actionID] = {}
					if pluginID not in out["actions"][actionID]:
						out["actions"][actionID][pluginID] = []
					out["actions"][actionID][pluginID].append(pluginAction)

			print("|")

		doOut = True
		#doOut = False
		if (doOut):

			self.debugLog("Building output for txt files")
			#Set output to Log folder
			os.chdir("{}/Logs/com.howartp.indidbparser".format(indigo.server.getInstallFolderPath()))

			outPluginLines = []

			for pID in out["plugins"]:
				#self.debugLog("Plugin: {}".format(pID))
				outPluginLines.append("Plugin: {}\n\r".format(pID))
				for aID in out["plugins"][pID]:
					#self.debugLog("|------{} [{}]".format(aID,indigo.actionGroups[int(aID)].name))
					outPluginLines.append("|------{} [{}]\n\r".format(aID,indigo.actionGroups[int(aID)].name))
					for step in out["plugins"][pID][aID]:
						#self.debugLog("|------|------{}".format(step))
						outPluginLines.append("|------|------{}\n\r".format(step))

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


