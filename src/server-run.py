import asyncio
import power_main
import reports_main
import datamgmt

TIME_POWER = 2 * 60 * 60 # every 2 hrs
TIME_REPORT = 4 * 60 * 60 + 20 # every 4 hrs and 20 secs (this is done to prevent accidental synchronisation causing lag spikes)

async def task_power():
    while True:
        # asyncio.to_thread offloads the blocking function to a separate thread,
        await asyncio.to_thread(power_main.main, True)
        datamgmt.save_memory_to_disk()         
        await asyncio.sleep(TIME_POWER)

async def task_reports():
    while True:
        await asyncio.to_thread(reports_main.main, True)
        datamgmt.save_memory_to_disk()
        await asyncio.sleep(TIME_REPORT)

async def main():
    # Explicitly turn on in-memory mode
    datamgmt.set_in_memory_mode(True)
    
    await asyncio.gather(
        task_power(),
        task_reports()
    )

try:
    asyncio.run(main())
except KeyboardInterrupt:
    print("Exiting")
    datamgmt.save_memory_to_disk() 