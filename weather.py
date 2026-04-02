# Open WeatherMaps History API
# https://home.openweathermap.org/api_keys
import requests

# Constants & Helper Fns -------------------------------------/
api_key = "73f942caf936d41a3cd62cede7f6eed6"
exclude = "current,minutely,daily,alerts"


def kelvin_to_celsius(k_in):
    return int(float(k_in) - 273.15)


def millibars_to_inches(mb_in):
    return round(float(mb_in) * 0.029529980, 2)


def centigrade_to_fahrenheit(c_in):
    return int((c_in * 9/5) + 32)


# Operational Functions -------------------------------------/
def get_weather_data(epoch, lat, lon):
    # current_url = f"https://api.openweathermap.org/data/3.0/onecall?lat={lat}&lon={lon}&exclude={exclude}&appid={api_key}"
    history_url = f"https://api.openweathermap.org/data/3.0/onecall/timemachine?lat={lat}&lon={lon}&dt={epoch}&appid={api_key}"

    r = requests.get(history_url)
    if r.status_code == 200:
        weather_data = r.json()["data"][0]
        weather_data["temp_c"] = kelvin_to_celsius(weather_data.pop("temp"))
        weather_data["temp_f"] = centigrade_to_fahrenheit(weather_data["temp_c"])
        weather_data.pop("feels_like")
        weather_data["dew_point"] = kelvin_to_celsius(weather_data.pop("dew_point"))
        weather_data["pressure_mb"] = weather_data["pressure"]
        weather_data["pressure_in"] = millibars_to_inches(weather_data.pop("pressure"))
        weather_data["condition_code"] = weather_data["weather"][0]["id"]
        weather_data["condition_desc"] = weather_data["weather"][0]["description"]
        weather_data.pop("weather")
        return weather_data
