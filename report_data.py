'''
Copyright 2020 Flexera Software LLC
See LICENSE.TXT for full license text
SPDX-License-Identifier: MIT

Author : sgeary  
Created On : Wed Oct 21 2020
File : report_data.py
'''

import logging
import os
import hashlib
import CodeInsight_RESTAPIs.project.get_project_inventory
import CodeInsight_RESTAPIs.project.get_scanned_files
import CodeInsight_RESTAPIs.project.get_project_evidence

import SPDX_license_mappings # To map evidence to an SPDX license name
import filetype_mappings

logger = logging.getLogger(__name__)

#-------------------------------------------------------------------#
def gather_data_for_report(baseURL, projectID, authToken, reportName, reportVersion):
    logger.info("Entering gather_data_for_report")

    projectInventory = CodeInsight_RESTAPIs.project.get_project_inventory.get_project_inventory_details(baseURL, projectID, authToken)
    inventoryItems = projectInventory["inventoryItems"]

    spdxPackages = {}

    for inventoryItem in inventoryItems:
        packageName = inventoryItem["name"]
        inventoryID = inventoryItem["id"]
        filesInInventory = inventoryItem["filePaths"]
        selectedLicenseSPDXIdentifier = inventoryItem["selectedLicenseSPDXIdentifier"]

        
        # Contains the deatils for the package/inventory item
        spdxPackages[packageName] ={}
        spdxPackages[packageName]["packageName"] = packageName
        spdxPackages[packageName]["SPDXID"] = "SPDXRef-Pkg-" + packageName + "-" + str(inventoryID)
        spdxPackages[packageName]["PackageFileName"] = packageName
        spdxPackages[packageName]["PackageLicenseDeclared"] = selectedLicenseSPDXIdentifier
        spdxPackages[packageName]["containedFiles"] = filesInInventory


    # Dictionary to contain all of the file specific data
    fileDetails = {}
    fileDetails["remoteFiles"] = {}
    fileDetails["localFiles"] = {}

    # Collect the copyright/license data per file and create dict based on 
    projectEvidenceDetails = CodeInsight_RESTAPIs.project.get_project_evidence.get_project_evidence(baseURL, projectID, authToken)
  

    # Dictionary to contain all of the file specific data
    fileEvidence = {}
    fileEvidence["remoteFiles"] = {}
    fileEvidence["localFiles"] = {}
    for fileEvidenceDetails in projectEvidenceDetails["data"]:
        evidence = {}
        remote = fileEvidenceDetails["remote"]
        filePath = fileEvidenceDetails["filePath"]
        evidence["copyrightEvidienceFound"] = fileEvidenceDetails["copyRightMatches"]
        evidence["licenseEvidenceFound"] =  fileEvidenceDetails["licenseMatches"]

        if remote:
            fileEvidence["localFiles"][filePath] = evidence
        else: 
            fileEvidence["remoteFiles"][filePath] = evidence


    # Collect a list of the scanned files
    scannedFiles = CodeInsight_RESTAPIs.project.get_scanned_files.get_scanned_files_details(baseURL, projectID, authToken)

    # Cycle through each scanned file
    for scannedFile in scannedFiles:
        scannedFileDetails = {}
        remoteFile = scannedFile["remote"]
        FileName = scannedFile["filePath"]  

        filename, file_extension = os.path.splitext(FileName)
        if file_extension in filetype_mappings.fileTypeMappings:
            scannedFileDetails["FileType"] = filetype_mappings.fileTypeMappings[file_extension]
        else:
            scannedFileDetails["FileType"] = "OTHER"
        scannedFileDetails["LicenseConcluded"] = "***TBD***"

        scannedFileDetails["fileId"] = scannedFile["fileId"]
        scannedFileDetails["fileMD5"] = scannedFile["fileMD5"]
        scannedFileDetails["inInventory"] = scannedFile["inInventory"]
        

        scannedFileDetails["SPDXID"] = "SPDXRef-File-" + FileName

        fileContainsEvidence = scannedFile["containsEvidence"]   

        if fileContainsEvidence:

            if remoteFile:
                if fileEvidence["remoteFiles"][FileName]["copyrightEvidienceFound"]:
                    scannedFileDetails["FileCopyrightText"] = fileEvidence["remoteFiles"][FileName]["copyrightEvidienceFound"]
                else:
                    scannedFileDetails["FileCopyrightText"] = "NOASSERTION"

                if fileEvidence["remoteFiles"][FileName]["licenseEvidenceFound"]:
                    scannedFileDetails["LicenseInfoInFile"] = fileEvidence["remoteFiles"][FileName]["licenseEvidenceFound"]
                else:
                    scannedFileDetails["LicenseInfoInFile"] = "NOASSERTION"

            else:
                if fileEvidence["localFiles"][FileName]["copyrightEvidienceFound"]:
                    scannedFileDetails["FileCopyrightText"] = fileEvidence["localFiles"][FileName]["copyrightEvidienceFound"]
                else:
                    scannedFileDetails["FileCopyrightText"] = "NOASSERTION"
                if fileEvidence["localFiles"][FileName]["licenseEvidenceFound"]:
                    scannedFileDetails["LicenseInfoInFile"] = fileEvidence["localFiles"][FileName]["licenseEvidenceFound"]
                else:
                    scannedFileDetails["LicenseInfoInFile"] = "NOASSERTION"

        if remoteFile:
            fileDetails["localFiles"][FileName] = scannedFileDetails
        else: 
            fileDetails["remoteFiles"][FileName] = scannedFileDetails

    # Merge the results to map each package (inventory item) with the assocaited files
    for package in spdxPackages:
        spdxPackages[package]["files"] = {}
        
        for file in spdxPackages[package]["containedFiles"]:
            if file in fileDetails["localFiles"]:
                spdxPackages[package]["files"][file] =  fileDetails["localFiles"][file]
            elif file in fileDetails["remoteFiles"]:
                spdxPackages[package]["files"][file] =  fileDetails["remoteFiles"][file]
            else:
                logger.error("Not possible since every file in an inventory item is in the file details dict")
        
        # Create a hash of the file hashes for PackageVerificationCode
        fileHashes = []
        for file in spdxPackages[package]["files"]:
            fileHashes.append(spdxPackages[package]["files"][file]["fileMD5"])

        stringHash = ''.join(sorted(fileHashes))
        spdxPackages[package]["PackageVerificationCode"] = (hashlib.sha1(stringHash.encode('utf-8'))).hexdigest()

    reportData = {}
    reportData["reportName"] = reportName
    reportData["reportVersion"] = reportVersion
    reportData["spdxPackages"] = spdxPackages

    return reportData




