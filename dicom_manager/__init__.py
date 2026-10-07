# ------------------------------------------------------------------------ INFO
# [/DICOM-Manager/dicom_manager/__init__.py]
# author        : Pascal Malouin @https://github.com/fantomH
# created       : 2023-05-26 16:36:50 UTC
# updated       : 2025-11-06 20:56:05 UTC
# description   : DICOM manipulation tools.

import argparse
import os
import shutil
import subprocess
import sys

import magic
import pydicom
from pydicom import (dcmread)

def locate_dicomdir(dicom_directory, msg=False):
    
    for root, _, files in os.walk(dicom_directory):
        for file_name in files:
            if file_name == "DICOMDIR":
                dicomdir_path = os.path.join(root, file_name)
                if msg:
                    print("================================================================================")
                    print(f"[+] DICOMDIR path:")
                    print()
                    print(f"{dicomdir_path}")
                return dicomdir_path
    if msg:
        print(f"[!] Unable to locate a DICOMDIR!")
    return None

def locate_dcm(dicom_directory, msg=False):

    dcm_list = []
    for root, _, files in os.walk(dicom_directory):
        for file in files:
            if file != "DICOMDIR":
                file = os.path.join(root, file)
                try:
                    if magic.from_buffer(open(file, "rb").read(2048), mime=True) == "application/dicom":
                        dcm_list.append(file)
                except:
                    pass

    if len(dcm_list) > 0:
        if msg:
            
            print("================================================================================")
            print(f"[+] List of DICOM files:")
            print()
            for f in dcm_list:
                print(f)
        return dcm_list
    else:
        if msg:
            print(f"[!] Unable to locate DICOM files!")
        return None

def read_dicomdir(dicom_directory):

    dicomdir = locate_dicomdir(dicom_directory)

    if dicomdir:
        dicomdir_dataset = dcmread(dicomdir)

        print("================================================================================")
        print(f"[+] DICOMDIR dataset:")
        print()
        print(dicomdir_dataset)
        return dicomdir_dataset

    else:
        print(f"[!] No DICOMDIR to read in the given directory!")

def read_dcm(dicom_directory):

    dcm_list = locate_dcm(dicom_directory)

    if dcm_list:
        for dcm in dcm_list:
            dataset = dcmread(dcm)
            print("================================================================================")
            print(f"[+] {dcm} dataset:")
            print()
            print(dataset)

    else:
        print(f"[!] No DICOM files to read in the given directory!")

def read_selection(dicom_directory):

    options = []
    dicomdir = locate_dicomdir(dicom_directory)
    dcm_list = locate_dcm(dicom_directory)

    if dicomdir:
        options = [dicomdir]

    if dcm_list:
        options = [*options, *dcm_list]

    if options:
        print("================================================================================")
        print(f"[*] Choose a file by its number.")
        print()

        for i, file in enumerate(options, 1):
            print(f"{i}. {file}")
        selection = input(f"Selection: ")

        try:
            index = int(selection)
            f = options[index -1]
            dataset = dcmread(f)

            print("================================================================================")
            print(f"[-] Dataset: {f}")
            print()
            print(dataset)
        except (ValueError, IndexError):
            print(f"[!] Invalid choice!")
            return
    else:
        print(f"[!] No DICOMDIR or DICOM files found!")

def change_tag_value(dataset, tag, new_value):
    for data_element in dataset:
        if data_element.VR == 'SQ':
            for item in data_element.value:
                change_tag_value(item, tag, new_value)
        elif data_element.tag == tag:
            data_element.value = new_value
    return dataset

def modify_dcm(dicom_directory, dcm_list, modifications, output_directory):

    for dcm in dcm_list:
        dataset = dcmread(dcm)

        for k, v in modifications.items():
            modified_dataset = change_tag_value(dataset, k, v)

        relative_path = os.path.relpath(dcm, dicom_directory)
        output_dcm = os.path.join(output_directory, relative_path)
        os.makedirs(os.path.dirname(output_dcm), exist_ok=True)

        modified_dataset.save_as(output_dcm)

def create_dicomdir(directory):

    if locate_dicomdir(directory):
        answer = input(f"[!] DICOMDIR already exists, overwrite it? (YES/no): ")

        if answer == 'YES':
            subprocess.run(["dcmmkdir", "+r"], cwd=directory)
    else:
        subprocess.run(["dcmmkdir", "+r"], cwd=directory)

def main():

    parser = argparse.ArgumentParser()

    parser.add_argument('-d',
                        '--directory',
                        help='Specify the DICOM directroy path.'
                       )
    parser.add_argument('-l',
                        '--locate',
                        choices=['DICOMDIR', 'dcm'],
                        action='append',
                        help='Locate DICOMDIR or dcm files.'
                       )
    parser.add_argument('-r',
                        '--read',
                        choices=['DICOMDIR', 'dcm', 'selection'],
                        action='append',
                        help='Read DICOMDIR, all dcm files or select a file to read.'
                       )
    parser.add_argument('-a',
                        '--anonymize',
                        action='store_true',
                        help='Anonymize DICOM files.'
                       )
    parser.add_argument('--modifyfromfile',
                        help='Modify value from file.'
                       )
    parser.add_argument('--createDICOMDIR',
                        action='store_true',
                        help='Creates a DICOMDIR.'
                       )

    # //print help if no argument are given.
    if len(sys.argv) == 1:
        print(f"[!] No argument given, showing help.")
        print()
        parser.print_help()
        sys.exit(0)

    args = parser.parse_args()

    # :--/ directory /--:

    if args.directory:
        if os.path.isdir(args.directory):
            dicom_directory = os.path.abspath(args.directory)
        else:
            print("[!] Invalid Directory")
    else:
        dicom_directory = os.path.abspath(os.curdir)

    # :--/ locate /--:

    if args.locate:
        if 'DICOMDIR' in args.locate:
            locate_dicomdir(dicom_directory, msg=True)

        if 'dcm' in args.locate:
            locate_dcm(dicom_directory, msg=True)

    # :--/ read /--:

    if args.read:
        if 'DICOMDIR' in args.read:
            read_dicomdir(dicom_directory)
        if 'dcm' in args.read:
            read_dcm(dicom_directory)
        if 'selection' in args.read:
            read_selection(dicom_directory)

    # / anonymize /
    if args.anonymize:

        output_directory = dicom_directory + '_MODIFIED'
        if os.path.isdir(output_directory):
            shutil.rmtree(output_directory, ignore_errors=True)
        os.makedirs(output_directory)

        dcm_list = locate_dcm(dicom_directory)

        modifications={
                    'PatientName': 'ANONYMOUS',
                    'PatientID': 'ANON_ID',
                    'PatientBirthDate': '19990101',
                    'AccessionNumber': 'ANON_ACC',
                    'StudyID': 'ANON_ACC',
                    'ScheduledProcedureStepID': 'ANON_ACC',
                    'RequestedProcedureID': 'ANON_ACC',
                    }

        modify_dcm(dicom_directory, dcm_list, modifications, output_directory)

    # :--/ modify from file /--:
    if args.modifyfromfile:

        modifications = {}
        with open(args.modifyfromfile) as _input:
            for line in _input:
                line = line.strip()
                if not line or line.startswith('#'):
                    continue
                else:
                    key, value = line.split(':', 1)
                    modifications[key.strip()] = value.strip()

        if modifications:

            output_directory = dicom_directory + '_MODIFIED'
            if os.path.isdir(output_directory):
                shutil.rmtree(output_directory, ignore_errors=True)
            os.makedirs(output_directory)

            dcm_list = locate_dcm(dicom_directory)

            modify_dcm(dicom_directory, dcm_list, modifications, output_directory)

        else:
            print(f"[!] Check the modifications file, no values were found!")

    # :--/ create DICOMDIR /--:

    if args.createDICOMDIR:

        if args.anonymize:
            create_dicomdir(output_directory)
        else:
            create_dicomdir(dicom_directory)

if __name__ == "__main__":
    main()
