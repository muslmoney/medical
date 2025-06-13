
No error handlers are registered, logging exception.
Traceback (most recent call last):
  File "/home/ergash/medical/venv/lib/python3.12/site-packages/telegram/ext/_application.py", line 1298, in process_update
    await coroutine
  File "/home/ergash/medical/venv/lib/python3.12/site-packages/telegram/ext/_handlers/basehandler.py", line 158, in handle_update
    return await self.callback(update, context)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/home/ergash/medical/venv/bot.py", line 152, in handle_answer
    context.user_data["step"] += 1
    ~~~~~~~~~~~~~~~~~^^^^^^^^
KeyError: 'step'
No error handlers are registered, logging exception.
Traceback (most recent call last):
  File "/home/ergash/medical/venv/lib/python3.12/site-packages/telegram/ext/_application.py", line 1298, in process_update
    await coroutine
  File "/home/ergash/medical/venv/lib/python3.12/site-packages/telegram/ext/_handlers/basehandler.py", line 158, in handle_update
    return await self.callback(update, context)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/home/ergash/medical/venv/bot.py", line 152, in handle_answer
    context.user_data["step"] += 1
    ~~~~~~~~~~~~~~~~~^^^^^^^^
KeyError: 'step'
