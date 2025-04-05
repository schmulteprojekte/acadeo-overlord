from dotenv import load_dotenv
import litellm, json, os


load_dotenv(dotenv_path=".env", override=True)


access_keys = json.loads(os.getenv("ACCESS_KEYS"))

litellm.success_callback = ["langfuse"]
litellm.failure_callback = ["langfuse"]
