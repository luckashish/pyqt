"""
Shoonya TOTP Manager
Handles TOTP generation for automatic authentication
"""
import pyotp
from utils.config_manager import config
from utils.logger import logger


class TOTPManager:
    """Manages TOTP generation for Shoonya authentication."""
    
    def __init__(self):
        self.totp_enabled = config.get('shoonya.auth.totp_enabled', False)
        self.totp_key = config.get('shoonya.auth.totp_key', '')
    
    def generate_totp(self) -> str:
        """
        Generate TOTP code.
        
        Returns:
            6-digit TOTP code
            
        Raises:
            ValueError: If TOTP is not configured
        """
        if not self.totp_enabled:
            raise ValueError("TOTP is not enabled in configuration")
        
        if not self.totp_key:
            raise ValueError("TOTP key is not configured")
        
        try:
            totp = pyotp.TOTP(self.totp_key)
            code = totp.now()
            logger.debug(f"Generated TOTP code: {code}")
            return code
        except Exception as e:
            logger.error(f"Failed to generate TOTP: {e}")
            raise
    
    def is_configured(self) -> bool:
        """Check if TOTP is properly configured."""
        return self.totp_enabled and bool(self.totp_key)
