import asyncio
import time
from bambu_connect import BambuClient, PrinterStatus


class PrinterMonitor:
    def __init__(self, hostname, access_code, serial):
        """Initialize with printer's hostname, LAN code and serial."""
        self.client = BambuClient(hostname, access_code, serial)
        self.monitoring_task = None
        self._running = False

    async def connect(self):
        """Connect to printer."""
        try:

            await self.client.start_watch_client(
                self._on_status,
                self._on_connect)

            print(f"Connected to printer at {self.printer_ip}")

        except Exception as e:
            print(f"Failed to connect to printer: {e}")
            self.client = None

    def _printer_state_listener(self):
        """Blocking function that listens to printer state changes."""
        while self._running:
            try:
                # Use lock to ensure thread-safe access to the printer client
                with self._lock:
                    if self.client:
                        # Assuming get_status() returns a PrinterStatus object
                        printer_status = self.client.get_status()

                        # Process the printer status
                        self._on_status(printer_status)
            except Exception as e:
                print(f"Error while monitoring printer state: {e}")
            time.sleep(1)  # Polling interval

    def _on_status(self, status: PrinterStatus):
        """Handle the incoming printer status."""
        print(f"Printer status: {
              status}")  # Adjust as per the actual status details

    async def start_monitoring(self):
        """Start monitoring the printer state in a separate thread."""
        if not self.client:
            await self.connect()

        if not self._running:
            self._running = True
            # Use asyncio.to_thread to run the blocking printer state listener in the background
            self.monitoring_task = asyncio.to_thread(
                self._printer_state_listener)

            await self.monitoring_task  # Awaiting the thread for async compatibility

    async def stop_monitoring(self):
        """Stop monitoring the printer state."""
        if self._running:
            self._running = False
            if self.monitoring_task:
                await self.monitoring_task


# Example usage of the PrinterStateMonitor

# async def main():
#     printer_ip = "192.168.1.100"  # Example printer IP
#     printer_monitor = PrinterStateMonitor(printer_ip)

#     # Start the monitoring (runs in a separate thread)
#     await printer_monitor.start_monitoring()

#     # Simulate the rest of your application running
#     await asyncio.sleep(10)

#     # Stop the monitoring
#     await printer_monitor.stop_monitoring()


# if __name__ == "__main__":
#     # Run the asyncio event loop
#     asyncio.run(main())
