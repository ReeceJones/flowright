# flowright
## Get Started
```python
import flowright as flow

# initialize databases, read files, etc.

while flow.running():
    flow.text("Hello world!")

    with flow.column():
        flow.text("Column 1")
    with flow.column():
        flow.text("Column 2")
        selection = flow.selectbox(["a", "b", "c"])
        flow.text(selection)
    with flow.column():
        flow.text("Column 3")
        resp = flow.button("Click me!")
        if resp:
            flow.text("button pressed!")
    
    flow.divider()

    flow.text("Look at this cool image!")

    flow.image("https://picsum.photos/500/300")

    flow.graph(plt.plot(list(range(10)), list(range(10))))  # soon maybe

    flow.divider()

    flow.text("And now look at this cool table!")
    for row in flow.table(range(5)):
        for col in flow.columns(range(5)):
            if (row + col) % 2 == 0:
                flow.text("Fizz")
            else:
                flow.button("Buzz")

# clean up


```