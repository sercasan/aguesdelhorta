"""API for Aigües de l'Horta."""
import logging
import re
import requests
from datetime import datetime
from bs4 import BeautifulSoup

_LOGGER = logging.getLogger(__name__)

BASE_URL = "https://www.aigueshorta.es"
LOGIN_URL = f"{BASE_URL}/es/auth/local/login"
CONSUMO_URL = f"{BASE_URL}/es/group/aigues-de-l-horta/consumos"

class AiguesHortaAPI:
    """API Client for Aigües de l'Horta."""
    
    def __init__(self, username, password):
        """Initialize the API client."""
        self.username = username
        self.password = password
        self.session = requests.Session()
        self._contracts = None
        self._account_info = None
        self._consumption_data = None
        
    def login(self):
        """Login to the portal."""
        # First get the login page to obtain any CSRF token
        login_page = self.session.get(LOGIN_URL)
        login_page.raise_for_status()
        
        # Extract CSRF token from the page if needed
        soup = BeautifulSoup(login_page.text, 'html.parser')
        csrf_token = None
        for form_input in soup.find_all('input'):
            if form_input.get('name') == '_csrf' or form_input.get('name', '').lower().find('csrf') >= 0:
                csrf_token = form_input.get('value')
                break
                
        # Prepare login data
        login_data = {
            "username": self.username,
            "password": self.password,
        }
        
        # Add CSRF token if found
        if csrf_token:
            login_data["_csrf"] = csrf_token
            
        # Perform login
        login_response = self.session.post(
            LOGIN_URL, 
            data=login_data,
            headers={"Referer": LOGIN_URL}
        )
        login_response.raise_for_status()
        
        # Check if login was successful
        if "login" in login_response.url.lower():
            raise Exception("Login failed. Please check credentials.")
            
        _LOGGER.debug("Login successful to Aigües de l'Horta")
        return True
        
    def get_account_info(self):
        """Get account information."""
        if not self._account_info:
            profile_url = f"{BASE_URL}/es/group/aigues-de-l-horta/mi-perfil"
            response = self.session.get(profile_url)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Extract account information from the profile page
            # This is a simplified example - you'll need to adapt it to the actual HTML structure
            name_element = soup.find('div', class_='user-name') or soup.find('h1', class_='profile-name')
            name = name_element.text.strip() if name_element else self.username
            
            self._account_info = {
                "name": name,
            }
            
        return self._account_info
        
    def get_contracts(self):
        """Get list of contracts."""
        if not self._contracts:
            # Get contracts page
            contracts_url = f"{BASE_URL}/es/group/aigues-de-l-horta/contratos"
            response = self.session.get(contracts_url)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.text, 'html.parser')
            
            contracts = []
            # Find contract information (adapt this to the actual HTML structure)
            contract_elements = soup.find_all('div', class_='contract-item') or soup.find_all('div', class_='contract-card')
            
            for contract_element in contract_elements:
                contract_number = contract_element.find('span', class_='contract-number')
                address = contract_element.find('div', class_='contract-address')
                
                if contract_number and address:
                    contracts.append({
                        "contract_number": contract_number.text.strip(),
                        "address": address.text.strip(),
                    })
            
            self._contracts = contracts
            
        return self._contracts
        
    def get_consumption_data(self):
        """Get water consumption data."""
        # Navigate to the consumption page
        response = self.session.get(CONSUMO_URL)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Extract consumption data
        # This is a placeholder - you'll need to adapt it to the actual page structure
        consumption_data = {}
        
        # Try to find the main consumption value
        consumption_element = soup.find('div', class_='consumption-value') or soup.find('span', class_='consumption-current')
        if consumption_element:
            current_consumption = self._extract_number(consumption_element.text)
            consumption_data["current_consumption"] = current_consumption
        
        # Try to find last reading date
        date_element = soup.find('div', class_='reading-date') or soup.find('span', class_='last-reading')
        if date_element:
            reading_date_text = date_element.text.strip()
            # Extract date with regex or parsing
            date_match = re.search(r'(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})', reading_date_text)
            if date_match:
                consumption_data["last_reading_date"] = date_match.group(1)
        
        # Extract yearly consumption if available
        yearly_element = soup.find('div', class_='yearly-consumption')
        if yearly_element:
            yearly_consumption = self._extract_number(yearly_element.text)
            consumption_data["yearly_consumption"] = yearly_consumption
            
        # Get contract data if needed
        if not self._contracts:
            self.get_contracts()
            
        # Add contract info to consumption data
        if self._contracts and len(self._contracts) > 0:
            consumption_data.update(self._contracts[0])
            
        self._consumption_data = consumption_data
        return consumption_data
    
    def _extract_number(self, text):
        """Extract numeric value from text."""
        if not text:
            return None
            
        # Try to find numbers in the text
        match = re.search(r'(\d+(?:[.,]\d+)?)', text)
        if match:
            # Convert to float, handling both comma and dot as decimal separator
            number_str = match.group(1).replace(',', '.')
            try:
                return float(number_str)
            except ValueError:
                return None
                
        return None
