from dotenv import load_dotenv
import litellm, json, os


load_dotenv(dotenv_path=".env", override=True)


name = os.getenv("APP_NAME")
access_keys = json.loads(os.getenv("ACCESS_KEYS", "[]"))
origins = json.loads(os.getenv("ALLOWED_ORIGINS", "[]"))
rates = json.loads(os.getenv("RATE_LIMITS", "[]"))

litellm.success_callback = ["langfuse"]
litellm.failure_callback = ["langfuse"]
