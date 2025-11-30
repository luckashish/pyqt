"""
Shoonya Authentication Manager
Handles login and session management
"""
from typing import Optional, Dict
from NorenRestApiPy.NorenApi import NorenApi
from brokers.shoonya.auth.totp_manager import TOTPManager
from utils.config_manager import config
from utils.logger import logger


class ShoonyaAuthManager:
    """Manages Shoonya authentication and sessions."""
    
    def __init__(self):
        self.api: Optional[NorenApi] = None
        self.session_token: Optional[str] = None
        self.user_info: Optional[Dict] = None
        self.totp_manager = TOTPManager()
        
        # Get API URLs from config
        self.api_url = config.get('shoonya.api.base_url', 
                                   'https://api.shoonya.com/NorenWClientTP/')
        self.ws_url = config.get('shoonya.ws_url',
                                  'wss://api.shoonya.com/NorenWSTP/')
    
    def login(self, credentials: Dict) -> bool:
        """
        Login to Shoonya API.
        
        Args:
            credentials: Dictionary with username, password, etc.
            
        Returns:
            True if login successful
        """
        try:
            # Create API instance
            self.api = NorenApi(host=self.api_url, websocket=self.ws_url)
            
            # Get credentials from config
            user_id = config.get('shoonya.auth.user_id', credentials.get('username', ''))
            password = config.get('shoonya.auth.password', credentials.get('password', ''))
            vendor_code = config.get('shoonya.auth.vendor_code', '')
            api_key = config.get('shoonya.auth.api_key', '')
            imei = config.get('shoonya.auth.imei', 'auto')
            
            # Validate credentials
            if not all([user_id, password, vendor_code, api_key]):
                logger.error("Missing Shoonya credentials in config")
                return False
            
            # Get TOTP or prompt for OTP
            if self.totp_manager.is_configured():
                logger.info("Using TOTP for authentication")
                two_fa = self.totp_manager.generate_totp()
            else:
                logger.warning("TOTP not configured - you'll need to enter OTP manually")
                # In production, show a dialog to get OTP
                two_fa = input("Enter OTP from your authenticator app: ")
            
            # Attempt login
            logger.info(f"Logging in to Shoonya as {user_id}...")
            result = self.api.login(
                userid=user_id,
                password=password,
                twoFA=two_fa,
                vendor_code=vendor_code,
                api_secret=api_key,
                imei=imei
            )
            
            # Check result
            if result and result.get('stat') == 'Ok':
                self.session_token = result.get('susertoken')
                self.user_info = {
                    'user_id': result.get('uid'),
                    'user_name': result.get('uname'),
                    'account_id': result.get('actid')
                }
                logger.info(f"Successfully logged in as {self.user_info['user_name']}")
                logger.info(f"Account ID: {self.user_info['account_id']}")
                return True
            else:
                error_msg = result.get('emsg', 'Unknown error') if result else 'No response'
                logger.error(f"Login failed: {error_msg}")
                return False
                
        except Exception as e:
            logger.error(f"Login exception: {e}")
            return False
    
    def logout(self):
        """Logout from Shoonya."""
        try:
            if self.api:
                logger.info("Logging out from Shoonya")
                # Shoonya doesn't have explicit logout, session expires
                self.api = None
                self.session_token = None
                self.user_info = None
        except Exception as e:
            logger.error(f"Logout error: {e}")
    
    def is_session_valid(self) -> bool:
        """Check if current session is valid."""
        return self.api is not None and self.session_token is not None
    
    def get_api(self) -> Optional[NorenApi]:
        """Get the API instance."""
        return self.api
    
    def get_session_token(self) -> Optional[str]:
        """Get current session token."""
        return self.session_token
    
    def get_user_info(self) -> Optional[Dict]:
        """Get logged-in user information."""
        return self.user_info
