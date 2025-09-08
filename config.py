from dotenv import load_dotenv
import litellm, json, os


load_dotenv(dotenv_path=".env", override=True)


name = os.getenv("APP_NAME", "overlord")
origins = json.loads(os.getenv("ALLOWED_ORIGINS", "[]"))
access_keys = json.loads(os.getenv("ACCESS_KEYS", "[]"))

if not access_keys:
    raise ValueError("No access keys are set!")

rate_limits_default = json.loads(os.getenv("RATE_LIMITS_DEFAULT", "[]"))
rate_limits_high = json.loads(os.getenv("RATE_LIMITS_HIGH", "[]"))

if not rate_limits_default:
    raise ValueError("No default rate limits are set!")
if not rate_limits_high:
    rate_limits_high = rate_limits_default

rates = {
    "default": rate_limits_default,
    "high-usage": rate_limits_high,
}


litellm.success_callback = ["langfuse"]
litellm.failure_callback = ["langfuse"]
# litellm._turn_on_debug()
