# weather_bot.py
import time
from typing import Optional, Dict, Any, List, Tuple
import httpx
import sys
from loguru import logger
from lxml import html
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes
from emoji_mappings import FORECA_EMOJI_MAPPINGS
from datetime import datetime
from dotenv import load_dotenv
import os

def configure_loguru():
	logger.remove()
	logger.add(sys.stderr)
	logger.add(
		"logs/weather_bot.log",
		retention="1 month",
		level="INFO",
		encoding="utf-8"
	)
	logger.add(
		"logs/weather_bot_errors.log",
		retention="1 month",
		level="ERROR",
		encoding="utf-8",
		backtrace=True,
		diagnose=True
	)

class WeatherBot:
	FORECA_BASE_URL = "https://api.foreca.net"
	FORECA_WEB_URL = "https://www.foreca.com"
	FORECA_LOCATION_ENDPOINT = "/data/location/{},{}.json"
	FORECA_WEATHER_ENDPOINT = "/data/recent/{}.json"
	FORECA_FAVOURITES_ENDPOINT = "/data/favorites/{}.json"
	FORECA_STATUS_DIV_XPATH = '(//div[@class="row wx"])[1]'
	DEFAULT_TIMEOUT = (3.9, 11)
	METERS_PER_SEC_TO_KMH_RATE= 3.6
	DAYS_TO_FORECAST = 3
	HELP_TEXT = """
Available commands:
/w <location> - Get current weather
/wf <location> - Get weather forecast
/help - Show this help message
	"""

	# Ignore commands older than this number of seconds
	OLD_MESSAGE_SECONDS_AGE = 60
	
	BROWSER_HEADERS = {
		"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
	}
	
	def __init__(self, telegram_token: str):
		logger.info("Initializing WeatherBot...")
		self.telegram_token = telegram_token
		self.http_client = httpx.Client(
			base_url=self.FORECA_BASE_URL,
			timeout=self.DEFAULT_TIMEOUT
		)
		self.web_client = httpx.Client(
			timeout=self.DEFAULT_TIMEOUT,
			headers=self.BROWSER_HEADERS
		)
		logger.info("WeatherBot initialized successfully")

	def get_location_by_coords(self, lat: float, lon: float) -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
		"""Get Foreca location data for given coordinates"""
		try:
			response = self.http_client.get(self.FORECA_LOCATION_ENDPOINT.format(lon, lat))
			response.raise_for_status()
			data = response.json()
			return data, data.get("id")
		except Exception as e:
			logger.error(f"Error getting location by coordinates: {e}")
			return None, None

	async def get_location(self, query: str, country_id: Optional[str] = None) -> Optional[Dict[str, Any]]:
		"""Get location data from Foreca API"""
		try:
			logger.info(f"Searching for location: {query}")
			params = {"limit": 30, "lang": "en"}
			if country_id:
				params["countryId"] = country_id
				
			response = self.http_client.get(
				f"/locations/search/{query}.json",
				params=params
			)
			response.raise_for_status()
			
			data = response.json()
			locations = data.get("results", [])
			if not locations:
				logger.warning(f"No locations found for query: {query}")
				return None
			
			best_location = self.get_best_location(locations)
			if best_location:
				logger.info(
					f"Found location: {best_location.get('name', 'Unknown')}, "
					f"{best_location.get('countryName', 'Unknown')} "
					f"(preference: {best_location.get('preference', 'Unknown')})"
				)
			return best_location
			
		except Exception as e:
			logger.error(f"Error getting location data: {e}")
			return None

	def build_foreca_web_url(self, location_data: Dict[str, Any]) -> Optional[str]:
		"""Build the Foreca webpage URL for a location"""
		try:
			loc_id = location_data.get("id")
			location_name = location_data.get("name", "").replace(' ', '-')
			if loc_id and location_name:
				return f"{self.FORECA_WEB_URL}/{loc_id}/{location_name}"
			return None
		except Exception as e:
			logger.error(f"Error building Foreca URL: {e}")
			return None

	def get_weather_summary(self, url: str) -> Optional[str]:
		"""Get the weather summary text from Foreca webpage"""
		try:
			response = self.web_client.get(url)
			response.raise_for_status()
			
			tree = html.fromstring(response.content)
			weather_div = tree.xpath(self.FORECA_STATUS_DIV_XPATH)
			
			if weather_div:
				summary = weather_div[0].text_content().strip()
				logger.info(f"Successfully found weather summary: {summary}")
				return summary
			else:
				logger.warning("No weather summary div found on page")
				return None
				
		except Exception as e:
			logger.error(f"Error getting weather summary: {e}")
			return None
		
	def get_best_location(self, locations: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
		"""
		Get the most relevant location from a list of locations.
		Lower preference number means higher preference.
		Ignores locations with preference=0 unless it's the only result.
		"""
		if not locations:
			return None
			
		# If only one result, use it regardless of preference
		if len(locations) == 1:
			return locations[0]
			
		# Filter out locations with preference=0 or None
		valid_locations = [
			loc for loc in locations 
			if loc.get("preference") is not None and loc.get("preference") > 0
		]
		
		# If no valid locations after filtering, use the first result
		if not valid_locations:
			logger.warning("No locations with valid preference found, using first result")
			return locations[0]
		
		# Find location with lowest preference number (highest preference)
		def get_preference(location: Dict[str, Any]) -> int:
			# We know preference exists and is > 0 due to our filter above
			return location["preference"]
		
		return min(valid_locations, key=get_preference)
		

	def format_weather_response(self, location: Dict[str, Any], current: Dict[str, Any], summary: Optional[str]) -> str:
		"""Format the weather response string"""
		if not current:
			return "No weather data available"
		
		location_name = location.get("name", "Unknown Location")
		country_name = location.get("countryName", "Unknown Country")
		
		# Get current temperature
		temp = current.get("temp")
		temp_str = f"{temp}°C" if temp is not None else "Temperature unavailable"
		feels_like = current.get("flike")
		if feels_like is not None and feels_like != temp:
			temp_str += f" (feels like {feels_like}°C)"
		
		humidity = current.get("rhum")
		humidity_str = f"{humidity}%" if humidity is not None else "Humidity unavailable"
		
		rain_prob = current.get("rainp")
		rain_str = f"{rain_prob}% chance of rain" if rain_prob is not None else "Rain probability unavailable"
		
		wind_speed = current.get("winds")
		wind_gusts = current.get("maxwind")
		if wind_speed is not None:
			wind_speed_kmh = wind_speed * self.METERS_PER_SEC_TO_KMH_RATE
			wind_str = f"{wind_speed_kmh:.1f} km/h"
			if wind_gusts is not None and wind_gusts > wind_speed:
				wind_gusts_kmh = wind_gusts * self.METERS_PER_SEC_TO_KMH_RATE
				wind_str += f" (gusting to {wind_gusts_kmh:.1f} km/h)"
		else:
			wind_str = "Wind speed unavailable"
		
		symbol = current.get("symb", "")
		conditions = FORECA_EMOJI_MAPPINGS.get(symbol, "❓")
		
		response = (
			f"Weather for {location_name}, {country_name}:\n"
			f"Temperature: {temp_str}\n"
			f"Conditions: {conditions}\n"
			f"Humidity: {humidity_str}\n"
			f"Wind: {wind_str}\n"
			f"Precipitation: {rain_str}"
		)
		
		if summary:
			response += f"\n\nSummary: {summary}"
			
		web_url = self.build_foreca_web_url(location)
		if web_url:
			response += f"\n\nMore details: {web_url}"
			
		return response

	def format_forecast_response(self, location: Dict[str, Any], forecast_data: List[Dict[str, Any]]) -> str:
		"""Format the weather forecast response string"""
		if not forecast_data:
			return "No weather forecast data available"

		location_name = f"{location.get('name', 'Unknown')}, {location.get('countryName', 'Unknown')}"
		forecast_response = f"3-day Forecast for {location_name}:\n"

		for i, day in enumerate(forecast_data):
			date_str = day.get('date', 'Unknown date')
			date_obj = datetime.strptime(date_str, '%Y-%m-%d')  # Assuming date is in 'YYYY-MM-DD' format
			
			day_name = date_obj.strftime('%A')
			if i == 0:
				day_name += " (today)"

			tmin = day.get('tmin', 'N/A')
			tmax = day.get('tmax', 'N/A')
			conditions = FORECA_EMOJI_MAPPINGS.get(day.get('symb', ''), '❓')
			rainp = day.get('rainp', 0)
			rain_str = f"{rainp}% chance of rain" if rainp > 0 else ""

			forecast_response += (
				f"\n{day_name} - {conditions}  {tmin}°C - {tmax}°C"
				f"{' (currently ' + str(day.get('tmax', 'N/A')) + '°C)' if i == 0 else ''}"
				f"   {rain_str}"
			)

		return forecast_response

	async def start(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
		"""Send a message when the command /start is issued."""
		user = update.effective_user
		logger.info(f"Start command received from user {user.id} ({user.first_name})")
		await update.message.reply_text("Welcome to the Weather Bot! Type /help for commands.")

	async def help(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
		"""Send a message when the command /help is issued."""
		user = update.effective_user
		logger.info(f"Help command received from user {user.id} ({user.first_name})")
		
		await update.message.reply_text(self.HELP_TEXT)

	async def weather(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
		"""Handle the weather command"""
		if (time.time() - update.message.date.timestamp()) > self.OLD_MESSAGE_SECONDS_AGE:
			logger.warning(f"Skipping old message: {update.message.text}")
			return

		query = " ".join(context.args)
		if not query:
			await update.message.reply_text("Please provide a location. Example: /w London")
			return

		user = update.effective_user
		logger.info(f"Weather request for '{query}' from user {user.id} ({user.first_name})")
		
		try:
			location = await self.get_location(query)
			if not location:
				await update.message.reply_text(f"Could not find location: {query}")
				return

			location_id = location.get("id")
			if not location_id:
				raise ValueError("Location ID not found")
				
			# Get weather data
			logger.info(f"Getting weather data for location ID: {location_id}")
			
			weather_url = f"{self.FORECA_WEATHER_ENDPOINT.format(location_id)}"
			logger.debug(f"Weather URL: {weather_url}")
			
			weather_response = self.http_client.get(weather_url)
			weather_response.raise_for_status()
			
			weather_data = weather_response.json()
			logger.debug(f"Weather data response: {weather_data}")
			
			# Extract the current weather for this location
			current_weather = weather_data.get(str(location_id))
			if not current_weather:
				raise ValueError("No weather data found for this location")
			
			# Get web summary
			web_url = self.build_foreca_web_url(location)
			summary = None
			if web_url:
				logger.info(f"Getting weather summary from: {web_url}")
				summary = self.get_weather_summary(web_url)
			
			response = self.format_weather_response(location, current_weather, summary)
			logger.info(f"Sending weather response for {location.get('name', 'Unknown')}")
			await update.message.reply_text(response, disable_web_page_preview=True)
			
		except Exception as e:
			logger.error(f"Error getting weather data: {e}", exc_info=True)
			await update.message.reply_text("Sorry, there was an error getting the weather data")

	async def weather_forecast(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
		"""Handle the weather forecast command"""
		if (time.time() - update.message.date.timestamp()) > self.OLD_MESSAGE_SECONDS_AGE:
			logger.warning(f"Skipping old message: {update.message.text}")
			return

		query = " ".join(context.args)
		if not query:
			await update.message.reply_text("Please provide a location. Example: /w London")
			return

		user = update.effective_user
		logger.info(f"Weather request for '{query}' from user {user.id} ({user.first_name})")

		try:
			location = await self.get_location(query)
			if not location:
				await update.message.reply_text(f"Could not find location: {query}")
				return

			location_id = location.get("id")
			if not location_id:
				raise ValueError("Location ID not found")
				
			# Get weather data
			logger.info(f"Getting weather data for location ID: {location_id}")
			
			weather_url = f"{self.FORECA_FAVOURITES_ENDPOINT.format(location_id)}"
			logger.debug(f"Weather forecast URL: {weather_url}")
			
			weather_response = self.http_client.get(weather_url)
			weather_response.raise_for_status()
			
			weather_data = weather_response.json()
			logger.debug(f"Weather forecast data response: {weather_data}")
			
			# Extract the forecast for the first 3 days
			forecast_data = weather_data.get(str(location_id), [])[:self.DAYS_TO_FORECAST]
			if not forecast_data:
				raise ValueError("No weather data forecast found for this location")
			
			# Format the forecast response
			forecast_response = self.format_forecast_response(location, forecast_data)

			logger.info(f"Sending weather forecast response for {location.get('name', 'Unknown')}")
			await update.message.reply_text(forecast_response)
			
		except Exception as e:
			logger.error(f"Error getting weather data: {e}", exc_info=True)
			await update.message.reply_text("Sorry, there was an error getting the weather data")

	def run(self) -> None:
		"""Run the bot."""
		try:
			logger.info("Starting weather bot...")
			print("Starting weather bot... Check the logs for details.")
			
			application = Application.builder().token(self.telegram_token).build()

			application.add_handler(CommandHandler("start", self.start))
			application.add_handler(CommandHandler("help", self.help))
			application.add_handler(CommandHandler("w", self.weather))
			application.add_handler(CommandHandler("weather", self.weather))
			application.add_handler(CommandHandler("wf", self.weather_forecast))
			application.add_handler(CommandHandler("forecast", self.weather_forecast))

			logger.info("Starting polling...")
			application.run_polling()
			
		except Exception as e:
			logger.error(f"Failed to start bot: {e}")
			raise

if __name__ == '__main__':
	configure_loguru()
	load_dotenv()

	# Get the token from environment variables
	TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")

	if not TELEGRAM_BOT_TOKEN:
		logger.error("TELEGRAM_BOT_TOKEN environment variable is not set or is empty. Check your .env file.")
		sys.exit(1)

	try:
		bot = WeatherBot(TELEGRAM_BOT_TOKEN)
		bot.run()
	except Exception as e:
		logger.exception(f"Fatal error in main: {e}")