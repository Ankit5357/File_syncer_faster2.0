import os
import re
import shutil
import traceback
from pathlib import Path
import sys
import pandas as pd
from openpyxl import load_workbook
import time
import getpass
import sys



# ============================================================
# AKLD AUTOMATION — EMAIL OTP ACCESS SYSTEM
# Paste this block at the START of each Python program
# ============================================================

import os
import sys
import json
import time
import hmac
import secrets
import smtplib
import ssl

from pathlib import Path
from datetime import datetime
from email.message import EmailMessage


# ============================================================
# CONFIGURATION
# ============================================================

# Configure these once in Windows using setx:
#
# AKLD_EMAIL          = Gmail sender address
# AKLD_APP_PASSWORD   = Gmail App Password
# AKLD_OTP_EMAIL      = Email address receiving the OTP

SENDER_EMAIL = os.environ.get("ankit20june@gmail.com", "").strip()
APP_PASSWORD = os.environ.get("hkeeejndnacihxwe", "").replace(" ", "")
RECEIVER_EMAIL = os.environ.get("ankit20@gmail.com", "").strip()


ACCESS_HOURS = 10
OTP_VALIDITY_MINUTES = 5
MAX_OTP_ATTEMPTS = 5

VALIDITY_SECONDS = ACCESS_HOURS * 60 * 60
OTP_VALIDITY_SECONDS = OTP_VALIDITY_MINUTES * 60

# Shared access file for all AKLD programs on this Windows account
ACCESS_DIR = (
    Path(os.environ.get("LOCALAPPDATA", str(Path.home())))
    / "AKLD_Automation"
)

ACCESS_FILE = ACCESS_DIR / "access.json"


# ============================================================
# SEND OTP EMAIL
# ============================================================

def akld_send_otp(otp):
    if not SENDER_EMAIL or not APP_PASSWORD or not RECEIVER_EMAIL:
        raise RuntimeError(
            "Missing email configuration. Set AKLD_EMAIL, "
            "AKLD_APP_PASSWORD and AKLD_OTP_EMAIL in Windows."
        )

    message = EmailMessage()
    message["Subject"] = "AKLD Automation - OTP Verification"
    message["From"] = SENDER_EMAIL
    message["To"] = RECEIVER_EMAIL

    message.set_content(
        "AKLD AUTOMATION ACCESS VERIFICATION\n\n"
        f"Your OTP is: {otp}\n\n"
        f"This OTP expires in {OTP_VALIDITY_MINUTES} minutes.\n"
        "Do not share this code with anyone."
    )

    context = ssl.create_default_context()

    with smtplib.SMTP_SSL(
        "smtp.gmail.com",
        465,
        context=context,
        timeout=20
    ) as server:
        server.login(SENDER_EMAIL, APP_PASSWORD)
        server.send_message(message)


# ============================================================
# CHECK EXISTING ACCESS
# ============================================================

def akld_has_valid_access():
    try:
        data = json.loads(
            ACCESS_FILE.read_text(encoding="utf-8")
        )

        activated_at = float(data["activated_at"])
        now = time.time()

        # Reject invalid or future timestamps
        if activated_at <= 0 or activated_at > now:
            return False

        elapsed = now - activated_at

        if 0 <= elapsed < VALIDITY_SECONDS:
            remaining = VALIDITY_SECONDS - elapsed

            hours = int(remaining // 3600)
            minutes = int((remaining % 3600) // 60)

            print(
                f"AKLD access valid: {hours}h {minutes}m remaining."
            )
            return True

    except (OSError, ValueError, TypeError, KeyError):
        pass

    return False


# ============================================================
# REQUEST AND VERIFY OTP
# ============================================================

def akld_require_access():
    ACCESS_DIR.mkdir(parents=True, exist_ok=True)

    # Valid activation means no new OTP is needed
    if akld_has_valid_access():
        return True

    print("\n" + "=" * 48)
    print("          AKLD AUTOMATION ACCESS")
    print("=" * 48)
    print("First activation or previous access expired.")

    # Generate a new random six-digit OTP
    otp = f"{secrets.randbelow(1_000_000):06d}"
    deadline = time.monotonic() + OTP_VALIDITY_SECONDS

    # Send the OTP
    try:
        akld_send_otp(otp)

    except Exception as exc:
        print(f"Could not send OTP email: {exc}")
        print("Access denied. Check internet and email settings.")
        return False

    print(f"OTP sent to: {RECEIVER_EMAIL}")
    print(f"Enter the code within {OTP_VALIDITY_MINUTES} minutes.")

    # Verify the entered OTP
    for attempt in range(1, MAX_OTP_ATTEMPTS + 1):

        if time.monotonic() >= deadline:
            print("OTP expired. Restart to request a new OTP.")
            return False

        try:
            entered_otp = input("Enter OTP: ").strip()

        except (EOFError, KeyboardInterrupt):
            print("\nVerification cancelled.")
            return False

        if time.monotonic() >= deadline:
            print("OTP expired. Access denied.")
            return False

        if hmac.compare_digest(entered_otp, otp):

            activated_at = time.time()

            # Save activation safely
            try:
                temp_file = ACCESS_FILE.with_suffix(".tmp")

                temp_file.write_text(
                    json.dumps({
                        "activated_at": activated_at
                    }),
                    encoding="utf-8"
                )

                os.replace(temp_file, ACCESS_FILE)

            except OSError as exc:
                print(f"Could not save activation: {exc}")
                return False

            expiry = datetime.fromtimestamp(
                activated_at + VALIDITY_SECONDS
            ).astimezone()

            print("\nOTP verified successfully.")
            print(f"Access granted for {ACCESS_HOURS} hours.")
            print(
                "Expires at:",
                expiry.strftime("%d-%m-%Y %I:%M:%S %p %Z")
            )

            return True

        remaining_attempts = MAX_OTP_ATTEMPTS - attempt

        print(
            f"Incorrect OTP. Attempts remaining: "
            f"{remaining_attempts}"
        )

    print("Maximum attempts reached. Access denied.")
    return False


# ============================================================
# ACCESS GATE
# This must execute BEFORE your automation starts
# ============================================================

if not akld_require_access():
    sys.exit(1)




def cleanup_empty_folders_after_sync(main_dir):
    """
    Delete empty folders recursively, starting with the deepest folders.
    Never delete files or folders containing files.
    """

    main_dir = Path(main_dir)

    if not main_dir.is_dir():
        print(f"[CLEANUP SKIPPED] Main folder not found: {main_dir}")
        return

    print("\n" + "=" * 70)
    print("CLEANUP: REMOVE EMPTY FOLDERS ONLY")
    print(f"Main directory: {main_dir}")
    print("=" * 70)

    # Collect all subfolders, deepest first.
    folders = sorted(
        (folder for folder in main_dir.rglob("*") if folder.is_dir()),
        key=lambda folder: len(folder.parts),
        reverse=True
    )

    deleted_count = 0

    for folder in folders:
        try:
            # Delete only if the folder is completely empty.
            if not any(folder.iterdir()):
                folder.rmdir()
                deleted_count += 1
                print(f"[DELETED EMPTY FOLDER] {folder}")

        except (PermissionError, OSError) as error:
            print(f"[COULD NOT DELETE] {folder}: {error}")

    print(f"Empty folders deleted: {deleted_count}")
    print("CLEANUP FINISHED")
    print("=" * 70)


# ============================================================
# YOUR EXISTING AUTOMATION CODE STARTS BELOW THIS LINE
# ============================================================

# Keep your existing imports, functions and processing logic.
# If your program uses main(), call it here:
#
# if __name__ == "__main__":
#     main()


# =========================================================
# 0. STARTUP PASSWORD
# =========================================================



START_PASSWORD = "Ankit8"

password = getpass.getpass("Enter password: ")

if password != START_PASSWORD:
    print("Incorrect password.")
    sys.exit(1)

print("Password accepted.")



import shutil
from pathlib import Path


# =========================================================
# PENDENCY SHEET UPDATER
# =========================================================

if getattr(sys, "frozen", False):
    PROGRAM_DIR = Path(sys.executable).resolve().parent
else:
    PROGRAM_DIR = Path(__file__).resolve().parent

# Local folder used by the program
PENDENCY_DIR = PROGRAM_DIR / "SHEETS" / "PENDENCY"

LOCAL_PENDENCY = (
    PENDENCY_DIR / "Master Data of Pendency Detail.xlsx"
)

# Source Excel file in ANKIT folder
SOURCE_PENDENCY = Path(
    r"C:\Users\ankit.das1\OneDrive - Apollo Tyres Limited"
    r"\Gaurav Kumar Singh's files - Export final Doc"
    r"\ANKIT\Master Data of Pendency Detail.xlsx"
)


def update_pendency_sheet():
    # Create the local folder if it does not exist
    PENDENCY_DIR.mkdir(parents=True, exist_ok=True)

    # Refresh local copy if the source file exists
    if SOURCE_PENDENCY.is_file():
        try:
            shutil.copy2(SOURCE_PENDENCY, LOCAL_PENDENCY)
            print("[UPDATED] Pendency Excel refreshed from ANKIT folder.")

        except (PermissionError, OSError) as e:
            if LOCAL_PENDENCY.is_file():
                print(f"[WARNING] Source copy failed: {e}")
                print("[FALLBACK] Using existing local pendency Excel.")
            else:
                raise RuntimeError(
                    "Could not copy the source pendency file, "
                    "and no local copy exists."
                ) from e

    # If source is missing, use the local copy
    elif LOCAL_PENDENCY.is_file():
        print("[SOURCE MISSING] Using existing local pendency Excel.")

    # Neither file exists
    else:
        raise FileNotFoundError(
            "No pendency Excel file found.\n"
            f"Source: {SOURCE_PENDENCY}\n"
            f"Local: {LOCAL_PENDENCY}"
        )

    print(f"[READING] {LOCAL_PENDENCY}")
    return LOCAL_PENDENCY


# Get the Excel path for the main program
EXCEL_PATH = update_pendency_sheet()

# =========================================================
# 1. CONFIGURATION
# =========================================================



TARGET_SHEET = "Sheet1"


# ---------------------------------------------------------
# SOURCE FOLDER
# ---------------------------------------------------------
# IMPORTANT:
# This folder is READ-ONLY.
# The program only searches and copies from here.
# It does NOT delete, rename, move or modify anything.
# ---------------------------------------------------------

EXISTING_FOLDERS_DIR = Path(
    r"C:\Users\ankit.das1\OneDrive - Apollo Tyres Limited\Gaurav Kumar Singh's files - Export final Doc\FINAL DOCUMENTS 2026-2027"
)


# ---------------------------------------------------------
# OUTPUT FOLDER
# ---------------------------------------------------------


# ---------------------------------------------------------
# OUTPUT FOLDER
# ---------------------------------------------------------


if getattr(sys, "frozen", False):
    PROGRAM_DIR = Path(sys.executable).resolve().parent
else:
    PROGRAM_DIR = Path(__file__).resolve().parent

BASE_DIR = PROGRAM_DIR / "Main"
MAIN_DIR = BASE_DIR

DESTINATION_BASE_DIR = BASE_DIR

# Result Excel stays beside the program
RESULT_EXCEL = PROGRAM_DIR / "SHEETS" / "final document folder availability excel" / "Folder_Matching_Result.xlsx"



# =========================================================
# 2. PARSE COMMERCIAL INVOICE
# =========================================================

def parse_invoice(inv_no):

    if pd.isna(inv_no):
        return None, None, None

    parts = [
        p.strip()
        for p in str(inv_no).split("/")
        if p.strip()
    ]

    if len(parts) < 3:
        return None, None, None

    prefix = parts[0]
    series = parts[1]

    raw_id = parts[-1]

    # Remove leading zeros
    clean_id = raw_id.lstrip("0")

    if clean_id == "":
        clean_id = "0"

    return prefix, series, clean_id


# =========================================================
# 3. NORMALIZE NUMBER
# =========================================================

def normalize_number(value):

    value = str(value).strip()

    if value.isdigit():
        return str(int(value))

    return value


# =========================================================
# 4. FIND MATCHING FOLDER
# =========================================================

def find_matching_folder(
    base_dir,
    prefix,
    series,
    invoice_id
):

    """
    Example Excel invoice:

        OTH/M/000456

    These can match:

        OTH M 456
        OTH M 0456
        OTH M 000456
        OTH M 456, 111, 666
        OTH M 0456, 0987
        OTH M 456 111 666

    Because leading zeros are ignored.

    This does NOT match:

        OTH M 1456
        OTH Y 456
        ABC M 456
    """

    if not base_dir.exists():
        return None

    invoice_id = normalize_number(
        invoice_id
    )

    # Prefix + Series must be at the beginning
    prefix_series_pattern = re.compile(
        rf"^{re.escape(prefix)}\s+{re.escape(series)}\b",
        re.IGNORECASE
    )

    ''' 
    # -----------------------------------------------------
    # Search folders recursively
    # -----------------------------------------------------

    for item in base_dir.rglob("*"):

        if not item.is_dir():
            continue

        folder_name = item.name

        # Check OTH + M
        if not prefix_series_pattern.search(
            folder_name
        ):
            continue

        # Extract all numbers from folder name
        folder_numbers = re.findall(
            r"\d+",
            folder_name
        )

        # Remove leading zeros
        folder_numbers = [
            normalize_number(number)
            for number in folder_numbers
        ]

        # Check invoice number
        if invoice_id in folder_numbers:

            return item

    return None'''
    
        # -----------------------------------------------------
    # Search folders created or modified in the last 60 days
    # -----------------------------------------------------

    

    cutoff_timestamp = time.time() - (10* 24 * 60 * 60)

    for item in base_dir.rglob("*"):

        if not item.is_dir():
            continue

        try:
            stat_info = item.stat()

            # Keep folders created OR modified recently.
            if not (
                stat_info.st_ctime >= cutoff_timestamp
                or stat_info.st_mtime >= cutoff_timestamp
            ):
                continue

        except OSError:
            continue

        folder_name = item.name

        # Check OTH + M
        if not prefix_series_pattern.search(folder_name):
            continue

        # Extract all numbers from folder name
        folder_numbers = re.findall(
            r"\d+",
            folder_name
        )

        # Remove leading zeros
        folder_numbers = [
            normalize_number(number)
            for number in folder_numbers
        ]

        # Check invoice number
        if invoice_id in folder_numbers:
            return item

    return None




# =========================================================
# 5. CREATE FOLDER SEARCH NAME
# =========================================================

def create_folder_search_name(value):

    if pd.isna(value):
        return ""

    parts = [
        p.strip()
        for p in str(value).split("/")
        if p.strip()
    ]

    if len(parts) < 3:
        return str(value)

    prefix = parts[0]
    series = parts[1]

    invoice_number = normalize_number(
        parts[-1]
    )

    return (
        f"{prefix} "
        f"{series} "
        f"{invoice_number}"
    )


# =========================================================
# 6. COPY / SYNC FOLDER WITH BL RENAMING
# =========================================================

def should_keep_existing_bl_name(file_name):
    """
    If the filename already contains BL anywhere, keep the
    original filename exactly as it is.
    """

    return "bl" in file_name.lower()


def is_bl_rename_candidate(file_name, bl_no):
    """
    Rename only during copying when:
    1. filename contains the BL number, OR
    2. filename contains BAL / SWB, OR
    3. filename contains Sea Waybill variations.

    If filename already contains BL, it is NOT renamed.
    """

    name_lower = file_name.lower()

    # If BL is already anywhere in the filename, do nothing.
    if should_keep_existing_bl_name(file_name):
        return False

    # BL number in filename.
    if not pd.isna(bl_no):
        bl_text = str(bl_no).strip()

        if bl_text and bl_text.lower() != "nan":
            if bl_text.lower() in name_lower:
                return True

    # BAL / SWB / BAL SWB.
    if re.search(
        r"(?<![a-z0-9])(bal|swb)(?![a-z0-9])",
        name_lower,
        re.IGNORECASE
    ):
        return True

    # Sea Waybill / Sea Way Bill / Seaway Bill / Seawaybill.
    if re.search(
        r"sea[\s_-]*way[\s_-]*bill",
        name_lower,
        re.IGNORECASE
    ):
        return True

    return False


def copy_folder_with_bl_renaming(
    source_folder,
    destination_folder,
    bl_no
):
    """
    Copy/sync the folder file-by-file.

    IMPORTANT:
    - Source files are never renamed or modified.
    - If a filename already contains BL anywhere, keep it unchanged.
    - BAL / SWB / Sea Waybill / BL-number filenames are renamed
      during destination copying only.
    - The extension is preserved.
    """

    destination_folder.mkdir(
        parents=True,
        exist_ok=True
    )

    for source_item in source_folder.rglob("*"):

        relative_path = source_item.relative_to(
            source_folder
        )

        if source_item.is_dir():

            (
                destination_folder
                / relative_path
            ).mkdir(
                parents=True,
                exist_ok=True
            )

            continue

        destination_relative = relative_path

        if is_bl_rename_candidate(
            source_item.name,
            bl_no
        ):

            destination_relative = (
                relative_path.parent
                / f"BL{source_item.suffix}"
            )

        destination_file = (
            destination_folder
            / destination_relative
        )

        destination_file.parent.mkdir(
            parents=True,
            exist_ok=True
        )

        # Do not overwrite an existing destination BL file
        # with a second BL candidate.
        if (
            destination_file.exists()
            and destination_file.name.lower()
            == f"bl{source_item.suffix}".lower()
            and destination_file.resolve()
            != source_item.resolve()
        ):

            # If the source itself already maps to the same
            # destination filename, preserve the existing file.
            if destination_relative.name.lower().startswith("bl"):
                continue

        shutil.copy2(
            source_item,
            destination_file
        )


# =========================================================
# 7. CHECK SOURCE FOLDER
# =========================================================

if not EXISTING_FOLDERS_DIR.exists():

    raise FileNotFoundError(
        "\nSource folder does not exist:\n"
        f"{EXISTING_FOLDERS_DIR.resolve()}\n"
    )


# =========================================================
# 7. FIND SHIP TO PARTY COLUMN
# =========================================================

def find_ship_to_party_column(columns):
    """
    Find the Ship To Party column without requiring one exact
    capitalisation/spelling of the header.
    """

    normalized_columns = {
        re.sub(r"[^a-z0-9]+", "", str(column).lower()): column
        for column in columns
    }

    # Exact/common normalized header names first.
    candidates = [
        "shiptopartyname",
        "shiptoparty",
        "shiptopartyname1",
        "shiptoname",
    ]

    for candidate in candidates:
        if candidate in normalized_columns:
            return normalized_columns[candidate]

    # Flexible fallback.
    for normalized, original in normalized_columns.items():
        if "shipto" in normalized and "party" in normalized:
            return original

    return None


# =========================================================
# 8. READ EXCEL
# =========================================================

print("\n")
print("=" * 70)
print("READING EXCEL")
print("=" * 70)

df = pd.read_excel(
    EXCEL_PATH,
    sheet_name=TARGET_SHEET
)

SHIP_TO_PARTY_COLUMN = find_ship_to_party_column(
    df.columns
)

if SHIP_TO_PARTY_COLUMN is None:

    raise ValueError(
        "Ship To Party column was not found. "
        "Available columns: "
        + ", ".join(map(str, df.columns))
    )

print(
    f"Ship To Party column found: "
    f"{SHIP_TO_PARTY_COLUMN}"
)

print(
    f"Total rows in Excel: {len(df)}"
)


# =========================================================
# 8. CHECK REQUIRED COLUMNS
# =========================================================

required_columns = [
    "Scan Date",
    "BL NO.",
    "COMM. INV. NO.",
    "REGION",
    "Country of Final Des"
]

missing_columns = [
    column
    for column in required_columns
    if column not in df.columns
]

if missing_columns:

    raise KeyError(
        "\nMissing required Excel columns:\n"
        f"{missing_columns}\n"
    )



# =========================================================
# CLEANUP COMPLETED FOLDERS FROM MAIN
# =========================================================

# SAFETY SWITCH:
# True  = preview only; no folders are deleted.
# False = permanently delete confirmed completed folders.
DRY_RUN_CLEANUP = True


def normalize_invoice(invoice):
    """
    Normalize invoices such as:
    OTH/M/EXP/26/005678
    OTH/M/EXP/26/5678
    """

    if pd.isna(invoice):
        return None

    parts = [
        part.strip().upper()
        for part in str(invoice).split("/")
    ]

    if len(parts) != 5:
        return None

    prefix, series, invoice_type, year, number = parts

    if not number.isdigit():
        return None

    return (
        f"{prefix}/{series}/{invoice_type}/{year}/"
        f"{number.zfill(6)}"
    )


# =========================================================
# CLEANUP COMPLETED OTH FOLDERS AND EMPTY PARENT FOLDERS
# =========================================================

# True  = preview only; no folders are deleted.
# False = permanently delete qualifying folders.
DRY_RUN_CLEANUP = True


def normalize_invoice(invoice):
    """
    Normalize invoice numbers:
    OTH/M/EXP/26/005678
    OTH/M/EXP/26/5678
    """

    if pd.isna(invoice):
        return None

    parts = [
        part.strip().upper()
        for part in str(invoice).split("/")
    ]

    if len(parts) != 5:
        return None

    prefix, series, invoice_type, year, number = parts

    if not number.isdigit():
        return None

    return (
        f"{prefix}/{series}/{invoice_type}/{year}/"
        f"{number.zfill(6)}"
    )


def folder_has_files(folder):
    """Check whether a folder contains files anywhere inside it."""

    try:
        return any(
            path.is_file()
            for path in folder.rglob("*")
        )
    except OSError:
        # Keep folders when their contents cannot be checked.
        return True


def contains_oth_with_files(folder):
    """
    Return True if any OTH folder beneath this folder
    contains at least one file.
    """

    try:
        for item in folder.rglob("*"):
            if not item.is_dir():
                continue

            if re.match(
                r"^OTH(?:\s|$)",
                item.name,
                re.IGNORECASE
            ):
                if folder_has_files(item):
                    return True

    except OSError:
        # Fail safely if a folder cannot be inspected.
        return True

    return False


def remove_folder(folder):
    """Delete a folder, or preview its deletion."""

    if DRY_RUN_CLEANUP:
        print(f"[DRY RUN - WOULD DELETE FOLDER] {folder}")
        return True

    try:
        shutil.rmtree(folder)
        print(f"[DELETED FOLDER] {folder}")
        return True

    except OSError as error:
        print(f"[DELETE ERROR] {folder}: {error}")
        return False


def cleanup_completed_folders(main_dir, df):
    """
    1. Delete completed OTH folders.
    2. Remove empty Ship To Party folders.
    3. Remove empty Country folders.
    4. Remove empty Region folders.

    Only operates inside the local Main directory.
    """

    main_dir = Path(main_dir).resolve()

    if not main_dir.is_dir():
        print(
            f"[CLEANUP SKIPPED] Main folder does not exist: "
            f"{main_dir}"
        )
        return

    required = ["COMM. INV. NO.", "Scan Date"]

    missing = [
        col for col in required
        if col not in df.columns
    ]

    if missing:
        raise KeyError(
            f"Missing required columns: {missing}"
        )

    # -----------------------------------------------------
    # 1. BUILD INVOICE STATUS LOOKUP
    # -----------------------------------------------------

    invoice_status = {}

    for _, row in df.iterrows():
        invoice_key = normalize_invoice(
            row["COMM. INV. NO."]
        )

        if invoice_key is None:
            continue

        scan_date = row["Scan Date"]

        is_complete = (
            pd.notna(scan_date)
            and str(scan_date).strip() != ""
        )

        # If duplicate rows disagree, keep the invoice
        # pending unless every matching row is complete.
        if invoice_key not in invoice_status:
            invoice_status[invoice_key] = is_complete
        else:
            invoice_status[invoice_key] = (
                invoice_status[invoice_key]
                and is_complete
            )

    print("\n" + "=" * 70)
    print("CLEANUP: COMPLETED OTH FOLDERS")
    print(f"Main directory: {main_dir}")
    print(
        "Mode:",
        "DRY RUN - NO DELETION"
        if DRY_RUN_CLEANUP
        else "LIVE - DELETION ENABLED"
    )
    print("=" * 70)

    # -----------------------------------------------------
    # 2. FIND AND DELETE COMPLETED OTH FOLDERS
    # -----------------------------------------------------

    # Search only folders whose names begin with OTH.
    oth_folders = sorted(
        (
            path for path in main_dir.rglob("*")
            if path.is_dir()
            and re.match(
                r"^OTH(?:\s|$)",
                path.name,
                re.IGNORECASE
            )
        ),
        key=lambda path: len(path.parts)
    )

    for folder_path in oth_folders:

        # It may already have been removed with a parent.
        if not folder_path.exists():
            continue

        # Expected examples:
        # OTH M 5678
        # OTH M 5678, 9656
        match = re.match(
            r"^OTH\s+([A-Z]+)\s+(.+)$",
            folder_path.name.strip(),
            re.IGNORECASE
        )

        if not match:
            print(f"[KEEP - UNKNOWN FOLDER FORMAT] {folder_path}")
            continue

        series, remainder = match.groups()

                # Use ONLY the first invoice number in the folder name.
        numbers = re.findall(r"\d+", remainder)

        if not numbers:
            print(f"[KEEP - NO INVOICE NUMBER] {folder_path}")
            continue

        first_number = numbers[0]

        invoice_key = normalize_invoice(
            f"OTH/{series}/EXP/26/{first_number}"
        )

        status = invoice_status.get(invoice_key)

        if status is None:
            print(f"[KEEP - INVOICE NOT FOUND IN EXCEL] {folder_path}")
            print(f"  Invoice: {invoice_key}")
            continue

        if status is True:
            print(f"[DELETE - SCAN DATE POPULATED] {folder_path}")
            remove_folder(folder_path)
        else:
            print(f"[KEEP - PENDING SYNC] {folder_path}")
            print(f"  Invoice: {invoice_key}")


        # -----------------------------------------------------

    print("=" * 70)
    print("CLEANUP FINISHED")
    print("=" * 70)


# =========================================================
# RUN CLEANUP
# =========================================================

cleanup_completed_folders(MAIN_DIR, df)
# =========================================================
# 9. FILTER BLANK SCAN DATE
# =========================================================

scan_date_blank = (
    df["Scan Date"].isna()
    | df["Scan Date"].astype(str).str.strip().eq("")
)

blank_date = df[scan_date_blank].copy()

print(
    f"Rows with blank Scan Date: "
    f"{len(blank_date)}"
)


# =========================================================
# 10. CREATE FOLDER SEARCH NAME
# =========================================================

blank_date["FOLDER SEARCH NAME"] = (
    blank_date[
        "COMM. INV. NO."
    ]
    .apply(create_folder_search_name)
)


# =========================================================
# 11. RESULT COLUMNS
# =========================================================

blank_date["FOLDER STATUS"] = ""

blank_date["FOLDER MATCHED INVOICE"] = ""

blank_date["FOLDER MATCHED NAME"] = ""

blank_date["PROCESS STATUS"] = ""

blank_date["ERROR DETAILS"] = ""


# =========================================================
# 12. ERROR LIST
# =========================================================

errors = []


# =========================================================
# 13. GROUP BY BL
# =========================================================

grouped_bl = blank_date.groupby(
    "BL NO.",
    dropna=False
)

print(
    f"Unique BLs to process: "
    f"{len(grouped_bl)}"
)


# =========================================================
# 14. PROCESS EACH BL
# =========================================================

for bl_no, group in grouped_bl:

    print("\n")
    print("=" * 70)
    print(
        f"PROCESSING BL: {bl_no}"
    )
    print("=" * 70)

    try:

        # =================================================
        # REGION
        # =================================================

        region = group[
            "REGION"
        ].iloc[0]

        if pd.isna(region):

            region = "Region Missing"

        else:

            region = str(
                region
            ).strip()


        # =================================================
        # COUNTRY
        # =================================================

        country = group[
            "Country of Final Des"
        ].iloc[0]

        if pd.isna(country):

            country = "Country Missing"

        else:

            country = str(
                country
            ).strip()


        print(
            f"Region : {region}"
        )

        print(
            f"Country: {country}"
        )


        # =================================================
        # SHIP TO PARTY NAME
        # =================================================

        ship_to_party = group[
            SHIP_TO_PARTY_COLUMN
        ].iloc[0]

        if pd.isna(ship_to_party):

            ship_to_party = "Ship To Party Missing"

        else:

            ship_to_party = str(
                ship_to_party
            ).strip()

            if not ship_to_party:
                ship_to_party = "Ship To Party Missing"


        print(
            f"Ship To Party: {ship_to_party}"
        )


        # =================================================
        # ALL INVOICES FOR THIS BL
        # =================================================

        invoices = (
            group[
                "COMM. INV. NO."
            ]
            .dropna()
            .astype(str)
            .unique()
        )


        print(
            "\nInvoices for this BL:"
        )

        for inv in invoices:

            print(
                f"  {inv}"
            )


        matched_folder = None

        matched_invoice = None



        # =================================================
        # TRY INVOICES ONE BY ONE
        # =================================================

        matched_folder = None
        matched_invoice = None

        for inv_no in invoices:
            prefix, series, invoice_id = parse_invoice(inv_no)

            # Invalid invoice: try the next invoice for this BL.
            if not (prefix and series and invoice_id):
                print(f"[INVALID INVOICE - TRY NEXT] {inv_no}")
                continue

            print(f"[SEARCHING INVOICE] {inv_no}")

            matched_folder = find_matching_folder(
                EXISTING_FOLDERS_DIR,
                prefix,
                series,
                invoice_id
            )

            if matched_folder:
                matched_invoice = inv_no
                print(f"[FOLDER FOUND] {matched_folder}")
                break

            # Valid invoice searched but folder not found:
            # skip this BL without trying its remaining invoices.
            print(f"[FOLDER MISSING] {inv_no} — skipping BL {bl_no}")
            break

        if not matched_folder:
            blank_date.loc[
                group.index, "FOLDER STATUS"
            ] = "Folder Missing"

            blank_date.loc[
                group.index, "PROCESS STATUS"
            ] = "Folder Missing"

            continue

        
        # =================================================
        # DESTINATION REGION / COUNTRY
        # =================================================

        target_dest_dir = (
            DESTINATION_BASE_DIR
            / region
            / country
            / ship_to_party
        )

        target_dest_dir.mkdir(
            parents=True,
            exist_ok=True
        )

        # =================================================
        # COPY / SYNC MATCHED FOLDER
        # =================================================

        dest_folder_path = (
            target_dest_dir
            / matched_folder.name
        )

        print("\n[SYNCING MATCHED FOLDER]")
        print(f"FROM: {matched_folder}")
        print(f"TO: {dest_folder_path}")

        copy_folder_with_bl_renaming(
            matched_folder,
            dest_folder_path,
            bl_no
        )

        print("\n[SYNC COMPLETE]")

        # =================================================
        # UPDATE RESULT
        # =================================================

        blank_date.loc[
            group.index, "FOLDER STATUS"
        ] = "Copied"

        blank_date.loc[
            group.index, "FOLDER MATCHED INVOICE"
        ] = matched_invoice

        blank_date.loc[
            group.index, "FOLDER MATCHED NAME"
        ] = matched_folder.name

        blank_date.loc[
            group.index, "PROCESS STATUS"
        ] = "Completed"


    # =====================================================
    # ERROR HANDLING
    # =====================================================

    except Exception as e:

        error_text = (
            f"{type(e).__name__}: {str(e)}"
        )

        full_traceback = (
            traceback.format_exc()
        )


        print("\n")
        print("=" * 70)
        print(
            "[ERROR - BL FAILED]"
        )
        print("=" * 70)

        print(
            f"BL: {bl_no}"
        )

        print(
            f"Error: {error_text}"
        )

        print("\n")
        print(
            "Full traceback:"
        )

        print(
            full_traceback
        )


        # -------------------------------------------------
        # SAVE ERROR
        # -------------------------------------------------

        errors.append(
            {
                "BL NO.": bl_no,
                "Error": error_text,
                "Traceback": full_traceback
            }
        )


        blank_date.loc[
            group.index,
            "PROCESS STATUS"
        ] = "ERROR"


        blank_date.loc[
            group.index,
            "ERROR DETAILS"
        ] = error_text


        # -------------------------------------------------
        # DO NOT STOP WHOLE PROGRAM
        # -------------------------------------------------

        print("\n")
        print(
            "[CONTINUING WITH NEXT BL]"
        )


# =========================================================
# 15. SAVE RESULT EXCEL
# =========================================================

print("\n")
print("=" * 70)
print("SAVING RESULT EXCEL")
print("=" * 70)


try:

    RESULT_EXCEL.parent.mkdir(
        parents=True,
        exist_ok=True
    )


    blank_date.to_excel(
        RESULT_EXCEL,
        index=False
    )


    print(
        "Result Excel saved:"
    )

    print(
        RESULT_EXCEL.resolve()
    )


except Exception as e:

    error_text = (
        f"{type(e).__name__}: {str(e)}"
    )

    full_traceback = (
        traceback.format_exc()
    )


    print("\n")
    print(
        "[EXCEL SAVE ERROR]"
    )

    print(
        error_text
    )


    errors.append(
        {
            "BL NO.": "EXCEL SAVE",
            "Error": error_text,
            "Traceback": full_traceback
        }
    )


# =========================================================
# SECOND CLEANUP — AFTER SYNCING
# =========================================================

cleanup_empty_folders_after_sync(MAIN_DIR)
# =========================================================
# 16. DATE FORMAT
# =========================================================
# Kept from the earlier version.
# Only formatting; no date logic is changed.
# =========================================================

try:

    DATE_COLUMNS = [
        "Date",
        "COMM. INV. DATE",
        "SOB Date",
        "ETA",
        "Scan Date"
    ]


    wb = load_workbook(
        RESULT_EXCEL
    )

    ws = wb.active


    column_positions = {
        cell.value: cell.column
        for cell in ws[1]
    }


    for column_name in DATE_COLUMNS:

        if column_name not in column_positions:
            continue


        column_number = (
            column_positions[
                column_name
            ]
        )


        for row in range(
            2,
            ws.max_row + 1
        ):

            cell = ws.cell(
                row=row,
                column=column_number
            )


            if cell.value is not None:

                cell.number_format = (
                    "dd-mm-yyyy"
                )


    wb.save(
        RESULT_EXCEL
    )


except Exception as e:

    error_text = (
        f"{type(e).__name__}: {str(e)}"
    )

    full_traceback = (
        traceback.format_exc()
    )


    print("\n")
    print(
        "[DATE FORMAT ERROR]"
    )

    print(
        error_text
    )


    errors.append(
        {
            "BL NO.": "DATE FORMAT",
            "Error": error_text,
            "Traceback": full_traceback
        }
    )


# =========================================================
# 17. FINAL SUMMARY
# =========================================================

print("\n")
print("=" * 70)
print("PROCESS FINISHED")
print("=" * 70)


print(
    f"Total blank-date rows : "
    f"{len(blank_date)}"
)


print(f"Copied rows           : {(blank_date['FOLDER STATUS'] == 'Copied').sum()}")


print(f"Folder Missing rows   : {(blank_date['FOLDER STATUS'] == 'Folder Missing').sum()}")


print(f"Error rows            : {(blank_date['PROCESS STATUS'] == 'ERROR').sum()}")


print("\n")
print(
    "Result Excel:"
)

print(
    RESULT_EXCEL.resolve()
)


# =========================================================
# 18. SHOW ERRORS
# =========================================================

if errors:

    print("\n")
    print("=" * 70)
    print("ERRORS FOUND")
    print("=" * 70)


    for number, error in enumerate(
        errors,
        start=1
    ):

        print("\n")
        print(
            f"ERROR #{number}"
        )

        print(
            f"BL: {error['BL NO.']}"
        )

        print(
            f"Reason: {error['Error']}"
        )

        print("\n")
        print(
            "Traceback:"
        )

        print(
            error["Traceback"]
        )


    print("\n")
    print("=" * 70)
    print(
        "PROGRAM FINISHED WITH ERRORS"
    )
    print(
        "Result Excel has been saved."
    )
    print(
        "Press ENTER to close."
    )
    print("=" * 70)


else:

    print("\n")
    print("=" * 70)
    print(
        "NO ERRORS"
    )
    print(
        "PROCESS COMPLETED SUCCESSFULLY"
    )
    print("=" * 70)

    print(
        "\nPress ENTER to close."
    )
    input()


