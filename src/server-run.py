import asyncio
import power_main
import reports_main
import datamgmt
from datetime import datetime
from time import sleep

TIME_POWER = 2 * 60 * 60 # every 2 hrs
TIME_REPORT = 4 * 60 * 60 + 20 # every 4 hrs and 20 secs (this is done to prevent accidental synchronisation causing lag spikes)
CAUTIOUS_MODE = True # Save data after every run, recommended
LOGGING_FILE = True
EXIT_ON_ERROR = False

async def task_power():
    while True:
        # asyncio.to_thread offloads the blocking function to a separate thread,
        await asyncio.to_thread(power_main.main, True)
        if CAUTIOUS_MODE:
            datamgmt.save_memory_to_disk()
        await asyncio.sleep(TIME_POWER)

async def task_reports():
    while True:
        await asyncio.to_thread(reports_main.main, True)
        if CAUTIOUS_MODE:
            datamgmt.save_memory_to_disk()
        await asyncio.sleep(TIME_REPORT)

async def main():
    # Explicitly turn on in-memory mode
    datamgmt.set_in_memory_mode(True)
    
    await asyncio.gather(
        task_power(),
        task_reports()
    )

def run():
    try:
        asyncio.run(main())

    except KeyboardInterrupt:
        print("Exiting")
        datamgmt.save_memory_to_disk() 
        exit(0)

    except Exception as e:
        print(f"ERROR: {e}")

        if EXIT_ON_ERROR:
            datamgmt.save_memory_to_disk() # minor chance of data corruption, might implement checking later
            exit(1)
        else:
            if LOGGING_FILE:
                try:
                    with open("logs.txt", 'a') as f:
                        f.write(f"[{datetime.now().strftime("%Y-%m-%d %H:%M:%S")}] ERROR: {e}\n")
                except Exception:
                    print("ERROR: Log file could not be accessed")
                    exit(1) # critical error
        
        sleep(60 * 5) # 5 mins

if __name__ == "__main__":
    print("Starting server...")
    print("Press Ctrl+C to stop.")
    while True:
        run()