# from kasa.iot import IotStrip
# import asyncio

# async def get_device_children():
#     # Replace with your device's IP address
#     device_ip = "192.168.11.105"
#     strip = IotStrip(device_ip)

#     await strip.update()  # Update the device state

#     # List all children sockets and their energy usage
#     for index, child in enumerate(strip.children):
#         await child.update()  # Update the child state
#         is_energy_avail = child.has_emeter if child.has_emeter else 'Not Available'
#         energy_usage_precise = child.state_information.get('Current consumption', 'Not Available') if is_energy_avail else 'Not Available'
#         current = child.state_information.get('Current', 'Not Available')
#         voltage = child.state_information.get('Voltage', 'Not Available')
#         print(f"Child socket {index + 1}: {child.alias} - State: {'On' if child.is_on else 'Off'}, Energy Usage: {energy_usage_precise} W, Current: {current} A, Voltage: {voltage} V")

# asyncio.run(get_device_children())

from kasa.iot import IotStrip
import asyncio
import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation
from collections import defaultdict
from datetime import datetime
import numpy as np
import threading
from queue import Queue
import csv
import os

class EnergyMonitor:
    aliases = ["rpi3", "rpi4", "rpi5"]  # Names of the sockets to monitor
    def __init__(self, device_ip="192.168.11.105", max_points=60, csv_filename="energy_data.csv"):
        self.device_ip = device_ip
        self.strip = IotStrip(device_ip)
        self.max_points = max_points
        
        # CSV file setup
        self.csv_filename = csv_filename
        self.csv_file = None
        self.csv_writer = None
        self._init_csv()
        
        # Data storage for each socket
        self.power_data = defaultdict(list)
        self.current_data = defaultdict(list)
        self.voltage_data = defaultdict(list)
        self.timestamps = []
        
        # Queue for thread-safe data updates
        self.data_queue = Queue()
        self.running = True
    
    def _init_csv(self):
        """Initialize CSV file with headers"""
        file_exists = os.path.exists(self.csv_filename)
        self.csv_file = open(self.csv_filename, 'a', newline='')
        self.csv_writer = csv.writer(self.csv_file)
        
        # Write header if file is new
        if not file_exists:
            self.csv_writer.writerow(['Timestamp', 'Socket', 'Power (W)', 'Current (A)', 'Voltage (V)'])
            self.csv_file.flush()
    
    def _write_to_csv(self, timestamp, socket_name, power, current, voltage):
        """Write a single row to CSV"""
        try:
            self.csv_writer.writerow([timestamp, socket_name, power, current, voltage])
            self.csv_file.flush()
        except Exception as e:
            print(f"Error writing to CSV: {e}")
        
    async def _update_data_async(self):
        """Fetch the latest data from the device"""
        try:
            await self.strip.update()
            
            data = {}
            for child in self.strip.children:   
                if child.alias in self.aliases:
                    await child.update()
                    
                    if child.has_emeter:
                        power = child.state_information.get('Current consumption', 0)
                        current = child.state_information.get('Current', 0)
                        voltage = child.state_information.get('Voltage', 0)

                        data[child.alias] = {
                            'power': power,
                            'current': current,
                            'voltage': voltage
                        }
            
            self.data_queue.put(data)
                
        except Exception as e:
            print(f"Error updating data: {e}")
    
    def _run_async_loop(self):
        """Run the async event loop in a separate thread"""
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        async def periodic_update():
            while self.running:
                await self._update_data_async()
                await asyncio.sleep(1)
        
        loop.run_until_complete(periodic_update())
    
    def start_background_thread(self):
        """Start the data collection thread"""
        thread = threading.Thread(target=self._run_async_loop, daemon=True)
        thread.start()
    
    def get_latest_data(self):
            """Get the latest data from the queue and write to CSV"""
            try:
                while not self.data_queue.empty():
                    data = self.data_queue.get_nowait()
                    # Higher resolution timestamp: includes milliseconds
                    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
                    
                    for socket_name, values in data.items():
                        self.power_data[socket_name].append(values['power'])
                        self.current_data[socket_name].append(values['current'])
                        self.voltage_data[socket_name].append(values['voltage'])
                        
                        # Write to CSV
                        self._write_to_csv(timestamp, socket_name, values['power'], values['current'], values['voltage'])
                        
                        # Keep only the last max_points measurements
                        if len(self.power_data[socket_name]) > self.max_points:
                            self.power_data[socket_name].pop(0)
                            self.current_data[socket_name].pop(0)
                            self.voltage_data[socket_name].pop(0)
                    
                    self.timestamps.append(timestamp)
                    if len(self.timestamps) > self.max_points:
                        self.timestamps.pop(0)
            except:
                pass
        
    def close(self):
        """Close the CSV file"""
        if self.csv_file:
            self.csv_file.close()

def create_plots(monitor):
    """Create the figure with three subplots for real-time visualization"""
    fig, (ax1, ax2, ax3) = plt.subplots(3, 1, figsize=(12, 10))
    fig.suptitle('Real-time Energy Monitoring - TPLink HS300', fontsize=14, fontweight='bold')
    
    # Configure axes
    for ax in [ax1, ax2, ax3]:
        ax.set_xlim(0, monitor.max_points)
        ax.grid(True, alpha=0.3)
    
    ax1.set_ylabel('Power (W)')
    ax2.set_ylabel('Current (A)')
    ax3.set_ylabel('Voltage (V)')
    ax3.set_xlabel('Time (seconds)')
    
    # Store line objects for updating
    lines_power = {}
    lines_current = {}
    lines_voltage = {}
    
    legend_created = [False]  # Use list to allow modification in nested function
    
    # Create line objects for each socket (will be populated as data arrives)
    def init_lines():
        for socket_name in sorted(monitor.power_data.keys()):
            if socket_name not in lines_power:
                color = plt.cm.tab10(len(lines_power) % 10)
                lines_power[socket_name], = ax1.plot([], [], label=socket_name, color=color, marker='o', markersize=4)
                lines_current[socket_name], = ax2.plot([], [], label=socket_name, color=color, marker='o', markersize=4)
                lines_voltage[socket_name], = ax3.plot([], [], label=socket_name, color=color, marker='o', markersize=4)
        
        # Only create legend once after all lines are added
        if not legend_created[0] and lines_power:
            ax1.legend(loc='upper right', fontsize=9)
            ax2.legend(loc='upper right', fontsize=9)
            ax3.legend(loc='upper right', fontsize=9)
            legend_created[0] = True
    
    def update_plots(frame):
        """Update function for animation"""
        # Get latest data from queue
        monitor.get_latest_data()
        
        # Initialize lines if needed
        init_lines()
        
        # Update each socket's data
        for socket_name in sorted(monitor.power_data.keys()):
            if socket_name in lines_power:
                x_data = list(range(len(monitor.power_data[socket_name])))
                
                lines_power[socket_name].set_data(x_data, monitor.power_data[socket_name])
                lines_current[socket_name].set_data(x_data, monitor.current_data[socket_name])
                lines_voltage[socket_name].set_data(x_data, monitor.voltage_data[socket_name])
        
        # Auto-scale y-axes
        for ax in [ax1, ax2, ax3]:
            ax.relim()
            ax.autoscale_view()
        
        # Update title with timestamp
        if monitor.timestamps:
            fig.suptitle(f'Real-time Energy Monitoring - TPLink HS300 | Last update: {monitor.timestamps[-1]}', 
                        fontsize=14, fontweight='bold')
        
        return list(lines_power.values()) + list(lines_current.values()) + list(lines_voltage.values())
    
    # Create animation: update every 500ms to check queue
    ani = FuncAnimation(fig, update_plots, interval=500, blit=False, cache_frame_data=False)
    
    return fig, ani

def main():
    """Main function to initialize and run the monitor"""
    monitor = EnergyMonitor(device_ip="192.168.11.105", max_points=60, csv_filename="energy_data.csv")
    
    # Start background thread for data collection
    monitor.start_background_thread()
    
    # Create plots
    fig, ani = create_plots(monitor)
    plt.tight_layout()
    
    try:
        plt.show()
    finally:
        monitor.running = False
        monitor.close()  # Close CSV file gracefully

if __name__ == "__main__":
    main()