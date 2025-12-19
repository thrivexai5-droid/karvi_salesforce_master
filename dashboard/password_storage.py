import json
import os
from django.conf import settings

class PasswordStorage:
    """Simple password storage system"""
    
    def __init__(self):
        self.storage_file = os.path.join(settings.BASE_DIR, 'user_passwords.json')
        self.passwords = self._load_passwords()
    
    def _load_passwords(self):
        """Load passwords from file"""
        if os.path.exists(self.storage_file):
            try:
                with open(self.storage_file, 'r') as f:
                    return json.load(f)
            except:
                return {}
        return {}
    
    def _save_passwords(self):
        """Save passwords to file"""
        try:
            with open(self.storage_file, 'w') as f:
                json.dump(self.passwords, f, indent=2)
        except:
            pass
    
    def store_password(self, username, password):
        """Store a password for a user"""
        self.passwords[username] = password
        self._save_passwords()
    
    def get_password(self, username):
        """Get stored password for a user"""
        return self.passwords.get(username, f"{username}123@")
    
    def remove_password(self, username):
        """Remove stored password for a user"""
        if username in self.passwords:
            del self.passwords[username]
            self._save_passwords()

# Global instance
password_storage = PasswordStorage()