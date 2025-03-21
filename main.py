# from fastapi import FastAPI

# from src.utils import call_ai
# from src.schemas import UserPrompt

# import random, time


# app = FastAPI()


# # @app.post("/prompt_ai")
# # async def prompt_ai(request: UserPrompt):

# #     # messages = []
# #     # messages.append({"role": "user", "content": request.prompt})

# #     # data = call_ai(messages, model="gpt-4o-mini")
# #     data = {"reply": f"test{random.randint(1, 100)}"}
# #     time.sleep(random.randint(1, 3))
# #     return data


# from fastapi.concurrency import run_in_threadpool


# @app.post("/prompt_ai")
# async def prompt_ai(request: UserPrompt):
#     # foo = lambda: call_ai([{"role": "user", "content": request.prompt}], model="gpt-4o-mini")

#     def foo():
#         time.sleep(random.randint(1, 3))
#         return {"reply": f"test{random.randint(1, 100)}"}

#     # Run blocking call_ai in a thread pool
#     data = await run_in_threadpool(foo)
#     return data
