"""API for Aigües de l'Horta using Direct API Call."""
import logging
import re
import requests
import json
from datetime import datetime, timedelta, date
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlencode
import locale

# Home Assistant specific exceptions
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers.update_coordinator import UpdateFailed

_LOGGER = logging.getLogger(__name__)

BASE_URL = "https://www.aigueshorta.es"
LOGIN_URL = f"{BASE_URL}/login"
# URL de la página HTML principal de consumos (para obtener p_auth fresco)
CONSUMO_PAGE_URL = f"{BASE_URL}/es/group/aigues-de-l-horta/mis-consumos"
# URL directa de la API JSON de consumo horario (es la misma base URL)
HOURLY_API_URL = f"{BASE_URL}/es/group/aigues-de-l-horta/mis-consumos"

class AiguesHortaAPI:
    """API Client for Aigües de l'Horta (Direct API Call Method)."""

    def __init__(self, username, password):
        """Initialize the API client."""
        self.username = username
        self.password = password
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/98.0.4758.102 Safari/537.36',
            'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7', # Default for page load
            'accept-language': 'es-ES,es;q=0.9',
        })
        self._account_info = None
        self._contracts = None
        self._p_auth_token_login = None # Store token extracted during login

        # Set locale
        try: locale.setlocale(locale.LC_TIME, 'es_ES.UTF-8')
        except locale.Error:
            try: locale.setlocale(locale.LC_TIME, 'es_ES')
            except locale.Error: _LOGGER.warning("Could not set Spanish locale.")


    def login(self):
        """Login to the portal and extract initial p_auth token."""
        _LOGGER.debug("Attempting login process for user: %s", self.username)
        try:
            _LOGGER.debug("Step 1: GET request to login page: %s", LOGIN_URL)
            login_page = self.session.get(LOGIN_URL, timeout=30)
            login_page.raise_for_status()
        except requests.exceptions.RequestException as err:
            _LOGGER.error("Login page GET failed: %s", err)
            raise ConfigEntryAuthFailed(f"Failed to retrieve login page: {err}") from err

        soup = BeautifulSoup(login_page.text, 'html.parser')
        login_form = soup.find('form', {'id': 'loginForm'})
        if not login_form: raise ConfigEntryAuthFailed("Login form not found.")

        action_url = login_form.get('action')
        if not action_url: raise ConfigEntryAuthFailed("Login form 'action' URL not found.")

        p_auth_match = re.search(r'[?&]p_auth=([^&]+)', action_url)
        if p_auth_match: self._p_auth_token_login = p_auth_match.group(1)
        else:
            p_auth_input = login_form.find('input', {'name': 'p_auth', 'type': 'hidden'})
            if p_auth_input and p_auth_input.get('value'): self._p_auth_token_login = p_auth_input['value']
        if self._p_auth_token_login: _LOGGER.info("Extracted initial p_auth token: %s", self._p_auth_token_login)
        else: _LOGGER.warning("Could not extract initial p_auth token during login.")

        if not action_url.startswith('http'): action_url = urljoin(LOGIN_URL, action_url)
        hidden_fields = { inp.get('name'): inp.get('value', '') for inp in login_form.find_all('input', type='hidden') if inp.get('name') }
        login_data = { "_CustomLoginPortlet_login": self.username, "_CustomLoginPortlet_password": self.password, **hidden_fields }

        try:
            _LOGGER.debug("Step 4: POST request to login action URL: %s", action_url)
            login_response = self.session.post( action_url, data=login_data, headers={"Referer": LOGIN_URL}, timeout=30, allow_redirects=True )
            _LOGGER.debug("Login POST completed. Status: %s, Final URL: %s", login_response.status_code, login_response.url)
            login_response.raise_for_status()
        except requests.exceptions.RequestException as err:
            _LOGGER.error("Login POST request failed: %s", err)
            raise ConfigEntryAuthFailed(f"Login POST request failed: {err}") from err

        final_url_lower = login_response.url.lower()
        if "login" in final_url_lower or "error" in final_url_lower or "claveacceso" in final_url_lower or "signin" in final_url_lower:
            _LOGGER.error("Login failed detected. Final URL: %s", login_response.url)
            raise ConfigEntryAuthFailed("Login failed. Invalid credentials or login error.")

        _LOGGER.info("Redirected after login POST: %s", login_response.url)
        _LOGGER.debug("Cookies after login: %s", self.session.cookies.items())
        _LOGGER.info("Login successful for user %s", self.username)
        return True


    def _find_fresh_p_auth(self, soup):
        """Helper to find p_auth token within a BeautifulSoup object, prioritizing scripts."""
        _LOGGER.debug("Searching for fresh p_auth token in page content...")
        scripts = soup.find_all('script')
        for script in scripts: # 1. Check scripts
            if script.string:
                match = re.search(r'p_auth=([a-zA-Z0-9]+)[&\s\'"]', script.string)
                if match: token = match.group(1); _LOGGER.info("Found p_auth in SCRIPT: %s", token); return token
        portlet_div = soup.find(id=re.compile(r'p_p_id_MisConsumos', re.I)) or soup
        forms = portlet_div.find_all('form') # 2. Check forms
        for form in forms:
            action = form.get('action', ''); match = re.search(r'[?&]p_auth=([^&]+)', action)
            if match: token = match.group(1); _LOGGER.info("Found p_auth in form action: %s", token); return token
            hidden = form.find('input', {'name': 'p_auth', 'type': 'hidden'})
            if hidden and hidden.get('value'): token = hidden['value']; _LOGGER.info("Found p_auth in form hidden: %s", token); return token
        links = portlet_div.find_all('a', href=True) # 3. Check links
        for link in links:
            match = re.search(r'[?&]p_auth=([^&]+)', link['href'])
            if match: token = match.group(1); _LOGGER.info("Found p_auth in link: %s", token); return token
        hidden = soup.find('input', {'name': 'p_auth', 'type': 'hidden'}) # 4. Check global hidden
        if hidden and hidden.get('value'): token = hidden['value']; _LOGGER.info("Found p_auth in global hidden: %s", token); return token
        _LOGGER.warning("Could not find a fresh p_auth token in page content.")
        return None


    def get_consumption_data(self, days_back=2):
        """Fetches consumption data by calling the direct hourly API endpoint."""

        # --- Step 1: Load Consumption Page HTML to find fresh p_auth ---
        _LOGGER.debug("Loading consumption page HTML for fresh p_auth: %s", CONSUMO_PAGE_URL)
        fresh_p_auth_token = None
        try:
            page_headers = self.session.headers.copy()
            page_headers['accept'] = 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8'
            if 'X-Requested-With' in page_headers: del page_headers['X-Requested-With']

            _LOGGER.debug("Cookies before loading consumption page: %s", self.session.cookies.items())
            response_page = self.session.get(CONSUMO_PAGE_URL, headers=page_headers, timeout=30, allow_redirects=True)
            _LOGGER.debug("Consumption page GET status: %s, final URL: %s", response_page.status_code, response_page.url)
            if "login" in response_page.url.lower(): raise UpdateFailed("Session expired (consumption page redirect).")
            response_page.raise_for_status()

            page_soup = BeautifulSoup(response_page.text, 'html.parser')
            fresh_p_auth_token = self._find_fresh_p_auth(page_soup)

        except requests.exceptions.RequestException as err:
             _LOGGER.error("Error loading consumption page HTML %s: %s", CONSUMO_PAGE_URL, err)
             _LOGGER.warning("Proceeding without fresh p_auth token.")
        except UpdateFailed as err: raise err
        except Exception as err:
             _LOGGER.exception("Error parsing consumption page HTML: %s", err)
             _LOGGER.warning("Proceeding without fresh p_auth token.")

        api_p_auth_token = fresh_p_auth_token or self._p_auth_token_login
        if not api_p_auth_token: raise UpdateFailed("Missing p_auth token, cannot call API.")
        _LOGGER.info("Using p_auth token for API call.")

        # --- Step 2: Prepare API Parameters ---
        end_date_str = date.today().strftime("%d/%m/%Y")
        start_date_str = (date.today() - timedelta(days=days_back)).strftime("%d/%m/%Y")
        params = {
            'p_p_id': 'MisConsumos', 'p_p_lifecycle': '2', 'p_p_state': 'normal', 'p_p_mode': 'view',
            'p_p_cacheability': 'cacheLevelPage', 'p_auth': api_p_auth_token,
            '_MisConsumos_op': 'buscarConsumosHoraria', '_MisConsumos_fechaInicio': start_date_str,
            '_MisConsumos_fechaFin': end_date_str, '_MisConsumos_inicio': '0', '_MisConsumos_fin': '200'
        }
        _LOGGER.debug("Calling API: %s", HOURLY_API_URL)
        _LOGGER.debug("API Params (p_auth hidden): %s", {k: v for k, v in params.items() if k != 'p_auth'})

        # --- Step 3: Call the API ---
        try:
            api_headers = self.session.headers.copy()
            api_headers['accept'] = 'application/json, text/javascript, */*; q=0.01'
            api_headers['X-Requested-With'] = 'XMLHttpRequest'
            api_headers['Referer'] = CONSUMO_PAGE_URL

            _LOGGER.debug("Cookies before API call: %s", self.session.cookies.items())
            response_api = self.session.get(HOURLY_API_URL, params=params, headers=api_headers, timeout=45)
            _LOGGER.debug("API response status: %s", response_api.status_code)

            if "login" in response_api.url.lower(): raise UpdateFailed("Session expired (API redirect).")
            if response_api.status_code == 401: raise UpdateFailed("Authorization error (401) calling API.")
            response_api.raise_for_status()

            # --- Step 4: Parse the JSON Response ---
            try: data = response_api.json()
            except json.JSONDecodeError as err:
                 _LOGGER.error("API response not JSON: %s", err); _LOGGER.debug("API Text: %s", response_api.text[:500])
                 raise UpdateFailed(f"API response not valid JSON: {err}")

            # --- Step 5: Process the JSON Data ---
            hourly_consumption_values = {}
            latest_reading = None
            latest_reading_datetime = None
            if "consumos" in data and isinstance(data["consumos"], list):
                _LOGGER.debug("Processing %d entries from API.", len(data["consumos"]))
                for entry in data["consumos"]:
                    if not isinstance(entry, dict): continue
                    fecha_str = entry.get("fechaConsumo"); hora_str = entry.get("horaConsumo")
                    consumo_str = entry.get("consumo"); lectura_str = entry.get("lectura")
                    if fecha_str and hora_str:
                        iso_timestamp = self._combine_date_hour_spanish(fecha_str, hora_str)
                        if iso_timestamp:
                            consumption_val = self._extract_number(consumo_str)
                            if consumption_val is not None: hourly_consumption_values[iso_timestamp] = consumption_val
                            reading_val = self._extract_number(lectura_str)
                            if reading_val is not None:
                                try:
                                    current_dt = datetime.fromisoformat(iso_timestamp)
                                    if latest_reading_datetime is None or current_dt >= latest_reading_datetime:
                                         latest_reading_datetime = current_dt; latest_reading = reading_val
                                except: pass
                _LOGGER.info("Parsed %d hourly points.", len(hourly_consumption_values))
            else: _LOGGER.warning("API JSON missing 'consumos' list.")

            # --- Prepare final data structure ---
            result_data = {
                "current_consumption": latest_reading,
                "last_reading_date": latest_reading_datetime.strftime('%Y-%m-%d') if latest_reading_datetime else None,
                "hourly_consumption": hourly_consumption_values,
                "contract_number": None, "address": None,
            }

            # --- Add Optional Contract Info ---
            try:
                contracts = self.get_contracts()
                if contracts:
                    result_data["contract_number"] = contracts[0].get("contract_number")
                    result_data["address"] = contracts[0].get("address")
            except Exception as contract_err: _LOGGER.warning("Could not get contract info: %s", contract_err)

            return result_data

        except requests.exceptions.RequestException as err:
             _LOGGER.error("Error calling API %s: %s", HOURLY_API_URL, err)
             raise UpdateFailed(f"Error calling API: {err}") from err
        except UpdateFailed as err: raise err
        except Exception as err:
             _LOGGER.exception("Unexpected error processing API data: %s", err)
             raise UpdateFailed(f"Error processing API data: {err}") from err


    # --- Optional get_contracts and _extract_contract_details ---
    def get_contracts(self):
        """Get list of contracts (optional, for attributes)."""
        if self._contracts is not None: return self._contracts
        self._contracts = []
        contracts_url = f"{BASE_URL}/es/group/aigues-de-l-horta/contratos"
        _LOGGER.debug("Fetching contracts (optional) from URL: %s", contracts_url)
        try:
            response = self.session.get(contracts_url, timeout=20, allow_redirects=True)
            if "login" in response.url.lower(): _LOGGER.warning("Session expired (contracts)."); return self._contracts
            response.raise_for_status()
            soup = BeautifulSoup(response.text, 'html.parser')
            contracts = []
            contract_containers = soup.select('div.contract-item, div.contract-summary, div.contract-card, li.contract, article.contrato, div[class*="contract"], div[class*="contrato"], div[class*="poliza"]')
            if not contract_containers:
                label_elements = soup.find_all(string=re.compile(r'N(?:º|umero)\s*d?e?\s*(?:Contrato|Póliza)', re.I))
                contract_containers = list({elem.find_parent(['div', 'li', 'article', 'section', 'tr']) for elem in label_elements if elem.parent})
            processed_numbers = set()
            for container in contract_containers:
                contract_data = self._extract_contract_details(container)
                number = contract_data.get("contract_number")
                if number and number not in processed_numbers:
                    contracts.append(contract_data); processed_numbers.add(number)
                    _LOGGER.info("Extracted contract: Number=%s", number)
            if not contracts: _LOGGER.warning("Failed to extract contracts from: %s", contracts_url)
            self._contracts = contracts
            return self._contracts
        except requests.exceptions.RequestException as err: _LOGGER.error("HTTP Error fetching contracts: %s", err); return self._contracts
        except Exception as err: _LOGGER.exception("Error parsing contracts page: %s", err); return self._contracts

    def _extract_contract_details(self, container):
        """Helper to extract number and address from a contract container."""
        if not container: return {}
        contract_data = {"contract_number": None, "address": None}
        container_text = container.get_text(" ", strip=True)
        number = None; number_match = re.search(r'N(?:º|umero)\s*d?e?\s*(?:Contrato|Póliza)\s*[:\-]?\s*(\d+)', container_text, re.I)
        if number_match: number = number_match.group(1)
        else:
            possible_numbers = re.findall(r'\b(\d{6,12})\b', container_text); number = next((n for n in possible_numbers if len(n) != 5), None) if possible_numbers else None
            if not number:
                 for attr_name, attr_val in container.attrs.items():
                     if 'contract' in attr_name.lower() or 'poliza' in attr_name.lower():
                         if isinstance(attr_val, str) and attr_val.isdigit() and len(attr_val) >= 6: number = attr_val; break
        contract_data["contract_number"] = number
        address = None; address_match = re.search(r'(?:Dirección|Ubicación|Emplazamiento|Localización)\s*Suministro?\s*[:\-]?\s*(.+)', container_text, re.IGNORECASE | re.DOTALL)
        if address_match: address_raw = address_match.group(1).strip(); address = re.split(r'\n|\s+(?:Población|CP|Teléfono|Móvil|Titular):', address_raw, maxsplit=1)[0].strip()
        elif container.find(class_=re.compile(r'address|direccion|ubicacion', re.I)): address_element = container.find(class_=re.compile(r'address|direccion|ubicacion', re.I)); address = address_element.get_text(" ", strip=True)
        contract_data["address"] = address
        return contract_data


    # --- Helper functions _combine_date_hour_spanish, _extract_number ---
    def _combine_date_hour_spanish(self, fecha_str, hora_str):
        """ Combines 'DD mon YYYY' and 'HH:MM' into ISO 'YYYY-MM-DDTHH:MM:SS' """
        try:
            parsed_date = None; fecha_str_cleaned = str(fecha_str).strip()
            try: # 1. Try locale parse
                 current_locale = locale.getlocale(locale.LC_TIME)[0]
                 if current_locale and 'es' in current_locale.lower(): parsed_date = datetime.strptime(fecha_str_cleaned, '%d %b %Y').date()
            except ValueError: pass
            except Exception as locale_err: _LOGGER.warning("Locale parse error: %s", locale_err)

            if not parsed_date: # 2. Fallback manual map
                 _LOGGER.debug("Attempting manual Spanish month mapping for '%s'", fecha_str_cleaned)
                 month_map = {'ene':'01','feb':'02','mar':'03','abr':'04','may':'05','jun':'06','jul':'07','ago':'08','sep':'09','oct':'10','nov':'11','dic':'12'}
                 match = re.match(r'(\d{1,2})\s+([a-záéíóú]+)\s+(\d{4})', fecha_str_cleaned, re.I)
                 if match:
                     day, month_str, year = match.groups(); month = month_map.get(month_str.lower()[:3])
                     if not month: month = month_map.get(month_str.lower())

                     # *** CORRECTED SYNTAX ***
                     if month:
                         try:
                             parsed_date = date(int(year), int(month), int(day.zfill(2)))
                         except ValueError:
                             _LOGGER.warning("Invalid date components parsed via regex: Day=%s, Month=%s(%s), Year=%s", day, month_str, month, year)
                             pass # parsed_date remains None
                     # *** END CORRECTION ***
                     else: _LOGGER.warning("Could not map Spanish month name: '%s'", month_str)

            if not parsed_date: _LOGGER.error("Failed date parse: '%s'", fecha_str); return None
            parsed_time = None; hora_str_cleaned = str(hora_str).strip()
            if hora_str_cleaned:
                 time_match = re.match(r'(\d{1,2}):(\d{2})', hora_str_cleaned)
                 if time_match: hour, minute = map(int, time_match.groups()); parsed_time = timedelta(hours=hour, minutes=minute)
            if not parsed_time: _LOGGER.warning("Bad time format: '%s', using 00:00", hora_str); parsed_time = timedelta()
            dt_obj = datetime.combine(parsed_date, datetime.min.time()) + parsed_time
            return dt_obj.isoformat(timespec='seconds')
        except Exception as e: _LOGGER.error(f"Error combining date '{fecha_str}', hour '{hora_str}': {e}"); return None


    def _extract_number(self, text):
        """ Extract numeric value, handling comma/dot decimals """
        if text is None: return None
        text_to_parse = str(text).strip();
        if not text_to_parse: return 0.0
        text_to_parse = re.sub(r'[€$£¥\s]|m[³3]|L', '', text_to_parse, flags=re.I)
        if ',' in text_to_parse and '.' in text_to_parse:
             if text_to_parse.rfind('.') < text_to_parse.rfind(','): text_to_parse = text_to_parse.replace('.', '')
        text_to_parse = text_to_parse.replace(',', '.')
        match = re.search(r'([-+]?\d+\.?\d*|\.\d+)', text_to_parse)
        if match:
            try: return float(match.group(1))
            except ValueError: pass
        _LOGGER.debug("Could not extract number from: '%s' (cleaned: '%s')", text, text_to_parse); return None

# --- END OF FILE aigues_horta_api.py ---
