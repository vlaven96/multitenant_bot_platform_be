# event_loop_manager.py
import asyncio
import threading

_background_loop = None

def get_or_create_event_loop():
    """
    Returns the background event loop, creating one if needed.
    Runs forever in a daemon thread so we can schedule tasks
    from synchronous code without 'no running event loop' errors.
    """
    global _background_loop
    if _background_loop is None:
        _background_loop = asyncio.new_event_loop()
        t = threading.Thread(target=_background_loop.run_forever, daemon=True)
        t.start()
    return _background_loop
