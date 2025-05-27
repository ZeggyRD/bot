import os
import json
import random
import logging
from datetime import datetime, timedelta

# Setup logger
logger = logging.getLogger("AccountOrchestrator")
# Basic logging configuration (can be refined later if a central logging setup is made)
if not logger.handlers:
    handler = logging.StreamHandler()
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)

ACCOUNTS_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data", "accounts.txt")
# ACCOUNTS_DB_FILE will store metadata like last_used, status, etc.
ACCOUNTS_DB_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data", "account_orchestrator_db.json")

RECENT_USE_THRESHOLD_HOURS = 12 # Define "recent" use on the same device

class AccountOrchestrator:
    def __init__(self):
        self.accounts_data = {}  # Stores credentials: {email: password}
        self.accounts_metadata = {}  # Stores metadata: {email: {status, last_used, device_id, etc.}}
        self._load_accounts_from_file()
        self._load_accounts_metadata()

    def _load_accounts_from_file(self):
        """Loads account credentials (email:password) from the primary ACCOUNTS_FILE."""
        logger.info(f"Loading accounts from {ACCOUNTS_FILE}...")
        if not os.path.exists(ACCOUNTS_FILE):
            logger.error(f"Accounts file not found: {ACCOUNTS_FILE}")
            # Create an empty accounts.txt if it doesn't exist, so the rest of the logic can proceed smoothly
            try:
                logger.info(f"Creating empty accounts file at {ACCOUNTS_FILE} as it was not found.")
                os.makedirs(os.path.dirname(ACCOUNTS_FILE), exist_ok=True)
                with open(ACCOUNTS_FILE, 'w') as f:
                    f.write("# Add accounts in email:password format\n")
            except Exception as e:
                logger.error(f"Failed to create empty accounts file {ACCOUNTS_FILE}: {e}")
            return

        temp_accounts_data = {}
        try:
            with open(ACCOUNTS_FILE, 'r') as f:
                for i, line in enumerate(f):
                    line = line.strip()
                    if not line or line.startswith("#"):
                        continue
                    parts = line.split(":", 1)
                    if len(parts) == 2:
                        email, password = parts
                        if email in temp_accounts_data:
                            logger.warning(f"Duplicate email {email} found in {ACCOUNTS_FILE} at line {i+1}. Keeping first instance.")
                        else:
                            temp_accounts_data[email] = password
                    else:
                        logger.warning(f"Malformed line in {ACCOUNTS_FILE} at line {i+1}: {line}")
            self.accounts_data = temp_accounts_data
            logger.info(f"Successfully loaded {len(self.accounts_data)} account credentials.")
        except Exception as e:
            logger.error(f"Error loading accounts from {ACCOUNTS_FILE}: {e}")

    def _load_accounts_metadata(self):
        """Loads account metadata from ACCOUNTS_DB_FILE. Creates default metadata if an account exists in ACCOUNTS_FILE but not in metadata."""
        logger.info(f"Loading accounts metadata from {ACCOUNTS_DB_FILE}...")
        if os.path.exists(ACCOUNTS_DB_FILE):
            try:
                with open(ACCOUNTS_DB_FILE, 'r') as f:
                    self.accounts_metadata = json.load(f)
                logger.info(f"Loaded metadata for {len(self.accounts_metadata)} accounts.")
            except Exception as e:
                logger.error(f"Error loading accounts metadata from {ACCOUNTS_DB_FILE}: {e}. Initializing with empty metadata.")
                self.accounts_metadata = {}
        else:
            logger.info(f"Metadata file {ACCOUNTS_DB_FILE} not found. Initializing with empty metadata.")
            self.accounts_metadata = {}

        # Ensure all loaded accounts have at least default metadata
        updated_metadata = False
        for email in self.accounts_data.keys():
            if email not in self.accounts_metadata:
                logger.info(f"No metadata found for account {email}. Creating default entry.")
                self.accounts_metadata[email] = {
                    "status": "active",  # active, needs_login, locked, problematic
                    "last_used_timestamp": None,
                    "assigned_device_id": None,
                    "login_attempts": 0,
                    "successful_logins": 0,
                    "last_login_timestamp": None,
                    "last_error": None
                }
                updated_metadata = True
        
        if updated_metadata:
            self._save_accounts_metadata() # Save if new entries were added

    def _save_accounts_metadata(self):
        """Saves the current state of accounts_metadata to ACCOUNTS_DB_FILE."""
        logger.debug(f"Saving accounts metadata to {ACCOUNTS_DB_FILE}...")
        try:
            os.makedirs(os.path.dirname(ACCOUNTS_DB_FILE), exist_ok=True)
            with open(ACCOUNTS_DB_FILE, 'w') as f:
                json.dump(self.accounts_metadata, f, indent=4)
            logger.info(f"Successfully saved metadata for {len(self.accounts_metadata)} accounts.")
        except Exception as e:
            logger.error(f"Error saving accounts metadata to {ACCOUNTS_DB_FILE}: {e}")

    def get_account_for_session(self, device_id: str) -> tuple[str, str] | None:
        logger.info(f"Attempting to get account for device_id: {device_id}")
        
        candidate_accounts = []
        now = datetime.now()

        for email, password in self.accounts_data.items():
            meta = self.accounts_metadata.get(email)
            if meta and meta["status"] == "active":
                last_used_ts_str = meta.get("last_used_timestamp")
                last_used_dt = None
                if last_used_ts_str:
                    try:
                        last_used_dt = datetime.fromisoformat(last_used_ts_str)
                    except ValueError:
                        logger.warning(f"Could not parse last_used_timestamp '{last_used_ts_str}' for account {email}")
                
                used_on_this_device_recently = False
                if meta.get("assigned_device_id") == device_id and last_used_dt:
                    if (now - last_used_dt) < timedelta(hours=RECENT_USE_THRESHOLD_HOURS):
                        used_on_this_device_recently = True
                
                candidate_accounts.append({
                    "email": email,
                    "password": password,
                    "last_used_dt": last_used_dt,
                    "used_on_this_device_recently": used_on_this_device_recently,
                    "original_email_order": email # For consistent tie-breaking
                })
        
        if not candidate_accounts:
            logger.warning(f"No active accounts found in metadata for device {device_id}.")
            return None

        # Sort candidates:
        # 1. Prefer accounts NOT used on this device recently (False comes before True).
        # 2. Prefer accounts that are None (never used) for last_used_dt (False for 'is not None' comes first).
        # 3. Prefer accounts with older last_used_dt (datetime.min for None ensures they are treated as oldest).
        # 4. Tie-break with original email string order for consistent round-robin like behavior.
        candidate_accounts.sort(key=lambda x: (
            x["used_on_this_device_recently"],
            x["last_used_dt"] is not None, 
            x["last_used_dt"] if x["last_used_dt"] else datetime.min, 
            x["original_email_order"]
        ))
        
        # Log sorted candidates for debugging if needed (use logger.debug)
        # logger.debug(f"Sorted candidate accounts: {candidate_accounts}")

        selected_account_details = candidate_accounts[0]
        selected_email = selected_account_details["email"]
        selected_password = selected_account_details["password"]
        
        # Update metadata
        self.accounts_metadata[selected_email]["last_used_timestamp"] = now.isoformat()
        self.accounts_metadata[selected_email]["assigned_device_id"] = device_id
        self.accounts_metadata[selected_email]["login_attempts"] = 0 # Reset on new assignment
        self._save_accounts_metadata()
        
        logger.info(f"Assigned account {selected_email} to device {device_id}. Last used: {selected_account_details['last_used_dt']}. Used on this device recently: {selected_account_details['used_on_this_device_recently']}.")
        return selected_email, selected_password

    def report_login_success(self, email: str, device_id: str):
        if email in self.accounts_metadata:
            self.accounts_metadata[email]["successful_logins"] = self.accounts_metadata[email].get("successful_logins", 0) + 1
            self.accounts_metadata[email]["last_login_timestamp"] = datetime.now().isoformat()
            self.accounts_metadata[email]["login_attempts"] = 0 # Reset attempts on success
            self.accounts_metadata[email]["status"] = "active" # Ensure it's marked active
            self.accounts_metadata[email]["assigned_device_id"] = device_id # Confirm assignment
            self.accounts_metadata[email]["last_error"] = None
            self._save_accounts_metadata()
            logger.info(f"Login success reported for {email} on {device_id}.")
        else:
            logger.warning(f"Cannot report login success for unknown account: {email}")

    def report_login_failure(self, email: str, device_id: str, error_message: str = "Unknown error"):
        if email in self.accounts_metadata:
            self.accounts_metadata[email]["login_attempts"] = self.accounts_metadata[email].get("login_attempts", 0) + 1
            self.accounts_metadata[email]["last_error"] = error_message
            
            # Basic logic: if too many attempts, mark as problematic
            if self.accounts_metadata[email]["login_attempts"] >= 3: # Configurable threshold
                self.accounts_metadata[email]["status"] = "problematic"
                logger.warning(f"Account {email} marked as problematic after {self.accounts_metadata[email]['login_attempts']} failed attempts on {device_id}.")
            
            self._save_accounts_metadata()
            logger.info(f"Login failure reported for {email} on {device_id}: {error_message}")
        else:
            logger.warning(f"Cannot report login failure for unknown account: {email}")
    
    def update_account_status(self, email: str, new_status: str):
        if email in self.accounts_metadata:
            self.accounts_metadata[email]["status"] = new_status
            self._save_accounts_metadata()
            logger.info(f"Status for account {email} updated to {new_status}.")
        else:
            logger.warning(f"Cannot update status for unknown account: {email}")


if __name__ == '__main__':
    orchestrator = AccountOrchestrator()
    print(f"Loaded {len(orchestrator.accounts_data)} accounts.")
    if orchestrator.accounts_data:
        # Test getting an account
        test_device_id = "test_device_123"
        account_info = orchestrator.get_account_for_session(test_device_id)
        if account_info:
            email, password = account_info
            print(f"Assigned account for {test_device_id}: {email}")
            
            # Test reporting success
            orchestrator.report_login_success(email, test_device_id)
            print(f"Metadata for {email}: {orchestrator.accounts_metadata.get(email)}")

            # Test getting another account (should ideally be different if multiple exist)
            account_info_2 = orchestrator.get_account_for_session("test_device_456")
            if account_info_2:
                 print(f"Assigned account for test_device_456: {account_info_2[0]}")

            # Test reporting failure
            orchestrator.report_login_failure(email, test_device_id, "Simulated login error")
            orchestrator.report_login_failure(email, test_device_id, "Simulated login error")
            orchestrator.report_login_failure(email, test_device_id, "Simulated login error - now problematic")
            print(f"Metadata for {email} after failures: {orchestrator.accounts_metadata.get(email)}")


        else:
            print(f"Could not assign an account to {test_device_id}.")
    else:
        print("No accounts loaded to test.")
