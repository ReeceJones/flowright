
FIFO_POLL_DELAY = 0.01  # How many seconds to wait before polling the client-server communication pipes
RERENDER_DELAY = 0.0  # How many seconds to wait before triggering a rerender after the previous render completes
BUFFER_INPUT = False # If False, any change in input will trigger a rerender. If True, only button inputs can trigger a rerender.
AUTO_REFRESH = False  # If True, the page will be rerendered at a fixed interval. If False, only input changes can trigger a rerender.
AUTO_REFRESH_DELAY = 5.0  # If AUTO_REFRESH = True, how many seconds the renderer will wait before triggering a rerender.

THEME = 'bootstrap'  # The theme to use
