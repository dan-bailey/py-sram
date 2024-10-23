# py-sram
Connecting to SRAM AXS components and reading data from them in real-time.
Currently operating with:
* SRAM Force AXS
* Wahoo Trackr HRM
* Quarq Power Meter

## why?
Why the fuck not?  Honestly, I did this to see if I could.  Exploring and playing are a huge part of learning and this was a great way to undertake that.

## how-to

**Installation:**

```pip install requirements.txt```
This will install all your necessary python libraries.

**Running the App:**
```python app.py```
Will run the app with the text interface on-screen in the terminal, and will run the API on port 8080.

## options
```--no-text``` will surpress the text display and only run the API
```--no-api``` will skip running the API portion of this
```--port <number>``` will run the API access on a specific port number (do not put the brackets around the number)

## API interface
```/get``` will pull the immediate data from the sensors as JSON formatted data; may want to set this up to do rolling 3-second averages, too. TBD.
