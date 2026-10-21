# DICOM-Manager - Default values.
# Author: Pascal Malouin (https://github.com/EGOUID0)
# Project: https://github.com/EGOUID0/DICOM-Manager
# Created: 2026-10-09

ANONYMIZE_DEFAULTS = {
    "PatientName": "ANONYMOUS^SUBJECT",
    "PatientID": "ANON_ID",
    "PatientBirthDate": "19990101",
    "AccessionNumber": "ANON_ACC",
    "StudyID": "ANON_ACC",
    "ScheduledProcedureStepID": "ANON_ACC",
    "RequestedProcedureID": "ANON_ACC",
}

INSPECT_DEFAULTS = (
    "PatientName", "PatientID", "PatientBirthDate", "AccessionNumber",
    "StudyID", "StudyDate", "StudyDescription", "Modality",
    "StudyInstanceUID", "SeriesInstanceUID", "SOPInstanceUID",
)
