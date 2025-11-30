# Shoonya Credentials Setup Guide

## Where to Enter Shoonya User Details

There are **three ways** to provide your Shoonya credentials:

---

## Option 1: Configuration File (Recommended for Development)

**File**: `d:\pyqt_app\config.yaml`

### Step 1: Open Shoonya Account
1. Visit https://shoonya.com
2. Create an account if you don't have one
3. Complete KYC verification

### Step 2: Get API Credentials
1. Login to **Prism**: https://prism.shoonya.com
2. Go to **Profile → Settings**
3. Navigate to **API** section
4. Click **"Generate API Key"**
5. Note down:
   - **User ID** (e.g., FA12345)
   - **Vendor Code**
   - **API Key**

### Step 3: Configure TOTP (Optional but Recommended)
1. In Prism, enable **Two-Factor Authentication (2FA)**
2. Use an authenticator app (Google Authenticator, Authy, etc.)
3. **Important**: Save the **TOTP secret key** (base32 format)
4. This allows automatic login without manual OTP entry

### Step 4: Update config.yaml

```yaml
broker:
  type: "shoonya"  # Change from "dummy" to "shoonya"

shoonya:
  auth:
    user_id: "FA12345"           # Your Shoonya user ID
    password: "YourPassword"     # Your password
    vendor_code: "YOUR_VENDOR"   # From API settings
    api_key: "YOUR_API_KEY"      # From API settings
    
    # If you have TOTP configured:
    totp_enabled: true
    totp_key: "YOUR_TOTP_SECRET_BASE32"  # From 2FA setup
    
    imei: "auto"
```

> **⚠️ SECURITY WARNING**: 
> - **Never commit** `config.yaml` with real credentials to Git!
> - Add `config.yaml` to `.gitignore`
> - Use environment variables for production

---

## Option 2: Environment Variables (Recommended for Production)

Create a `.env` file:

```bash
# .env (DO NOT COMMIT THIS FILE)
SHOONYA_USER_ID=FA12345
SHOONYA_PASSWORD=YourPassword
SHOONYA_VENDOR_CODE=YOUR_VENDOR
SHOONYA_API_KEY=YOUR_API_KEY
SHOONYA_TOTP_KEY=YOUR_TOTP_SECRET
```

Then update the code to read from environment:

```python
# In shoonya authentication module
import os
from dotenv import load_dotenv

load_dotenv()

user_id = os.getenv('SHOONYA_USER_ID')
password = os.getenv('SHOONYA_PASSWORD')
vendor_code = os.getenv('SHOONYA_VENDOR_CODE')
api_key = os.getenv('SHOONYA_API_KEY')
totp_key = os.getenv('SHOONYA_TOTP_KEY')
```

---

## Option 3: Login Dialog (Best for End Users)

For a production application, create a login dialog where users enter credentials at runtime.

**File**: `ui/brokers/shoonya_login.py` (to be created)

```python
from PyQt5.QtWidgets import QDialog, QLineEdit, QLabel, QPushButton

class ShoonyaLoginDialog(QDialog):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Shoonya Login")
        
        # Create input fields
        self.user_id_input = QLineEdit()
        self.password_input = QLineEdit()
        self.password_input.setEchoMode(QLineEdit.Password)
        
        self.otp_input = QLineEdit()
        self.otp_input.setPlaceholderText("6-digit OTP")
        
        # Login button
        self.login_button = QPushButton("Login")
        self.login_button.clicked.connect(self.accept)
    
    def get_credentials(self):
        return {
            'user_id': self.user_id_input.text(),
            'password': self.password_input.text(),
            'otp': self.otp_input.text()
        }
```

Usage in main.py:
```python
def _connect_broker(self):
    if config.get('broker.type') == 'shoonya':
        # Show login dialog
        dialog = ShoonyaLoginDialog()
        if dialog.exec_():
            credentials = dialog.get_credentials()
            self.broker.connect(
                server="Shoonya",
                username=credentials['user_id'],
                password=credentials['password']
            )
```

---

## Current Status

### ✅ Configuration File Ready
`config.yaml` now has a complete Shoonya section with:
- Authentication fields
- API endpoints
- Symbol settings
- Order defaults
- WebSocket config

### ⏳ Implementation Required
The Shoonya broker modules need to be implemented to **read** these credentials:

1. **Auth Module** (`brokers/shoonya/auth/totp_manager.py`):
   - Read credentials from config
   - Handle TOTP generation
   - Perform login API call

2. **Broker Class** (`brokers/shoonya/shoonya_broker.py`):
   - Update `connect()` method to use config values

---

## How to Use Right Now

### Step 1: Fill in Your Credentials
Edit `d:\pyqt_app\config.yaml`:

```yaml
shoonya:
  auth:
    user_id: "YOUR_USER_ID_HERE"
    password: "YOUR_PASSWORD_HERE"
    vendor_code: "YOUR_VENDOR_CODE"
    api_key: "YOUR_API_KEY"
```

### Step 2: Switch to Shoonya Broker
```yaml
broker:
  type: "shoonya"  # Change from "dummy"
```

### Step 3: Wait for Implementation
Currently, the Shoonya broker is a **skeleton** with placeholder methods. The actual implementation will:
1. Read these credentials from config
2. Authenticate with Shoonya API
3. Establish WebSocket connection
4. Enable live trading

---

## Security Best Practices

### ✅ DO:
- Use environment variables for production
- Encrypt sensitive config files
- Use TOTP instead of manual OTP
- Add `config.yaml` to `.gitignore`
- Use separate credentials for testing/production

### ❌ DON'T:
- Commit credentials to Git
- Share your API keys
- Hardcode passwords in code
- Use production credentials for testing
- Store passwords in plain text (use encryption)

---

## Example: Encrypted Credentials

For enhanced security, encrypt your credentials:

```python
# utils/encryption.py
from cryptography.fernet import Fernet
import base64

def encrypt_credential(value: str, key: bytes) -> str:
    """Encrypt a credential."""
    f = Fernet(key)
    return f.encrypt(value.encode()).decode()

def decrypt_credential(encrypted: str, key: bytes) -> str:
    """Decrypt a credential."""
    f = Fernet(key)
    return f.decrypt(encrypted.encode()).decode()

# Generate key once and store securely
# key = Fernet.generate_key()
```

---

## Testing Without Real Credentials

For development, keep using the **dummy broker**:

```yaml
broker:
  type: "dummy"  # Use dummy broker for testing
```

This allows you to:
- Test the UI
- Develop features
- Run without internet
- Avoid API rate limits
- No risk to real account

---

## Next Steps

1. **Immediate**: Fill in `config.yaml` with your credentials
2. **Short-term**: Implement Shoonya auth module to read config
3. **Medium-term**: Add login dialog for better UX
4. **Long-term**: Add credential encryption and vault

---

## Getting Help

- **Shoonya Support**: support@finvasia.com
- **API Docs**: https://shoonya.com/api-documentation
- **GitHub**: https://github.com/Shoonya-Dev/ShoonyaApi-py

---

## Summary

**Current Setup**:
```
config.yaml (Updated) ✅
  ↓
Shoonya credentials stored here
  ↓
broker.type = "shoonya"
  ↓
Application reads config (when implemented)
  ↓
Connects to Shoonya API
```

**You can enter credentials in `config.yaml` RIGHT NOW**, but the Shoonya broker implementation needs to be completed to actually use them for authentication.
