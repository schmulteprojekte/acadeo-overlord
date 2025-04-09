from dotenv import load_dotenv
import litellm, json, os


load_dotenv(dotenv_path=".env", override=True)


access_keys = json.loads(os.getenv("ACCESS_KEYS", "[]"))
origins = json.loads(os.getenv("ALLOWED_ORIGINS", "[]"))

rates = ["3/second", "60/minute", "3000/day"]

litellm.success_callback = ["langfuse"]
litellm.failure_callback = ["langfuse"]
